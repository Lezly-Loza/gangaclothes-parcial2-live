from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, get_scope, require_super
from ...models import Plan
from ..suscripciones.schemas import PlanOut


router = APIRouter(prefix="/planes", tags=["Planes"])


class PlanCreateIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: str | None = None
    max_sucursales: int = Field(ge=1)
    max_usuarios: int = Field(ge=1)
    max_productos: int = Field(ge=1)
    modulos: list[str] = Field(default_factory=list)
    precio_mensual: float = Field(ge=0)


class PlanUpdateIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    descripcion: str | None = None
    max_sucursales: int | None = Field(default=None, ge=1)
    max_usuarios: int | None = Field(default=None, ge=1)
    max_productos: int | None = Field(default=None, ge=1)
    modulos: list[str] | None = None
    precio_mensual: float | None = Field(default=None, ge=0)
    activo: bool | None = None


@router.get("", response_model=list[PlanOut])
def listar_planes(
    _: TenantScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    """Lista los planes del catalogo. Cualquier usuario autenticado puede verlos."""
    return db.query(Plan).order_by(Plan.precio_mensual).all()


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def crear_plan(
    body: PlanCreateIn,
    _: TenantScope = Depends(require_super),
    db: Session = Depends(get_db),
):
    """Solo el superadministrador configura los planes."""
    if db.query(Plan).filter(Plan.codigo == body.codigo).first():
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe un plan con codigo '{body.codigo}'")
    plan = Plan(
        codigo=body.codigo,
        nombre=body.nombre,
        descripcion=body.descripcion,
        max_sucursales=body.max_sucursales,
        max_usuarios=body.max_usuarios,
        max_productos=body.max_productos,
        modulos=list(body.modulos or []),
        precio_mensual=body.precio_mensual,
        activo=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.patch("/{plan_id}", response_model=PlanOut)
def actualizar_plan(
    plan_id: int,
    body: PlanUpdateIn,
    _: TenantScope = Depends(require_super),
    db: Session = Depends(get_db),
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    datos = body.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(plan, campo, valor)
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/{plan_id}/desactivar", response_model=PlanOut)
def desactivar_plan(
    plan_id: int,
    _: TenantScope = Depends(require_super),
    db: Session = Depends(get_db),
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    plan.activo = False
    db.commit()
    db.refresh(plan)
    return plan
