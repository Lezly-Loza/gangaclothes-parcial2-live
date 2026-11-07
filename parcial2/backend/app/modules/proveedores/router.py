from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_roles
from . import schemas, service

router = APIRouter(prefix="/proveedores", tags=["CU-10 Proveedores"])


def _out(p):
    return {"id": p.id, "razon_social": p.razon_social, "nit": p.nit, "contacto": p.contacto, "telefono": p.telefono, "correo": p.correo, "activo": p.activo}


@router.get("")
def listar(scope: TenantScope = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return [_out(p) for p in service.listar(db, scope.tenant_id)]


@router.post("", status_code=201)
def crear(body: schemas.ProveedorIn, scope: TenantScope = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return _out(service.crear(db, scope.tenant_id, body))


@router.patch("/{id}")
def actualizar(id: int, body: schemas.ProveedorUpdateIn, scope: TenantScope = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return _out(service.actualizar(db, scope.tenant_id, id, body))


@router.post("/{id}/desactivar")
def desactivar(id: int, scope: TenantScope = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return _out(service.desactivar(db, scope.tenant_id, id))
