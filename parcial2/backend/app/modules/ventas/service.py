from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...models import (CambioPrenda, Cliente, DetalleVenta, Inventario, MovimientoInventario,
                       Pago, Sucursal, Variante, Venta)
from ..pasarela import service as pasarela
from . import schemas


def _out(venta):
    return schemas.VentaOut(id=venta.id, codigo=venta.codigo, total=float(venta.total),
                            estado=venta.estado, comprobante=f"Comprobante {venta.codigo}")


def registrar_venta(db: Session, tenant_id: int, data: schemas.VentaIn, usuario_id: int | None = None):
    if data.uuid_operacion:
        anterior = db.query(Venta).filter_by(tenant_id=tenant_id, uuid_operacion=data.uuid_operacion).first()
        if anterior:
            return _out(anterior)
    if not db.query(Sucursal).filter_by(id=data.sucursal_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "Sucursal no encontrada")
    if data.cliente_id and not db.query(Cliente).filter_by(id=data.cliente_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "Cliente no encontrado")
    if data.forma_pago not in {"EFECTIVO", "EN_LINEA"}:
        raise HTTPException(422, "Forma de pago inválida")
    items = []
    total = Decimal("0")
    for item in data.items:
        variante = db.query(Variante).filter_by(id=item.variante_id, tenant_id=tenant_id, activo=True).first()
        inv = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=data.sucursal_id,
                                             variante_id=item.variante_id).first()
        if not variante or not inv:
            raise HTTPException(404, "Variante o inventario no encontrado")
        items.append((item, variante, inv))
        total += variante.precio * item.cantidad
    venta = Venta(tenant_id=tenant_id, codigo=f"V-{uuid4().hex[:10].upper()}",
                  sucursal_id=data.sucursal_id, usuario_id=usuario_id, cliente_id=data.cliente_id,
                  uuid_operacion=data.uuid_operacion, origen="EN_LINEA", forma_pago=data.forma_pago,
                  total=total, estado="CONFIRMADA")
    venta.validarCobrarYGuardar(db, [(inv, item.cantidad) for item, _, inv in items])
    cobro = pasarela.crear_cobro(total) if data.forma_pago == "EN_LINEA" else {"aprobado": True, "referencia": None}
    if not cobro["aprobado"]:
        db.rollback()
        raise HTTPException(402, "Pago rechazado")
    for item, variante, inv in items:
        inv.validarStockYGuardar(db, "VENTA", item.cantidad)
        db.add(DetalleVenta(tenant_id=tenant_id, venta_id=venta.id, variante_id=variante.id,
                            cantidad=item.cantidad, precio_unitario=variante.precio,
                            subtotal=variante.precio * item.cantidad))
        db.add(MovimientoInventario(tenant_id=tenant_id, sucursal_id=data.sucursal_id,
                                    variante_id=variante.id, tipo="VENTA", cantidad=item.cantidad,
                                    motivo=venta.codigo, usuario_id=usuario_id))
    db.add(Pago(tenant_id=tenant_id, venta_id=venta.id, metodo=data.forma_pago, monto=total,
                referencia_pasarela=cobro["referencia"], estado="APROBADO"))
    db.commit()
    db.refresh(venta)
    return _out(venta)


def anular_venta(db: Session, tenant_id: int, id: int, motivo: str, usuario_id: int | None = None):
    venta = db.query(Venta).filter_by(id=id, tenant_id=tenant_id).first()
    if not venta:
        raise HTTPException(404, "Venta no encontrada")
    if db.query(CambioPrenda).filter_by(tenant_id=tenant_id, venta_id=id).first():
        raise HTTPException(409, "La venta tiene un cambio de prenda")
    detalles = db.query(DetalleVenta).filter_by(tenant_id=tenant_id, venta_id=id).all()
    reposiciones = []
    for item in detalles:
        inv = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=venta.sucursal_id,
                                             variante_id=item.variante_id).first()
        if inv is None:
            raise HTTPException(409, "Inventario no encontrado")
        reposiciones.append((inv, item.cantidad))
    venta.validarYRevertirStock(db, reposiciones, motivo, usuario_id)
    for item in detalles:
        db.add(MovimientoInventario(tenant_id=tenant_id, sucursal_id=venta.sucursal_id,
                                    variante_id=item.variante_id, tipo="DEVOLUCION",
                                    cantidad=item.cantidad, motivo=f"Anulación {venta.codigo}", usuario_id=usuario_id))
    db.commit()
    return _out(venta)
