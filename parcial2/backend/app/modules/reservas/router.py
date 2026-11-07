from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_roles
from . import schemas, service

router = APIRouter(prefix="/reservas", tags=["CU-14/17 Reservas"])


@router.post("", response_model=schemas.ReservaOut, status_code=201)
def crear(body: schemas.ReservaIn, scope: TenantScope = Depends(require_roles("cliente")), db: Session = Depends(get_db)):
    return service.crear(db, scope.tenant_id, body)


@router.post("/{id}/anular", response_model=schemas.ReservaOut)
def anular(id: int, body: schemas.AnularIn, scope: TenantScope = Depends(require_roles("encargado")), db: Session = Depends(get_db)):
    return service.anular_reserva(db, scope.tenant_id, id, body.motivo)
