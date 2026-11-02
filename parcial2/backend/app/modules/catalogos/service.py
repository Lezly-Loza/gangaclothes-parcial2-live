from fastapi import HTTPException
from sqlalchemy.orm import Session
from ...models import Categoria, Color, Talla, Temporada
from . import schemas

MODELOS = {"categorias": Categoria, "tallas": Talla, "colores": Color, "temporadas": Temporada}


def _modelo(tipo):
    if tipo not in MODELOS:
        raise HTTPException(404, "Catálogo no encontrado")
    return MODELOS[tipo]


def listar_registros(db: Session, tenant_id: int, tipo: str):
    model = _modelo(tipo)
    return db.query(model).filter_by(tenant_id=tenant_id).order_by(model.id).all()


def guardar_registro(db: Session, tenant_id: int, tipo: str, data: schemas.RegistroIn):
    model = _modelo(tipo)
    if db.query(model).filter_by(tenant_id=tenant_id, nombre=data.nombre).first():
        raise HTTPException(409, "Nombre repetido en el catálogo")
    campos = {"nombre": data.nombre}
    if tipo == "colores":
        campos["codigo_hex"] = data.codigo_hex
    if tipo == "temporadas":
        campos.update(fecha_inicio=data.fecha_inicio, fecha_fin=data.fecha_fin)
    row = model(tenant_id=tenant_id, activo=True, **campos)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def desactivar_registro(db: Session, tenant_id: int, tipo: str, id: int):
    row = db.query(_modelo(tipo)).filter_by(tenant_id=tenant_id, id=id).first()
    if not row:
        raise HTTPException(404, "Registro no encontrado")
    row.activo = False
    db.commit()
    return row
