from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_roles
from . import schemas, service

router = APIRouter(prefix="/catalogos", tags=["CU-09 Catálogos"])


def _out(row):
    return {"id": row.id, "nombre": row.nombre, "activo": row.activo}


@router.get("/{tipo}")
def listar_registros(tipo: str, scope: TenantScope = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return [_out(r) for r in service.listar_registros(db, scope.tenant_id, tipo)]


@router.post("/{tipo}", status_code=201)
def guardar_registro(tipo: str, body: schemas.RegistroIn, scope: TenantScope = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return _out(service.guardar_registro(db, scope.tenant_id, tipo, body))


@router.post("/{tipo}/{id}/desactivar")
def desactivar_registro(tipo: str, id: int, scope: TenantScope = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    return _out(service.desactivar_registro(db, scope.tenant_id, tipo, id))
