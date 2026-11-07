from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.security import hash_password
from ...models import DatosComplementarios, PerfilUsuario, Proveedor, User
from ..seguridad import service as seguridad
from ..suscripciones.service import exigir_capacidad
from . import schemas


def listar(db: Session, tenant_id: int):
    return db.query(User).filter_by(tenant_id=tenant_id).order_by(User.id).all()


def _roles_solicitados(data):
    if data.roles is not None:
        return data.roles
    if data.rol is not None:
        return [data.rol] if data.rol else []
    return []


def _vincular_proveedor(db, tenant_id, user, proveedor_id):
    if proveedor_id is not None and not db.query(Proveedor).filter_by(tenant_id=tenant_id, id=proveedor_id, activo=True).first():
        raise HTTPException(404, "Proveedor no encontrado")
    extra = db.query(DatosComplementarios).filter_by(tenant_id=tenant_id, tipo="usuario_proveedor", registro_id=user.id).first()
    if extra is None:
        extra = DatosComplementarios(tenant_id=tenant_id, tipo="usuario_proveedor", registro_id=user.id, datos={})
        db.add(extra)
    extra.datos = {"proveedor_id": proveedor_id}


def _ultimo_admin(db: Session, tenant_id: int, user: User) -> bool:
    if not user.activo or not any(r.nombre == "administrador" for r in seguridad.roles_usuario(db, user)):
        return False
    return sum(any(r.nombre == "administrador" for r in seguridad.roles_usuario(db, u))
               for u in db.query(User).filter_by(tenant_id=tenant_id, activo=True).all()) <= 1


def crear(db: Session, tenant_id: int, data: schemas.UsuarioIn, actor_id: int | None = None):
    exigir_capacidad(db, tenant_id, "usuarios")
    email = str(data.email).lower()
    if db.query(User).filter(User.tenant_id == tenant_id, func.lower(User.email) == email).first():
        raise HTTPException(409, "Email ya registrado en el tenant")
    user = User(tenant_id=tenant_id, nombre=data.nombre, email=email,
                password_hash=hash_password(data.password), rol="", activo=True, estado="activo")
    db.add(user)
    db.flush()
    seguridad.asignar_roles(db, user, _roles_solicitados(data))
    if data.proveedor_id is not None:
        _vincular_proveedor(db, tenant_id, user, data.proveedor_id)
    db.add(PerfilUsuario(tenant_id=tenant_id, usuario_id=user.id, apellido=data.apellido, telefono=data.telefono))
    seguridad.registrar(db, tenant_id, actor_id, "USUARIOS", "CREAR", "usuario", user.id, f"Usuario {email} creado")
    db.commit()
    db.refresh(user)
    return user


def actualizar(db: Session, tenant_id: int, id: int, data: schemas.UsuarioUpdateIn, actor_id: int | None = None):
    user = db.query(User).filter_by(tenant_id=tenant_id, id=id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    campos = data.model_dump(exclude_unset=True)
    if "proveedor_id" in campos:
        _vincular_proveedor(db, tenant_id, user, campos["proveedor_id"])
    cambia_roles = "roles" in campos or "rol" in campos
    nuevos = _roles_solicitados(data) if cambia_roles else None
    pierde_admin = nuevos is not None and "administrador" not in [seguridad.normalizar(r) for r in nuevos]
    if (campos.get("activo") is False or pierde_admin) and _ultimo_admin(db, tenant_id, user):
        raise HTTPException(409, "No se puede desactivar o quitar el rol al último administrador activo")
    if campos.get("nombre") is not None:
        user.nombre = campos["nombre"]
    if campos.get("activo") is not None:
        user.activo = campos["activo"]
        user.estado = "activo" if user.activo else "inactivo"
    if cambia_roles:
        seguridad.asignar_roles(db, user, nuevos or [])
    if "apellido" in campos or "telefono" in campos:
        perfil = db.query(PerfilUsuario).filter_by(tenant_id=tenant_id, usuario_id=id).first()
        if not perfil:
            perfil = PerfilUsuario(tenant_id=tenant_id, usuario_id=id)
            db.add(perfil)
        for campo in ("apellido", "telefono"):
            if campo in campos:
                setattr(perfil, campo, campos[campo])
    seguridad.registrar(db, tenant_id, actor_id, "USUARIOS", "EDITAR", "usuario", user.id, f"Usuario {user.email} actualizado")
    db.commit()
    return user


def desactivar(db: Session, tenant_id: int, id: int, actor_id: int | None = None):
    return actualizar(db, tenant_id, id, schemas.UsuarioUpdateIn(activo=False), actor_id)
