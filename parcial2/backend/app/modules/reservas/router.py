from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso, require_tenant
from . import schemas, service
from ...models import Cliente, Reserva

router = APIRouter(prefix="/reservas", tags=["CU-14/17 Reservas"])


@router.get("")
def listar(sucursal_id: int, estado: str | None = None, scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    if "reservas:ver" not in scope.permisos and not {"ventas:crear", "clientes:ver"}.issubset(scope.permisos):
        raise HTTPException(403, "No tiene permiso para consultar reservas")
    from ...models import Sucursal
    if not db.query(Sucursal).filter_by(tenant_id=scope.tenant_id, id=sucursal_id).first():
        raise HTTPException(404, "Sucursal no encontrada")
    query = db.query(Reserva).filter_by(tenant_id=scope.tenant_id, sucursal_id=sucursal_id)
    if estado: query = query.filter_by(estado=estado.upper())
    return [service.salida_panel(db, scope.tenant_id, r) for r in query.order_by(Reserva.id.desc()).all()]


@router.get("/buscar/{codigo}", response_model=schemas.ReservaOut)
def buscar(codigo: str, scope: TenantScope = Depends(require_permiso("reservas:anular")), db: Session = Depends(get_db)):
    reserva = db.query(Reserva).filter_by(tenant_id=scope.tenant_id, codigo=codigo).first()
    if reserva is None:
        raise HTTPException(404, "Reserva no encontrada")
    return reserva


@router.post("", response_model=schemas.ReservaOut, status_code=201)
def crear(body: schemas.ReservaIn, scope: TenantScope = Depends(require_permiso("reservas:crear")), db: Session = Depends(get_db)):
    if "cliente" in scope.roles and "clientes:ver" not in scope.permisos:
        if not db.query(Cliente).filter_by(tenant_id=scope.tenant_id, id=body.cliente_id, user_id=scope.user_id).first():
            raise HTTPException(404, "Cliente no encontrado")
    return service.crear(db, scope.tenant_id, body)


@router.post("/{id}/anular", response_model=schemas.ReservaOut)
def anular(id: int, body: schemas.AnularIn, scope: TenantScope = Depends(require_permiso("reservas:anular")), db: Session = Depends(get_db)):
    return service.anular_reserva(db, scope.tenant_id, id, body.motivo)


@router.post("/{id}/{accion}")
def cambiar_estado(id: int, accion: str, scope: TenantScope = Depends(require_permiso("reservas:editar")), db: Session = Depends(get_db)):
    return service.transicion_panel(db, scope.tenant_id, id, accion)
