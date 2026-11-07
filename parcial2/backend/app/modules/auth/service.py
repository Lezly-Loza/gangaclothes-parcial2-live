from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from sqlalchemy import func
from ...core.security import create_access_token, hash_password, verify_password
from ...models import Cliente, PerfilUsuario, SuperAdmin, Tenant, User
from . import schemas


_CREDS_INVALID = "Credenciales invalidas"


def registrar_cliente(db: Session, data: schemas.RegistroClienteIn) -> schemas.TokenOut:
    from ..seguridad.service import asignar_roles, asegurar_roles
    from ..suscripciones.service import exigir_capacidad
    tenant = db.query(Tenant).filter_by(codigo=data.codigo_tenant.strip(), activo=True).first()
    if not tenant: raise HTTPException(404, "Empresa no encontrada")
    email, documento = str(data.email).strip().lower(), data.documento.strip()
    if not data.nombre.strip() or not documento: raise HTTPException(422, "Nombre y documento son obligatorios")
    if db.query(User).filter(User.tenant_id == tenant.id, func.lower(User.email) == email).first():
        raise HTTPException(409, "El correo ya está registrado en esta empresa")
    if db.query(Cliente).filter_by(tenant_id=tenant.id, documento=documento).first():
        raise HTTPException(409, "El documento ya está registrado en esta empresa")
    exigir_capacidad(db, tenant.id, "usuarios")
    asegurar_roles(db, tenant.id)
    nombre = " ".join(x for x in (data.nombre.strip(), (data.apellido or "").strip()) if x)
    user = User(tenant_id=tenant.id, nombre=nombre, email=email, password_hash=hash_password(data.password),
                rol="", activo=True, estado="activo")
    db.add(user); db.flush(); asignar_roles(db, user, ["cliente"])
    db.add(PerfilUsuario(tenant_id=tenant.id, usuario_id=user.id, apellido=data.apellido, telefono=data.telefono))
    db.add(Cliente(tenant_id=tenant.id, user_id=user.id, nombre=nombre, documento=documento,
                   correo=email, telefono=data.telefono))
    db.commit()
    return login_tenant(db, schemas.LoginIn(codigo_tenant=tenant.codigo, email=email, password=data.password))


def login_tenant(db: Session, data: schemas.LoginIn) -> schemas.TokenOut:
    tenant = db.query(Tenant).filter(Tenant.codigo == data.codigo_tenant).first()
    if not tenant or not tenant.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _CREDS_INVALID)

    user = (
        db.query(User)
        .filter(User.tenant_id == tenant.id, User.email == data.email)
        .first()
    )
    if not user or not user.activo or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _CREDS_INVALID)

    from ..seguridad.service import permisos_usuario, roles_usuario
    roles = ["admin" if r.nombre == "administrador" else r.nombre for r in roles_usuario(db, user)]
    permisos = permisos_usuario(db, user)
    token = create_access_token({
        "kind": "tenant",
        "sub": str(user.id),
        "tenant_id": tenant.id,
        "roles": roles,
    })
    return schemas.TokenOut(
        access_token=token,
        kind="tenant",
        tenant_id=tenant.id,
        tenant_codigo=tenant.codigo,
        user_id=user.id,
        nombre=user.nombre,
        roles=roles,
        permisos=permisos,
    )


def login_super(db: Session, data: schemas.SuperLoginIn) -> schemas.TokenOut:
    super_user = db.query(SuperAdmin).filter(SuperAdmin.email == data.email).first()
    if not super_user or not super_user.activo or not verify_password(data.password, super_user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _CREDS_INVALID)

    token = create_access_token({
        "kind": "super",
        "sub": str(super_user.id),
        "roles": ["superadmin"],
    })
    return schemas.TokenOut(
        access_token=token,
        kind="super",
        user_id=super_user.id,
        nombre=super_user.nombre,
        roles=["superadmin"],
        permisos=["tenants:gestionar", "planes:gestionar"],
    )
