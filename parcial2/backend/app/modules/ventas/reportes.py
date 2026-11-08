"""Reportes del tenant. Costos y ganancias usan los costos actuales conocidos."""
import csv
import io
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso
from ...models import (Categoria, Color, Compra, DatosComplementarios, DescuentoVenta, DetalleVenta, Inventario,
                       MovimientoInventario, Pago, Producto, Promocion, Reserva, Sucursal, Talla, User, Variante, Venta)

router = APIRouter(prefix="/reportes", tags=["Reportes"])


def _periodo(desde, hasta):
    hoy = (datetime.now(timezone.utc) - timedelta(hours=4)).date()
    hasta = hasta or hoy
    desde = desde or hasta - timedelta(days=29)
    if desde > hasta or (hasta - desde).days > 731: raise HTTPException(422, "Periodo inválido (máximo dos años)")
    return desde, hasta


def _fecha(fecha):
    return (fecha.replace(tzinfo=None) - timedelta(hours=4)).date() if fecha else None


def _costo(db, tid, id):
    extra = db.query(DatosComplementarios).filter_by(tenant_id=tid, tipo="prendas", registro_id=id).first()
    return float(extra.datos["costo"]) if extra and (extra.datos or {}).get("costo") is not None else None


def _datos(db, tid, desde, hasta, sucursal_id, canal=None):
    if sucursal_id and not db.query(Sucursal).filter_by(tenant_id=tid, id=sucursal_id).first(): raise HTTPException(404, "Sucursal no encontrada")
    ventas, lineas = [], []
    for venta in db.query(Venta).filter_by(tenant_id=tid, estado="CONFIRMADA").all():
        fecha = _fecha(venta.fecha)
        if not fecha or not (desde <= fecha <= hasta) or (sucursal_id and venta.sucursal_id != sucursal_id): continue
        canal_venta = "caja" if venta.origen == "PRESENCIAL" else ("movil" if venta.origen == "MOVIL" else "web")
        if canal and canal != canal_venta: continue
        pagos = db.query(Pago).filter_by(tenant_id=tid, venta_id=venta.id, estado="APROBADO").all()
        if not pagos: continue
        sucursal = db.query(Sucursal).filter_by(tenant_id=tid, id=venta.sucursal_id).first()
        detalles = []
        for d in db.query(DetalleVenta).filter_by(tenant_id=tid, venta_id=venta.id).all():
            v = db.query(Variante).filter_by(tenant_id=tid, id=d.variante_id).first()
            p = db.query(Producto).filter_by(tenant_id=tid, id=v.producto_id).first() if v else None
            if not p: continue
            costo = _costo(db, tid, p.id)
            subtotal = float(d.subtotal)
            descuento = db.query(DescuentoVenta).filter_by(tenant_id=tid, detalle_venta_id=d.id).first()
            detalle = {"producto": p, "cantidad": d.cantidad, "subtotal": subtotal,
                       "descuento": float(descuento.descuento) if descuento else 0,
                       "costo": costo * d.cantidad if costo is not None else 0,
                       "ganancia": subtotal - costo * d.cantidad if costo is not None else 0,
                       "con_costo": costo is not None}
            detalles.append(detalle); lineas.append(detalle)
        total = float(venta.total)
        ventas.append({"id": venta.id, "fecha": venta.fecha, "fecha_local": fecha, "nro_comprobante": venta.codigo,
                       "sucursal_id": venta.sucursal_id, "sucursal": sucursal.nombre if sucursal else "—", "canal": canal_venta,
                       "unidades": sum(d["cantidad"] for d in detalles),
                       "subtotal": total + sum(d["descuento"] for d in detalles),
                       "descuento": sum(d["descuento"] for d in detalles), "total": total,
                       "costo": sum(d["costo"] for d in detalles), "ganancia": sum(d["ganancia"] for d in detalles),
                       "pagos": pagos})
    return ventas, lineas


def _totales(ventas):
    total = sum(v["total"] for v in ventas); ganancia = sum(v["ganancia"] for v in ventas)
    unidades = sum(v["unidades"] for v in ventas); cantidad = len(ventas)
    return {"ventas": cantidad, "unidades": unidades, "subtotal": sum(v["subtotal"] for v in ventas),
            "descuento": sum(v["descuento"] for v in ventas), "total": total,
            "costo": sum(v["costo"] for v in ventas), "ganancia": ganancia,
            "ticket_promedio": total / cantidad if cantidad else 0,
            "margen_porcentaje": ganancia / total * 100 if total else 0,
            "ganancia_por_unidad": ganancia / unidades if unidades else 0}


def _grupos(ventas, clave):
    grupos = defaultdict(list)
    for venta in ventas:
        k, etiqueta = clave(venta); grupos[(k, etiqueta)].append(venta)
    total = sum(v["total"] for v in ventas)
    return [{"clave": k, "etiqueta": etiqueta, **_totales(vs),
             "participacion": sum(v["total"] for v in vs) / total * 100 if total else 0}
            for (k, etiqueta), vs in sorted(grupos.items(), key=lambda x: str(x[0][0]))]


def _margen(db, tid, desde, hasta, sucursal_id):
    ventas, lineas = _datos(db, tid, desde, hasta, sucursal_id)
    prendas = []
    for p in db.query(Producto).filter_by(tenant_id=tid, activo=True).all():
        costo = _costo(db, tid, p.id)
        if costo is None: continue
        categoria = db.query(Categoria).filter_by(tenant_id=tid, id=p.categoria_id).first() if p.categoria_id else None
        propias = [d for d in lineas if d["producto"].id == p.id]
        precio = float(p.precio_base); ganancia = precio - costo
        prendas.append({"prenda_id": p.id, "prenda": p.nombre, "categoria": categoria.nombre if categoria else None,
                        "publicado": p.activo, "precio_venta": precio, "costo": costo,
                        "ganancia_unitaria": ganancia, "margen_porcentaje": ganancia / precio * 100 if precio else 0,
                        "promocion": None, "precio_con_promocion": precio, "ganancia_con_promocion": ganancia,
                        "unidades_vendidas": sum(d["cantidad"] for d in propias), "ingreso": sum(d["subtotal"] for d in propias),
                        "descuento_otorgado": sum(d["descuento"] for d in propias), "ganancia_realizada": sum(d["ganancia"] for d in propias)})
    ordenadas = sorted(prendas, key=lambda p: p["ganancia_unitaria"])
    unidades = sum(p["unidades_vendidas"] for p in prendas); ganancia = sum(p["ganancia_realizada"] for p in prendas)
    return {"periodo": {"desde": desde, "hasta": hasta}, "resumen": {"prendas": len(prendas),
            "ganancia_promedio_por_prenda": sum(p["ganancia_unitaria"] for p in prendas) / len(prendas) if prendas else 0,
            "margen_promedio_porcentaje": sum(p["margen_porcentaje"] for p in prendas) / len(prendas) if prendas else 0,
            "ganancia_promedio_por_unidad_vendida": ganancia / unidades if unidades else 0, "unidades_vendidas": unidades,
            "ganancia_realizada": ganancia, "mayor_ganancia": ordenadas[-1]["prenda"] if ordenadas else None,
            "menor_ganancia": ordenadas[0]["prenda"] if ordenadas else None}, "prendas": prendas}


def _inventario(db, tid, desde, hasta, sucursal_id):
    grupos = {}
    query = db.query(Inventario).filter_by(tenant_id=tid)
    if sucursal_id: query = query.filter_by(sucursal_id=sucursal_id)
    for i in query.all():
        v = db.query(Variante).filter_by(tenant_id=tid, id=i.variante_id).first()
        p = db.query(Producto).filter_by(tenant_id=tid, id=v.producto_id).first() if v else None
        s = db.query(Sucursal).filter_by(tenant_id=tid, id=i.sucursal_id).first()
        if not p or not s: continue
        key = (p.id, s.id)
        f = grupos.setdefault(key, {"prenda_id": p.id, "prenda": p.nombre, "sucursal_id": s.id, "sucursal": s.nombre,
                                   "variantes": 0, "unidades": 0, "reservadas": 0, "disponibles": 0,
                                   "bajo_minimo": 0, "sin_stock": 0, "valor_costo": 0, "valor_venta": 0})
        f["variantes"] += 1; f["unidades"] += i.stock; f["reservadas"] += i.reservado
        f["disponibles"] += i.stock - i.reservado; f["bajo_minimo"] += int(i.stock < i.stock_min)
        f["sin_stock"] += int(i.stock - i.reservado <= 0); f["valor_costo"] += i.stock * (_costo(db, tid, p.id) or 0)
        f["valor_venta"] += i.stock * float(v.precio)
    campos = ("variantes", "unidades", "reservadas", "disponibles", "bajo_minimo", "sin_stock", "valor_costo", "valor_venta")
    por_sucursal = {}
    for f in grupos.values():
        s = por_sucursal.setdefault(f["sucursal_id"], {"sucursal_id": f["sucursal_id"], "sucursal": f["sucursal"], **{k: 0 for k in campos}})
        for k in campos: s[k] += f[k]
    totales = {k: sum(f[k] for f in grupos.values()) for k in campos}
    movimientos = []
    q = db.query(MovimientoInventario).filter_by(tenant_id=tid)
    if sucursal_id: q = q.filter_by(sucursal_id=sucursal_id)
    for m in q.order_by(MovimientoInventario.id.desc()).all():
        if not m.fecha or not desde <= _fecha(m.fecha) <= hasta: continue
        v = db.query(Variante).filter_by(tenant_id=tid, id=m.variante_id).first()
        p = db.query(Producto).filter_by(tenant_id=tid, id=v.producto_id).first() if v else None
        t = db.query(Talla).filter_by(tenant_id=tid, id=v.talla_id).first() if v and v.talla_id else None
        c = db.query(Color).filter_by(tenant_id=tid, id=v.color_id).first() if v and v.color_id else None
        s = db.query(Sucursal).filter_by(tenant_id=tid, id=m.sucursal_id).first()
        u = db.query(User).filter_by(tenant_id=tid, id=m.usuario_id).first() if m.usuario_id else None
        movimientos.append({"id": m.id, "fecha": m.fecha, "tipo": m.tipo.lower(), "sku": v.sku if v else "—",
                            "prenda": p.nombre if p else "—", "talla": t.nombre if t else "—", "color": c.nombre if c else "—",
                            "sucursal": s.nombre if s else "—", "cantidad": m.cantidad, "motivo": m.motivo, "usuario": u.nombre if u else None})
    tipos = defaultdict(list)
    for m in movimientos: tipos[m["tipo"]].append(m)
    return {"periodo": {"desde": desde, "hasta": hasta}, "totales": totales, "por_sucursal": list(por_sucursal.values()),
            "stock": list(grupos.values()), "movimientos": movimientos,
            "movimientos_por_tipo": [{"tipo": k, "movimientos": len(v), "unidades": sum(x["cantidad"] for x in v)} for k, v in tipos.items()]}


def _csv(nombre, filas):
    salida = io.StringIO(newline="")
    if filas:
        claves = list(filas[0])
        escritor = csv.DictWriter(salida, fieldnames=claves, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows({k: ("'" + str(v) if isinstance(v, str) and str(v).lstrip().startswith(("=", "+", "-", "@")) else v)
                            for k, v in fila.items()} for fila in filas)
    return Response(content="\ufeff" + salida.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}.csv"'})


def _excel(nombre, filas):
    salida = io.StringIO(newline="")
    if filas:
        claves = list(filas[0])
        escritor = csv.DictWriter(salida, fieldnames=claves, delimiter=";", extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows({k: ("'" + str(v) if isinstance(v, str) and str(v).lstrip().startswith(("=", "+", "-", "@")) else v)
                            for k, v in fila.items()} for fila in filas)
    return Response(content="\ufeff" + salida.getvalue(), media_type="application/vnd.ms-excel; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}_excel.csv"'})


def _json(nombre, datos):
    contenido = json.dumps(datos, ensure_ascii=False, indent=2, default=str)
    return Response(content=contenido, media_type="application/json; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}.json"'})


@router.get("/ventas")
def ventas(desde: date | None = None, hasta: date | None = None, sucursal_id: int | None = None,
           canal: str | None = None, agrupar: str = "dia", formato: str | None = None,
           scope: TenantScope = Depends(require_permiso("reportes:ver")), db: Session = Depends(get_db)):
    desde, hasta = _periodo(desde, hasta)
    if agrupar not in {"dia", "semana", "mes"}: raise HTTPException(422, "Agrupación inválida")
    vs, _ = _datos(db, scope.tenant_id, desde, hasta, sucursal_id, canal)
    def periodo(v):
        f = v["fecha_local"]
        if agrupar == "semana": f -= timedelta(days=f.weekday())
        if agrupar == "mes": f = f.replace(day=1)
        valor = f.isoformat()
        return (valor, f"Semana del {valor}" if agrupar == "semana" else valor)
    filas = [{k: v[k] for k in ("id", "fecha", "nro_comprobante", "sucursal", "canal", "unidades", "subtotal", "descuento", "total", "ganancia")} for v in vs]
    if formato == "csv": return _csv("ventas", filas)
    if formato in ("excel", "xlsx"): return _excel("ventas", filas)
    if formato == "json": return _json("ventas", {"totales": _totales(vs), "ventas": filas})
    return {"periodo": {"desde": desde, "hasta": hasta}, "totales": _totales(vs),
            "por_periodo": _grupos(vs, periodo), "por_sucursal": _grupos(vs, lambda v: (v["sucursal_id"], v["sucursal"])),
            "por_canal": _grupos(vs, lambda v: (v["canal"], v["canal"])),
            "por_sucursal_y_canal": _grupos(vs, lambda v: (f'{v["sucursal_id"]}-{v["canal"]}', f'{v["sucursal"]} · {v["canal"]}')),
            "ventas": filas}


@router.get("/inventario")
def inventario(desde: date | None = None, hasta: date | None = None, sucursal_id: int | None = None,
               formato: str | None = None, scope: TenantScope = Depends(require_permiso("reportes:ver")), db: Session = Depends(get_db)):
    desde, hasta = _periodo(desde, hasta)
    if sucursal_id and not db.query(Sucursal).filter_by(tenant_id=scope.tenant_id, id=sucursal_id).first(): raise HTTPException(404, "Sucursal no encontrada")
    resultado = _inventario(db, scope.tenant_id, desde, hasta, sucursal_id)
    if formato == "csv": return _csv("inventario", resultado["stock"])
    if formato in ("excel", "xlsx"): return _excel("inventario", resultado["stock"])
    if formato == "json": return _json("inventario", resultado)
    return resultado


@router.get("/margen")
def margen(desde: date | None = None, hasta: date | None = None, sucursal_id: int | None = None,
           formato: str | None = None, scope: TenantScope = Depends(require_permiso("reportes:ver")), db: Session = Depends(get_db)):
    desde, hasta = _periodo(desde, hasta)
    resultado = _margen(db, scope.tenant_id, desde, hasta, sucursal_id)
    if formato == "csv": return _csv("margen", resultado["prendas"])
    if formato in ("excel", "xlsx"): return _excel("margen", resultado["prendas"])
    if formato == "json": return _json("margen", resultado)
    return resultado


@router.get("/dashboard")
def dashboard(desde: date | None = None, hasta: date | None = None, sucursal_id: int | None = None,
              scope: TenantScope = Depends(require_permiso("reportes:ver")), db: Session = Depends(get_db)):
    desde, hasta = _periodo(desde, hasta); tid = scope.tenant_id
    vs, lineas = _datos(db, tid, desde, hasta, sucursal_id)
    dias = (hasta - desde).days + 1
    anteriores, _ = _datos(db, tid, desde - timedelta(days=dias), desde - timedelta(days=1), sucursal_id)
    anterior = sum(v["total"] for v in anteriores); total = sum(v["total"] for v in vs)
    inv = _inventario(db, tid, desde, hasta, sucursal_id); margen = _margen(db, tid, desde, hasta, sucursal_id)
    reservas = db.query(Reserva).filter_by(tenant_id=tid)
    compras = db.query(Compra).filter_by(tenant_id=tid, estado="pendiente")
    if sucursal_id: reservas = reservas.filter_by(sucursal_id=sucursal_id); compras = compras.filter_by(sucursal_id=sucursal_id)
    reservas = reservas.all(); resumen = margen["resumen"]
    por_dia = []
    for i in range(dias):
        fecha = desde + timedelta(days=i); ventas_dia = [v for v in vs if v["fecha_local"] == fecha]
        por_dia.append({"fecha": fecha, "ventas": len(ventas_dia), "total": sum(v["total"] for v in ventas_dia),
                        "ganancia": sum(v["ganancia"] for v in ventas_dia)})
    productos = defaultdict(list); categorias = defaultdict(list)
    for linea in lineas:
        p = linea["producto"]; productos[(p.id, p.nombre)].append(linea)
        cat = db.query(Categoria).filter_by(tenant_id=tid, id=p.categoria_id).first() if p.categoria_id else None
        categorias[(cat.id if cat else 0, cat.nombre if cat else "Sin categoría")].append(linea)
    def agrupar_lineas(grupos):
        return [{"clave": k[0], "etiqueta": k[1], "unidades": sum(x["cantidad"] for x in ls),
                 "total": sum(x["subtotal"] for x in ls), "ganancia": sum(x["ganancia"] for x in ls),
                 "participacion": sum(x["subtotal"] for x in ls) / total * 100 if total else 0} for k, ls in grupos.items()]
    pagos = defaultdict(list)
    for v in vs:
        for pago in v["pagos"]: pagos[pago.metodo].append(pago)
    estados = defaultdict(int)
    for r in reservas: estados[r.estado.lower()] += 1
    indicadores = {**_totales(vs), "total_periodo_anterior": anterior,
                   "variacion_porcentaje": (total - anterior) / anterior * 100 if anterior else None,
                   "ganancia_promedio_por_prenda": resumen["ganancia_promedio_por_prenda"],
                   "margen_promedio_porcentaje": resumen["margen_promedio_porcentaje"], "prendas_activas": resumen["prendas"],
                   "reservas_activas": sum(r.estado in {"PENDIENTE", "PREPARADA"} for r in reservas),
                   "alertas_stock": inv["totales"]["bajo_minimo"], "unidades_en_stock": inv["totales"]["unidades"],
                   "valor_inventario_costo": inv["totales"]["valor_costo"], "valor_inventario_venta": inv["totales"]["valor_venta"],
                   "compras_pendientes": compras.count(), "promociones_vigentes": db.query(Promocion).filter(
                       Promocion.tenant_id == tid, Promocion.activo.is_(True),
                       Promocion.fecha_inicio <= (datetime.now(timezone.utc) - timedelta(hours=4)).date(),
                       Promocion.fecha_fin >= (datetime.now(timezone.utc) - timedelta(hours=4)).date()).count()}
    return {"periodo": {"desde": desde, "hasta": hasta, "dias": dias, "hoy": (datetime.now(timezone.utc) - timedelta(hours=4)).date()},
            "indicadores": indicadores, "ventas_por_dia": por_dia,
            "por_canal": _grupos(vs, lambda v: (v["canal"], v["canal"])),
            "por_sucursal": _grupos(vs, lambda v: (v["sucursal_id"], v["sucursal"])),
            "por_categoria": agrupar_lineas(categorias), "top_prendas": sorted(agrupar_lineas(productos), key=lambda x: x["total"], reverse=True)[:10],
            "metodos_pago": [{"metodo": k, "pagos": len(p), "total": sum(float(x.monto) for x in p)} for k, p in pagos.items()],
            "reservas_por_estado": [{"estado": k, "reservas": v} for k, v in estados.items()]}
