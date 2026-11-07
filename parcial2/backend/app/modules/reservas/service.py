from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...models import Cliente, DetalleReserva, Inventario, Reserva, Sucursal, Variante
from . import schemas


def crear(db: Session, tenant_id: int, data: schemas.ReservaIn):
    if data.uuid_operacion:
        previa = db.query(Reserva).filter_by(tenant_id=tenant_id, uuid_operacion=data.uuid_operacion).first()
        if previa:
            return previa
    for model, id_ in ((Cliente, data.cliente_id), (Sucursal, data.sucursal_id), (Variante, data.variante_id)):
        if not db.query(model).filter_by(id=id_, tenant_id=tenant_id).first():
            raise HTTPException(404, "Recurso no encontrado")
    inv = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=data.sucursal_id,
                                         variante_id=data.variante_id).first()
    if not inv:
        raise HTTPException(409, "Stock insuficiente en la sucursal")
    reserva = Reserva(tenant_id=tenant_id, codigo=f"RES-{uuid4().hex[:10].upper()}",
                      sucursal_id=data.sucursal_id, cliente_id=data.cliente_id,
                      uuid_operacion=data.uuid_operacion, origen="EN_LINEA", estado="PENDIENTE")
    reserva.validarStockYApartar(db, inv, data.cantidad)
    db.add(DetalleReserva(tenant_id=tenant_id, reserva_id=reserva.id,
                          variante_id=data.variante_id, cantidad=data.cantidad))
    db.commit()
    db.refresh(reserva)
    return reserva


def anular_reserva(db: Session, tenant_id: int, id: int, motivo: str):
    reserva = db.query(Reserva).filter_by(id=id, tenant_id=tenant_id).first()
    if not reserva:
        raise HTTPException(404, "Reserva no encontrada")
    if reserva.estado != "PENDIENTE":
        raise HTTPException(409, "La reserva ya no está pendiente")
    for item in db.query(DetalleReserva).filter_by(reserva_id=id, tenant_id=tenant_id):
        inv = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=reserva.sucursal_id,
                                             variante_id=item.variante_id).first()
        if inv:
            inv.reservado -= item.cantidad
    reserva.estado, reserva.motivo_anulacion = "ANULADA", motivo
    db.commit()
    return reserva
