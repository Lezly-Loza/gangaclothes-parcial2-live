from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso, require_tenant
from . import schemas, service

router = APIRouter(prefix="/productos", tags=["CU-08 Productos"])


def _out(p):
    return {"id": p.id, "nombre": p.nombre, "descripcion": p.descripcion,
            "precio_base": float(p.precio_base), "activo": p.activo,
            "categoria_id": p.categoria_id, "temporada_id": p.temporada_id}


@router.get("")
def listar(scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    return [_out(p) for p in service.listar(db, scope.tenant_id)]


@router.get("/{id}")
def obtener(id: int, scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    return _out(service._get(db, scope.tenant_id, id))


@router.post("", status_code=201)
def crear(body: schemas.ProductoIn, scope: TenantScope = Depends(require_permiso("prendas:crear")), db: Session = Depends(get_db)):
    return _out(service.crear(db, scope.tenant_id, body))


@router.patch("/{id}")
def actualizar(id: int, body: schemas.ProductoUpdateIn, scope: TenantScope = Depends(require_permiso("prendas:editar")), db: Session = Depends(get_db)):
    return _out(service.actualizar(db, scope.tenant_id, id, body))


@router.post("/{id}/desactivar")
def desactivar(id: int, scope: TenantScope = Depends(require_permiso("prendas:eliminar")), db: Session = Depends(get_db)):
    return _out(service.desactivar(db, scope.tenant_id, id))


@router.post("/{id}/variantes", status_code=201)
def agregar_variantes(id: int, body: list[schemas.VarianteIn], scope: TenantScope = Depends(require_permiso("prendas:crear")), db: Session = Depends(get_db)):
    return [{"id": v.id, "sku": v.sku, "precio": float(v.precio)} for v in service.agregar_variantes(db, scope.tenant_id, id, body)]
