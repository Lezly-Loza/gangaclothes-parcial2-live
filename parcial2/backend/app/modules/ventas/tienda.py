from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_roles, require_tenant
from ...models import (CarritoCliente, CitaReserva, Cliente, Color, DatosComplementarios, DetalleReserva,
    DetalleVenta, Envio, Inventario, Pago, PrendaFavorita, PrendaResena, Producto, Reserva, Sucursal, Talla, User, Variante, Venta)
from ..productos.promociones import precio_promocional
from ..reservas import service as reservas
from . import schemas, service
from .envios import _salida as salida_envio

router = APIRouter(prefix='/tienda', tags=['Portal cliente'])
cliente_scope = require_roles('cliente')

class SucursalIn(BaseModel):
    sucursal_id: int

class ItemIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0, le=100)

class CantidadIn(BaseModel):
    cantidad: int = Field(gt=0, le=100)

class CompraIn(BaseModel):
    direccion: str | None = Field(default=None, max_length=300)
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    referencia: str | None = Field(default=None, max_length=300)
    telefono: str | None = Field(default=None, max_length=50)

class ResenaIn(BaseModel):
    calificacion: int = Field(ge=1, le=5)
    comentario: str = Field(min_length=3, max_length=1000)

class ReservaIn(BaseModel):
    sucursal_id: int
    fecha_hora_prueba: datetime
    notas: str | None = Field(default=None, max_length=500)
    detalle: list[ItemIn] = Field(min_length=1, max_length=20)


def cliente(db, scope):
    c = db.query(Cliente).filter_by(tenant_id=scope.tenant_id, user_id=scope.user_id).first()
    if c is None: raise HTTPException(403, 'La cuenta no tiene un cliente asociado')
    return c


def sucursal(db, tid, sid):
    s = db.query(Sucursal).filter_by(tenant_id=tid, id=sid, activo=True).first()
    if not s: raise HTTPException(404, 'Sucursal no encontrada')
    return s


def variante_publicada(db, tid, vid):
    v = db.query(Variante).filter_by(tenant_id=tid, id=vid, activo=True).first()
    p = db.query(Producto).filter_by(tenant_id=tid, id=v.producto_id, activo=True).first() if v else None
    extra = db.query(DatosComplementarios).filter_by(tenant_id=tid, tipo='prendas', registro_id=p.id).first() if p else None
    if not p or (extra and not (extra.datos or {}).get('publicado', p.activo)):
        raise HTTPException(404, 'Prenda no disponible')
    return v, p


def salida_carrito(db, tid, carrito):
    if not carrito: return None
    suc = db.query(Sucursal).filter_by(tenant_id=tid, id=carrito.sucursal_id).first()
    detalle = []
    for i in carrito.items:
        v = db.query(Variante).filter_by(tenant_id=tid, id=i['variante_id']).first()
        p = db.query(Producto).filter_by(tenant_id=tid, id=v.producto_id).first() if v else None
        if not v or not p: continue
        talla = db.query(Talla).filter_by(tenant_id=tid, id=v.talla_id).first()
        color = db.query(Color).filter_by(tenant_id=tid, id=v.color_id).first()
        inv = db.query(Inventario).filter_by(tenant_id=tid, sucursal_id=carrito.sucursal_id, variante_id=v.id).first()
        disponible = max(0, inv.stock - inv.reservado) if inv else 0
        extra = db.query(DatosComplementarios).filter_by(tenant_id=tid, tipo='prendas', registro_id=p.id).first()
        vigente = v.activo and p.activo and (not extra or (extra.datos or {}).get('publicado', p.activo))
        precio, promo = precio_promocional(db, tid, p.id, v.precio)
        detalle.append({'id': v.id, 'variante_id': v.id, 'sku': v.sku, 'prenda': p.nombre,
            'talla': talla.nombre if talla else 'Sin talla', 'color': color.nombre if color else 'Sin color',
            'cantidad': i['cantidad'], 'precio_unitario': float(v.precio), 'precio_final': float(precio),
            'descuento': float((v.precio-precio)*i['cantidad']), 'subtotal': float(precio*i['cantidad']),
            'disponible': disponible, 'alcanza': vigente and bool(suc and suc.activo) and disponible >= i['cantidad']})
    total = sum(d['subtotal'] for d in detalle)
    return {'id': carrito.id, 'sucursal_id': carrito.sucursal_id, 'sucursal': suc.nombre if suc else None,
            'unidades': sum(d['cantidad'] for d in detalle), 'total': total, 'detalle': detalle}


def obtener_carrito(db, scope):
    c = cliente(db, scope)
    return db.query(CarritoCliente).filter_by(tenant_id=scope.tenant_id, cliente_id=c.id).first()

@router.get('/carrito')
def ver_carrito(scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    return salida_carrito(db, scope.tenant_id, obtener_carrito(db, scope))

@router.post('/carrito')
def abrir_carrito(body: SucursalIn, scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    sucursal(db, tid, body.sucursal_id)
    c = cliente(db, scope)
    cart = obtener_carrito(db, scope)
    if cart is None:
        cart = CarritoCliente(tenant_id=tid, cliente_id=c.id, sucursal_id=body.sucursal_id, items=[])
        db.add(cart)
    else: cart.sucursal_id = body.sucursal_id
    db.commit(); db.refresh(cart)
    return salida_carrito(db, tid, cart)

@router.post('/carrito/items')
def agregar(body: ItemIn, scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    cart = obtener_carrito(db, scope)
    if cart is None: raise HTTPException(409, 'Selecciona una sucursal')
    variante_publicada(db, scope.tenant_id, body.variante_id)
    items = [dict(i) for i in cart.items]
    item = next((i for i in items if i['variante_id'] == body.variante_id), None)
    cantidad = body.cantidad + (item['cantidad'] if item else 0)
    inv = db.query(Inventario).filter_by(tenant_id=scope.tenant_id, sucursal_id=cart.sucursal_id, variante_id=body.variante_id).first()
    if not inv or cantidad > inv.stock-inv.reservado: raise HTTPException(409, 'Stock insuficiente en la sucursal')
    if item: item['cantidad'] = cantidad
    else: items.append({'variante_id': body.variante_id, 'cantidad': cantidad})
    cart.items = items; db.commit()
    return salida_carrito(db, scope.tenant_id, cart)

@router.put('/carrito/items/{vid}')
def cantidad(vid: int, body: CantidadIn, scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    cart = obtener_carrito(db, scope)
    if not cart or not any(i['variante_id'] == vid for i in cart.items): raise HTTPException(404, 'Prenda no encontrada en el carrito')
    variante_publicada(db, scope.tenant_id, vid)
    inv = db.query(Inventario).filter_by(tenant_id=scope.tenant_id, sucursal_id=cart.sucursal_id, variante_id=vid).first()
    if not inv or body.cantidad > inv.stock-inv.reservado: raise HTTPException(409, 'Stock insuficiente en la sucursal')
    cart.items = [{**i, 'cantidad': body.cantidad} if i['variante_id'] == vid else i for i in cart.items]
    db.commit(); return salida_carrito(db, scope.tenant_id, cart)

@router.delete('/carrito/items/{vid}')
def quitar(vid: int, scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    cart = obtener_carrito(db, scope)
    if not cart or not any(i['variante_id'] == vid for i in cart.items): raise HTTPException(404, 'Prenda no encontrada en el carrito')
    cart.items = [i for i in cart.items if i['variante_id'] != vid]
    db.commit(); return salida_carrito(db, scope.tenant_id, cart)

@router.post('/carrito/comprar')
def comprar(body: CompraIn, scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    c = cliente(db, scope)
    cart = db.query(CarritoCliente).filter_by(tenant_id=scope.tenant_id, cliente_id=c.id).with_for_update().first()
    if not cart or not cart.items: raise HTTPException(409, 'El carrito está vacío')
    if body.direccion is not None and (len(body.direccion.strip()) < 3 or body.latitud is None or body.longitud is None):
        raise HTTPException(422, 'Indica dirección y coordenadas válidas para el envío')
    sucursal(db, scope.tenant_id, cart.sucursal_id)
    for i in cart.items: variante_publicada(db, scope.tenant_id, i['variante_id'])
    data = schemas.VentaIn(sucursal_id=cart.sucursal_id, cliente_id=c.id, forma_pago='EN_LINEA',
                           items=cart.items, uuid_operacion=str(uuid4()))
    def finalizar(venta):
        if body.direccion is not None:
            db.add(Envio(tenant_id=scope.tenant_id, venta_id=venta.id, direccion=body.direccion.strip(),
                         latitud=body.latitud, longitud=body.longitud, referencia=body.referencia,
                         telefono_contacto=body.telefono, estado='pendiente'))
        db.delete(cart)
    resultado = service.registrar_venta(db, scope.tenant_id, data, scope.user_id,
                                        simular_pago=True, antes_de_guardar=finalizar)
    return {'codigo': resultado.codigo, 'total': resultado.total, 'mensaje': 'Compra de prueba registrada. No se cobró dinero.'}

@router.post('/reservas', status_code=201)
def crear_reserva(body: ReservaIn, scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    c = cliente(db, scope); sucursal(db, tid, body.sucursal_id)
    if body.fecha_hora_prueba.tzinfo is not None: raise HTTPException(422, 'La cita debe ser hora local de la sucursal')
    ahora = datetime.utcnow() - timedelta(hours=4)
    if body.fecha_hora_prueba <= ahora: raise HTTPException(422, 'La fecha debe ser futura')
    if len({i.variante_id for i in body.detalle}) != len(body.detalle): raise HTTPException(422, 'No repitas variantes')
    r = Reserva(tenant_id=tid, codigo=f'RES-{uuid4().hex[:10].upper()}', sucursal_id=body.sucursal_id,
                cliente_id=c.id, origen='EN_LINEA', estado='PENDIENTE', fecha_limite=body.fecha_hora_prueba)
    db.add(r); db.flush()
    for item in body.detalle:
        variante_publicada(db, tid, item.variante_id)
        inv = db.query(Inventario).filter_by(tenant_id=tid, sucursal_id=body.sucursal_id, variante_id=item.variante_id).with_for_update().first()
        if not inv or inv.stock-inv.reservado < item.cantidad: raise HTTPException(409, 'Stock insuficiente en la sucursal')
        inv.reservado += item.cantidad
        db.add(DetalleReserva(tenant_id=tid, reserva_id=r.id, variante_id=item.variante_id, cantidad=item.cantidad))
    db.add(CitaReserva(tenant_id=tid, reserva_id=r.id, fecha_hora_prueba=body.fecha_hora_prueba, notas=body.notas))
    db.commit(); return reservas.salida_panel(db, tid, r)

@router.get('/reservas')
def mis_reservas(scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    c = cliente(db, scope)
    return [reservas.salida_panel(db, scope.tenant_id, r) for r in db.query(Reserva).filter_by(tenant_id=scope.tenant_id, cliente_id=c.id).order_by(Reserva.id.desc()).all()]

@router.post('/reservas/{rid}/cancelar')
def cancelar(rid: int, scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    c = cliente(db, scope)
    if not db.query(Reserva).filter_by(tenant_id=scope.tenant_id, cliente_id=c.id, id=rid).first(): raise HTTPException(404, 'Reserva no encontrada')
    r = reservas.anular_reserva(db, scope.tenant_id, rid, 'Cancelada por el cliente')
    return reservas.salida_panel(db, scope.tenant_id, r)

@router.get('/compras')
def mis_compras(scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    c = cliente(db, scope); tid = scope.tenant_id
    resultado = []
    for v in db.query(Venta).filter_by(tenant_id=tid, cliente_id=c.id).order_by(Venta.id.desc()).all():
        suc = db.query(Sucursal).filter_by(tenant_id=tid, id=v.sucursal_id).first()
        envio = db.query(Envio).filter_by(tenant_id=tid, venta_id=v.id).first()
        detalle = []
        for d in db.query(DetalleVenta).filter_by(tenant_id=tid, venta_id=v.id).all():
            var = db.query(Variante).filter_by(tenant_id=tid, id=d.variante_id).first()
            p = db.query(Producto).filter_by(tenant_id=tid, id=var.producto_id).first() if var else None
            t = db.query(Talla).filter_by(tenant_id=tid, id=var.talla_id).first() if var else None
            col = db.query(Color).filter_by(tenant_id=tid, id=var.color_id).first() if var else None
            detalle.append({'id': d.id, 'sku': var.sku if var else '', 'prenda': p.nombre if p else '', 'talla': t.nombre if t else '', 'color': col.nombre if col else '', 'cantidad': d.cantidad, 'subtotal': float(d.subtotal)})
        pagos = db.query(Pago).filter_by(tenant_id=tid, venta_id=v.id).all()
        resultado.append({'id': v.id, 'estado': v.estado.lower(), 'fecha': v.fecha, 'sucursal': suc.nombre if suc else None,
            'unidades': sum(d['cantidad'] for d in detalle), 'subtotal': float(v.total), 'descuento': 0,
            'tipo_entrega': 'delivery' if envio else 'sucursal', 'costo_envio': 0,
            'envio': {'id': envio.id, 'estado': envio.estado, 'direccion': envio.direccion} if envio else None,
            'total': float(v.total), 'nro_comprobante': v.codigo, 'detalle': detalle,
            'pagos': [{'id': p.id, 'metodo': 'Simulado (sin cobro real)' if (p.referencia_pasarela or '').startswith('SIM-') else p.metodo,
                       'monto': float(p.monto), 'estado': p.estado.lower(), 'referencia_externa': p.referencia_pasarela} for p in pagos]})
    return resultado

@router.get('/pedidos')
def mis_pedidos(scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    c = cliente(db, scope); tid = scope.tenant_id
    envios = db.query(Envio).join(Venta, Venta.id == Envio.venta_id).filter(Envio.tenant_id == tid, Venta.tenant_id == tid, Venta.cliente_id == c.id).order_by(Envio.id.desc()).all()
    return [salida_envio(db, tid, e) for e in envios]


@router.get('/favoritos/ids')
def mis_favoritos_ids(scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    favs = db.query(PrendaFavorita).filter_by(tenant_id=scope.tenant_id, usuario_id=scope.user_id).all()
    return [f.producto_id for f in favs]


@router.get('/favoritos')
def mis_favoritos(scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    favs = db.query(PrendaFavorita).filter_by(tenant_id=tid, usuario_id=scope.user_id).order_by(PrendaFavorita.id.desc()).all()
    resultado = []
    extras = {e.registro_id: e.datos or {} for e in db.query(DatosComplementarios).filter_by(tenant_id=tid, tipo='prendas').all()}
    for f in favs:
        p = db.query(Producto).filter_by(tenant_id=tid, id=f.producto_id).first()
        if not p or not p.activo: continue
        extra = extras.get(p.id, {})
        final, promo = precio_promocional(db, tid, p.id, p.precio_base)
        variantes = db.query(Variante).filter_by(tenant_id=tid, producto_id=p.id, activo=True).all()
        stock_total = sum(i.stock - i.reservado for i in db.query(Inventario).filter(Inventario.tenant_id == tid, Inventario.variante_id.in_([v.id for v in variantes])).all()) if variantes else 0
        resultado.append({
            'favorito_id': f.id,
            'producto_id': p.id,
            'nombre': p.nombre,
            'descripcion': p.descripcion,
            'marca': extra.get('marca'),
            'imagen_url': p.imagen_url,
            'precio_base': float(p.precio_base),
            'precio_final': float(final),
            'en_promocion': bool(promo),
            'promocion_etiqueta': f'{promo.valor:g}%' if promo and promo.tipo_descuento == 'porcentaje' else (f'Bs {promo.valor:g}' if promo else None),
            'stock_disponible': max(0, stock_total),
            'fecha_guardado': f.fecha.isoformat(),
        })
    return resultado


@router.post('/favoritos/{producto_id}')
def agregar_favorito(producto_id: int, scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    p = db.query(Producto).filter_by(tenant_id=tid, id=producto_id, activo=True).first()
    if not p: raise HTTPException(404, 'Prenda no encontrada')
    existente = db.query(PrendaFavorita).filter_by(tenant_id=tid, usuario_id=scope.user_id, producto_id=producto_id).first()
    if not existente:
        nuevo = PrendaFavorita(tenant_id=tid, usuario_id=scope.user_id, producto_id=producto_id, fecha=datetime.utcnow())
        db.add(nuevo)
        db.commit()
    return {'ok': True, 'producto_id': producto_id, 'favorito': True}


@router.delete('/favoritos/{producto_id}')
def eliminar_favorito(producto_id: int, scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    existente = db.query(PrendaFavorita).filter_by(tenant_id=tid, usuario_id=scope.user_id, producto_id=producto_id).first()
    if existente:
        db.delete(existente)
        db.commit()
    return {'ok': True, 'producto_id': producto_id, 'favorito': False}


@router.get('/prendas/{producto_id}/resenas')
def ver_resenas(producto_id: int, scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    resenas = db.query(PrendaResena).filter_by(tenant_id=tid, producto_id=producto_id).order_by(PrendaResena.id.desc()).all()
    total = len(resenas)
    promedio = sum(r.calificacion for r in resenas) / total if total > 0 else 0.0
    return {
        'producto_id': producto_id,
        'total': total,
        'promedio': round(promedio, 1),
        'resenas': [{
            'id': r.id,
            'autor': r.autor_nombre,
            'calificacion': r.calificacion,
            'comentario': r.comentario,
            'fecha': r.fecha.isoformat(),
            'es_propia': (r.usuario_id == scope.user_id) if hasattr(scope, 'user_id') else False
        } for r in resenas]
    }


@router.post('/prendas/{producto_id}/resenas')
def crear_resena(producto_id: int, body: ResenaIn, scope: TenantScope = Depends(cliente_scope), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    p = db.query(Producto).filter_by(tenant_id=tid, id=producto_id, activo=True).first()
    if not p: raise HTTPException(404, 'Prenda no encontrada')
    u = db.query(User).filter_by(tenant_id=tid, id=scope.user_id).first()
    autor = u.nombre if u else 'Cliente'
    resena = PrendaResena(
        tenant_id=tid,
        producto_id=producto_id,
        usuario_id=scope.user_id,
        autor_nombre=autor,
        calificacion=body.calificacion,
        comentario=body.comentario.strip(),
        fecha=datetime.utcnow()
    )
    db.add(resena)
    db.commit()
    return {'ok': True, 'mensaje': 'Reseña registrada con éxito', 'id': resena.id}

