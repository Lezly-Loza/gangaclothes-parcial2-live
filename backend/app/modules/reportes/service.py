"""Reportes y dashboard (CU19).

Solo cuentan las ventas PAGADAS: un carrito o una venta pendiente todavia no es
ingreso. Las fechas de la base estan en UTC; los reportes se piden y se agrupan
en hora de Bolivia (UTC-4, sin horario de verano).

La ganancia de una linea es lo cobrado (precio de lista menos descuento) menos
el costo de la prenda por la cantidad. El costo es el actual de la prenda: el
modelo no guarda costo historico por venta.

Los calculos se hacen en Python y no en SQL a proposito: el volumen de una
tienda es chico y asi el mismo codigo corre igual en SQLite y en PostgreSQL.
"""
import csv
import io
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.fechas import a_bolivia, texto_bolivia, utc_iso
from app.models.catalogo import Categoria, Color, Prenda, Talla, Variante
from app.models.inventario import Compra, Inventario, MovimientoInventario
from app.models.sucursales import Sucursal
from app.models.usuarios import Usuario
from app.models.ventas import DetalleVenta, Pago, Reserva, Venta
from app.modules.promociones import service as promociones

DESFASE = timedelta(hours=4)          # UTC -> Bolivia
CANALES = ("caja", "web", "movil")
AGRUPACIONES = {"dia", "semana", "mes"}
DIAS_POR_DEFECTO = 30


# ------------------------------------------------------------- utilidades
def _f(valor) -> float:
    return round(float(valor or 0), 2)


def _local(fecha: datetime | None) -> datetime | None:
    """Instante UTC de la base -> hora de Bolivia, para agrupar por dia e imprimir."""
    return a_bolivia(fecha)


def periodo(desde: date | None, hasta: date | None) -> tuple[date, date]:
    hoy = promociones.hoy_bolivia()
    hasta = hasta or hoy
    desde = desde or (hasta - timedelta(days=DIAS_POR_DEFECTO - 1))
    if desde > hasta:
        raise HTTPException(400, "La fecha 'desde' no puede ser posterior a 'hasta'")
    if (hasta - desde).days > 731:
        raise HTTPException(400, "El periodo maximo de un reporte es de dos anos")
    return desde, hasta


def _limites_utc(desde: date, hasta: date) -> tuple[datetime, datetime]:
    """[inicio, fin) en UTC del rango de dias bolivianos [desde, hasta]."""
    return (datetime.combine(desde, time.min) + DESFASE,
            datetime.combine(hasta + timedelta(days=1), time.min) + DESFASE)


def _validar_filtros(db: Session, sucursal_id: int | None, canal: str | None) -> None:
    if sucursal_id is not None and db.get(Sucursal, sucursal_id) is None:
        raise HTTPException(404, "La sucursal no existe")
    if canal is not None and canal not in CANALES:
        raise HTTPException(400, f"Canal invalido. Use uno de: {', '.join(CANALES)}")


def _clave_periodo(dia: date, agrupar: str) -> tuple[str, str]:
    """(clave ordenable, etiqueta legible)"""
    if agrupar == "mes":
        return dia.strftime("%Y-%m"), dia.strftime("%m/%Y")
    if agrupar == "semana":
        lunes = dia - timedelta(days=dia.weekday())
        return lunes.isoformat(), f"Semana del {lunes.strftime('%d/%m/%Y')}"
    return dia.isoformat(), dia.strftime("%d/%m/%Y")


# --------------------------------------------------------- lectura de ventas
def _ventas_pagadas(db: Session, desde: date, hasta: date, sucursal_id: int | None = None,
                    canal: str | None = None) -> list[dict]:
    """Ventas pagadas del periodo, cada una con sus lineas ya valorizadas."""
    inicio, fin = _limites_utc(desde, hasta)
    consulta = db.query(Venta).filter(Venta.estado == "pagada", Venta.fecha >= inicio, Venta.fecha < fin)
    if sucursal_id:
        consulta = consulta.filter(Venta.sucursal_id == sucursal_id)
    if canal:
        consulta = consulta.filter(Venta.canal == canal)
    ventas = consulta.order_by(Venta.fecha, Venta.id).all()
    if not ventas:
        return []

    ids = [v.id for v in ventas]
    lineas = defaultdict(list)
    filas = (
        db.query(DetalleVenta, Variante, Prenda)
        .join(Variante, Variante.id == DetalleVenta.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .filter(DetalleVenta.venta_id.in_(ids))
        .all()
    )
    for d, v, p in filas:
        neto = Decimal(str(d.subtotal or 0))
        costo = Decimal(str(p.costo or 0)) * d.cantidad
        lineas[d.venta_id].append({
            "prenda_id": p.id, "prenda": p.nombre, "categoria_id": p.categoria_id,
            "cantidad": d.cantidad, "descuento": Decimal(str(d.descuento or 0)),
            "neto": neto, "costo": costo, "ganancia": neto - costo,
        })

    sucursales = {s.id: s.nombre for s in db.query(Sucursal).all()}
    salida = []
    for v in ventas:
        ls = lineas[v.id]
        salida.append({
            "id": v.id,
            # `fecha` en hora de Bolivia (agrupar e imprimir); `fecha_utc` es el
            # instante que viaja por la API, para que cada cliente lo muestre en su hora.
            "fecha": _local(v.fecha),
            "fecha_utc": v.fecha,
            "nro_comprobante": v.nro_comprobante,
            "sucursal_id": v.sucursal_id,
            "sucursal": sucursales.get(v.sucursal_id, f"#{v.sucursal_id}"),
            "canal": v.canal,
            "subtotal": Decimal(str(v.subtotal or 0)),
            "descuento": Decimal(str(v.descuento or 0)),
            # CU29: `venta.total` incluye el costo del envio a domicilio, que el
            # cliente paga pero NO es venta de mercaderia: es el servicio de
            # reparto. Los reportes miden lo vendido en prendas, asi que se
            # descuenta; si no, el margen saldria inflado en las compras con
            # delivery. En retiro en sucursal el costo es 0 y no cambia nada.
            "total": Decimal(str(v.total or 0)) - Decimal(str(v.costo_envio or 0)),
            "unidades": sum(l["cantidad"] for l in ls),
            "costo": sum((l["costo"] for l in ls), Decimal("0")),
            "ganancia": sum((l["ganancia"] for l in ls), Decimal("0")),
            "lineas": ls,
        })
    return salida


def _acumular(grupos: dict, clave, etiqueta: str, venta: dict) -> None:
    g = grupos.setdefault(clave, {"clave": clave, "etiqueta": etiqueta, "ventas": 0, "unidades": 0,
                                  "subtotal": Decimal("0"), "descuento": Decimal("0"),
                                  "total": Decimal("0"), "ganancia": Decimal("0")})
    g["ventas"] += 1
    g["unidades"] += venta["unidades"]
    for campo in ("subtotal", "descuento", "total", "ganancia"):
        g[campo] += venta[campo]


def _cerrar(grupos: dict, total_general: Decimal | None = None, ordenar_por_total: bool = False) -> list[dict]:
    filas = []
    for g in grupos.values():
        fila = {**g, "subtotal": _f(g["subtotal"]), "descuento": _f(g["descuento"]),
                "total": _f(g["total"]), "ganancia": _f(g["ganancia"]),
                "ticket_promedio": _f(g["total"] / g["ventas"]) if g["ventas"] else 0.0,
                "margen_porcentaje": _f(g["ganancia"] * 100 / g["total"]) if g["total"] else 0.0}
        if total_general is not None:
            fila["participacion"] = _f(g["total"] * 100 / total_general) if total_general else 0.0
        filas.append(fila)
    if ordenar_por_total:
        filas.sort(key=lambda f: -f["total"])
    else:
        filas.sort(key=lambda f: str(f["clave"]))
    return filas


def _totales(ventas: list[dict]) -> dict:
    total = sum((v["total"] for v in ventas), Decimal("0"))
    ganancia = sum((v["ganancia"] for v in ventas), Decimal("0"))
    unidades = sum(v["unidades"] for v in ventas)
    return {
        "ventas": len(ventas),
        "unidades": unidades,
        "subtotal": _f(sum((v["subtotal"] for v in ventas), Decimal("0"))),
        "descuento": _f(sum((v["descuento"] for v in ventas), Decimal("0"))),
        "total": _f(total),
        "costo": _f(sum((v["costo"] for v in ventas), Decimal("0"))),
        "ganancia": _f(ganancia),
        "ticket_promedio": _f(total / len(ventas)) if ventas else 0.0,
        "margen_porcentaje": _f(ganancia * 100 / total) if total else 0.0,
        "ganancia_por_unidad": _f(ganancia / unidades) if unidades else 0.0,
    }


# ------------------------------------------------------ margen por prenda
def margen(db: Session, desde: date | None = None, hasta: date | None = None,
           sucursal_id: int | None = None) -> dict:
    """Ganancia por prenda: la de catalogo (precio_venta - costo) y la realizada
    en las ventas del periodo. El promedio es el indicador que pide el enunciado."""
    desde, hasta = periodo(desde, hasta)
    _validar_filtros(db, sucursal_id, None)
    ventas = _ventas_pagadas(db, desde, hasta, sucursal_id)

    vendido = defaultdict(lambda: {"unidades": 0, "ingreso": Decimal("0"), "ganancia": Decimal("0"),
                                   "descuento": Decimal("0")})
    for v in ventas:
        for l in v["lineas"]:
            a = vendido[l["prenda_id"]]
            a["unidades"] += l["cantidad"]
            a["ingreso"] += l["neto"]
            a["ganancia"] += l["ganancia"]
            a["descuento"] += l["descuento"]

    categorias = {c.id: c.nombre for c in db.query(Categoria).all()}
    prendas = db.query(Prenda).filter(Prenda.activo.isnot(False)).order_by(Prenda.nombre).all()
    vigentes = promociones.vigentes_por_prenda(db, [p.id for p in prendas])

    filas = []
    for p in prendas:
        precio, costo = Decimal(str(p.precio_venta)), Decimal(str(p.costo))
        ganancia = precio - costo
        calculo = promociones.aplicar(precio, vigentes.get(p.id))
        v = vendido[p.id]
        filas.append({
            "prenda_id": p.id,
            "prenda": p.nombre,
            "categoria": categorias.get(p.categoria_id),
            "publicado": bool(p.publicado),
            "precio_venta": _f(precio),
            "costo": _f(costo),
            "ganancia_unitaria": _f(ganancia),
            "margen_porcentaje": _f(ganancia * 100 / precio) if precio else 0.0,
            "promocion": calculo["promocion"].nombre if calculo["promocion"] else None,
            "precio_con_promocion": _f(calculo["precio_final"]),
            "ganancia_con_promocion": _f(calculo["precio_final"] - costo),
            "unidades_vendidas": v["unidades"],
            "ingreso": _f(v["ingreso"]),
            "descuento_otorgado": _f(v["descuento"]),
            "ganancia_realizada": _f(v["ganancia"]),
        })

    n = len(filas)
    unidades = sum(f["unidades_vendidas"] for f in filas)
    ganancia_total = sum(f["ganancia_realizada"] for f in filas)
    ordenadas = sorted(filas, key=lambda f: f["ganancia_unitaria"])
    resumen = {
        "prendas": n,
        # El indicador del enunciado: promedio simple de (precio_venta - costo).
        "ganancia_promedio_por_prenda": _f(sum(f["ganancia_unitaria"] for f in filas) / n) if n else 0.0,
        "margen_promedio_porcentaje": _f(sum(f["margen_porcentaje"] for f in filas) / n) if n else 0.0,
        # Lo que de verdad dejo cada unidad vendida (con descuentos ya restados).
        "ganancia_promedio_por_unidad_vendida": _f(ganancia_total / unidades) if unidades else 0.0,
        "unidades_vendidas": unidades,
        "ganancia_realizada": _f(ganancia_total),
        "mayor_ganancia": ordenadas[-1]["prenda"] if ordenadas else None,
        "menor_ganancia": ordenadas[0]["prenda"] if ordenadas else None,
    }
    return {"periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
            "sucursal_id": sucursal_id, "resumen": resumen, "prendas": filas}


# ---------------------------------------------------------------- ventas
def ventas(db: Session, desde: date | None = None, hasta: date | None = None,
           sucursal_id: int | None = None, canal: str | None = None, agrupar: str = "dia") -> dict:
    desde, hasta = periodo(desde, hasta)
    _validar_filtros(db, sucursal_id, canal)
    if agrupar not in AGRUPACIONES:
        raise HTTPException(400, f"Agrupacion invalida. Use una de: {', '.join(sorted(AGRUPACIONES))}")
    lista = _ventas_pagadas(db, desde, hasta, sucursal_id, canal)
    total = sum((v["total"] for v in lista), Decimal("0"))

    por_periodo, por_sucursal, por_canal, cruce = {}, {}, {}, {}
    for v in lista:
        clave, etiqueta = _clave_periodo(v["fecha"].date(), agrupar)
        _acumular(por_periodo, clave, etiqueta, v)
        _acumular(por_sucursal, v["sucursal_id"], v["sucursal"], v)
        _acumular(por_canal, v["canal"], v["canal"], v)
        _acumular(cruce, f"{v['sucursal']}|{v['canal']}", f"{v['sucursal']} · {v['canal']}", v)

    return {
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "filtros": {"sucursal_id": sucursal_id, "canal": canal, "agrupar": agrupar},
        "totales": _totales(lista),
        "por_periodo": _cerrar(por_periodo, total),
        "por_sucursal": _cerrar(por_sucursal, total, ordenar_por_total=True),
        "por_canal": _cerrar(por_canal, total, ordenar_por_total=True),
        "por_sucursal_y_canal": _cerrar(cruce, total),
        "ventas": [{
            "id": v["id"], "fecha": utc_iso(v["fecha_utc"]), "nro_comprobante": v["nro_comprobante"],
            "sucursal": v["sucursal"], "canal": v["canal"], "unidades": v["unidades"],
            "subtotal": _f(v["subtotal"]), "descuento": _f(v["descuento"]), "total": _f(v["total"]),
            "ganancia": _f(v["ganancia"]),
        } for v in reversed(lista)],
    }


# ------------------------------------------------------------- inventario
def inventario(db: Session, desde: date | None = None, hasta: date | None = None,
               sucursal_id: int | None = None) -> dict:
    """Foto del stock de hoy (valorizado a costo y a precio de venta) y los
    movimientos del periodo."""
    desde, hasta = periodo(desde, hasta)
    _validar_filtros(db, sucursal_id, None)

    consulta = (
        db.query(Inventario, Variante, Prenda, Sucursal)
        .join(Variante, Variante.id == Inventario.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Sucursal, Sucursal.id == Inventario.sucursal_id)
        .filter(Prenda.activo.isnot(False), Variante.activo.isnot(False))
    )
    if sucursal_id:
        consulta = consulta.filter(Inventario.sucursal_id == sucursal_id)

    por_prenda, por_sucursal = {}, {}
    for inv, _v, p, s in consulta.all():
        disponible = inv.cantidad - inv.cantidad_reservada
        bajo = disponible <= (inv.stock_minimo or 0)
        costo = Decimal(str(p.costo or 0)) * inv.cantidad
        venta = Decimal(str(p.precio_venta or 0)) * inv.cantidad
        for grupo, clave, base in (
            (por_prenda, (p.id, s.id), {"prenda_id": p.id, "prenda": p.nombre, "sucursal_id": s.id,
                                        "sucursal": s.nombre}),
            (por_sucursal, s.id, {"sucursal_id": s.id, "sucursal": s.nombre}),
        ):
            g = grupo.setdefault(clave, {**base, "variantes": 0, "unidades": 0, "reservadas": 0,
                                         "disponibles": 0, "bajo_minimo": 0, "sin_stock": 0,
                                         "valor_costo": Decimal("0"), "valor_venta": Decimal("0")})
            g["variantes"] += 1
            g["unidades"] += inv.cantidad
            g["reservadas"] += inv.cantidad_reservada
            g["disponibles"] += disponible
            g["bajo_minimo"] += 1 if bajo else 0
            g["sin_stock"] += 1 if disponible <= 0 else 0
            g["valor_costo"] += costo
            g["valor_venta"] += venta

    def cerrar(filas):
        return [{**f, "valor_costo": _f(f["valor_costo"]), "valor_venta": _f(f["valor_venta"])} for f in filas]

    stock = cerrar(sorted(por_prenda.values(), key=lambda f: (f["prenda"], f["sucursal"])))
    sucursales = cerrar(sorted(por_sucursal.values(), key=lambda f: f["sucursal"]))

    # ---- movimientos del periodo
    inicio, fin = _limites_utc(desde, hasta)
    mq = (
        db.query(MovimientoInventario, Variante, Prenda, Talla, Color, Sucursal)
        .join(Variante, Variante.id == MovimientoInventario.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .join(Sucursal, Sucursal.id == MovimientoInventario.sucursal_id)
        .filter(MovimientoInventario.fecha >= inicio, MovimientoInventario.fecha < fin)
    )
    if sucursal_id:
        mq = mq.filter(MovimientoInventario.sucursal_id == sucursal_id)
    filas_mov = mq.order_by(MovimientoInventario.fecha.desc(), MovimientoInventario.id.desc()).all()

    usuarios = {u.id: " ".join(filter(None, [u.nombre, u.apellido])) for u in db.query(Usuario).all()}
    por_tipo = {}
    movimientos = []
    for m, v, p, t, c, s in filas_mov:
        g = por_tipo.setdefault(m.tipo, {"tipo": m.tipo, "movimientos": 0, "unidades": 0})
        g["movimientos"] += 1
        g["unidades"] += m.cantidad
        movimientos.append({
            "id": m.id, "fecha": utc_iso(m.fecha), "tipo": m.tipo,
            "sku": v.sku, "prenda": p.nombre, "talla": t.nombre, "color": c.nombre,
            "sucursal": s.nombre, "cantidad": m.cantidad, "motivo": m.motivo,
            "usuario": usuarios.get(m.usuario_id),
        })

    return {
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "sucursal_id": sucursal_id,
        "totales": {
            "unidades": sum(f["unidades"] for f in sucursales),
            "reservadas": sum(f["reservadas"] for f in sucursales),
            "disponibles": sum(f["disponibles"] for f in sucursales),
            "bajo_minimo": sum(f["bajo_minimo"] for f in sucursales),
            "sin_stock": sum(f["sin_stock"] for f in sucursales),
            "valor_costo": _f(sum(f["valor_costo"] for f in sucursales)),
            "valor_venta": _f(sum(f["valor_venta"] for f in sucursales)),
        },
        "por_sucursal": sucursales,
        "stock": stock,
        "movimientos_por_tipo": sorted(por_tipo.values(), key=lambda f: f["tipo"]),
        "movimientos": movimientos,
    }


# -------------------------------------------------------------- dashboard
def dashboard(db: Session, desde: date | None = None, hasta: date | None = None,
              sucursal_id: int | None = None) -> dict:
    desde, hasta = periodo(desde, hasta)
    _validar_filtros(db, sucursal_id, None)
    lista = _ventas_pagadas(db, desde, hasta, sucursal_id)
    totales = _totales(lista)

    # Mismo largo de periodo, inmediatamente anterior: para la variacion.
    dias = (hasta - desde).days + 1
    anterior = _totales(_ventas_pagadas(db, desde - timedelta(days=dias), desde - timedelta(days=1), sucursal_id))
    variacion = (_f((totales["total"] - anterior["total"]) * 100 / anterior["total"])
                 if anterior["total"] else None)

    # Serie diaria completa: los dias sin ventas van en cero para que el grafico no mienta.
    por_dia = {(desde + timedelta(days=i)).isoformat(): {"fecha": (desde + timedelta(days=i)).isoformat(),
                                                           "ventas": 0, "total": Decimal("0"),
                                                           "ganancia": Decimal("0")}
               for i in range(dias)}
    por_canal, por_sucursal, por_categoria, por_prenda = {}, {}, {}, {}
    categorias = {c.id: c.nombre for c in db.query(Categoria).all()}
    total = sum((v["total"] for v in lista), Decimal("0"))
    for v in lista:
        d = por_dia[v["fecha"].date().isoformat()]
        d["ventas"] += 1
        d["total"] += v["total"]
        d["ganancia"] += v["ganancia"]
        _acumular(por_canal, v["canal"], v["canal"], v)
        _acumular(por_sucursal, v["sucursal_id"], v["sucursal"], v)
        for l in v["lineas"]:
            for grupo, clave, etiqueta in (
                (por_categoria, l["categoria_id"], categorias.get(l["categoria_id"], "Sin categoria")),
                (por_prenda, l["prenda_id"], l["prenda"]),
            ):
                g = grupo.setdefault(clave, {"clave": clave, "etiqueta": etiqueta, "unidades": 0,
                                             "total": Decimal("0"), "ganancia": Decimal("0")})
                g["unidades"] += l["cantidad"]
                g["total"] += l["neto"]
                g["ganancia"] += l["ganancia"]

    def cerrar_lineas(grupo, limite=None):
        filas = sorted(grupo.values(), key=lambda g: -g["total"])[:limite]
        return [{**g, "total": _f(g["total"]), "ganancia": _f(g["ganancia"]),
                 "participacion": _f(g["total"] * 100 / total) if total else 0.0} for g in filas]

    # ---- pagos por metodo
    metodos = {}
    if lista:
        por_venta = {v["id"]: v["total"] for v in lista}
        for pg in (db.query(Pago).filter(Pago.estado == "exitoso",
                                         Pago.venta_id.in_(list(por_venta))).all()):
            g = metodos.setdefault(pg.metodo, {"metodo": pg.metodo, "pagos": 0, "total": Decimal("0")})
            g["pagos"] += 1
            # Se suma el total de la venta y no lo recibido: el efectivo incluye el cambio.
            g["total"] += por_venta[pg.venta_id]

    # ---- reservas del periodo
    inicio, fin = _limites_utc(desde, hasta)
    rq = db.query(Reserva).filter(Reserva.fecha_creacion >= inicio, Reserva.fecha_creacion < fin)
    if sucursal_id:
        rq = rq.filter(Reserva.sucursal_id == sucursal_id)
    reservas = defaultdict(int)
    for r in rq.all():
        reservas[r.estado] += 1
    activas = db.query(Reserva).filter(Reserva.estado.in_(["pendiente", "preparada"]))
    if sucursal_id:
        activas = activas.filter(Reserva.sucursal_id == sucursal_id)

    # ---- estado actual (no depende del periodo)
    foto = inventario(db, desde, hasta, sucursal_id)["totales"]
    ganancias = margen(db, desde, hasta, sucursal_id)["resumen"]
    compras = db.query(Compra).filter(Compra.estado == "pendiente")
    if sucursal_id:
        compras = compras.filter(Compra.sucursal_id == sucursal_id)
    hoy = promociones.hoy_bolivia()
    vigentes = sum(1 for p in promociones.listar(db) if p["estado"] == "vigente")

    return {
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "dias": dias,
                    "hoy": hoy.isoformat()},
        "sucursal_id": sucursal_id,
        "indicadores": {
            **totales,
            "total_periodo_anterior": anterior["total"],
            "variacion_porcentaje": variacion,
            "ganancia_promedio_por_prenda": ganancias["ganancia_promedio_por_prenda"],
            "margen_promedio_porcentaje": ganancias["margen_promedio_porcentaje"],
            "prendas_activas": ganancias["prendas"],
            "reservas_activas": activas.count(),
            "alertas_stock": foto["bajo_minimo"],
            "unidades_en_stock": foto["unidades"],
            "valor_inventario_costo": foto["valor_costo"],
            "valor_inventario_venta": foto["valor_venta"],
            "compras_pendientes": compras.count(),
            "promociones_vigentes": vigentes,
        },
        "ventas_por_dia": [{**d, "total": _f(d["total"]), "ganancia": _f(d["ganancia"])}
                           for d in por_dia.values()],
        "por_canal": _cerrar(por_canal, total, ordenar_por_total=True),
        "por_sucursal": _cerrar(por_sucursal, total, ordenar_por_total=True),
        "por_categoria": cerrar_lineas(por_categoria),
        "top_prendas": cerrar_lineas(por_prenda, 5),
        "metodos_pago": sorted(({**m, "total": _f(m["total"])} for m in metodos.values()),
                               key=lambda m: -m["total"]),
        "reservas_por_estado": [{"estado": e, "reservas": n} for e, n in sorted(reservas.items())],
    }


# ----------------------------------------------------------- exportacion
def _celda(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "si" if valor else "no"
    if isinstance(valor, float):
        # Excel en espanol espera coma decimal y punto y coma como separador.
        return f"{valor:.2f}".replace(".", ",")
    return str(valor)


def a_csv(titulo: str, secciones: list[tuple[str, list[str], list[list]]]) -> bytes:
    """Un CSV con varias tablas, una debajo de la otra, que Excel abre directo."""
    salida = io.StringIO()
    w = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    w.writerow([titulo])
    for nombre, columnas, filas in secciones:
        w.writerow([])
        w.writerow([nombre.upper()])
        w.writerow(columnas)
        for fila in filas:
            w.writerow([_celda(c) for c in fila])
    # BOM: sin el, Excel muestra mal los acentos.
    return ("﻿" + salida.getvalue()).encode("utf-8")


def csv_ventas(r: dict) -> bytes:
    p, t = r["periodo"], r["totales"]
    cols = ["Ventas", "Unidades", "Subtotal (Bs)", "Descuento (Bs)", "Total (Bs)", "Ganancia (Bs)",
            "Ticket promedio (Bs)", "Margen %"]

    def fila(g):
        return [g["ventas"], g["unidades"], g["subtotal"], g["descuento"], g["total"], g["ganancia"],
                g["ticket_promedio"], g["margen_porcentaje"]]

    return a_csv(f"GangaClothes - Reporte de ventas del {p['desde']} al {p['hasta']}", [
        ("Totales", cols, [fila(t)]),
        ("Por periodo", ["Periodo", *cols], [[g["etiqueta"], *fila(g)] for g in r["por_periodo"]]),
        ("Por sucursal", ["Sucursal", *cols], [[g["etiqueta"], *fila(g)] for g in r["por_sucursal"]]),
        ("Por canal", ["Canal", *cols], [[g["etiqueta"], *fila(g)] for g in r["por_canal"]]),
        ("Por sucursal y canal", ["Sucursal y canal", *cols],
         [[g["etiqueta"], *fila(g)] for g in r["por_sucursal_y_canal"]]),
        ("Ventas", ["Venta", "Fecha", "Comprobante", "Sucursal", "Canal", "Unidades", "Subtotal (Bs)",
                    "Descuento (Bs)", "Total (Bs)", "Ganancia (Bs)"],
         [[v["id"], texto_bolivia(v["fecha"]), v["nro_comprobante"], v["sucursal"], v["canal"],
           v["unidades"], v["subtotal"], v["descuento"], v["total"], v["ganancia"]] for v in r["ventas"]]),
    ])


def csv_inventario(r: dict) -> bytes:
    p = r["periodo"]
    return a_csv(f"GangaClothes - Reporte de inventario y movimientos del {p['desde']} al {p['hasta']}", [
        ("Stock por sucursal", ["Sucursal", "Variantes", "Unidades", "Reservadas", "Disponibles",
                                "Bajo minimo", "Sin stock", "Valor a costo (Bs)", "Valor a venta (Bs)"],
         [[f["sucursal"], f["variantes"], f["unidades"], f["reservadas"], f["disponibles"], f["bajo_minimo"],
           f["sin_stock"], f["valor_costo"], f["valor_venta"]] for f in r["por_sucursal"]]),
        ("Stock por prenda y sucursal", ["Prenda", "Sucursal", "Variantes", "Unidades", "Reservadas",
                                         "Disponibles", "Bajo minimo", "Valor a costo (Bs)",
                                         "Valor a venta (Bs)"],
         [[f["prenda"], f["sucursal"], f["variantes"], f["unidades"], f["reservadas"], f["disponibles"],
           f["bajo_minimo"], f["valor_costo"], f["valor_venta"]] for f in r["stock"]]),
        ("Movimientos por tipo", ["Tipo", "Movimientos", "Unidades"],
         [[f["tipo"], f["movimientos"], f["unidades"]] for f in r["movimientos_por_tipo"]]),
        ("Movimientos", ["Fecha", "Tipo", "SKU", "Prenda", "Talla", "Color", "Sucursal", "Cantidad",
                         "Motivo", "Usuario"],
         [[texto_bolivia(m["fecha"]), m["tipo"], m["sku"], m["prenda"], m["talla"],
           m["color"], m["sucursal"], m["cantidad"], m["motivo"], m["usuario"]] for m in r["movimientos"]]),
    ])


def csv_margen(r: dict) -> bytes:
    p, s = r["periodo"], r["resumen"]
    return a_csv(f"GangaClothes - Ganancia por prenda (ventas del {p['desde']} al {p['hasta']})", [
        ("Indicadores", ["Prendas", "Ganancia promedio por prenda (Bs)", "Margen promedio %",
                         "Ganancia promedio por unidad vendida (Bs)", "Unidades vendidas",
                         "Ganancia realizada (Bs)"],
         [[s["prendas"], s["ganancia_promedio_por_prenda"], s["margen_promedio_porcentaje"],
           s["ganancia_promedio_por_unidad_vendida"], s["unidades_vendidas"], s["ganancia_realizada"]]]),
        ("Prendas", ["Prenda", "Categoria", "Precio de venta (Bs)", "Costo (Bs)", "Ganancia unitaria (Bs)",
                     "Margen %", "Promocion vigente", "Precio con promocion (Bs)",
                     "Ganancia con promocion (Bs)", "Unidades vendidas", "Ingreso (Bs)",
                     "Descuento otorgado (Bs)", "Ganancia realizada (Bs)"],
         [[f["prenda"], f["categoria"], f["precio_venta"], f["costo"], f["ganancia_unitaria"],
           f["margen_porcentaje"], f["promocion"], f["precio_con_promocion"], f["ganancia_con_promocion"],
           f["unidades_vendidas"], f["ingreso"], f["descuento_otorgado"], f["ganancia_realizada"]]
          for f in r["prendas"]]),
    ])


# =========================================================== CU-24: EXCEL ===

def xlsx_ventas(r: dict) -> bytes:
    """Genera un archivo Excel (.xlsx) con formato corporativo para ventas (CU-24)."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ventas"

    AZUL_MARINO = "1E293B"
    ROJO_OSCURO = "C60000"
    CELESTE = "E0F2FE"
    BLANCO = "FFFFFF"
    GRIS_CLARO = "F8FAFC"

    def _header_font(color=BLANCO):
        return Font(bold=True, color=color, size=11)

    def _header_fill(hex_color=AZUL_MARINO):
        return PatternFill("solid", fgColor=hex_color)

    def _border():
        thin = Side(style="thin", color="CBD5E1")
        return Border(left=thin, right=thin, top=thin, bottom=thin)

    def _centrar():
        return Alignment(horizontal="center", vertical="center", wrap_text=True)

    p = r["periodo"]
    ws.merge_cells("A1:J1")
    titulo = ws["A1"]
    titulo.value = f"GangaClothes · Reporte de Ventas · {p['desde']} al {p['hasta']}"
    titulo.font = Font(bold=True, size=14, color=ROJO_OSCURO)
    titulo.alignment = _centrar()
    ws.row_dimensions[1].height = 28

    ws.append([])

    t = r["totales"]
    ws.append(["RESUMEN GENERAL"])
    ws[f"A{ws.max_row}"].font = Font(bold=True, size=12, color=AZUL_MARINO)

    encab_totales = ["Ventas", "Unidades", "Subtotal (Bs)", "Descuento (Bs)", "Total (Bs)",
                     "Costo (Bs)", "Ganancia (Bs)", "Ticket Promedio (Bs)", "Margen %"]
    ws.append(encab_totales)
    fila_enc = ws.max_row
    for col_idx in range(1, len(encab_totales) + 1):
        cell = ws.cell(row=fila_enc, column=col_idx)
        cell.font = _header_font()
        cell.fill = _header_fill(AZUL_MARINO)
        cell.border = _border()
        cell.alignment = _centrar()

    ws.append([t["ventas"], t["unidades"], t["subtotal"], t["descuento"], t["total"],
               t.get("costo", 0), t["ganancia"], t["ticket_promedio"], t["margen_porcentaje"]])
    fila_datos = ws.max_row
    for col_idx in range(1, len(encab_totales) + 1):
        cell = ws.cell(row=fila_datos, column=col_idx)
        cell.fill = PatternFill("solid", fgColor=CELESTE)
        cell.border = _border()
        cell.alignment = _centrar()

    ws.append([])
    ws.append(["DETALLE DE VENTAS"])
    ws[f"A{ws.max_row}"].font = Font(bold=True, size=11, color=AZUL_MARINO)

    encab_det = ["#Venta", "Fecha", "Comprobante", "Sucursal", "Canal",
                 "Unidades", "Subtotal (Bs)", "Descuento (Bs)", "Total (Bs)", "Ganancia (Bs)"]
    ws.append(encab_det)
    fila_enc_det = ws.max_row
    for col_idx in range(1, len(encab_det) + 1):
        c = ws.cell(row=fila_enc_det, column=col_idx)
        c.font = _header_font()
        c.fill = _header_fill(AZUL_MARINO)
        c.border = _border()
        c.alignment = _centrar()

    for idx, v in enumerate(r["ventas"]):
        fill = PatternFill("solid", fgColor=GRIS_CLARO if idx % 2 else BLANCO)
        fecha_str = v.get("fecha", "")[:19].replace("T", " ")
        row_data = [v["id"], fecha_str, v.get("nro_comprobante", ""),
                    v["sucursal"], v["canal"], v["unidades"],
                    v["subtotal"], v["descuento"], v["total"], v["ganancia"]]
        ws.append(row_data)
        for col_idx in range(1, len(row_data) + 1):
            c = ws.cell(row=ws.max_row, column=col_idx)
            c.fill = fill
            c.border = _border()

    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=0)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max_len + 4, 35)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def xlsx_inventario(r: dict) -> bytes:
    """Genera un archivo Excel (.xlsx) para inventario con estilos (CU-24)."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario"

    AZUL_MARINO = "1E293B"
    ROJO_OSCURO = "C60000"
    NARANJA = "FEF3C7"
    BLANCO = "FFFFFF"
    GRIS = "F8FAFC"

    def _hf():
        return Font(bold=True, color="FFFFFF", size=10)

    def _hfill(hex_color=AZUL_MARINO):
        return PatternFill("solid", fgColor=hex_color)

    def _bd():
        s = Side(style="thin", color="CBD5E1")
        return Border(left=s, right=s, top=s, bottom=s)

    p = r["periodo"]
    ws.merge_cells("A1:I1")
    ws["A1"].value = f"GangaClothes · Inventario · {p['desde']} al {p['hasta']}"
    ws["A1"].font = Font(bold=True, size=13, color=ROJO_OSCURO)
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[1].height = 25
    ws.append([])

    tot = r["totales"]
    ws.append(["RESUMEN GENERAL"])
    ws[f"A{ws.max_row}"].font = Font(bold=True, color=AZUL_MARINO)
    encab = ["Unidades", "Reservadas", "Disponibles", "Bajo Mínimo", "Sin Stock",
             "Valor Costo (Bs)", "Valor Venta (Bs)"]
    ws.append(encab)
    fila_e = ws.max_row
    for c in range(1, len(encab)+1):
        cell = ws.cell(fila_e, c)
        cell.font = _hf(); cell.fill = _hfill(); cell.border = _bd()
    ws.append([tot["unidades"], tot["reservadas"], tot["disponibles"],
               tot["bajo_minimo"], tot["sin_stock"], tot["valor_costo"], tot["valor_venta"]])
    fila_v = ws.max_row
    for c in range(1, 8):
        cell = ws.cell(fila_v, c)
        cell.fill = PatternFill("solid", fgColor=NARANJA); cell.border = _bd()

    ws.append([])
    ws.append(["STOCK POR SUCURSAL"])
    ws[f"A{ws.max_row}"].font = Font(bold=True, color=AZUL_MARINO)
    encab2 = ["Sucursal", "Variantes", "Unidades", "Reservadas", "Disponibles",
              "Bajo Mínimo", "Sin Stock", "Valor Costo (Bs)", "Valor Venta (Bs)"]
    ws.append(encab2)
    fila_e2 = ws.max_row
    for c in range(1, len(encab2)+1):
        cell = ws.cell(fila_e2, c)
        cell.font = _hf(); cell.fill = _hfill(ROJO_OSCURO); cell.border = _bd()
    for idx, f in enumerate(r["por_sucursal"]):
        fill = PatternFill("solid", fgColor=GRIS if idx % 2 else BLANCO)
        ws.append([f["sucursal"], f["variantes"], f["unidades"], f["reservadas"],
                   f["disponibles"], f["bajo_minimo"], f["sin_stock"],
                   f["valor_costo"], f["valor_venta"]])
        fila_cur = ws.max_row
        for c in range(1, len(encab2)+1):
            cell = ws.cell(fila_cur, c); cell.fill = fill; cell.border = _bd()

    # Movimientos en hoja separada
    ws2 = wb.create_sheet("Movimientos")
    encab_mov = ["Fecha", "Tipo", "SKU", "Prenda", "Talla", "Color", "Sucursal", "Cantidad", "Motivo", "Usuario"]
    ws2.append(encab_mov)
    for c in range(1, len(encab_mov)+1):
        cell = ws2.cell(1, c)
        cell.font = _hf(); cell.fill = _hfill(); cell.border = _bd()
    for idx, m in enumerate(r["movimientos"][:100]):
        fill = PatternFill("solid", fgColor=GRIS if idx % 2 else BLANCO)
        fecha_m = m.get("fecha", "")[:19].replace("T", " ") if m.get("fecha") else ""
        ws2.append([fecha_m, m["tipo"], m["sku"], m["prenda"],
                    m["talla"], m["color"], m["sucursal"], m["cantidad"], m["motivo"], m["usuario"]])
        fila_cur_m = ws2.max_row
        for c in range(1, len(encab_mov)+1):
            cell = ws2.cell(fila_cur_m, c); cell.fill = fill; cell.border = _bd()

    for sheet in [ws, ws2]:
        for col in sheet.columns:
            ml = max((len(str(cell.value or "")) for cell in col), default=0)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = min(ml + 4, 35)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# =========================================================== CU-24: PDF ====

def pdf_ventas(r: dict) -> bytes:
    """PDF corporativo de ventas con ReportLab (CU-24)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    p = r["periodo"]
    t = r["totales"]

    AZUL = colors.HexColor("#1E293B")
    ROJO = colors.HexColor("#C60000")
    CELESTE = colors.HexColor("#E0F2FE")
    GRIS = colors.HexColor("#F8FAFC")

    estilo_titulo = ParagraphStyle("titulo", fontSize=16, textColor=ROJO,
                                   spaceAfter=4, fontName="Helvetica-Bold", alignment=1)
    estilo_sub = ParagraphStyle("sub", fontSize=10, textColor=AZUL,
                                spaceAfter=4, fontName="Helvetica-Bold")

    contenido = [
        Paragraph("GANGACLOTHES · E-COMMERCE", estilo_titulo),
        Paragraph(f"Reporte de Ventas · {p['desde']} al {p['hasta']}", estilo_sub),
        HRFlowable(width="100%", thickness=2, color=ROJO),
        Spacer(1, 0.3*cm),
    ]

    datos_resumen = [
        ["Ventas", "Unidades", "Subtotal (Bs)", "Descuento (Bs)", "Total (Bs)", "Ganancia (Bs)", "Margen %"],
        [t["ventas"], t["unidades"], f"{t['subtotal']:.2f}", f"{t['descuento']:.2f}",
         f"{t['total']:.2f}", f"{t['ganancia']:.2f}", f"{t['margen_porcentaje']:.1f}%"],
    ]
    tabla_res = Table(datos_resumen, repeatRows=1)
    tabla_res.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CELESTE]),
    ]))
    contenido += [Paragraph("Resumen General", estilo_sub), tabla_res, Spacer(1, 0.4*cm)]

    filas_det = [["#Venta", "Fecha", "Sucursal", "Canal", "Unidades", "Total (Bs)"]]
    for v in r["ventas"][:20]:
        fecha_legible = v.get("fecha", "")[:10]
        filas_det.append([v["id"], fecha_legible, v["sucursal"], v["canal"],
                          v["unidades"], f"{v['total']:.2f}"])
    tabla_det = Table(filas_det, repeatRows=1)
    tabla_det.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (4, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
    ]))
    contenido += [Paragraph(f"Detalle de Ventas (primeras {min(20, len(r['ventas']))} ventas)", estilo_sub),
                  tabla_det]

    doc.build(contenido)
    return buf.getvalue()


def pdf_inventario(r: dict) -> bytes:
    """PDF corporativo de inventario con ReportLab (CU-24)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    p = r["periodo"]
    tot = r["totales"]
    AZUL = colors.HexColor("#1E293B")
    ROJO = colors.HexColor("#C60000")
    GRIS = colors.HexColor("#F8FAFC")

    estilo_titulo = ParagraphStyle("titulo", fontSize=16, textColor=ROJO,
                                   spaceAfter=4, fontName="Helvetica-Bold", alignment=1)
    estilo_sub = ParagraphStyle("sub", fontSize=10, textColor=AZUL,
                                spaceAfter=4, fontName="Helvetica-Bold")

    contenido = [
        Paragraph("GANGACLOTHES · E-COMMERCE", estilo_titulo),
        Paragraph(f"Reporte de Inventario · {p['desde']} al {p['hasta']}", estilo_sub),
        HRFlowable(width="100%", thickness=2, color=ROJO),
        Spacer(1, 0.3*cm),
    ]

    filas_suc = [["Sucursal", "Variantes", "Unidades", "Reservadas", "Disponibles",
                  "Bajo Mín", "Sin Stock", "Valor Costo (Bs)", "Valor Venta (Bs)"]]
    for s in r["por_sucursal"]:
        filas_suc.append([s["sucursal"], s["variantes"], s["unidades"], s["reservadas"],
                          s["disponibles"], s["bajo_minimo"], s["sin_stock"],
                          f"{s['valor_costo']:.2f}", f"{s['valor_venta']:.2f}"])

    tabla = Table(filas_suc, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
    ]))
    contenido += [Paragraph("Stock por Sucursal", estilo_sub), tabla]
    doc.build(contenido)
    return buf.getvalue()
