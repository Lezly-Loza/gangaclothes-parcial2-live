from fastapi import HTTPException
from sqlalchemy.orm import Session
from ...models import Cliente, User
from . import schemas


def buscar(db: Session, tenant_id: int, q: str = ""):
    query = db.query(Cliente).filter_by(tenant_id=tenant_id)
    if q:
        query = query.filter((Cliente.nombre.ilike(f"%{q}%")) | (Cliente.documento.ilike(f"%{q}%")))
    return query.order_by(Cliente.id).all()


def crear(db: Session, tenant_id: int, data: schemas.ClienteIn):
    previa = db.query(Cliente).filter_by(tenant_id=tenant_id, documento=data.documento).first()
    if previa:
        raise HTTPException(409, {"mensaje": "Documento repetido", "cliente_id": previa.id})
    if data.user_id and not db.query(User).filter_by(tenant_id=tenant_id, id=data.user_id).first():
        raise HTTPException(404, "Usuario no encontrado")
    row = Cliente(tenant_id=tenant_id, **data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def actualizar(db: Session, tenant_id: int, id: int, data: schemas.ClienteUpdateIn):
    row = db.query(Cliente).filter_by(tenant_id=tenant_id, id=id).first()
    if not row:
        raise HTTPException(404, "Cliente no encontrado")
    if data.documento and db.query(Cliente).filter(Cliente.tenant_id == tenant_id, Cliente.documento == data.documento, Cliente.id != id).first():
        raise HTTPException(409, "Documento repetido")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(row, key, val)
    db.commit()
    return row
