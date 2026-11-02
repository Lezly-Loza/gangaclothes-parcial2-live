from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_roles
from . import schemas, service
from ...models import DetalleVenta

router = APIRouter(tags=["CU-16 Cambios"])


@router.get("/ventas/{codigo}")
def obtener(codigo: str, scope: TenantScope = Depends(require_roles("vendedor", "admin")), db: Session = Depends(get_db)):
    venta = service.obtener_venta(db, scope.tenant_id, codigo)
    detalles = db.query(DetalleVenta).filter_by(tenant_id=scope.tenant_id, venta_id=venta.id).all()
    return {"id": venta.id, "codigo": venta.codigo, "total": float(venta.total), "estado": venta.estado,
            "detalles": [{"variante_id": d.variante_id, "cantidad": d.cantidad,
                          "precio_unitario": float(d.precio_unitario)} for d in detalles]}


@router.post("/cambios", status_code=201)
def registrar(body: schemas.CambioIn, scope: TenantScope = Depends(require_roles("vendedor", "admin")), db: Session = Depends(get_db)):
    return service.registrar_cambio(db, scope.tenant_id, body)
