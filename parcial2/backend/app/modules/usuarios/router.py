from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_roles
from . import schemas, service

router = APIRouter(prefix="/usuarios", tags=["CU-03 Usuarios"])


def _out(user):
    return {"id": user.id, "nombre": user.nombre, "email": user.email, "rol": user.rol, "activo": user.activo}


@router.get("")
def listar(scope: TenantScope = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return [_out(u) for u in service.listar(db, scope.tenant_id)]


@router.post("", status_code=201)
def crear(body: schemas.UsuarioIn, scope: TenantScope = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return _out(service.crear(db, scope.tenant_id, body))


@router.patch("/{id}")
def actualizar(id: int, body: schemas.UsuarioUpdateIn, scope: TenantScope = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return _out(service.actualizar(db, scope.tenant_id, id, body))


@router.post("/{id}/desactivar")
def desactivar(id: int, scope: TenantScope = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return _out(service.desactivar(db, scope.tenant_id, id))
