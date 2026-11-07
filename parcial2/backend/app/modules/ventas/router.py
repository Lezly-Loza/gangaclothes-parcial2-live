from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso
from . import schemas, service
from ...models import Cliente

router = APIRouter(prefix="/ventas", tags=["CU-15/17 Ventas"])


@router.post("", response_model=schemas.VentaOut, status_code=201)
def registrar(body: schemas.VentaIn, scope: TenantScope = Depends(require_permiso("ventas:crear")), db: Session = Depends(get_db)):
    if "cliente" in scope.roles and "clientes:ver" not in scope.permisos:
        cliente = db.query(Cliente).filter_by(tenant_id=scope.tenant_id, user_id=scope.user_id).first()
        if not cliente or (body.cliente_id is not None and body.cliente_id != cliente.id):
            raise HTTPException(404, "Cliente no encontrado")
        body = body.model_copy(update={"cliente_id": cliente.id})
    return service.registrar_venta(db, scope.tenant_id, body, scope.user_id)


@router.post("/{id}/anular", response_model=schemas.VentaOut)
def anular(id: int, body: schemas.AnularIn, scope: TenantScope = Depends(require_permiso("ventas:anular")), db: Session = Depends(get_db)):
    return service.anular_venta(db, scope.tenant_id, id, body.motivo, scope.user_id)
