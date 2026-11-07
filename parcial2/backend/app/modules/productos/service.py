from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ...models import Categoria, Color, Producto, Talla, Temporada, Variante
from ..suscripciones.service import exigir_capacidad
from . import schemas


def _get(db, tenant_id, id):
    row = db.query(Producto).filter_by(tenant_id=tenant_id, id=id).first()
    if not row:
        raise HTTPException(404, "Producto no encontrado")
    return row


def _refs(db, tenant_id, data):
    for model, id_ in ((Categoria, data.categoria_id), (Temporada, data.temporada_id)):
        if id_ and not db.query(model).filter_by(tenant_id=tenant_id, id=id_).first():
            raise HTTPException(404, "Catálogo no encontrado")


def listar(db: Session, tenant_id: int):
    return db.query(Producto).filter_by(tenant_id=tenant_id).order_by(Producto.id).all()


def crear(db: Session, tenant_id: int, data: schemas.ProductoIn):
    exigir_capacidad(db, tenant_id, "productos")
    _refs(db, tenant_id, data)
    row = Producto(tenant_id=tenant_id, **data.model_dump(exclude={"variantes"}), activo=True)
    db.add(row)
    db.flush()
    if data.variantes:
        agregar_variantes(db, tenant_id, row.id, data.variantes, commit=False)
    db.commit()
    db.refresh(row)
    return row


def actualizar(db: Session, tenant_id: int, id: int, data: schemas.ProductoUpdateIn):
    row = _get(db, tenant_id, id)
    _refs(db, tenant_id, data)
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(row, key, val)
    if "precio_base" in data.model_fields_set:
        row.actualizado_en = datetime.now(timezone.utc)
        for variante in db.query(Variante).filter_by(tenant_id=tenant_id, producto_id=id):
            variante.precio = data.precio_base
            variante.precio_actualizado_en = row.actualizado_en
    db.commit()
    return row


def desactivar(db: Session, tenant_id: int, id: int):
    row = _get(db, tenant_id, id)
    row.activo = False
    db.commit()
    return row


def agregar_variantes(db: Session, tenant_id: int, id: int, data: list[schemas.VarianteIn], commit=True):
    _get(db, tenant_id, id)
    result = []
    for item in data:
        if db.query(Variante).filter_by(tenant_id=tenant_id, sku=item.sku).first() or any(v.sku == item.sku for v in result):
            raise HTTPException(409, "SKU repetido en el tenant")
        for model, ref in ((Talla, item.talla_id), (Color, item.color_id)):
            if ref and not db.query(model).filter_by(tenant_id=tenant_id, id=ref).first():
                raise HTTPException(404, "Talla o color no encontrado")
        v = Variante(tenant_id=tenant_id, producto_id=id, **item.model_dump(), activo=True)
        db.add(v)
        result.append(v)
    if commit:
        db.commit()
    return result
