from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso
from . import schemas, service

router = APIRouter(prefix="/clientes", tags=["CU-11 Clientes"])


def _out(c):
    return {"id": c.id, "nombre": c.nombre, "documento": c.documento, "telefono": c.telefono, "correo": c.correo, "user_id": c.user_id}


@router.get("")
def buscar(q: str = "", scope: TenantScope = Depends(require_permiso("clientes:ver")), db: Session = Depends(get_db)):
    return [_out(c) for c in service.buscar(db, scope.tenant_id, q)]


@router.post("", status_code=201)
def crear(body: schemas.ClienteIn, scope: TenantScope = Depends(require_permiso("clientes:crear")), db: Session = Depends(get_db)):
    return _out(service.crear(db, scope.tenant_id, body))


@router.patch("/{id}")
def actualizar(id: int, body: schemas.ClienteUpdateIn, scope: TenantScope = Depends(require_permiso("clientes:editar")), db: Session = Depends(get_db)):
    return _out(service.actualizar(db, scope.tenant_id, id, body))
