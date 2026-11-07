from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...models import Inventario, MovimientoInventario, Sucursal, Variante, Producto, Talla, Color, User
from . import schemas


def _inventario(db: Session, tenant_id: int, sucursal_id: int, variante_id: int) -> Inventario:
    if not db.query(Sucursal).filter_by(id=sucursal_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "Sucursal no encontrada")
    if not db.query(Variante).filter_by(id=variante_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "Variante no encontrada")
    row = db.query(Inventario).filter_by(sucursal_id=sucursal_id, variante_id=variante_id, tenant_id=tenant_id).with_for_update().first()
    if row is None:
        row = Inventario(tenant_id=tenant_id, sucursal_id=sucursal_id, variante_id=variante_id,
                         stock=0, reservado=0, stock_min=0, stock_max=100)
        db.add(row)
        db.flush()
    return row


def consultar_stock(db: Session, tenant_id: int, sucursal_id: int):
    if not db.query(Sucursal).filter_by(id=sucursal_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "Sucursal no encontrada")
    return [_fila_inventario(db, tenant_id, inv) for inv in db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=sucursal_id).all()]


def _fila_inventario(db: Session, tenant_id: int, inv: Inventario):
    variante = db.query(Variante).filter_by(tenant_id=tenant_id, id=inv.variante_id).first()
    producto = db.query(Producto).filter_by(tenant_id=tenant_id, id=variante.producto_id).first() if variante else None
    talla = db.query(Talla).filter_by(tenant_id=tenant_id, id=variante.talla_id).first() if variante and variante.talla_id else None
    color = db.query(Color).filter_by(tenant_id=tenant_id, id=variante.color_id).first() if variante and variante.color_id else None
    sucursal = db.query(Sucursal).filter_by(tenant_id=tenant_id, id=inv.sucursal_id).first()
    return {"id": inv.id, "variante_id": inv.variante_id, "sku": variante.sku if variante else "",
            "prenda_id": producto.id if producto else None, "prenda": producto.nombre if producto else "",
            "prenda_publicada": bool(producto and producto.activo), "precio_venta": float(variante.precio) if variante else None,
            "talla": talla.nombre if talla else "Sin talla", "color": color.nombre if color else "Sin color",
            "color_hex": color.codigo_hex if color else None, "sucursal_id": inv.sucursal_id,
            "sucursal": sucursal.nombre if sucursal else "", "cantidad": inv.stock,
            "cantidad_reservada": inv.reservado, "disponible": inv.stock - inv.reservado,
            "stock_minimo": inv.stock_min, "stock_maximo": inv.stock_max, "bajo_minimo": inv.stock < inv.stock_min,
            "stock": inv.stock, "reservado": inv.reservado, "stock_min": inv.stock_min, "stock_max": inv.stock_max}


def _fila_movimiento(db: Session, tenant_id: int, mov: MovimientoInventario):
    variante = db.query(Variante).filter_by(tenant_id=tenant_id, id=mov.variante_id).first()
    producto = db.query(Producto).filter_by(tenant_id=tenant_id, id=variante.producto_id).first() if variante else None
    sucursal = db.query(Sucursal).filter_by(tenant_id=tenant_id, id=mov.sucursal_id).first()
    usuario = db.query(User).filter_by(tenant_id=tenant_id, id=mov.usuario_id).first() if mov.usuario_id else None
    tipos = {"ENTRADA": "ingreso", "SALIDA": "salida", "VENTA": "salida", "TRASPASO": "salida", "AJUSTE": "ajuste", "DEVOLUCION": "devolucion"}
    return {"id": mov.id, "fecha": mov.fecha, "tipo": tipos.get(mov.tipo, mov.tipo.lower()), "cantidad": mov.cantidad,
            "motivo": mov.motivo, "variante_id": mov.variante_id, "sku": variante.sku if variante else "",
            "prenda": producto.nombre if producto else "", "sucursal_id": mov.sucursal_id,
            "sucursal": sucursal.nombre if sucursal else "", "usuario_id": mov.usuario_id, "usuario": usuario.nombre if usuario else None}


def consultar_movimientos(db: Session, tenant_id: int, sucursal_id: int, variante_id: int | None):
    if not db.query(Sucursal).filter_by(id=sucursal_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "Sucursal no encontrada")
    consulta = db.query(MovimientoInventario).filter_by(tenant_id=tenant_id, sucursal_id=sucursal_id)
    if variante_id is not None:
        consulta = consulta.filter_by(variante_id=variante_id)
    return [_fila_movimiento(db, tenant_id, m) for m in consulta.order_by(MovimientoInventario.id.desc()).limit(200).all()]


def registrar_movimiento(db: Session, tenant_id: int, data: schemas.MovimientoIn, usuario_id: int | None = None):
    inv = _inventario(db, tenant_id, data.sucursal_id, data.variante_id)
    stock_anterior = inv.stock
    inv.validarStockYGuardar(db, data.tipo, data.cantidad)
    mov = MovimientoInventario(tenant_id=tenant_id, sucursal_id=data.sucursal_id,
                               variante_id=data.variante_id, tipo=data.tipo, cantidad=data.cantidad,
                               motivo=data.motivo, proveedor_id=data.proveedor_id, usuario_id=usuario_id)
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return schemas.MovimientoOut(id=mov.id, sucursal_id=mov.sucursal_id, variante_id=mov.variante_id,
                                 tipo=mov.tipo, cantidad=mov.cantidad, alerta_minimo=inv.stock < inv.stock_min,
                                 movimiento=_fila_movimiento(db, tenant_id, mov), stock_anterior=stock_anterior,
                                 stock_actual=inv.stock, inventario=_fila_inventario(db, tenant_id, inv))


def actualizar_limites(db: Session, tenant_id: int, inventario_id: int, data: schemas.LimitesPanel):
    inv = db.query(Inventario).filter_by(tenant_id=tenant_id, id=inventario_id).first()
    if inv is None:
        raise HTTPException(404, "Inventario no encontrado")
    if data.stock_minimo > data.stock_maximo:
        raise HTTPException(422, "El mínimo supera el máximo")
    inv.stock_min, inv.stock_max = data.stock_minimo, data.stock_maximo
    db.commit()
    return _fila_inventario(db, tenant_id, inv)


def definir_stock_min_max(db: Session, tenant_id: int, data: schemas.MinMaxIn):
    if data.stock_min > data.stock_max:
        raise HTTPException(422, "stock_min supera stock_max")
    inv = _inventario(db, tenant_id, data.sucursal_id, data.variante_id)
    inv.stock_min, inv.stock_max = data.stock_min, data.stock_max
    db.commit()
    return inv
