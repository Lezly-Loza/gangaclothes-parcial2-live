from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...models import Inventario, MovimientoInventario, Sucursal, Variante
from . import schemas


def _inventario(db: Session, tenant_id: int, sucursal_id: int, variante_id: int) -> Inventario:
    if not db.query(Sucursal).filter_by(id=sucursal_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "Sucursal no encontrada")
    if not db.query(Variante).filter_by(id=variante_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "Variante no encontrada")
    row = db.query(Inventario).filter_by(sucursal_id=sucursal_id, variante_id=variante_id, tenant_id=tenant_id).first()
    if row is None:
        row = Inventario(tenant_id=tenant_id, sucursal_id=sucursal_id, variante_id=variante_id,
                         stock=0, reservado=0, stock_min=0, stock_max=100)
        db.add(row)
        db.flush()
    return row


def consultar_stock(db: Session, tenant_id: int, sucursal_id: int):
    if not db.query(Sucursal).filter_by(id=sucursal_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "Sucursal no encontrada")
    return db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=sucursal_id).all()


def registrar_movimiento(db: Session, tenant_id: int, data: schemas.MovimientoIn, usuario_id: int | None = None):
    inv = _inventario(db, tenant_id, data.sucursal_id, data.variante_id)
    inv.validarStockYGuardar(db, data.tipo, data.cantidad)
    mov = MovimientoInventario(tenant_id=tenant_id, sucursal_id=data.sucursal_id,
                               variante_id=data.variante_id, tipo=data.tipo, cantidad=data.cantidad,
                               motivo=data.motivo, proveedor_id=data.proveedor_id, usuario_id=usuario_id)
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return schemas.MovimientoOut(id=mov.id, sucursal_id=mov.sucursal_id, variante_id=mov.variante_id,
                                 tipo=mov.tipo, cantidad=mov.cantidad, alerta_minimo=inv.stock < inv.stock_min)


def definir_stock_min_max(db: Session, tenant_id: int, data: schemas.MinMaxIn):
    if data.stock_min > data.stock_max:
        raise HTTPException(422, "stock_min supera stock_max")
    inv = _inventario(db, tenant_id, data.sucursal_id, data.variante_id)
    inv.stock_min, inv.stock_max = data.stock_min, data.stock_max
    db.commit()
    return inv
