"""Sincronización idempotente: las operaciones se confirman en una transacción."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_tenant
from ...models import CitaReserva, Cliente, Inventario, OperacionLog, Producto, Reserva, Sucursal, Variante, Venta
from ..productos.promociones import precio_promocional
from ..reservas import schemas as reserva_schemas, service as reservas
from ..ventas import schemas as venta_schemas, service as ventas
from ..ventas.tienda import variante_publicada

router = APIRouter(prefix='/offline', tags=['CU-20/23 Sincronización'])


class OperacionOfflineIn(BaseModel):
    uuid_operacion: UUID
    tipo: Literal['reserva', 'venta']
    sucursal_id: int
    variante_id: int
    cantidad: int = Field(gt=0, le=100)
    precio_unitario: Decimal = Field(ge=0, decimal_places=2, max_digits=12)
    monto_recibido: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    fecha_hora_prueba: datetime | None = None
    fecha_local: datetime


@router.post('/sincronizar')
def sincronizar(body: OperacionOfflineIn, scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    tid, uid = scope.tenant_id, scope.user_id
    uid_op = str(body.uuid_operacion)
    datos = body.model_dump(mode='json')
    previa = db.query(OperacionLog).filter_by(tenant_id=tid, uuid_operacion=uid_op).first()
    if previa:
        if previa.payload.get('usuario_id') != uid or previa.payload.get('datos') != datos:
            raise HTTPException(409, 'El identificador ya fue usado para otra operación')
        return {**previa.payload['resultado'], 'repetida': True}

    if body.tipo == 'reserva' and ('cliente' not in scope.roles or 'reservas:crear' not in scope.permisos):
        raise HTTPException(403, 'La reserva sin conexión requiere una cuenta de cliente autorizada')
    if body.tipo == 'venta' and ('ventas:crear' not in scope.permisos or not any(r not in ('cliente', 'proveedor') for r in scope.roles)):
        raise HTTPException(403, 'Solo el personal autorizado puede registrar ventas de contado')
    momento = datetime.now(timezone.utc)
    if body.fecha_local.tzinfo is None:
        raise HTTPException(422, 'La fecha de registro debe indicar la zona horaria')
    if body.fecha_local.astimezone(timezone.utc) > momento + timedelta(minutes=5):
        raise HTTPException(409, 'La fecha del dispositivo está adelantada; revisa su reloj antes de registrar otra operación')
    log = OperacionLog(tenant_id=tid, uuid_operacion=uid_op, tipo=body.tipo, estado='CONFIRMADA',
                       sincronizado_at=momento, payload={'usuario_id': uid, 'datos': datos})
    db.add(log)
    try:
        # El índice único serializa reintentos antes de validar el stock o el precio.
        # Si alguna validación posterior falla, toda esta transacción se revierte.
        db.flush()
    except IntegrityError:
        db.rollback()
        previa = db.query(OperacionLog).filter_by(tenant_id=tid, uuid_operacion=uid_op).first()
        if previa and previa.payload.get('usuario_id') == uid and previa.payload.get('datos') == datos:
            return {**previa.payload['resultado'], 'repetida': True}
        raise HTTPException(409, 'El identificador ya fue usado para otra operación')
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(503, 'El servidor está ocupado; conserva la operación y vuelve a intentar') from exc

    if not db.query(Sucursal).filter_by(tenant_id=tid, id=body.sucursal_id, activo=True).first():
        raise HTTPException(409, 'La sucursal ya no está disponible')
    if body.tipo == 'reserva':
        cliente = db.query(Cliente).filter_by(tenant_id=tid, user_id=uid).first()
        if not cliente: raise HTTPException(403, 'La cuenta no tiene cliente asociado')
        try:
            variante, _ = variante_publicada(db, tid, body.variante_id)
        except HTTPException as exc:
            if exc.status_code == 404:
                raise HTTPException(409, 'La prenda ya no está publicada o disponible') from exc
            raise
        if not body.fecha_hora_prueba or body.fecha_hora_prueba.tzinfo is not None:
            raise HTTPException(422, 'La fecha de visita debe ser una hora local')
        if body.fecha_hora_prueba <= (datetime.now(timezone.utc) - timedelta(hours=4)).replace(tzinfo=None):
            raise HTTPException(409, 'La fecha de visita ya pasó; crea una nueva reserva')
    else:
        cliente = None
        variante = db.query(Variante).filter_by(tenant_id=tid, id=body.variante_id, activo=True).first()
        if not variante: raise HTTPException(409, 'La variante ya no está disponible')
        if not db.query(Producto).filter_by(tenant_id=tid, id=variante.producto_id, activo=True).first():
            raise HTTPException(409, 'La prenda ya no está disponible')
        precio_actual, _ = precio_promocional(db, tid, variante.producto_id, variante.precio)
        if precio_actual != body.precio_unitario:
            raise HTTPException(409, f'El precio cambió: registrado Bs {body.precio_unitario}, actual Bs {precio_actual}. Revisa la operación antes de continuar')
        if body.monto_recibido is None or body.monto_recibido < precio_actual * body.cantidad:
            raise HTTPException(409, 'El efectivo registrado no cubre el total actual')

    inv = db.query(Inventario).filter_by(tenant_id=tid, sucursal_id=body.sucursal_id,
                                         variante_id=body.variante_id).with_for_update().first()
    if not inv or inv.stock - inv.reservado < body.cantidad:
        disponible = max(0, inv.stock - inv.reservado) if inv else 0
        raise HTTPException(409, f'Stock insuficiente: quedan {disponible} unidades en la sucursal')
    if db.query(Venta).filter_by(tenant_id=tid, uuid_operacion=uid_op).first() or db.query(Reserva).filter_by(tenant_id=tid, uuid_operacion=uid_op).first():
        raise HTTPException(409, 'El identificador ya pertenece a otra operación')

    try:
        # SQLite no implementa FOR UPDATE; vuelve a leer tras obtener el bloqueo de escritura.
        db.expire(inv)
        def finalizar(op):
            if body.tipo == 'reserva':
                op.fecha_limite = body.fecha_hora_prueba
                db.add(CitaReserva(tenant_id=tid, reserva_id=op.id, fecha_hora_prueba=body.fecha_hora_prueba))
            else:
                # La venta pertenece al día en que se cobró; el log conserva cuándo se sincronizó.
                op.fecha = body.fecha_local.astimezone(timezone.utc).replace(tzinfo=None)
            log.payload = {'usuario_id': uid, 'datos': datos,
                           'resultado': {'uuid_operacion': uid_op, 'tipo': body.tipo, 'codigo': op.codigo,
                                         'estado': 'CONFIRMADA', 'confirmada_en': momento.isoformat()}}
        if body.tipo == 'reserva':
            reservas.crear(db, tid, reserva_schemas.ReservaIn(sucursal_id=body.sucursal_id,
                variante_id=body.variante_id, cliente_id=cliente.id, cantidad=body.cantidad, uuid_operacion=uid_op), antes_de_guardar=finalizar)
        else:
            ventas.registrar_venta(db, tid, venta_schemas.VentaIn(sucursal_id=body.sucursal_id,
                forma_pago='EFECTIVO', monto_recibido=body.monto_recibido,
                items=[{'variante_id': body.variante_id, 'cantidad': body.cantidad}], uuid_operacion=uid_op), uid,
                antes_de_guardar=finalizar)
    except IntegrityError:
        db.rollback()
        previa = db.query(OperacionLog).filter_by(tenant_id=tid, uuid_operacion=uid_op).first()
        if previa and previa.payload.get('usuario_id') == uid and previa.payload.get('datos') == datos:
            return {**previa.payload['resultado'], 'repetida': True}
        raise HTTPException(409, 'El identificador ya fue usado para otra operación')
    return {**log.payload['resultado'], 'repetida': False}
