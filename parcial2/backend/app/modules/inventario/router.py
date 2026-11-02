from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.deps import get_db, require_roles
from ...core.database import TenantScope
from . import schemas, service

router = APIRouter(prefix="/inventario", tags=["CU-12 Inventario"])


@router.get("")
def consultar_stock(sucursal_id: int, scope: TenantScope = Depends(require_roles("encargado", "admin")), db: Session = Depends(get_db)):
    return service.consultar_stock(db, scope.tenant_id, sucursal_id)


@router.post("/movimientos", response_model=schemas.MovimientoOut, status_code=201)
def registrar_movimiento(body: schemas.MovimientoIn, scope: TenantScope = Depends(require_roles("encargado", "admin")), db: Session = Depends(get_db)):
    return service.registrar_movimiento(db, scope.tenant_id, body, scope.user_id)


@router.post("/limites")
def definir_stock_min_max(body: schemas.MinMaxIn, scope: TenantScope = Depends(require_roles("encargado", "admin")), db: Session = Depends(get_db)):
    return service.definir_stock_min_max(db, scope.tenant_id, body)
