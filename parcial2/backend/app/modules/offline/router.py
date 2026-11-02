from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_roles
from ...models import Sucursal
from . import service

router = APIRouter(prefix="/offline", tags=["CU-18 Offline"])


@router.get("/catalogo")
def catalogo(sucursal_id: int, desde: datetime | None = None,
             scope: TenantScope = Depends(require_roles("vendedor")), db: Session = Depends(get_db)):
    if not db.query(Sucursal).filter_by(tenant_id=scope.tenant_id, id=sucursal_id).first():
        raise HTTPException(404, "Sucursal no encontrada")
    return service.obtener_catalogo_sucursal(db, scope.tenant_id, sucursal_id, desde)
