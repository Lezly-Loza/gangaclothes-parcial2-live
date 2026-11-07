from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso
from ...models import DatosComplementarios, Producto, Promocion, Variante

router = APIRouter(prefix='/promociones', tags=['Promociones'])


class PromocionIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, max_length=500)
    tipo_descuento: str | None = None
    valor: Decimal | None = Field(default=None, gt=0)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    activo: bool | None = None
    prenda_ids: list[int] | None = None


def hoy():
    return (datetime.now(timezone.utc) - timedelta(hours=4)).date()


def calcular(precio: Decimal, promo: Promocion) -> Decimal:
    descuento = precio * promo.valor / 100 if promo.tipo_descuento == 'porcentaje' else promo.valor
    return max(Decimal('0'), precio - descuento).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def precio_promocional(db: Session, tenant_id: int, producto_id: int, precio: Decimal):
    actual = hoy()
    promos = db.query(Promocion).filter(Promocion.tenant_id == tenant_id, Promocion.activo.is_(True),
                Promocion.fecha_inicio <= actual, Promocion.fecha_fin >= actual).all()
    aplicables = [p for p in promos if producto_id in p.prenda_ids]
    if not aplicables: return precio, None
    promo = min(aplicables, key=lambda p: (calcular(precio, p), p.id))
    return calcular(precio, promo), promo


def _salida(db, tid, promo):
    fecha = hoy()
    estado = ('inactiva' if not promo.activo else 'programada' if fecha < promo.fecha_inicio else
              'vencida' if fecha > promo.fecha_fin else 'vigente')
    prendas = []
    for p in db.query(Producto).filter(Producto.tenant_id == tid, Producto.id.in_(promo.prenda_ids)).all():
        extra = db.query(DatosComplementarios).filter_by(tenant_id=tid, tipo='prendas', registro_id=p.id).first()
        costo = (extra.datos or {}).get('costo') if extra else None
        final = calcular(p.precio_base, promo)
        prendas.append({'id': p.id, 'nombre': p.nombre, 'imagen_url': p.imagen_url, 'precio_venta': float(p.precio_base),
                        'precio_final': float(final), 'costo': float(costo) if costo is not None else 0,
                        'bajo_costo': costo is not None and final < Decimal(str(costo))})
    cruces = []
    if promo.activo:
        for otra in db.query(Promocion).filter_by(tenant_id=tid, activo=True).all():
            if otra.id == promo.id or otra.fecha_inicio > promo.fecha_fin or otra.fecha_fin < promo.fecha_inicio: continue
            ids = set(promo.prenda_ids) & set(otra.prenda_ids)
            nombres = [p['nombre'] for p in prendas if p['id'] in ids]
            if nombres: cruces.append({'promocion_id': otra.id, 'promocion': otra.nombre,
                                       'desde': max(promo.fecha_inicio, otra.fecha_inicio),
                                       'hasta': min(promo.fecha_fin, otra.fecha_fin), 'prendas': nombres})
    return {'id': promo.id, 'nombre': promo.nombre, 'descripcion': promo.descripcion,
            'tipo_descuento': promo.tipo_descuento, 'valor': float(promo.valor),
            'etiqueta': f'{promo.valor:g}%' if promo.tipo_descuento == 'porcentaje' else f'Bs {promo.valor:g}',
            'fecha_inicio': promo.fecha_inicio, 'fecha_fin': promo.fecha_fin, 'activo': promo.activo,
            'estado': estado, 'prenda_ids': promo.prenda_ids, 'prendas': prendas, 'solapamientos': cruces,
            'advertencia': 'Algunas prendas quedan por debajo de su costo.' if any(p['bajo_costo'] for p in prendas) else None}


def _cambios(db, tid, promo, body, nuevo=False):
    datos = body.model_dump(exclude_unset=True)
    for k, v in datos.items():
        if v is not None: setattr(promo, k, v)
    if not promo.nombre or not promo.nombre.strip() or promo.tipo_descuento not in {'porcentaje', 'monto'} or not promo.valor:
        raise HTTPException(422, 'Nombre, tipo y descuento son obligatorios')
    if promo.tipo_descuento == 'porcentaje' and promo.valor > 90: raise HTTPException(422, 'El porcentaje máximo es 90')
    if not promo.fecha_inicio or not promo.fecha_fin or promo.fecha_inicio > promo.fecha_fin:
        raise HTTPException(422, 'Fechas inválidas')
    if not promo.prenda_ids: raise HTTPException(422, 'Seleccione al menos una prenda')
    ids = set(promo.prenda_ids)
    consulta = db.query(Producto).filter(Producto.tenant_id == tid, Producto.id.in_(ids))
    if nuevo or 'prenda_ids' in datos or datos.get('activo') is True:
        consulta = consulta.filter(Producto.activo.is_(True))
    encontradas = consulta.all()
    if len(encontradas) != len(ids): raise HTTPException(404, 'Una prenda no pertenece a la empresa o está inactiva')
    variantes = db.query(Variante).filter(Variante.tenant_id == tid, Variante.producto_id.in_(ids), Variante.activo.is_(True)).all()
    if promo.activo is not False and (any(calcular(p.precio_base, promo) <= 0 for p in encontradas) or any(calcular(v.precio, promo) <= 0 for v in variantes)):
        raise HTTPException(422, 'El descuento debe dejar un precio mayor que cero')
    promo.prenda_ids = sorted(ids)
    promo.nombre = promo.nombre.strip()
    if nuevo: promo.activo = True


@router.get('')
def listar(scope: TenantScope = Depends(require_permiso('promociones:ver')), db: Session = Depends(get_db)):
    return [_salida(db, scope.tenant_id, p) for p in db.query(Promocion).filter_by(tenant_id=scope.tenant_id).order_by(Promocion.id.desc()).all()]


@router.post('', status_code=201)
def crear(body: PromocionIn, scope: TenantScope = Depends(require_permiso('promociones:crear')), db: Session = Depends(get_db)):
    promo = Promocion(tenant_id=scope.tenant_id); _cambios(db, scope.tenant_id, promo, body, True)
    db.add(promo); db.commit(); return _salida(db, scope.tenant_id, promo)


@router.put('/{id}')
def editar(id: int, body: PromocionIn, scope: TenantScope = Depends(require_permiso('promociones:editar')), db: Session = Depends(get_db)):
    promo = db.query(Promocion).filter_by(tenant_id=scope.tenant_id, id=id).first()
    if not promo: raise HTTPException(404, 'Promoción no encontrada')
    _cambios(db, scope.tenant_id, promo, body); db.commit(); return _salida(db, scope.tenant_id, promo)


@router.delete('/{id}')
def eliminar(id: int, scope: TenantScope = Depends(require_permiso('promociones:eliminar')), db: Session = Depends(get_db)):
    promo = db.query(Promocion).filter_by(tenant_id=scope.tenant_id, id=id).first()
    if not promo: raise HTTPException(404, 'Promoción no encontrada')
    promo.activo = False; db.commit()
    return {'detail': 'Promoción desactivada; se conserva el historial de ventas.', 'eliminada': False}
