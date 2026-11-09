from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...models import (CambioPrenda, DetalleVenta, Inventario, MovimientoInventario,
                       Tenant, Variante, Venta)
from . import schemas
from ..productos.promociones import precio_promocional


def obtener_venta(db: Session, tenant_id: int, codigo: str):
    venta = db.query(Venta).filter_by(tenant_id=tenant_id, codigo=codigo).first()
    if venta is None:
        raise HTTPException(404, "Venta no encontrada")
    return venta


def verificar_plazo(venta: Venta, plazo_dias: int):
    fecha = venta.fecha.replace(tzinfo=timezone.utc) if venta.fecha.tzinfo is None else venta.fecha
    if datetime.now(timezone.utc) - fecha > timedelta(days=plazo_dias):
        raise HTTPException(409, "Fuera de plazo")


def _evaluar(db: Session, tenant_id: int, data: schemas.CotizarIn, *, bloquear=False):
    consulta_venta = db.query(Venta).filter_by(tenant_id=tenant_id, id=data.venta_id)
    venta = (consulta_venta.with_for_update() if bloquear else consulta_venta).first()
    if not venta:
        raise HTTPException(404, "Venta no encontrada")
    if venta.estado == "ANULADA":
        raise HTTPException(409, "Venta anulada")
    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    verificar_plazo(venta, tenant.plazo_cambio_dias)
    if data.variante_nueva_id is not None and data.variante_devuelta_id == data.variante_nueva_id:
        raise HTTPException(422, "Seleccione una variante diferente")
    items = db.query(DetalleVenta).filter_by(tenant_id=tenant_id, venta_id=venta.id,
                                             variante_id=data.variante_devuelta_id).order_by(DetalleVenta.id).all()
    if not items:
        raise HTTPException(404, "Variante no encontrada en venta")
    nueva = None
    if data.variante_nueva_id is not None:
        nueva = db.query(Variante).filter_by(tenant_id=tenant_id, id=data.variante_nueva_id, activo=True).first()
        if not nueva:
            raise HTTPException(404, "Variante nueva no encontrada en catálogo")
    ya_cambiadas = db.query(CambioPrenda).filter_by(tenant_id=tenant_id, venta_id=venta.id,
                                                    variante_devuelta_id=data.variante_devuelta_id).count()
    if ya_cambiadas >= sum(detalle.cantidad for detalle in items):
        raise HTTPException(409, "Ya se cambiaron todas las unidades de esta variante")
    restante = ya_cambiadas
    item = items[0]
    for detalle in items:
        if restante < detalle.cantidad:
            item = detalle
            break
        restante -= detalle.cantidad
    v_ids = [data.variante_devuelta_id]
    if data.variante_nueva_id is not None:
        v_ids.append(data.variante_nueva_id)
    consulta_inv = db.query(Inventario).filter(Inventario.tenant_id == tenant_id,
        Inventario.sucursal_id == venta.sucursal_id, Inventario.variante_id.in_(v_ids)).order_by(Inventario.variante_id)
    inventarios = (consulta_inv.with_for_update() if bloquear else consulta_inv).all()
    inv_vieja = next((i for i in inventarios if i.variante_id == data.variante_devuelta_id), None)
    inv_nueva = next((i for i in inventarios if i.variante_id == data.variante_nueva_id), None) if data.variante_nueva_id else None
    if data.variante_nueva_id is not None:
        if not inv_nueva or inv_nueva.stock - inv_nueva.reservado < 1:
            raise HTTPException(409, "Sin stock de la prenda nueva seleccionada")
        precio_nuevo, _ = precio_promocional(db, tenant_id, nueva.producto_id, nueva.precio)
        diferencia = precio_nuevo - item.precio_unitario
    else:
        precio_nuevo = 0.0
        diferencia = -item.precio_unitario
    return venta, tenant, item, inv_vieja, inv_nueva, precio_nuevo, diferencia


def cotizar_cambio(db: Session, tenant_id: int, data: schemas.CotizarIn):
    _, tenant, item, _, _, precio_nuevo, diferencia = _evaluar(db, tenant_id, data)
    es_devolucion = data.variante_nueva_id is None
    aviso = ("Devolución monetaria en efectivo: entregar el dinero al cliente en caja; la prenda reingresa al inventario."
             if es_devolucion else "La diferencia se cobra o devuelve en caja.")
    return {"precio_pagado": float(item.precio_unitario), "precio_nuevo": float(precio_nuevo),
            "diferencia": float(diferencia), "cobrar": float(max(diferencia, 0)),
            "devolver": float(max(-diferencia, 0)), "plazo_dias": tenant.plazo_cambio_dias,
            "es_devolucion_monetaria": es_devolucion,
            "aviso": aviso}


def registrar_cambio(db: Session, tenant_id: int, data: schemas.CambioIn):
    venta, tenant, item, inv_vieja, inv_nueva, precio_nuevo, diferencia = _evaluar(db, tenant_id, data, bloquear=True)
    if data.diferencia_esperada is not None and data.diferencia_esperada != diferencia:
        raise HTTPException(409, "El precio cambió. Consulta la diferencia antes de registrar el cambio")
    if not inv_vieja:
        inv_vieja = Inventario(tenant_id=tenant_id, sucursal_id=venta.sucursal_id,
                               variante_id=data.variante_devuelta_id, stock=0, reservado=0, stock_min=0, stock_max=100)
        db.add(inv_vieja)
    cambio = CambioPrenda(tenant_id=tenant_id, venta_id=venta.id,
                          variante_devuelta_id=data.variante_devuelta_id,
                          variante_nueva_id=data.variante_nueva_id,
                          diferencia=diferencia, motivo=data.motivo)
    cambio.verificarPlazoYGuardar(db, venta, tenant.plazo_cambio_dias)
    inv_vieja.validarStockYGuardar(db, "DEVOLUCION", 1)
    db.add(MovimientoInventario(tenant_id=tenant_id, sucursal_id=venta.sucursal_id,
                                variante_id=data.variante_devuelta_id, tipo="DEVOLUCION", cantidad=1, motivo=f"Cambio/Devolución {venta.codigo}"))
    if inv_nueva and data.variante_nueva_id:
        inv_nueva.validarStockYGuardar(db, "SALIDA", 1)
        db.add(MovimientoInventario(tenant_id=tenant_id, sucursal_id=venta.sucursal_id,
                                    variante_id=data.variante_nueva_id, tipo="SALIDA", cantidad=1, motivo=f"Cambio {venta.codigo}"))
    db.commit()
    db.refresh(cambio)
    return cambio
