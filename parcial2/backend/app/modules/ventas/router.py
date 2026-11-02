from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_roles
from . import schemas, service

router = APIRouter(prefix="/ventas", tags=["CU-15/17 Ventas"])


@router.post("", response_model=schemas.VentaOut, status_code=201)
def registrar(body: schemas.VentaIn, scope: TenantScope = Depends(require_roles("vendedor", "cliente")), db: Session = Depends(get_db)):
    return service.registrar_venta(db, scope.tenant_id, body, scope.user_id)


@router.post("/{id}/anular", response_model=schemas.VentaOut)
def anular(id: int, body: schemas.AnularIn, scope: TenantScope = Depends(require_roles("encargado")), db: Session = Depends(get_db)):
    return service.anular_venta(db, scope.tenant_id, id, body.motivo, scope.user_id)
