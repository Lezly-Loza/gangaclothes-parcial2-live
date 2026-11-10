"""Cobros de la tienda. La web y Flutter usan los mismos endpoints."""
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...models import (CarritoCliente, DescuentoVenta, DetalleVenta, Envio,
                       Inventario, MovimientoInventario, Pago, Variante, Venta)
from ..productos.promociones import precio_promocional
from ..ventas import schemas, service as ventas
from ..ventas.tienda import cliente, salida_carrito, sucursal, variante_publicada
from . import cliente_http, qr_bcp, stripe_gw


def _carrito(db: Session, scope, entrega):
    comprador = cliente(db, scope)
    cart = db.query(CarritoCliente).filter_by(tenant_id=scope.tenant_id,
        cliente_id=comprador.id).with_for_update().first()
    if cart is None or not cart.items:
        raise HTTPException(409, 'El carrito está vacío')
    if entrega.direccion is not None and (
        len(entrega.direccion.strip()) < 3 or entrega.latitud is None or entrega.longitud is None
    ):
        raise HTTPException(422, 'Indica dirección y coordenadas válidas para el envío')
    sucursal(db, scope.tenant_id, cart.sucursal_id)
    for item in cart.items:
        variante_publicada(db, scope.tenant_id, item['variante_id'])
    resumen = salida_carrito(db, scope.tenant_id, cart)
    if len(resumen['detalle']) != len(cart.items) or any(not i['alcanza'] for i in resumen['detalle']):
        raise HTTPException(409, 'Stock insuficiente o prenda no disponible')
    return comprador, cart, resumen


def _agregar_envio(db: Session, tenant_id: int, venta: Venta, entrega):
    if entrega.direccion is not None:
        db.add(Envio(tenant_id=tenant_id, venta_id=venta.id,
            direccion=entrega.direccion.strip(), latitud=entrega.latitud,
            longitud=entrega.longitud, referencia=entrega.referencia,
            telefono_contacto=entrega.telefono, estado='pendiente'))


def pagar_tarjeta(db: Session, scope, body):
    comprador, cart, _ = _carrito(db, scope, body)
    resultado_pasarela = {}

    def cobrar(venta_id, total):
        try:
            cobro = stripe_gw.cobrar(venta_id, float(total),
                f'GangaClothes venta #{venta_id}', body.numero_tarjeta)
        except cliente_http.ErrorPasarela as exc:
            db.rollback()
            if 'Amount must convert to at least' in exc.mensaje:
                raise HTTPException(422, 'El total no alcanza el mínimo que acepta Stripe en modo prueba') from exc
            raise HTTPException(502, 'Stripe no pudo procesar el pago de prueba. Intenta otra vez') from exc
        resultado_pasarela.update(cobro.a_dict())
        return cobro.a_dict()

    def finalizar(venta):
        _agregar_envio(db, scope.tenant_id, venta, body)
        db.delete(cart)

    data = schemas.VentaIn(sucursal_id=cart.sucursal_id, cliente_id=comprador.id,
        forma_pago='EN_LINEA', items=list(cart.items), uuid_operacion=str(uuid4()))
    venta = ventas.registrar_venta(db, scope.tenant_id, data, scope.user_id,
        cobrador=cobrar, metodo_pago='TARJETA', antes_de_guardar=finalizar)
    return {'aprobado': True, 'codigo': venta.codigo, 'total': venta.total,
            'metodo': 'tarjeta', 'referencia': resultado_pasarela['referencia'],
            'simulado': resultado_pasarela['simulado']}


def _pago_pendiente(db: Session, scope, comprador):
    return (db.query(Pago, Venta).join(Venta, Pago.venta_id == Venta.id)
        .filter(Pago.tenant_id == scope.tenant_id, Venta.tenant_id == scope.tenant_id,
                Venta.cliente_id == comprador.id, Venta.estado == 'PENDIENTE',
                Pago.metodo == 'QR', Pago.estado == 'PENDIENTE')
        .order_by(Pago.id.desc()).first())


def generar_qr(db: Session, scope, body):
    comprador, cart, resumen = _carrito(db, scope, body)
    anterior = _pago_pendiente(db, scope, comprador)
    if anterior:
        pago, venta = anterior
        try:
            estado = qr_bcp.consultar(pago.referencia_pasarela, venta.id)
            if estado.estado == qr_bcp.EN_COLA:
                return {'venta_id': venta.id, **estado.a_dict()}
            resolver_qr(db, scope, pago.referencia_pasarela, estado=estado)
            if estado.aprobado:
                raise HTTPException(409, 'El QR anterior ya fue pagado; revisa Mis compras')
        except cliente_http.ErrorPasarela:
            _rechazar_qr(db, venta, pago)

    total = Decimal(str(resumen['total'])).quantize(Decimal('0.01'))
    venta = Venta(tenant_id=scope.tenant_id, codigo=f'V-{uuid4().hex[:10].upper()}',
        sucursal_id=cart.sucursal_id, usuario_id=scope.user_id, cliente_id=comprador.id,
        uuid_operacion=str(uuid4()), origen='EN_LINEA', forma_pago='QR',
        total=total, estado='PENDIENTE')
    db.add(venta)
    db.flush()
    for linea in resumen['detalle']:
        vid, cantidad = linea['variante_id'], linea['cantidad']
        inv = (db.query(Inventario).filter_by(tenant_id=scope.tenant_id,
            sucursal_id=cart.sucursal_id, variante_id=vid).with_for_update().first())
        if not inv or inv.stock - inv.reservado < cantidad:
            db.rollback()
            raise HTTPException(409, 'Stock insuficiente para generar el QR')
        inv.reservado += cantidad
        variante = db.query(Variante).filter_by(tenant_id=scope.tenant_id, id=vid).first()
        precio, promo = precio_promocional(db, scope.tenant_id, variante.producto_id, variante.precio)
        detalle = DetalleVenta(tenant_id=scope.tenant_id, venta_id=venta.id,
            variante_id=vid, cantidad=cantidad, precio_unitario=precio,
            subtotal=precio * cantidad)
        db.add(detalle)
        db.flush()
        if promo:
            db.add(DescuentoVenta(tenant_id=scope.tenant_id, detalle_venta_id=detalle.id,
                promocion_id=promo.id, promocion_nombre=promo.nombre,
                precio_lista=variante.precio,
                descuento=(variante.precio - precio) * cantidad))
    _agregar_envio(db, scope.tenant_id, venta, body)
    try:
        qr = qr_bcp.generar(venta.id, float(total), f'GangaClothes venta #{venta.id}')
    except cliente_http.ErrorPasarela as exc:
        db.rollback()
        raise HTTPException(502, 'No se pudo generar el QR. Revisa la configuración de BCP') from exc
    db.add(Pago(tenant_id=scope.tenant_id, venta_id=venta.id, metodo='QR',
        monto=total, referencia_pasarela=qr.id, estado='PENDIENTE'))
    db.commit()
    return {'venta_id': venta.id, 'codigo': venta.codigo, **qr.a_dict()}


def _rechazar_qr(db: Session, venta: Venta, pago: Pago):
    for detalle in db.query(DetalleVenta).filter_by(tenant_id=venta.tenant_id, venta_id=venta.id):
        inv = db.query(Inventario).filter_by(tenant_id=venta.tenant_id,
            sucursal_id=venta.sucursal_id, variante_id=detalle.variante_id).with_for_update().first()
        if inv:
            inv.reservado = max(0, inv.reservado - detalle.cantidad)
    venta.estado = 'ANULADA'
    pago.estado = 'RECHAZADO'
    envio = db.query(Envio).filter_by(tenant_id=venta.tenant_id, venta_id=venta.id).first()
    if envio:
        envio.estado = 'cancelado'
    db.commit()


def resolver_qr(db: Session, scope, qr_id: str, *, estado=None):
    comprador = cliente(db, scope)
    fila = (db.query(Pago, Venta).join(Venta, Pago.venta_id == Venta.id)
        .filter(Pago.tenant_id == scope.tenant_id, Venta.tenant_id == scope.tenant_id,
                Venta.cliente_id == comprador.id, Pago.metodo == 'QR',
                Pago.referencia_pasarela == qr_id).with_for_update().first())
    if fila is None:
        raise HTTPException(404, 'QR no encontrado para esta cuenta')
    pago, venta = fila
    if pago.estado == 'APROBADO':
        return {'aprobado': True, 'pendiente': False, 'rechazado': False,
                'estado': 'P', 'qr_id': qr_id, 'codigo': venta.codigo,
                'total': float(venta.total)}
    if pago.estado == 'RECHAZADO':
        return {'aprobado': False, 'pendiente': False, 'rechazado': True,
                'estado': 'V', 'qr_id': qr_id}
    try:
        cobro = estado or qr_bcp.consultar(qr_id, venta.id)
    except cliente_http.ErrorPasarela as exc:
        raise HTTPException(502, 'No se pudo consultar el estado del QR') from exc
    salida = {'venta_id': venta.id, 'codigo': venta.codigo, **cobro.a_dict()}
    if cobro.estado == qr_bcp.EN_COLA:
        return salida
    if cobro.rechazado:
        _rechazar_qr(db, venta, pago)
        return salida
    if not cobro.aprobado:
        return salida
    for detalle in db.query(DetalleVenta).filter_by(tenant_id=scope.tenant_id, venta_id=venta.id):
        inv = db.query(Inventario).filter_by(tenant_id=scope.tenant_id,
            sucursal_id=venta.sucursal_id, variante_id=detalle.variante_id).with_for_update().first()
        if not inv or inv.reservado < detalle.cantidad or inv.stock < detalle.cantidad:
            db.rollback()
            raise HTTPException(409, 'El QR fue pagado, pero el inventario cambió. Contacta a la tienda con el código de compra')
        inv.reservado -= detalle.cantidad
        inv.validarStockYGuardar(db, 'VENTA', detalle.cantidad)
        db.add(MovimientoInventario(tenant_id=scope.tenant_id,
            sucursal_id=venta.sucursal_id, variante_id=detalle.variante_id,
            tipo='VENTA', cantidad=detalle.cantidad, motivo=venta.codigo,
            usuario_id=scope.user_id))
    venta.estado = 'CONFIRMADA'
    pago.estado = 'APROBADO'
    cart = db.query(CarritoCliente).filter_by(tenant_id=scope.tenant_id,
        cliente_id=comprador.id).first()
    if cart and cart.sucursal_id == venta.sucursal_id:
        detalle = db.query(DetalleVenta).filter_by(tenant_id=scope.tenant_id, venta_id=venta.id).all()
        if sorted((i['variante_id'], i['cantidad']) for i in cart.items) == sorted((d.variante_id, d.cantidad) for d in detalle):
            db.delete(cart)
    db.commit()
    return {**salida, 'total': float(venta.total)}
