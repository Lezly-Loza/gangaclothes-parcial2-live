from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...models import (CambioPrenda, Cliente, DescuentoVenta, DetalleReserva, DetalleVenta, Envio, Inventario, MovimientoInventario,
                       Pago, Reserva, Sucursal, Variante, Venta)
from ..pasarela import service as pasarela
from ..productos.promociones import precio_promocional
from . import schemas


def _out(venta, db=None):
    items = []
    if db is not None:
        for d in db.query(DetalleVenta).filter_by(tenant_id=venta.tenant_id, venta_id=venta.id).all():
            descuento = db.query(DescuentoVenta).filter_by(tenant_id=venta.tenant_id, detalle_venta_id=d.id).first()
            items.append({'variante_id': d.variante_id, 'cantidad': d.cantidad, 'precio_unitario': float(d.precio_unitario),
                          'subtotal': float(d.subtotal), 'precio_lista': float(descuento.precio_lista) if descuento else float(d.precio_unitario),
                          'descuento': float(descuento.descuento) if descuento else 0, 'promocion': descuento.promocion_nombre if descuento else None})
    return schemas.VentaOut(id=venta.id, codigo=venta.codigo, total=float(venta.total),
                            estado=venta.estado, comprobante=f"Comprobante {venta.codigo}", items=items)


def registrar_venta(db: Session, tenant_id: int, data: schemas.VentaIn, usuario_id: int | None = None, *, simular_pago: bool = False, antes_de_guardar=None, cobrador=None, metodo_pago=None):
    if data.uuid_operacion:
        anterior = db.query(Venta).filter_by(tenant_id=tenant_id, uuid_operacion=data.uuid_operacion).first()
        if anterior:
            return _out(anterior, db)
    if not db.query(Sucursal).filter_by(id=data.sucursal_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "Sucursal no encontrada")
    if data.cliente_id and not db.query(Cliente).filter_by(id=data.cliente_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "Cliente no encontrado")
    if data.forma_pago not in {"EFECTIVO", "EN_LINEA"}:
        raise HTTPException(422, "Forma de pago inválida")
    if len({item.variante_id for item in data.items}) != len(data.items):
        raise HTTPException(422, "Agrupe las cantidades de cada variante")
    reserva = None
    if data.reserva_id is not None:
        reserva = db.query(Reserva).filter_by(tenant_id=tenant_id, id=data.reserva_id).with_for_update().first()
        if not reserva: raise HTTPException(404, "Reserva no encontrada")
        if reserva.estado != "PREPARADA" or reserva.sucursal_id != data.sucursal_id:
            raise HTTPException(409, "La reserva no está preparada en esta sucursal")
        if data.cliente_id is not None and data.cliente_id != reserva.cliente_id:
            raise HTTPException(404, "Reserva no encontrada")
        data = data.model_copy(update={"cliente_id": reserva.cliente_id})
        retenidas = db.query(DetalleReserva).filter_by(tenant_id=tenant_id, reserva_id=reserva.id).all()
        cantidades = {i.variante_id: i.cantidad for i in data.items}
        if any(cantidades.get(d.variante_id, 0) < d.cantidad for d in retenidas):
            raise HTTPException(409, "La venta debe incluir las prendas reservadas")
        for d in retenidas:
            inv = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=data.sucursal_id,
                                                 variante_id=d.variante_id).with_for_update().first()
            if not inv or inv.reservado < d.cantidad: raise HTTPException(409, "El stock reservado no coincide")
            inv.reservado -= d.cantidad
    items = []
    total = Decimal("0")
    for item in data.items:
        variante = db.query(Variante).filter_by(id=item.variante_id, tenant_id=tenant_id, activo=True).first()
        inv = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=data.sucursal_id,
                                             variante_id=item.variante_id).with_for_update().first()
        if not variante or not inv:
            raise HTTPException(404, "Variante o inventario no encontrado")
        precio, promo = precio_promocional(db, tenant_id, variante.producto_id, variante.precio)
        items.append((item, variante, inv, precio, promo))
        total += precio * item.cantidad
    if data.forma_pago == "EFECTIVO" and data.monto_recibido is not None and data.monto_recibido < total:
        raise HTTPException(409, "El monto recibido no cubre el total")
    venta = Venta(tenant_id=tenant_id, codigo=f"V-{uuid4().hex[:10].upper()}",
                  sucursal_id=data.sucursal_id, usuario_id=usuario_id, cliente_id=data.cliente_id,
                  uuid_operacion=data.uuid_operacion, origen="PRESENCIAL" if data.monto_recibido is not None else "EN_LINEA", forma_pago=data.forma_pago,
                  total=total, estado="CONFIRMADA")
    venta.validarCobrarYGuardar(db, [(inv, item.cantidad) for item, _, inv, _, _ in items])
    cobro = (cobrador(venta.id, total) if cobrador else
             ({"aprobado": True, "referencia": f"SIM-{uuid4().hex[:12]}"} if simular_pago else pasarela.crear_cobro(total))) if data.forma_pago == "EN_LINEA" else {"aprobado": True, "referencia": None}
    if not cobro["aprobado"]:
        db.rollback()
        raise HTTPException(402, cobro.get("motivo") or "Pago rechazado")
    for item, variante, inv, precio, promo in items:
        inv.validarStockYGuardar(db, "VENTA", item.cantidad)
        detalle = DetalleVenta(tenant_id=tenant_id, venta_id=venta.id, variante_id=variante.id,
                               cantidad=item.cantidad, precio_unitario=precio, subtotal=precio * item.cantidad)
        db.add(detalle); db.flush()
        if promo:
            db.add(DescuentoVenta(tenant_id=tenant_id, detalle_venta_id=detalle.id, promocion_id=promo.id,
                                  promocion_nombre=promo.nombre, precio_lista=variante.precio,
                                  descuento=(variante.precio - precio) * item.cantidad))
        db.add(MovimientoInventario(tenant_id=tenant_id, sucursal_id=data.sucursal_id,
                                    variante_id=variante.id, tipo="VENTA", cantidad=item.cantidad,
                                    motivo=venta.codigo, usuario_id=usuario_id))
    db.add(Pago(tenant_id=tenant_id, venta_id=venta.id, metodo=metodo_pago or data.forma_pago, monto=total,
                referencia_pasarela=cobro["referencia"], estado="APROBADO"))
    if reserva is not None:
        reserva.estado = "ATENDIDA"
    if antes_de_guardar is not None:
        antes_de_guardar(venta)
    db.commit()
    db.refresh(venta)
    return _out(venta, db)


def anular_venta(db: Session, tenant_id: int, id: int, motivo: str, usuario_id: int | None = None):
    venta = db.query(Venta).filter_by(id=id, tenant_id=tenant_id).first()
    if not venta:
        raise HTTPException(404, "Venta no encontrada")
    if db.query(CambioPrenda).filter_by(tenant_id=tenant_id, venta_id=id).first():
        raise HTTPException(409, "La venta tiene un cambio de prenda")
    envio = db.query(Envio).filter_by(tenant_id=tenant_id, venta_id=id).first()
    if envio and envio.estado != "cancelado":
        raise HTTPException(409, "La venta tiene un envío que no está cancelado")
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
    return _out(venta, db)
