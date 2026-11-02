from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ...models import Inventario, Producto, Variante


def obtener_catalogo_sucursal(db: Session, tenant_id: int, sucursal_id: int, desde: datetime | None):
    query = db.query(Producto).filter_by(tenant_id=tenant_id, activo=True)
    if desde:
        query = query.filter(Producto.actualizado_en > desde)
    productos = query.all()
    ids = [p.id for p in productos]
    variantes = db.query(Variante).filter(Variante.tenant_id == tenant_id, Variante.producto_id.in_(ids),
                                          Variante.activo.is_(True)).all() if ids else []
    stocks = db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=sucursal_id).all()
    por_variante = {i.variante_id: i for i in stocks}
    return {"fecha_descarga": datetime.now(timezone.utc).isoformat(),
            "productos": [{"id": p.id, "nombre": p.nombre, "precio_base": float(p.precio_base),
                            "categoria_id": p.categoria_id, "temporada_id": p.temporada_id} for p in productos],
            "variantes": [{"id": v.id, "producto_id": v.producto_id, "sku": v.sku,
                           "precio": float(v.precio), "stock": por_variante[v.id].stock if v.id in por_variante else 0}
                          for v in variantes]}
