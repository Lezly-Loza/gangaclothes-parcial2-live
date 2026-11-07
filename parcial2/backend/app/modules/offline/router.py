from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_tenant
from ...models import Categoria, Sucursal, Temporada
from . import service

router = APIRouter(prefix="/offline", tags=["CU-18 Offline"])


@router.get("/opciones")
def opciones(scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    if not any(r in scope.roles for r in ("admin", "vendedor", "cliente")):
        raise HTTPException(403, "No tiene acceso al catálogo offline")
    return {"categorias": [{"id": x.id, "nombre": x.nombre} for x in db.query(Categoria).filter_by(tenant_id=scope.tenant_id, activo=True).all()],
            "temporadas": [{"id": x.id, "nombre": x.nombre} for x in db.query(Temporada).filter_by(tenant_id=scope.tenant_id, activo=True).all()]}


@router.get("/catalogo")
def catalogo(sucursal_id: int, desde: datetime | None = None, categoria_id: int | None = None,
             temporada_id: int | None = None,
             scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    if not any(r in scope.roles for r in ("admin", "vendedor", "cliente")):
        raise HTTPException(403, "Solo clientes y personal autorizado pueden descargar el catálogo")
    if not db.query(Sucursal).filter_by(tenant_id=scope.tenant_id, id=sucursal_id).first():
        raise HTTPException(404, "Sucursal no encontrada")
    solo_publicados = "cliente" in scope.roles and not any(r in scope.roles for r in ("admin", "vendedor"))
    return service.obtener_catalogo_sucursal(db, scope.tenant_id, sucursal_id, desde, categoria_id, temporada_id, solo_publicados)
