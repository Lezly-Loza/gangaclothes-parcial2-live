from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.deps import get_db, require_permiso
from ...core.database import TenantScope
from . import schemas, service

router = APIRouter(prefix="/inventario", tags=["CU-12 Inventario"])


@router.get("")
def consultar_stock(sucursal_id: int, scope: TenantScope = Depends(require_permiso("inventario:ver")), db: Session = Depends(get_db)):
    return service.consultar_stock(db, scope.tenant_id, sucursal_id)


@router.get("/alertas")
def consultar_alertas(sucursal_id: int, scope: TenantScope = Depends(require_permiso("inventario:ver")), db: Session = Depends(get_db)):
    return [fila for fila in service.consultar_stock(db, scope.tenant_id, sucursal_id) if fila["bajo_minimo"]]


@router.get("/movimientos")
def consultar_movimientos(sucursal_id: int, variante_id: int | None = None, scope: TenantScope = Depends(require_permiso("inventario:ver")), db: Session = Depends(get_db)):
    return service.consultar_movimientos(db, scope.tenant_id, sucursal_id, variante_id)


@router.post("/movimientos", response_model=schemas.MovimientoOut, status_code=201)
def registrar_movimiento(body: schemas.MovimientoIn, scope: TenantScope = Depends(require_permiso("inventario:crear")), db: Session = Depends(get_db)):
    return service.registrar_movimiento(db, scope.tenant_id, body, scope.user_id)


@router.post("/limites")
def definir_stock_min_max(body: schemas.MinMaxIn, scope: TenantScope = Depends(require_permiso("inventario:editar")), db: Session = Depends(get_db)):
    return service.definir_stock_min_max(db, scope.tenant_id, body)


@router.put("/{inventario_id}")
def actualizar_limites(inventario_id: int, body: schemas.LimitesPanel, scope: TenantScope = Depends(require_permiso("inventario:editar")), db: Session = Depends(get_db)):
    return service.actualizar_limites(db, scope.tenant_id, inventario_id, body)
