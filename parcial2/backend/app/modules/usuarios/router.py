from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso
from . import schemas, service
from ..seguridad import service as seguridad
from ...models import DatosComplementarios, PerfilUsuario

router = APIRouter(prefix="/usuarios", tags=["CU-03 Usuarios"])


def _autorizar_roles(scope, body):
    nombres = body.roles if body.roles is not None else ([body.rol] if body.rol else [])
    if nombres and "roles:editar" not in scope.permisos:
        raise HTTPException(403, "Se requiere permiso para asignar roles")
    if any(seguridad.normalizar(r) == "administrador" for r in nombres) and "admin" not in scope.roles:
        raise HTTPException(403, "Solo un administrador puede asignar el rol administrador")


def _out(user, db):
    perfil = db.query(PerfilUsuario).filter_by(tenant_id=user.tenant_id, usuario_id=user.id).first()
    proveedor = db.query(DatosComplementarios).filter_by(tenant_id=user.tenant_id, tipo="usuario_proveedor", registro_id=user.id).first()
    roles_list = [r.nombre for r in seguridad.roles_usuario(db, user)]
    roles_out = ["cajero" if r == "vendedor" else r for r in roles_list]
    rol_str = user.rol
    if "cajero" in roles_out or rol_str == "cajero" or rol_str == "vendedor":
        rol_str = "cajero"
    return {"id": user.id, "nombre": user.nombre, "email": user.email, "rol": rol_str,
            "roles": roles_out, "activo": user.activo,
            "apellido": perfil.apellido if perfil else None, "telefono": perfil.telefono if perfil else None,
            "proveedor_id": (proveedor.datos or {}).get("proveedor_id") if proveedor else None}


@router.get("")
def listar(scope: TenantScope = Depends(require_permiso("usuarios:ver")), db: Session = Depends(get_db)):
    return [_out(u, db) for u in service.listar(db, scope.tenant_id)]


@router.post("", status_code=201)
def crear(body: schemas.UsuarioIn, scope: TenantScope = Depends(require_permiso("usuarios:crear")), db: Session = Depends(get_db)):
    _autorizar_roles(scope, body)
    return _out(service.crear(db, scope.tenant_id, body, scope.user_id), db)


@router.patch("/{id}")
@router.put("/{id}")
def actualizar(id: int, body: schemas.UsuarioUpdateIn, scope: TenantScope = Depends(require_permiso("usuarios:editar")), db: Session = Depends(get_db)):
    if "roles" in body.model_fields_set or "rol" in body.model_fields_set:
        if "roles:editar" not in scope.permisos:
            raise HTTPException(403, "Se requiere permiso para modificar roles")
        _autorizar_roles(scope, body)
    return _out(service.actualizar(db, scope.tenant_id, id, body, scope.user_id), db)


@router.get("/{id}")
def obtener(id: int, scope: TenantScope = Depends(require_permiso("usuarios:ver")), db: Session = Depends(get_db)):
    user = db.query(service.User).filter_by(tenant_id=scope.tenant_id, id=id).first()
    if not user or not user.activo:
        raise HTTPException(404, "Usuario no encontrado")
    return _out(user, db)


@router.delete("/{id}", status_code=204)
def eliminar(id: int, scope: TenantScope = Depends(require_permiso("usuarios:eliminar")), db: Session = Depends(get_db)):
    if id == scope.user_id:
        raise HTTPException(400, "No puedes eliminar tu propia cuenta")
    user = db.query(service.User).filter_by(tenant_id=scope.tenant_id, id=id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    service.desactivar(db, scope.tenant_id, id, scope.user_id)
    return None


@router.post("/{id}/desactivar")
def desactivar(id: int, scope: TenantScope = Depends(require_permiso("usuarios:eliminar")), db: Session = Depends(get_db)):
    return _out(service.desactivar(db, scope.tenant_id, id, scope.user_id), db)
