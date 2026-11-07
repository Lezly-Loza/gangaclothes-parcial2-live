from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso
from ...models import (Cliente, Color, DatosComplementarios, DetalleVenta, Envio, Pago, Producto,
                       Sucursal, Talla, Variante, Venta)

router = APIRouter(prefix="/envios", tags=["Envíos"])


class EnvioIn(BaseModel):
    codigo_venta: str = Field(min_length=1)
    sucursal_id: int
    direccion: str = Field(min_length=3, max_length=300)
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    referencia: str | None = Field(default=None, max_length=300)
    telefono_contacto: str | None = Field(default=None, max_length=50)


class AccionIn(BaseModel):
    repartidor: str | None = Field(default=None, max_length=200)
    motivo: str | None = Field(default=None, max_length=300)


def _salida(db, tid, envio):
    venta = db.query(Venta).filter_by(tenant_id=tid, id=envio.venta_id).first()
    suc = db.query(Sucursal).filter_by(tenant_id=tid, id=venta.sucursal_id).first()
    extra = db.query(DatosComplementarios).filter_by(tenant_id=tid, tipo="sucursales", registro_id=suc.id).first()
    datos = extra.datos if extra else {}
    cliente = db.query(Cliente).filter_by(tenant_id=tid, id=venta.cliente_id).first() if venta.cliente_id else None
    pago = db.query(Pago).filter_by(tenant_id=tid, venta_id=venta.id, estado="APROBADO").first()
    prendas = []
    for d in db.query(DetalleVenta).filter_by(tenant_id=tid, venta_id=venta.id).all():
        v = db.query(Variante).filter_by(tenant_id=tid, id=d.variante_id).first()
        p = db.query(Producto).filter_by(tenant_id=tid, id=v.producto_id).first() if v else None
        talla = db.query(Talla).filter_by(tenant_id=tid, id=v.talla_id).first() if v and v.talla_id else None
        color = db.query(Color).filter_by(tenant_id=tid, id=v.color_id).first() if v and v.color_id else None
        prendas.append({"id": d.id, "sku": v.sku if v else "", "prenda": p.nombre if p else "",
                        "talla": talla.nombre if talla else "—", "color": color.nombre if color else "—", "cantidad": d.cantidad})
    etiquetas = {"pendiente": "Pendiente", "asignado": "Asignado", "en_camino": "En camino", "entregado": "Entregado", "cancelado": "Cancelado"}
    return {"id": envio.id, "estado": envio.estado, "etiqueta_estado": etiquetas[envio.estado],
            "activo": envio.estado in {"pendiente", "asignado", "en_camino"}, "direccion": envio.direccion,
            "latitud": envio.latitud, "longitud": envio.longitud, "referencia": envio.referencia,
            "telefono_contacto": envio.telefono_contacto, "distancia_km": None, "costo_envio": 0, "express": False,
            "repartidor": envio.repartidor, "motivo_cancelacion": envio.motivo_cancelacion,
            "fecha_creacion": envio.fecha_creacion, "fecha_asignacion": envio.fecha_asignacion,
            "fecha_salida": envio.fecha_salida, "fecha_estimada": None, "fecha_entrega": envio.fecha_entrega,
            "sucursal": {"id": suc.id, "nombre": suc.nombre, "direccion": suc.direccion, "ciudad": suc.ciudad,
                         "telefono": datos.get("telefono"), "latitud": datos.get("latitud"), "longitud": datos.get("longitud")},
            "cliente": {"id": cliente.id, "nombre": cliente.nombre, "email": cliente.correo, "telefono": cliente.telefono} if cliente else None,
            "venta": {"id": venta.id, "estado": venta.estado, "canal": venta.origen, "fecha": venta.fecha,
                      "nro_comprobante": venta.codigo, "subtotal": float(venta.total), "descuento": 0,
                      "costo_envio": 0, "total": float(venta.total)}, "prendas": prendas,
            "pago": {"metodo": pago.metodo, "pasarela": None, "etiqueta": "Simulado (sin cobro real)" if (pago.referencia_pasarela or '').startswith('SIM-') else pago.metodo, "monto": float(pago.monto),
                     "referencia_externa": pago.referencia_pasarela, "fecha": None} if pago else None}


@router.get("")
def listar(sucursal_id: int, scope: TenantScope = Depends(require_permiso("envios:ver")), db: Session = Depends(get_db)):
    if not db.query(Sucursal).filter_by(tenant_id=scope.tenant_id, id=sucursal_id).first(): raise HTTPException(404, "Sucursal no encontrada")
    envios = db.query(Envio).join(Venta, Venta.id == Envio.venta_id).filter(Envio.tenant_id == scope.tenant_id,
                    Venta.tenant_id == scope.tenant_id, Venta.sucursal_id == sucursal_id).order_by(Envio.id.desc()).all()
    return [_salida(db, scope.tenant_id, e) for e in envios]


@router.post("", status_code=201)
def crear(body: EnvioIn, scope: TenantScope = Depends(require_permiso("envios:crear")), db: Session = Depends(get_db)):
    venta = db.query(Venta).filter_by(tenant_id=scope.tenant_id, codigo=body.codigo_venta.strip()).first()
    if not venta: raise HTTPException(404, "Venta no encontrada")
    if venta.sucursal_id != body.sucursal_id: raise HTTPException(409, "La venta pertenece a otra sucursal")
    if venta.estado != "CONFIRMADA" or not db.query(Pago).filter_by(tenant_id=scope.tenant_id, venta_id=venta.id, estado="APROBADO").first():
        raise HTTPException(409, "La venta debe estar confirmada y pagada")
    if db.query(Envio).filter_by(tenant_id=scope.tenant_id, venta_id=venta.id).first(): raise HTTPException(409, "La venta ya tiene un envío")
    envio = Envio(tenant_id=scope.tenant_id, venta_id=venta.id, **body.model_dump(exclude={"codigo_venta", "sucursal_id"}))
    db.add(envio); db.commit()
    return _salida(db, scope.tenant_id, envio)


@router.post("/{id}/{accion}")
def transicionar(id: int, accion: str, body: AccionIn, scope: TenantScope = Depends(require_permiso("envios:editar")), db: Session = Depends(get_db)):
    envio = db.query(Envio).filter_by(tenant_id=scope.tenant_id, id=id).with_for_update().first()
    if not envio: raise HTTPException(404, "Envío no encontrado")
    ahora = datetime.now(timezone.utc)
    if accion == "asignar" and envio.estado == "pendiente" and body.repartidor and len(body.repartidor.strip()) >= 3:
        envio.repartidor, envio.fecha_asignacion, envio.estado = body.repartidor.strip(), ahora, "asignado"
    elif accion == "en-camino" and envio.estado == "asignado": envio.fecha_salida, envio.estado = ahora, "en_camino"
    elif accion == "entregar" and envio.estado == "en_camino": envio.fecha_entrega, envio.estado = ahora, "entregado"
    elif accion == "cancelar" and envio.estado in {"pendiente", "asignado", "en_camino"}:
        envio.estado, envio.motivo_cancelacion = "cancelado", body.motivo
    else: raise HTTPException(409, "El envío no admite esa transición")
    db.commit()
    return _salida(db, scope.tenant_id, envio)
