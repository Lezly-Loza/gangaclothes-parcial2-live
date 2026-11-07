from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...models import (CambioPrenda, DetalleVenta, Inventario, MovimientoInventario,
                       Tenant, Variante, Venta)
from . import schemas


def obtener_venta(db: Session, tenant_id: int, codigo: str):
    venta = db.query(Venta).filter_by(tenant_id=tenant_id, codigo=codigo).first()
    if venta is None:
        raise HTTPException(404, "Venta no encontrada")
    return venta


def verificar_plazo(venta: Venta, plazo_dias: int):
    fecha = venta.fecha.replace(tzinfo=timezone.utc) if venta.fecha.tzinfo is None else venta.fecha
    if datetime.now(timezone.utc) - fecha > timedelta(days=plazo_dias):
        raise HTTPException(409, "Fuera de plazo")


def registrar_cambio(db: Session, tenant_id: int, data: schemas.CambioIn):
    venta = db.query(Venta).filter_by(tenant_id=tenant_id, id=data.venta_id).first()
    if not venta:
        raise HTTPException(404, "Venta no encontrada")
    if venta.estado == "ANULADA":
        raise HTTPException(409, "Venta anulada")
    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    verificar_plazo(venta, tenant.plazo_cambio_dias)
    item = db.query(DetalleVenta).filter_by(tenant_id=tenant_id, venta_id=venta.id,
                                            variante_id=data.variante_devuelta_id).first()
    nueva = db.query(Variante).filter_by(tenant_id=tenant_id, id=data.variante_nueva_id).first()
    if not item or not nueva:
        raise HTTPException(404, "Variante no encontrada en venta o catálogo")
    inv_vieja = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=venta.sucursal_id,
                                               variante_id=data.variante_devuelta_id).first()
    inv_nueva = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=venta.sucursal_id,
                                               variante_id=data.variante_nueva_id).first()
    if not inv_nueva or inv_nueva.stock - inv_nueva.reservado < 1:
        raise HTTPException(409, "Sin stock")
    if not inv_vieja:
        inv_vieja = Inventario(tenant_id=tenant_id, sucursal_id=venta.sucursal_id,
                               variante_id=data.variante_devuelta_id, stock=0, reservado=0, stock_min=0, stock_max=100)
        db.add(inv_vieja)
    cambio = CambioPrenda(tenant_id=tenant_id, venta_id=venta.id,
                          variante_devuelta_id=data.variante_devuelta_id,
                          variante_nueva_id=data.variante_nueva_id,
                          diferencia=nueva.precio - item.precio_unitario, motivo=data.motivo)
    cambio.verificarPlazoYGuardar(db, venta, tenant.plazo_cambio_dias)
    inv_vieja.validarStockYGuardar(db, "DEVOLUCION", 1)
    inv_nueva.validarStockYGuardar(db, "SALIDA", 1)
    for variante_id, tipo in ((data.variante_devuelta_id, "DEVOLUCION"), (data.variante_nueva_id, "SALIDA")):
        db.add(MovimientoInventario(tenant_id=tenant_id, sucursal_id=venta.sucursal_id,
                                    variante_id=variante_id, tipo=tipo, cantidad=1, motivo=f"Cambio {venta.codigo}"))
    db.commit()
    db.refresh(cambio)
    return cambio
