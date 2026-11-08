"""Catálogo de la tienda para la empresa de la sesión autenticada."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_tenant
from ...models import Categoria, Color, DatosComplementarios, Inventario, PrendaResena, Producto, Sucursal, Talla, Temporada, Variante
from .promociones import precio_promocional

router = APIRouter(prefix='/catalogo', tags=['Catálogo de la tienda'])


@router.get('/opciones')
def opciones(scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    def filas(modelo):
        return [{'id': x.id, 'nombre': x.nombre, 'activo': x.activo,
                 **({'codigo_hex': x.codigo_hex} if isinstance(x, Color) else {})}
                for x in db.query(modelo).filter_by(tenant_id=tid, activo=True).all()]
    return {'categorias': filas(Categoria), 'temporadas': filas(Temporada), 'tallas': filas(Talla),
            'colores': filas(Color), 'sucursales': filas(Sucursal)}


@router.get('')
def armar_catalogo(q: str | None = None, categoria_id: int | None = None, temporada_id: int | None = None,
                   talla_id: int | None = None, color_id: int | None = None, sucursal_id: int | None = None,
                   scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    sucursales = db.query(Sucursal).filter_by(tenant_id=tid, activo=True).all()
    por_sucursal = {s.id: s for s in sucursales}
    if sucursal_id is not None and sucursal_id not in por_sucursal:
        raise HTTPException(404, 'Sucursal no encontrada')
    consulta = db.query(Producto).filter_by(tenant_id=tid, activo=True)
    if categoria_id is not None: consulta = consulta.filter_by(categoria_id=categoria_id)
    if temporada_id is not None: consulta = consulta.filter_by(temporada_id=temporada_id)
    extras = {e.registro_id: e.datos or {} for e in db.query(DatosComplementarios).filter_by(tenant_id=tid, tipo='prendas').all()}
    resultado = []
    for p in consulta.order_by(Producto.nombre).all():
        extra = extras.get(p.id, {})
        if not extra.get('publicado', p.activo): continue
        if q and q.strip().lower() not in f"{p.nombre} {extra.get('marca') or ''} {p.descripcion or ''}".lower(): continue
        variantes = []
        for v in db.query(Variante).filter_by(tenant_id=tid, producto_id=p.id, activo=True).all():
            if talla_id is not None and v.talla_id != talla_id: continue
            if color_id is not None and v.color_id != color_id: continue
            talla = db.query(Talla).filter_by(tenant_id=tid, id=v.talla_id).first() if v.talla_id else None
            color = db.query(Color).filter_by(tenant_id=tid, id=v.color_id).first() if v.color_id else None
            stock = db.query(Inventario).filter_by(tenant_id=tid, variante_id=v.id).all()
            disponibilidad = [{'sucursal_id': i.sucursal_id, 'sucursal': por_sucursal[i.sucursal_id].nombre,
                               'disponible': max(0, i.stock-i.reservado)} for i in stock
                              if i.sucursal_id in por_sucursal and (sucursal_id is None or i.sucursal_id == sucursal_id)]
            disponible = sum(i['disponible'] for i in disponibilidad)
            if sucursal_id is not None and disponible <= 0: continue
            variantes.append({'id': v.id, 'sku': v.sku, 'talla_id': v.talla_id, 'talla': talla.nombre if talla else 'Sin talla',
                              'color_id': v.color_id, 'color': color.nombre if color else 'Sin color',
                              'color_hex': color.codigo_hex if color else None, 'imagen_url': None,
                              'disponible_total': disponible, 'disponibilidad': disponibilidad})
        if (sucursal_id is not None or talla_id is not None or color_id is not None) and not variantes: continue
        final, promo = precio_promocional(db, tid, p.id, p.precio_base)
        resenas_prod = db.query(PrendaResena).filter_by(tenant_id=tid, producto_id=p.id).all()
        calif_promedio = round(sum(r.calificacion for r in resenas_prod) / len(resenas_prod), 1) if resenas_prod else None
        resultado.append({'id': p.id, 'nombre': p.nombre, 'descripcion': p.descripcion, 'marca': extra.get('marca'),
                          'precio_venta': float(p.precio_base), 'precio_final': float(final),
                          'descuento': float(p.precio_base-final), 'imagen_url': p.imagen_url,
                          'categoria_id': p.categoria_id, 'coleccion_id': extra.get('coleccion_id'),
                          'calificacion_promedio': calif_promedio,
                          'calificacion_total': len(resenas_prod),
                          'promocion': {'id': promo.id, 'nombre': promo.nombre,
                            'etiqueta': f'{promo.valor:g}%' if promo.tipo_descuento == 'porcentaje' else f'Bs {promo.valor:g}',
                            'fecha_fin': promo.fecha_fin} if promo else None,
                          'disponible_total': sum(v['disponible_total'] for v in variantes), 'variantes': variantes})
    return resultado
