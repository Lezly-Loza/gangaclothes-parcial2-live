from fastapi import HTTPException
from sqlalchemy.orm import Session
from ...models import Proveedor
from . import schemas


def listar(db: Session, tenant_id: int):
    return db.query(Proveedor).filter_by(tenant_id=tenant_id).order_by(Proveedor.id).all()


def crear(db: Session, tenant_id: int, data: schemas.ProveedorIn):
    if db.query(Proveedor).filter_by(tenant_id=tenant_id, nit=data.nit).first():
        raise HTTPException(409, "NIT repetido")
    row = Proveedor(tenant_id=tenant_id, **data.model_dump(), activo=True)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def actualizar(db: Session, tenant_id: int, id: int, data: schemas.ProveedorUpdateIn):
    row = db.query(Proveedor).filter_by(tenant_id=tenant_id, id=id).first()
    if not row:
        raise HTTPException(404, "Proveedor no encontrado")
    if data.nit and db.query(Proveedor).filter(Proveedor.tenant_id == tenant_id, Proveedor.nit == data.nit, Proveedor.id != id).first():
        raise HTTPException(409, "NIT repetido")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(row, key, val)
    db.commit()
    return row


def desactivar(db: Session, tenant_id: int, id: int):
    row = db.query(Proveedor).filter_by(tenant_id=tenant_id, id=id).first()
    if not row:
        raise HTTPException(404, "Proveedor no encontrado")
    row.activo = False
    db.commit()
    return row
