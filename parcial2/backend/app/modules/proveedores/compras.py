"""Compras y oferta sobre registros aislados por empresa."""
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso
from ...models import (Categoria, Color, Compra, DatosComplementarios, DetalleCompra, Inventario,
                       MovimientoInventario, Producto, ProductoProveedor, Proveedor, Sucursal, Talla, Temporada, Variante)

router = APIRouter(tags=["Compras y oferta"])


class EnlaceIn(BaseModel):
    prenda_id: int | None


class LineaIn(BaseModel):
    producto_proveedor_id: int | None = None
    variante_id: int
    cantidad: int = Field(gt=0)
    precio_unitario: Decimal = Field(ge=0)


class CompraIn(BaseModel):
    proveedor_id: int
    sucursal_id: int
    detalle: list[LineaIn] = Field(min_length=1)


class OfertaIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None
    categoria_id: int | None = None
    precio_referencial: Decimal | None = Field(default=None, gt=0)
    cantidad_minima: int | None = Field(default=None, gt=0)
    disponible: bool | None = None
    temporada_ids: list[int] | None = None


def _oferta(db, tenant_id, p):
    proveedor = db.query(Proveedor).filter_by(tenant_id=tenant_id, id=p.proveedor_id).first()
    categoria = db.query(Categoria).filter_by(tenant_id=tenant_id, id=p.categoria_id).first() if p.categoria_id else None
    prenda = db.query(Producto).filter_by(tenant_id=tenant_id, id=p.prenda_id).first() if p.prenda_id else None
    temporadas = db.query(Temporada).filter(Temporada.tenant_id == tenant_id, Temporada.id.in_(p.temporada_ids)).all()
    return {"id": p.id, "proveedor_id": p.proveedor_id, "proveedor": proveedor.razon_social if proveedor else None,
            "nombre": p.nombre, "descripcion": p.descripcion, "categoria_id": p.categoria_id,
            "categoria": categoria.nombre if categoria else None, "prenda_id": p.prenda_id,
            "prenda": prenda.nombre if prenda else None, "precio_referencial": float(p.precio_referencial),
            "cantidad_minima": p.cantidad_minima, "disponible": p.disponible, "temporada_ids": p.temporada_ids,
            "temporadas": [{"id": t.id, "nombre": t.nombre} for t in temporadas], "fecha_actualizacion": p.fecha_actualizacion}


def _proveedor_usuario(db, scope):
    extra = db.query(DatosComplementarios).filter_by(tenant_id=scope.tenant_id, tipo="usuario_proveedor", registro_id=scope.user_id).first()
    proveedor_id = (extra.datos or {}).get("proveedor_id") if extra else None
    proveedor = db.query(Proveedor).filter_by(tenant_id=scope.tenant_id, id=proveedor_id, activo=True).first() if proveedor_id else None
    if not proveedor: raise HTTPException(403, "La cuenta no está enlazada a un proveedor activo")
    return proveedor


@router.get("/oferta/perfil")
def perfil(scope: TenantScope = Depends(require_permiso("oferta:ver")), db: Session = Depends(get_db)):
    proveedor = _proveedor_usuario(db, scope)
    productos = db.query(ProductoProveedor).filter_by(tenant_id=scope.tenant_id, proveedor_id=proveedor.id).all()
    return {"id": proveedor.id, "nombre": proveedor.razon_social, "nit": proveedor.nit, "contacto": proveedor.contacto,
            "telefono": proveedor.telefono, "email": proveedor.correo, "productos": len(productos),
            "disponibles": sum(p.disponible for p in productos),
            "ultima_actualizacion": max((p.fecha_actualizacion for p in productos), default=None)}


@router.get("/oferta/mia")
def mi_oferta(scope: TenantScope = Depends(require_permiso("oferta:ver")), db: Session = Depends(get_db)):
    proveedor = _proveedor_usuario(db, scope)
    return [_oferta(db, scope.tenant_id, p) for p in db.query(ProductoProveedor).filter_by(tenant_id=scope.tenant_id, proveedor_id=proveedor.id).all()]


def _actualizar_oferta(db, scope, producto, body, nuevo=False):
    datos = body.model_dump(exclude_unset=True)
    if nuevo and (not datos.get("nombre") or not datos.get("precio_referencial") or not datos.get("temporada_ids")):
        raise HTTPException(422, "Nombre, precio y temporada son obligatorios")
    if datos.get("categoria_id") and not db.query(Categoria).filter_by(tenant_id=scope.tenant_id, id=datos["categoria_id"]).first():
        raise HTTPException(404, "Categoría no encontrada")
    if "temporada_ids" in datos:
        if not datos["temporada_ids"]: raise HTTPException(422, "Seleccione al menos una temporada")
        for id in datos["temporada_ids"]:
            if not db.query(Temporada).filter_by(tenant_id=scope.tenant_id, id=id).first(): raise HTTPException(404, "Temporada no encontrada")
    for key, val in datos.items(): setattr(producto, key, val)
    producto.fecha_actualizacion = datetime.now(timezone.utc)


@router.post("/oferta/mia", status_code=201)
def crear_oferta(body: OfertaIn, scope: TenantScope = Depends(require_permiso("oferta:crear")), db: Session = Depends(get_db)):
    proveedor = _proveedor_usuario(db, scope)
    producto = ProductoProveedor(tenant_id=scope.tenant_id, proveedor_id=proveedor.id)
    _actualizar_oferta(db, scope, producto, body, True)
    db.add(producto); db.commit()
    return _oferta(db, scope.tenant_id, producto)


@router.put("/oferta/mia/{id}")
def editar_oferta(id: int, body: OfertaIn, scope: TenantScope = Depends(require_permiso("oferta:editar")), db: Session = Depends(get_db)):
    proveedor = _proveedor_usuario(db, scope)
    producto = db.query(ProductoProveedor).filter_by(tenant_id=scope.tenant_id, proveedor_id=proveedor.id, id=id).first()
    if not producto: raise HTTPException(404, "Producto no encontrado")
    _actualizar_oferta(db, scope, producto, body); db.commit()
    return _oferta(db, scope.tenant_id, producto)


@router.delete("/oferta/mia/{id}")
def quitar_oferta(id: int, scope: TenantScope = Depends(require_permiso("oferta:eliminar")), db: Session = Depends(get_db)):
    proveedor = _proveedor_usuario(db, scope)
    producto = db.query(ProductoProveedor).filter_by(tenant_id=scope.tenant_id, proveedor_id=proveedor.id, id=id).first()
    if not producto: raise HTTPException(404, "Producto no encontrado")
    # Se conserva para el historial de compras.
    producto.disponible = False; db.commit()
    return {"detail": "Producto retirado de la oferta"}


@router.get("/oferta")
def listar_oferta(proveedor_id: int | None = None, solo_disponibles: bool = True,
                  scope: TenantScope = Depends(require_permiso("inventario:ver")), db: Session = Depends(get_db)):
    query = db.query(ProductoProveedor).filter_by(tenant_id=scope.tenant_id)
    if proveedor_id is not None: query = query.filter_by(proveedor_id=proveedor_id)
    if solo_disponibles: query = query.filter_by(disponible=True)
    return [_oferta(db, scope.tenant_id, p) for p in query.order_by(ProductoProveedor.id.desc()).all()]


@router.put("/oferta/{id}/prenda")
def asociar(id: int, body: EnlaceIn, scope: TenantScope = Depends(require_permiso("inventario:editar")), db: Session = Depends(get_db)):
    p = db.query(ProductoProveedor).filter_by(tenant_id=scope.tenant_id, id=id).first()
    if not p: raise HTTPException(404, "Producto de proveedor no encontrado")
    if body.prenda_id is not None and not db.query(Producto).filter_by(tenant_id=scope.tenant_id, id=body.prenda_id, activo=True).first():
        raise HTTPException(404, "Prenda no encontrada")
    p.prenda_id = body.prenda_id; db.commit()
    return _oferta(db, scope.tenant_id, p)


def _compra(db, tenant_id, compra):
    proveedor = db.query(Proveedor).filter_by(tenant_id=tenant_id, id=compra.proveedor_id).first()
    sucursal = db.query(Sucursal).filter_by(tenant_id=tenant_id, id=compra.sucursal_id).first()
    detalle = []
    for d in db.query(DetalleCompra).filter_by(tenant_id=tenant_id, compra_id=compra.id).all():
        v = db.query(Variante).filter_by(tenant_id=tenant_id, id=d.variante_id).first()
        p = db.query(Producto).filter_by(tenant_id=tenant_id, id=v.producto_id).first() if v else None
        talla = db.query(Talla).filter_by(tenant_id=tenant_id, id=v.talla_id).first() if v and v.talla_id else None
        color = db.query(Color).filter_by(tenant_id=tenant_id, id=v.color_id).first() if v and v.color_id else None
        oferta = db.query(ProductoProveedor).filter_by(tenant_id=tenant_id, id=d.producto_proveedor_id).first() if d.producto_proveedor_id else None
        detalle.append({"id": d.id, "producto_proveedor": oferta.nombre if oferta else None, "variante_id": d.variante_id,
                        "sku": v.sku if v else "", "prenda": p.nombre if p else "", "talla": talla.nombre if talla else "—",
                        "color": color.nombre if color else "—", "cantidad": d.cantidad,
                        "precio_unitario": float(d.precio_unitario), "subtotal": float(d.precio_unitario * d.cantidad)})
    return {"id": compra.id, "fecha": compra.fecha, "estado": compra.estado, "total": float(compra.total),
            "proveedor_id": compra.proveedor_id, "proveedor": proveedor.razon_social if proveedor else None,
            "sucursal_id": compra.sucursal_id, "sucursal": sucursal.nombre if sucursal else None,
            "items": len(detalle), "detalle": detalle}


@router.get("/compras")
def listar_compras(sucursal_id: int, scope: TenantScope = Depends(require_permiso("inventario:ver")), db: Session = Depends(get_db)):
    if not db.query(Sucursal).filter_by(tenant_id=scope.tenant_id, id=sucursal_id).first(): raise HTTPException(404, "Sucursal no encontrada")
    return [_compra(db, scope.tenant_id, c) for c in db.query(Compra).filter_by(tenant_id=scope.tenant_id, sucursal_id=sucursal_id).order_by(Compra.id.desc()).all()]


@router.get("/compras/{id}")
def detalle_compra(id: int, scope: TenantScope = Depends(require_permiso("inventario:ver")), db: Session = Depends(get_db)):
    compra = db.query(Compra).filter_by(tenant_id=scope.tenant_id, id=id).first()
    if not compra: raise HTTPException(404, "Compra no encontrada")
    return _compra(db, scope.tenant_id, compra)


@router.post("/compras", status_code=201)
def crear_compra(body: CompraIn, scope: TenantScope = Depends(require_permiso("inventario:crear")), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    if not db.query(Proveedor).filter_by(tenant_id=tid, id=body.proveedor_id, activo=True).first(): raise HTTPException(404, "Proveedor no encontrado")
    if not db.query(Sucursal).filter_by(tenant_id=tid, id=body.sucursal_id, activo=True).first(): raise HTTPException(404, "Sucursal no encontrada")
    for d in body.detalle:
        variante = db.query(Variante).filter_by(tenant_id=tid, id=d.variante_id, activo=True).first()
        if not variante: raise HTTPException(404, "Variante no encontrada")
        if d.producto_proveedor_id is not None:
            oferta = db.query(ProductoProveedor).filter_by(tenant_id=tid, id=d.producto_proveedor_id, proveedor_id=body.proveedor_id, disponible=True).first()
            if not oferta or (oferta.prenda_id and oferta.prenda_id != variante.producto_id): raise HTTPException(422, "La oferta no corresponde a esta variante")
            if d.cantidad < oferta.cantidad_minima: raise HTTPException(422, "No se alcanza la cantidad mínima del proveedor")
    compra = Compra(tenant_id=tid, proveedor_id=body.proveedor_id, sucursal_id=body.sucursal_id,
                    total=sum((d.precio_unitario * d.cantidad for d in body.detalle), Decimal(0)), estado="pendiente")
    db.add(compra); db.flush()
    for d in body.detalle: db.add(DetalleCompra(tenant_id=tid, compra_id=compra.id, **d.model_dump()))
    db.commit()
    return _compra(db, tid, compra)


@router.post("/compras/{id}/recibir")
def recibir_compra(id: int, scope: TenantScope = Depends(require_permiso("inventario:crear")), db: Session = Depends(get_db)):
    tid = scope.tenant_id
    compra = db.query(Compra).filter_by(tenant_id=tid, id=id).with_for_update().first()
    if not compra: raise HTTPException(404, "Compra no encontrada")
    if compra.estado != "pendiente": raise HTTPException(409, "La compra ya fue recibida o anulada")
    movimientos = []
    for d in db.query(DetalleCompra).filter_by(tenant_id=tid, compra_id=id).all():
        inv = db.query(Inventario).filter_by(tenant_id=tid, sucursal_id=compra.sucursal_id, variante_id=d.variante_id).with_for_update().first()
        if inv is None:
            inv = Inventario(tenant_id=tid, sucursal_id=compra.sucursal_id, variante_id=d.variante_id, stock=0, reservado=0, stock_min=0, stock_max=0)
            db.add(inv); db.flush()
        inv.validarStockYGuardar(db, "ENTRADA", d.cantidad)
        movimiento = MovimientoInventario(tenant_id=tid, sucursal_id=compra.sucursal_id, variante_id=d.variante_id,
                                           tipo="ENTRADA", cantidad=d.cantidad, motivo=f"Compra #{id}",
                                           proveedor_id=compra.proveedor_id, usuario_id=scope.user_id)
        db.add(movimiento); movimientos.append({"cantidad": d.cantidad})
    compra.estado = "recibida"; db.commit()
    return {"compra": _compra(db, tid, compra), "movimientos": movimientos}
