"""CU-16: Cambio de prendas.

Reglas de negocio:
  1. La venta debe pertenecer a la sucursal del usuario y estar PAGADA.
  2. La venta debe ser de los últimos 7 días.
  3. La variante devuelta debe estar en el detalle de la venta.
  4. En una transacción atómica:
     a. Se suma stock a la variante devuelta.
     b. Se descuenta stock de la variante nueva (verifica disponibilidad).
     c. Se calcula saldo (precio_nueva - precio_devuelta).
     d. Se registra en cambio_prenda.
     e. Se crean movimientos de inventario para auditoría.

Controller (ICONIX): este módulo es el controlador que orquesta la lógica.
Entity (ICONIX): Venta, Inventario, CambioPrenda son las entidades afectadas.
"""
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.fechas import utc_iso
from app.models.catalogo import Color, Prenda, Talla, Variante
from app.models.inventario import Inventario, MovimientoInventario
from app.models.sucursales import Sucursal
from app.models.usuarios import Usuario
from app.models.ventas import CambioPrenda, DetalleVenta, Venta

PLAZO_DIAS = 7  # días máximos para hacer un cambio


def _inventario_de(db: Session, variante_id: int, sucursal_id: int) -> Inventario:
    inv = (
        db.query(Inventario)
        .filter(Inventario.variante_id == variante_id, Inventario.sucursal_id == sucursal_id)
        .first()
    )
    if inv is None:
        raise HTTPException(404, f"La variante {variante_id} no tiene stock en esa sucursal")
    return inv


def _info_variante(db: Session, variante_id: int) -> tuple:
    """Retorna (Variante, Prenda, Talla, Color) o lanza 404."""
    fila = (
        db.query(Variante, Prenda, Talla, Color)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .filter(Variante.id == variante_id)
        .first()
    )
    if fila is None:
        raise HTTPException(404, f"La variante {variante_id} no existe")
    return fila


def registrar_cambio(db: Session, datos, usuario: Usuario) -> dict:
    """
    Controller: orquesta la validación y la transacción atómica del cambio.
    """
    # --- validar venta ---
    venta = db.get(Venta, datos.venta_id)
    if venta is None:
        raise HTTPException(404, "La venta no existe")
    if venta.estado != "pagada":
        raise HTTPException(
            400,
            f"Solo se pueden cambiar prendas de ventas pagadas. "
            f"Esta venta está '{venta.estado}'."
        )

    # --- validar plazo de 7 días ---
    ahora = datetime.utcnow()
    dias_transcurridos = (ahora - venta.fecha).days if venta.fecha else 999
    if dias_transcurridos > PLAZO_DIAS:
        raise HTTPException(
            400,
            f"El plazo para hacer cambios venció hace {dias_transcurridos - PLAZO_DIAS} día(s). "
            f"Los cambios se aceptan dentro de los {PLAZO_DIAS} días siguientes a la compra."
        )

    # --- verificar que la variante devuelta esté en la venta ---
    linea_devuelta = (
        db.query(DetalleVenta)
        .filter(
            DetalleVenta.venta_id == datos.venta_id,
            DetalleVenta.variante_id == datos.variante_devuelta_id,
        )
        .first()
    )
    if linea_devuelta is None:
        raise HTTPException(
            400,
            "La variante a devolver no está en el detalle de esta venta. "
            "Verifica el ID de la variante."
        )

    # --- verificar que no sea el mismo ítem ---
    if datos.variante_devuelta_id == datos.variante_nueva_id:
        raise HTTPException(400, "La variante nueva debe ser diferente a la devuelta")

    # --- verificar que no haya un cambio previo de esta venta ---
    cambio_previo = (
        db.query(CambioPrenda)
        .filter(CambioPrenda.venta_id == datos.venta_id)
        .first()
    )
    if cambio_previo:
        raise HTTPException(
            400,
            f"Esta venta ya tiene un cambio registrado (cambio #{cambio_previo.id}). "
            "Solo se permite un cambio por venta."
        )

    variante_dev, prenda_dev, talla_dev, color_dev = _info_variante(db, datos.variante_devuelta_id)
    variante_nva, prenda_nva, talla_nva, color_nva = _info_variante(db, datos.variante_nueva_id)

    # --- verificar disponibilidad de la variante nueva ---
    sucursal_id = venta.sucursal_id
    inv_nueva = _inventario_de(db, datos.variante_nueva_id, sucursal_id)
    disponible = inv_nueva.cantidad - inv_nueva.cantidad_reservada
    if disponible < 1:
        raise HTTPException(
            400,
            f"{variante_nva.sku} ({prenda_nva.nombre}, {talla_nva.nombre}/{color_nva.nombre}): "
            "no hay unidades disponibles para el cambio."
        )

    # --- calcular saldo ---
    precio_devuelta = float(prenda_dev.precio_venta)
    precio_nueva = float(prenda_nva.precio_venta)
    saldo = precio_nueva - precio_devuelta  # positivo: cliente paga; negativo: saldo a favor

    # --- TRANSACCIÓN ATÓMICA: todo o nada ---
    # a) Reingreso de la prenda devuelta al inventario
    inv_devuelta = _inventario_de(db, datos.variante_devuelta_id, sucursal_id)
    inv_devuelta.cantidad += 1
    db.add(MovimientoInventario(
        variante_id=datos.variante_devuelta_id,
        sucursal_id=sucursal_id,
        usuario_id=usuario.id,
        tipo="devolucion",
        cantidad=1,
        motivo=f"Cambio de prenda (venta #{datos.venta_id}): {datos.motivo or 'sin motivo'}",
    ))

    # b) Descuento de la prenda nueva del inventario
    inv_nueva.cantidad -= 1
    db.add(MovimientoInventario(
        variante_id=datos.variante_nueva_id,
        sucursal_id=sucursal_id,
        usuario_id=usuario.id,
        tipo="salida",
        cantidad=1,
        motivo=f"Cambio de prenda (venta #{datos.venta_id}): entregada como cambio",
    ))

    # c) Registrar el cambio
    cambio = CambioPrenda(
        venta_id=datos.venta_id,
        variante_devuelta_id=datos.variante_devuelta_id,
        variante_nueva_id=datos.variante_nueva_id,
        motivo=datos.motivo,
        saldo=saldo,
        usuario_id=usuario.id,
    )
    db.add(cambio)
    db.commit()
    db.refresh(cambio)

    sucursal = db.get(Sucursal, sucursal_id)

    return {
        "cambio_id": cambio.id,
        "venta_id": datos.venta_id,
        "sucursal": sucursal.nombre if sucursal else None,
        "devuelta": {
            "variante_id": datos.variante_devuelta_id,
            "sku": variante_dev.sku,
            "prenda": prenda_dev.nombre,
            "talla": talla_dev.nombre,
            "color": color_dev.nombre,
            "precio": precio_devuelta,
        },
        "nueva": {
            "variante_id": datos.variante_nueva_id,
            "sku": variante_nva.sku,
            "prenda": prenda_nva.nombre,
            "talla": talla_nva.nombre,
            "color": color_nva.nombre,
            "precio": precio_nueva,
        },
        "saldo": round(saldo, 2),
        "saldo_tipo": "cobrar" if saldo > 0 else ("devolver" if saldo < 0 else "sin_diferencia"),
        "motivo": datos.motivo,
        "fecha": utc_iso(cambio.fecha),
        "dias_desde_venta": dias_transcurridos,
        "dias_restantes_plazo": max(0, PLAZO_DIAS - dias_transcurridos),
    }


def buscar_venta(db: Session, venta_id: int, sucursal_id: int | None = None) -> dict:
    """Busca venta por ID para el flujo de cambio en el frontend."""
    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(404, f"No se encontró la venta #{venta_id}")
    if venta.estado != "pagada":
        raise HTTPException(400, f"Esta venta está '{venta.estado}': solo las ventas pagadas se pueden cambiar")

    ahora = datetime.utcnow()
    dias = (ahora - venta.fecha).days if venta.fecha else 0
    if dias > PLAZO_DIAS:
        raise HTTPException(400, f"Plazo de {PLAZO_DIAS} días vencido (han pasado {dias} días desde la compra)")

    # Verificar si ya tiene cambio
    cambio = db.query(CambioPrenda).filter(CambioPrenda.venta_id == venta_id).first()
    if cambio:
        raise HTTPException(400, f"Esta venta ya tiene un cambio registrado (#{cambio.id})")

    sucursal = db.get(Sucursal, venta.sucursal_id)
    lineas = (
        db.query(DetalleVenta, Variante, Prenda, Talla, Color)
        .join(Variante, Variante.id == DetalleVenta.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .filter(DetalleVenta.venta_id == venta_id)
        .all()
    )
    return {
        "venta_id": venta_id,
        "estado": venta.estado,
        "fecha": utc_iso(venta.fecha),
        "sucursal": sucursal.nombre if sucursal else None,
        "sucursal_id": venta.sucursal_id,
        "total": float(venta.total or 0),
        "dias_desde_compra": dias,
        "dias_restantes_plazo": max(0, PLAZO_DIAS - dias),
        "detalle": [
            {
                "detalle_id": d.id,
                "variante_id": v.id,
                "sku": v.sku,
                "prenda": p.nombre,
                "talla": t.nombre,
                "color": c.nombre,
                "cantidad": d.cantidad,
                "precio_unitario": float(d.precio_unitario),
            }
            for d, v, p, t, c in lineas
        ],
    }
