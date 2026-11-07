from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ...models import Categoria, DatosComplementarios, Inventario, Producto, Temporada, Variante
from ..productos.promociones import precio_promocional


def obtener_catalogo_sucursal(db: Session, tenant_id: int, sucursal_id: int, desde: datetime | None,
                             categoria_id: int | None = None, temporada_id: int | None = None, solo_publicados: bool = False):
    query = db.query(Producto).filter_by(tenant_id=tenant_id, activo=True)
    if desde:
        query = query.filter(Producto.actualizado_en > desde)
    if categoria_id is not None: query = query.filter_by(categoria_id=categoria_id)
    if temporada_id is not None: query = query.filter_by(temporada_id=temporada_id)
    productos = query.all()
    if solo_publicados:
        extras = {x.registro_id: x.datos for x in db.query(DatosComplementarios).filter_by(tenant_id=tenant_id, tipo="prendas").all()}
        productos = [p for p in productos if extras.get(p.id, {}).get("publicado", p.activo)]
    ids = [p.id for p in productos]
    variantes = db.query(Variante).filter(Variante.tenant_id == tenant_id, Variante.producto_id.in_(ids),
                                          Variante.activo.is_(True)).all() if ids else []
    stocks = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=sucursal_id).all()
    por_variante = {i.variante_id: i for i in stocks}
    return {"fecha_descarga": datetime.now(timezone.utc).isoformat(),
            "categorias": [{"id": c.id, "nombre": c.nombre} for c in db.query(Categoria).filter_by(tenant_id=tenant_id, activo=True).all()],
            "temporadas": [{"id": t.id, "nombre": t.nombre} for t in db.query(Temporada).filter_by(tenant_id=tenant_id, activo=True).all()],
            "productos": [{"id": p.id, "nombre": p.nombre, "precio_base": float(precio_promocional(db, tenant_id, p.id, p.precio_base)[0]), "imagen_url": p.imagen_url,
                            "categoria_id": p.categoria_id, "temporada_id": p.temporada_id} for p in productos],
            "variantes": [{"id": v.id, "producto_id": v.producto_id, "sku": v.sku,
                           "precio": float(precio_promocional(db, tenant_id, v.producto_id, v.precio)[0]), "stock": max(0, por_variante[v.id].stock - por_variante[v.id].reservado) if v.id in por_variante else 0}
                          for v in variantes]}
