from datetime import date, datetime, time
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core import permisos
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso
from ...models import Bitacora, Rol
from . import service

router = APIRouter(prefix="/seguridad", tags=["Seguridad"])


class RolIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=50)
    descripcion: str | None = None
    permisos: list[str] = Field(default_factory=list)


class RolUpdateIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=50)
    descripcion: str | None = None
    activo: bool | None = None
    permisos: list[str] | None = None


@router.get("/permisos")
def listar_permisos(scope: TenantScope = Depends(require_permiso("roles:ver")), db: Session = Depends(get_db)):
    return permisos.catalogo()


@router.get("/roles")
def listar_roles(scope: TenantScope = Depends(require_permiso("roles:ver")), db: Session = Depends(get_db)):
    return [service.salida_rol(db, r) for r in db.query(Rol).filter_by(tenant_id=scope.tenant_id).order_by(Rol.id)]


@router.post("/roles", status_code=201)
def crear_rol(body: RolIn, scope: TenantScope = Depends(require_permiso("roles:crear")), db: Session = Depends(get_db)):
    return service.salida_rol(db, service.crear_rol(db, scope.tenant_id, body.nombre, body.descripcion, body.permisos, scope.user_id))


@router.put("/roles/{id}")
def editar_rol(id: int, body: RolUpdateIn, scope: TenantScope = Depends(require_permiso("roles:editar")), db: Session = Depends(get_db)):
    return service.salida_rol(db, service.actualizar_rol(db, scope.tenant_id, id, body.model_dump(exclude_unset=True), scope.user_id))


@router.delete("/roles/{id}")
def eliminar_rol(id: int, scope: TenantScope = Depends(require_permiso("roles:eliminar")), db: Session = Depends(get_db)):
    return service.eliminar_rol(db, scope.tenant_id, id, scope.user_id)


@router.get("/bitacora/filtros")
def filtros_bitacora(scope: TenantScope = Depends(require_permiso("bitacora:ver")), db: Session = Depends(get_db)):
    filas = db.query(Bitacora).filter_by(tenant_id=scope.tenant_id).all()
    return {"modulos": sorted({f.modulo for f in filas}), "acciones": sorted({f.accion for f in filas})}


@router.get("/bitacora")
def listar_bitacora(modulo: str | None = None, accion: str | None = None, desde: date | None = None,
                    hasta: date | None = None, limite: int = Query(200, ge=1, le=1000),
                    scope: TenantScope = Depends(require_permiso("bitacora:ver")), db: Session = Depends(get_db)):
    query = db.query(Bitacora).filter_by(tenant_id=scope.tenant_id)
    if modulo: query = query.filter(Bitacora.modulo == modulo.upper())
    if accion: query = query.filter(Bitacora.accion == accion.upper())
    if desde: query = query.filter(Bitacora.fecha >= datetime.combine(desde, time.min))
    if hasta: query = query.filter(Bitacora.fecha <= datetime.combine(hasta, time.max))
    return [{"id": f.id, "fecha": f.fecha.isoformat(), "actor": f.actor, "modulo": f.modulo,
             "accion": f.accion, "nivel": f.nivel, "entidad": f.entidad, "entidad_id": f.entidad_id,
             "detalle": f.detalle, "ip": f.ip} for f in query.order_by(Bitacora.id.desc()).limit(limite)]
