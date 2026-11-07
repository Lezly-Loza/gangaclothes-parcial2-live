from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso
from . import schemas, service


router = APIRouter(prefix="/suscripciones", tags=["CU-05/07 Suscripciones"])


@router.post("/contratar", response_model=schemas.SuscripcionOut)
def contratar(
    body: schemas.ContratarPlanIn,
    scope: TenantScope = Depends(require_permiso("suscripcion:gestionar")),
    db: Session = Depends(get_db),
):
    """CU-05: el administrador del tenant contrata un plan."""
    sub = service.contratar_plan(db, scope.tenant_id, body)
    db.refresh(sub)
    return schemas.SuscripcionOut(
        id=sub.id,
        plan=schemas.PlanOut.model_validate(sub.plan),
        fecha_inicio=sub.fecha_inicio,
        fecha_fin=sub.fecha_fin,
        estado=sub.estado,
    )


@router.get("/estado", response_model=schemas.EstadoSuscripcionOut)
def consultar_estado(
    scope: TenantScope = Depends(require_permiso("suscripcion:ver")),
    db: Session = Depends(get_db),
):
    """CU-07: estado del plan vigente + consumo real por cada limite."""
    return service.consumo(db, scope.tenant_id)


@router.post("/cambiar", response_model=schemas.SuscripcionOut)
def cambiar(body: schemas.CambiarPlanIn, scope: TenantScope = Depends(require_permiso("suscripcion:gestionar")), db: Session = Depends(get_db)):
    return service.cambiar_plan(db, scope.tenant_id, body)


@router.post("/renovar", response_model=schemas.SuscripcionOut)
def renovar(body: schemas.RenovarPlanIn, scope: TenantScope = Depends(require_permiso("suscripcion:gestionar")), db: Session = Depends(get_db)):
    return service.renovar_plan(db, scope.tenant_id, body)
