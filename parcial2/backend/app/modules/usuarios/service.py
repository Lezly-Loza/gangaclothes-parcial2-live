from fastapi import HTTPException
from sqlalchemy.orm import Session
from ...core.security import hash_password
from ...models import User
from ..suscripciones.service import exigir_capacidad
from . import schemas

ROLES = {"admin", "encargado", "vendedor", "cliente"}


def listar(db: Session, tenant_id: int):
    return db.query(User).filter_by(tenant_id=tenant_id).order_by(User.id).all()


def crear(db: Session, tenant_id: int, data: schemas.UsuarioIn):
    exigir_capacidad(db, tenant_id, "usuarios")
    if data.rol not in ROLES:
        raise HTTPException(422, "Rol inválido")
    if db.query(User).filter_by(tenant_id=tenant_id, email=data.email).first():
        raise HTTPException(409, "Email ya registrado en el tenant")
    user = User(tenant_id=tenant_id, nombre=data.nombre, email=data.email,
                password_hash=hash_password(data.password), rol=data.rol, activo=True, estado="activo")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def actualizar(db: Session, tenant_id: int, id: int, data: schemas.UsuarioUpdateIn):
    user = db.query(User).filter_by(tenant_id=tenant_id, id=id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if user.rol == "admin" and user.activo and (data.activo is False or (data.rol is not None and data.rol != "admin")):
        if db.query(User).filter_by(tenant_id=tenant_id, rol="admin", activo=True).count() <= 1:
            raise HTTPException(409, "No se puede desactivar el último admin activo")
    for key, val in data.model_dump(exclude_unset=True).items():
        if key == "rol" and val not in ROLES:
            raise HTTPException(422, "Rol inválido")
        setattr(user, key, val)
    db.commit()
    return user


def desactivar(db: Session, tenant_id: int, id: int):
    user = db.query(User).filter_by(tenant_id=tenant_id, id=id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if user.rol == "admin" and user.activo and db.query(User).filter_by(tenant_id=tenant_id, rol="admin", activo=True).count() <= 1:
        raise HTTPException(409, "No se puede desactivar el último admin activo")
    user.activo, user.estado = False, "inactivo"
    db.commit()
    return user
