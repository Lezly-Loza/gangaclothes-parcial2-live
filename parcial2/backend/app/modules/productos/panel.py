"""Contrato del panel original sobre los productos e inventario multitenant."""
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_permiso, require_tenant
from ...models import (Categoria, Color, DatosComplementarios, Inventario, MovimientoInventario,
                       Producto, RegistroComplementario, Sucursal, Talla, Variante)
from ..suscripciones.service import exigir_capacidad
from .promociones import precio_promocional

router = APIRouter(prefix="/prendas", tags=["Panel de prendas"])


class PrendaIn(BaseModel):
    nombre: str | None = None
    categoria_id: int | None = None
    coleccion_id: int | None = None
    marca: str | None = None
    genero: str | None = None
    precio_venta: Decimal | None = Field(default=None, ge=0)
    costo: Decimal | None = Field(default=None, ge=0)
    imagen_url: str | None = None
    descripcion: str | None = None
    activo: bool | None = None


class StockIn(BaseModel):
    sucursal_id: int
    cantidad: int = Field(ge=0)
    stock_minimo: int = Field(ge=0)
    stock_maximo: int = Field(ge=0)


class LoteIn(BaseModel):
    talla_ids: list[int] = Field(min_length=1)
    color_ids: list[int] = Field(min_length=1)
    imagen_url: str | None = None
    stock_inicial: list[StockIn] = []


class CargarStockIn(BaseModel):
    sucursales: list[StockIn] = Field(min_length=1)


class PublicarIn(BaseModel):
    confirmar_sin_stock: bool = False


def _producto(db, tenant_id, id):
    p = db.query(Producto).filter_by(tenant_id=tenant_id, id=id).first()
    if p is None: raise HTTPException(404, "Prenda no encontrada")
    return p


def _extra(db, tenant_id, tipo, id):
    return db.query(DatosComplementarios).filter_by(tenant_id=tenant_id, tipo=tipo, registro_id=id).first()


def _guardar_extra(db, tenant_id, tipo, id, datos):
    row = _extra(db, tenant_id, tipo, id)
    if row is None:
        row = DatosComplementarios(tenant_id=tenant_id, tipo=tipo, registro_id=id, datos={})
        db.add(row)
    row.datos = {**(row.datos or {}), **datos}


def _variante_salida(db, tenant_id, v):
    talla = db.query(Talla).filter_by(tenant_id=tenant_id, id=v.talla_id).first()
    color = db.query(Color).filter_by(tenant_id=tenant_id, id=v.color_id).first()
    filas = []
    for inv in db.query(Inventario).filter_by(tenant_id=tenant_id, variante_id=v.id).all():
        sucursal = db.query(Sucursal).filter_by(tenant_id=tenant_id, id=inv.sucursal_id).first()
        filas.append({"inventario_id": inv.id, "sucursal_id": inv.sucursal_id, "sucursal": sucursal.nombre if sucursal else "",
                      "sucursal_activa": bool(sucursal and sucursal.activo), "cantidad": inv.stock,
                      "cantidad_reservada": inv.reservado, "disponible": inv.stock - inv.reservado,
                      "stock_minimo": inv.stock_min, "stock_maximo": inv.stock_max})
    return {"id": v.id, "sku": v.sku, "talla_id": v.talla_id, "color_id": v.color_id,
            "talla": talla.nombre if talla else "Sin talla", "color": color.nombre if color else "Sin color",
            "color_hex": color.codigo_hex if color else None, "activo": v.activo, "tiene_asset_ar": False,
            "stock": filas, "stock_total": sum(x["cantidad"] for x in filas),
            "disponible_total": sum(x["disponible"] for x in filas)}


def _salida(db, tenant_id, p):
    extra = _extra(db, tenant_id, "prendas", p.id)
    datos = (extra.datos or {}) if extra else {}
    variantes = db.query(Variante).filter_by(tenant_id=tenant_id, producto_id=p.id).all()
    stocks = [s for v in variantes for s in _variante_salida(db, tenant_id, v)["stock"]]
    return {**datos, "id": p.id, "nombre": p.nombre, "categoria_id": p.categoria_id,
            "descripcion": p.descripcion, "imagen_url": p.imagen_url, "precio_venta": float(p.precio_base),
            "costo": datos.get("costo", 0), "activo": p.activo, "publicado": datos.get("publicado", p.activo),
            "variantes": len(variantes), "disponible_total": sum(s["disponible"] for s in stocks),
            "sucursales_con_stock": len({s["sucursal_id"] for s in stocks if s["disponible"] > 0})}


def _actualizar(db, tenant_id, p, body, nuevo=False):
    datos = body.model_dump(exclude_unset=True)
    if nuevo and (not datos.get("nombre") or datos.get("precio_venta") is None or not datos.get("categoria_id")):
        raise HTTPException(422, "Nombre, categoría y precio son obligatorios")
    if "nombre" in datos and (not datos["nombre"] or not datos["nombre"].strip()):
        raise HTTPException(422, "El nombre es obligatorio")
    if datos.get("categoria_id") and not db.query(Categoria).filter_by(tenant_id=tenant_id, id=datos["categoria_id"]).first():
        raise HTTPException(404, "Categoría no encontrada")
    if datos.get("coleccion_id") and not db.query(RegistroComplementario).filter_by(tenant_id=tenant_id, tipo="colecciones", id=datos["coleccion_id"]).first():
        raise HTTPException(404, "Colección no encontrada")
    if datos.get("activo") and not p.activo: exigir_capacidad(db, tenant_id, "productos")
    for key in ("nombre", "categoria_id", "descripcion", "imagen_url", "activo"):
        if key in datos and datos[key] is not None: setattr(p, key, datos[key])
    if "precio_venta" in datos and datos["precio_venta"] is not None:
        p.precio_base = datos["precio_venta"]
        for v in db.query(Variante).filter_by(tenant_id=tenant_id, producto_id=p.id): v.precio = p.precio_base
    extras = {k: (float(datos[k]) if k == "costo" and datos[k] is not None else datos[k]) for k in ("marca", "genero", "coleccion_id", "costo") if k in datos}
    if nuevo or datos.get("activo") is False: extras["publicado"] = False
    if extras: _guardar_extra(db, tenant_id, "prendas", p.id, extras)


def _cargar_stock(db, tenant_id, v, lineas, usuario_id):
    ids = [x.sucursal_id for x in lineas]
    if len(ids) != len(set(ids)): raise HTTPException(422, "Sucursal repetida")
    for linea in lineas:
        if not db.query(Sucursal).filter_by(tenant_id=tenant_id, id=linea.sucursal_id, activo=True).first():
            raise HTTPException(404, "Sucursal activa no encontrada")
        if linea.stock_maximo and linea.stock_minimo > linea.stock_maximo: raise HTTPException(422, "El mínimo supera el máximo")
        if db.query(Inventario).filter_by(tenant_id=tenant_id, sucursal_id=linea.sucursal_id, variante_id=v.id).first():
            raise HTTPException(409, "La variante ya tiene stock en esa sucursal")
        db.add(Inventario(tenant_id=tenant_id, sucursal_id=linea.sucursal_id, variante_id=v.id,
                          stock=linea.cantidad, reservado=0, stock_min=linea.stock_minimo, stock_max=linea.stock_maximo))
        if linea.cantidad:
            db.add(MovimientoInventario(tenant_id=tenant_id, sucursal_id=linea.sucursal_id, variante_id=v.id,
                                        tipo="ENTRADA", cantidad=linea.cantidad, motivo="Stock inicial", usuario_id=usuario_id))


@router.get("")
def listar(scope: TenantScope = Depends(require_permiso("prendas:ver")), db: Session = Depends(get_db)):
    return [_salida(db, scope.tenant_id, p) for p in db.query(Producto).filter_by(tenant_id=scope.tenant_id).all()]


@router.get("/catalogo-interno")
def catalogo_interno(scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    if not any(p in scope.permisos for p in ("prendas:ver", "inventario:ver", "ventas:crear")):
        raise HTTPException(403, "No tiene permiso para consultar el catálogo interno")
    salida = []
    for producto in db.query(Producto).filter_by(tenant_id=scope.tenant_id, activo=True).all():
        precio_final, promocion = precio_promocional(db, scope.tenant_id, producto.id, producto.precio_base)
        variantes = []
        for variante in db.query(Variante).filter_by(tenant_id=scope.tenant_id, producto_id=producto.id, activo=True).all():
            fila = _variante_salida(db, scope.tenant_id, variante)
            precio_variante, promo_variante = precio_promocional(db, scope.tenant_id, producto.id, variante.precio)
            variantes.append({"id": variante.id, "sku": variante.sku, "talla": fila["talla"], "color": fila["color"], "precio": float(precio_variante), "precio_lista": float(variante.precio),
                              "promocion": {"nombre": promo_variante.nombre, "etiqueta": f'{promo_variante.valor:g}%' if promo_variante.tipo_descuento == 'porcentaje' else f'Bs {promo_variante.valor:g}'} if promo_variante else None,
                              "disponibilidad": [{"sucursal_id": s["sucursal_id"], "disponible": s["disponible"]}
                                                 for s in fila["stock"] if s["sucursal_activa"]]})
        salida.append({"id": producto.id, "nombre": producto.nombre, "categoria_id": producto.categoria_id,
                       "precio_venta": float(producto.precio_base), "precio_final": float(precio_final),
                       "promocion": {"nombre": promocion.nombre, "etiqueta": f'{promocion.valor:g}%' if promocion.tipo_descuento == 'porcentaje' else f'Bs {promocion.valor:g}'} if promocion else None, "variantes": variantes})
    return salida


@router.post("", status_code=201)
def crear(body: PrendaIn, scope: TenantScope = Depends(require_permiso("prendas:crear")), db: Session = Depends(get_db)):
    exigir_capacidad(db, scope.tenant_id, "productos")
    if not body.nombre or body.precio_venta is None: raise HTTPException(422, "Nombre y precio son obligatorios")
    p = Producto(tenant_id=scope.tenant_id, nombre=body.nombre, precio_base=body.precio_venta, activo=True)
    db.add(p); db.flush(); _actualizar(db, scope.tenant_id, p, body, True); db.commit()
    return _salida(db, scope.tenant_id, p)


@router.put("/{id}")
def actualizar(id: int, body: PrendaIn, scope: TenantScope = Depends(require_permiso("prendas:editar")), db: Session = Depends(get_db)):
    p = _producto(db, scope.tenant_id, id); _actualizar(db, scope.tenant_id, p, body); db.commit()
    return _salida(db, scope.tenant_id, p)


@router.get("/{id}/variantes")
def variantes(id: int, scope: TenantScope = Depends(require_permiso("prendas:ver")), db: Session = Depends(get_db)):
    _producto(db, scope.tenant_id, id)
    return [_variante_salida(db, scope.tenant_id, v) for v in db.query(Variante).filter_by(tenant_id=scope.tenant_id, producto_id=id).all()]


@router.post("/{id}/variantes/lote", status_code=201)
def crear_lote(id: int, body: LoteIn, scope: TenantScope = Depends(require_permiso("prendas:crear")), db: Session = Depends(get_db)):
    p = _producto(db, scope.tenant_id, id)
    for model, ids in ((Talla, set(body.talla_ids)), (Color, set(body.color_ids))):
        for ref in ids:
            if not db.query(model).filter_by(tenant_id=scope.tenant_id, id=ref, activo=True).first(): raise HTTPException(404, "Talla o color no encontrado")
    creadas, omitidas = [], []
    for talla_id in set(body.talla_ids):
        for color_id in set(body.color_ids):
            if db.query(Variante).filter_by(tenant_id=scope.tenant_id, producto_id=id, talla_id=talla_id, color_id=color_id).first():
                omitidas.append(f"{talla_id}-{color_id}"); continue
            v = Variante(tenant_id=scope.tenant_id, producto_id=id, talla_id=talla_id, color_id=color_id,
                         sku=f"P{id}-{uuid4().hex[:10].upper()}", precio=p.precio_base, activo=True)
            db.add(v); db.flush(); _cargar_stock(db, scope.tenant_id, v, body.stock_inicial, scope.user_id); creadas.append(v)
    db.commit()
    return {"creadas": [_variante_salida(db, scope.tenant_id, v) for v in creadas], "omitidas": omitidas}


@router.post("/variantes/{id}/stock-inicial")
def stock_inicial(id: int, body: CargarStockIn, scope: TenantScope = Depends(require_permiso("inventario:crear")), db: Session = Depends(get_db)):
    v = db.query(Variante).filter_by(tenant_id=scope.tenant_id, id=id).first()
    if v is None: raise HTTPException(404, "Variante no encontrada")
    _cargar_stock(db, scope.tenant_id, v, body.sucursales, scope.user_id); db.commit()
    return _variante_salida(db, scope.tenant_id, v)


@router.post("/{id}/publicar")
def publicar(id: int, body: PublicarIn, scope: TenantScope = Depends(require_permiso("prendas:editar")), db: Session = Depends(get_db)):
    p = _producto(db, scope.tenant_id, id)
    if not p.activo: raise HTTPException(409, "La prenda está archivada")
    if not body.confirmar_sin_stock and _salida(db, scope.tenant_id, p)["disponible_total"] <= 0:
        raise HTTPException(409, "La prenda no tiene stock disponible")
    _guardar_extra(db, scope.tenant_id, "prendas", id, {"publicado": True}); db.commit()
    return _salida(db, scope.tenant_id, p)


@router.post("/{id}/despublicar")
def despublicar(id: int, scope: TenantScope = Depends(require_permiso("prendas:editar")), db: Session = Depends(get_db)):
    p = _producto(db, scope.tenant_id, id)
    _guardar_extra(db, scope.tenant_id, "prendas", id, {"publicado": False}); db.commit()
    return _salida(db, scope.tenant_id, p)
