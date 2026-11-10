"""Pasarelas de prueba compartidas por web y Flutter."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_roles
from ...models import Pago, Venta
from ..ventas.tienda import CompraIn
from . import checkout, qr_bcp, stripe_gw

router = APIRouter(prefix='/pagos', tags=['Pagos de tienda'])
cliente_scope = require_roles('cliente')


class TarjetaIn(CompraIn):
    numero_tarjeta: str = Field(min_length=13, max_length=25)


class SimularQrIn(BaseModel):
    qr_id: str
    estado: str = Field(pattern='^(C|P|V|A)$')


@router.get('/metodos')
def metodos():
    return {'tarjeta': stripe_gw.estado_del_servicio(),
            'qr': qr_bcp.estado_del_servicio()}


@router.post('/tarjeta')
def tarjeta(body: TarjetaIn, scope: TenantScope = Depends(cliente_scope),
            db: Session = Depends(get_db)):
    return checkout.pagar_tarjeta(db, scope, body)


@router.post('/qr')
def generar_qr(body: CompraIn, scope: TenantScope = Depends(cliente_scope),
               db: Session = Depends(get_db)):
    return checkout.generar_qr(db, scope, body)


@router.get('/qr/{qr_id}')
def consultar_qr(qr_id: str, scope: TenantScope = Depends(cliente_scope),
                db: Session = Depends(get_db)):
    return checkout.resolver_qr(db, scope, qr_id)


@router.post('/qr/simular')
def simular_qr(body: SimularQrIn, scope: TenantScope = Depends(cliente_scope),
               db: Session = Depends(get_db)):
    if qr_bcp.modo() != 'simulado':
        raise HTTPException(404, 'La simulación de QR no está disponible')
    propio = (db.query(Pago).join(Venta, Pago.venta_id == Venta.id)
        .filter(Pago.tenant_id == scope.tenant_id, Venta.tenant_id == scope.tenant_id,
                Venta.usuario_id == scope.user_id, Pago.referencia_pasarela == body.qr_id,
                Pago.metodo == 'QR').first())
    if propio is None:
        raise HTTPException(404, 'QR no encontrado para esta cuenta')
    try:
        qr_bcp.marcar_simulado(body.qr_id, body.estado)
    except Exception as exc:
        raise HTTPException(400, 'No se pudo simular el QR') from exc
    return checkout.resolver_qr(db, scope, body.qr_id)
