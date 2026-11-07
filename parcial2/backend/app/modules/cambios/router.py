from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso, require_tenant
from . import schemas, service
from ...models import DetalleVenta, Reserva, Sucursal, Venta

router = APIRouter(tags=["CU-16 Cambios"])


@router.get("/operaciones/recientes")
def operaciones_recientes(tipo: str = "ventas", scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    if tipo == "ventas":
        if not any(p in scope.permisos for p in ("cambios:crear", "ventas:anular")):
            raise HTTPException(403, "No tiene permiso para consultar ventas")
        ventas = db.query(Venta).filter_by(tenant_id=scope.tenant_id).order_by(Venta.id.desc()).limit(100).all()
        return [{"codigo": v.codigo, "estado": v.estado, "fecha": v.fecha, "total": float(v.total),
                 "sucursal": (s.nombre if (s := db.query(Sucursal).filter_by(tenant_id=scope.tenant_id, id=v.sucursal_id).first()) else "")}
                for v in ventas]
    if tipo == "reservas":
        if "reservas:anular" not in scope.permisos: raise HTTPException(403, "No tiene permiso para consultar reservas")
        reservas = db.query(Reserva).filter_by(tenant_id=scope.tenant_id).order_by(Reserva.id.desc()).limit(100).all()
        return [{"codigo": r.codigo, "estado": r.estado, "fecha": r.fecha_limite, "total": None,
                 "sucursal": (s.nombre if (s := db.query(Sucursal).filter_by(tenant_id=scope.tenant_id, id=r.sucursal_id).first()) else "")}
                for r in reservas]
    raise HTTPException(422, "Tipo de operación inválido")


@router.get("/ventas/{codigo}")
def obtener(codigo: str, scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    if not any(p in scope.permisos for p in ("cambios:crear", "ventas:anular")):
        raise HTTPException(403, "No tiene permiso para consultar esta venta")
    venta = service.obtener_venta(db, scope.tenant_id, codigo)
    detalles = db.query(DetalleVenta).filter_by(tenant_id=scope.tenant_id, venta_id=venta.id).all()
    return {"id": venta.id, "codigo": venta.codigo, "sucursal_id": venta.sucursal_id, "total": float(venta.total), "estado": venta.estado,
            "detalles": [{"variante_id": d.variante_id, "cantidad": d.cantidad,
                          "precio_unitario": float(d.precio_unitario)} for d in detalles]}


@router.post("/cambios", status_code=201)
def registrar(body: schemas.CambioIn, scope: TenantScope = Depends(require_permiso("cambios:crear")), db: Session = Depends(get_db)):
    return service.registrar_cambio(db, scope.tenant_id, body)
