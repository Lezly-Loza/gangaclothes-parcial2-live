"""Adaptador de la interfaz del primer parcial a los modelos multitenant actuales."""
from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_tenant
from ...models import (Categoria, Talla, Color, Temporada, Sucursal, Proveedor, Cliente,
                       RegistroComplementario, DatosComplementarios)
from ..suscripciones.service import exigir_capacidad

router = APIRouter(prefix="/admin", tags=["Compatibilidad con panel anterior"])
MODELOS = {"categorias": Categoria, "tallas": Talla, "colores": Color, "temporadas": Temporada,
           "sucursales": Sucursal, "proveedores": Proveedor, "clientes": Cliente}
COMPLEMENTARIOS = {"ciudades", "colecciones"}
EXTRAS = {"categorias": ("descripcion",), "tallas": ("orden",),
          "sucursales": ("ciudad_id", "telefono", "latitud", "longitud"),
          "proveedores": ("direccion",), "clientes": ("activo",)}


def _permiso(scope: TenantScope, tipo: str, accion: str):
    if tipo not in MODELOS and tipo not in COMPLEMENTARIOS:
        raise HTTPException(404, "Catálogo no encontrado")
    if tipo == "sucursales" and accion == "ver":
        return
    if tipo in {"categorias", "temporadas"} and accion == "ver" and "oferta:ver" in scope.permisos:
        return
    modulo = ("sucursales" if tipo in {"ciudades", "sucursales"} else
              "proveedores" if tipo == "proveedores" else "clientes" if tipo == "clientes" else "catalogos")
    if f"{modulo}:{accion}" not in scope.permisos:
        raise HTTPException(403, f"Requiere permiso: {modulo}:{accion}")


def _extra(db: Session, tenant_id: int, tipo: str, id: int):
    return db.query(DatosComplementarios).filter_by(tenant_id=tenant_id, tipo=tipo, registro_id=id).first()


def _guardar_extra(db: Session, tenant_id: int, tipo: str, id: int, datos: dict):
    permitidos = {k: datos[k] for k in EXTRAS.get(tipo, ()) if k in datos}
    if not permitidos:
        return
    extra = _extra(db, tenant_id, tipo, id)
    if extra is None:
        extra = DatosComplementarios(tenant_id=tenant_id, tipo=tipo, registro_id=id, datos={})
        db.add(extra)
    extra.datos = {**(extra.datos or {}), **permitidos}


def _obtener(db: Session, tenant_id: int, tipo: str, id: int):
    if tipo in COMPLEMENTARIOS:
        row = db.query(RegistroComplementario).filter_by(tenant_id=tenant_id, tipo=tipo, id=id).first()
    else:
        row = db.query(MODELOS[tipo]).filter_by(tenant_id=tenant_id, id=id).first()
    if row is None:
        raise HTTPException(404, "Registro no encontrado")
    return row


def _salida(db: Session, tenant_id: int, tipo: str, row):
    if tipo in COMPLEMENTARIOS:
        return {**(row.datos or {}), "id": row.id, "nombre": row.nombre, "activo": row.activo}
    extra = _extra(db, tenant_id, tipo, row.id)
    result = {**((extra.datos or {}) if extra else {}), "id": row.id}
    if tipo == "proveedores":
        result.update(nombre=row.razon_social, nit=row.nit, contacto=row.contacto,
                      telefono=row.telefono, email=row.correo, activo=row.activo)
    elif tipo == "clientes":
        result.update(nombre=row.nombre, documento=row.documento, telefono=row.telefono,
                      correo=row.correo, user_id=row.user_id)
        result.setdefault("activo", True)
    elif tipo == "sucursales":
        result.update(nombre=row.nombre, codigo=row.codigo, ciudad=row.ciudad, direccion=row.direccion,
                      horario=row.horario, estado=row.estado, activo=row.activo)
    else:
        result.update(nombre=row.nombre, activo=row.activo)
        if tipo == "colores": result["codigo_hex"] = row.codigo_hex
        if tipo == "temporadas":
            result.update(fecha_inicio=row.fecha_inicio, fecha_fin=row.fecha_fin)
    return result


def asegurar_ciudades(db: Session, tenant_id: int):
    for sucursal in db.query(Sucursal).filter_by(tenant_id=tenant_id).all():
        ciudad = db.query(RegistroComplementario).filter_by(tenant_id=tenant_id, tipo="ciudades", nombre=sucursal.ciudad).first()
        if ciudad is None:
            ciudad = RegistroComplementario(tenant_id=tenant_id, tipo="ciudades", nombre=sucursal.ciudad,
                                            activo=True, datos={})
            db.add(ciudad)
            db.flush()
        if _extra(db, tenant_id, "sucursales", sucursal.id) is None:
            _guardar_extra(db, tenant_id, "sucursales", sucursal.id, {"ciudad_id": ciudad.id})


def _fecha(valor):
    if not valor: return None
    try: return date.fromisoformat(str(valor))
    except ValueError as exc: raise HTTPException(422, "Fecha inválida") from exc


def _campos(db: Session, tenant_id: int, tipo: str, row, datos: dict, nuevo: bool):
    nombre = datos.get("nombre")
    if nuevo and (not isinstance(nombre, str) or not nombre.strip()):
        raise HTTPException(422, "El nombre es obligatorio")
    if nombre is not None:
        if not isinstance(nombre, str) or not nombre.strip(): raise HTTPException(422, "El nombre es obligatorio")
        setattr(row, "razon_social" if tipo == "proveedores" else "nombre", nombre.strip())
    if tipo in COMPLEMENTARIOS:
        claves = ("departamento",) if tipo == "ciudades" else ("temporada_id", "anio", "descripcion")
        extra = {k: datos[k] for k in claves if k in datos}
        if tipo == "colecciones" and (nuevo or "temporada_id" in datos):
            if not db.query(Temporada).filter_by(tenant_id=tenant_id, id=datos.get("temporada_id")).first():
                raise HTTPException(404, "Temporada no encontrada")
        row.datos = {**(row.datos or {}), **extra}
    elif tipo == "colores" and "codigo_hex" in datos:
        row.codigo_hex = datos["codigo_hex"]
    elif tipo == "temporadas":
        if "fecha_inicio" in datos: row.fecha_inicio = _fecha(datos["fecha_inicio"])
        if "fecha_fin" in datos: row.fecha_fin = _fecha(datos["fecha_fin"])
        if row.fecha_inicio and row.fecha_fin and row.fecha_inicio > row.fecha_fin:
            raise HTTPException(422, "La fecha de inicio debe ser anterior a la fecha de fin")
    elif tipo == "proveedores":
        for campo, destino in (("nit", "nit"), ("contacto", "contacto"), ("telefono", "telefono"), ("email", "correo")):
            if campo in datos: setattr(row, destino, datos[campo])
        if not row.nit: raise HTTPException(422, "El NIT es obligatorio")
    elif tipo == "clientes":
        for campo in ("documento", "telefono", "correo"):
            if campo in datos: setattr(row, campo, datos[campo])
        if not row.documento: raise HTTPException(422, "El documento es obligatorio")
    elif tipo == "sucursales":
        if nuevo or "ciudad_id" in datos:
            ciudad = db.query(RegistroComplementario).filter_by(tenant_id=tenant_id, tipo="ciudades", id=datos.get("ciudad_id"), activo=True).first()
            if ciudad is None: raise HTTPException(404, "Ciudad no encontrada")
            row.ciudad = ciudad.nombre
        for campo in ("direccion", "horario"):
            if campo in datos: setattr(row, campo, datos[campo])
        if not row.direccion: raise HTTPException(422, "La dirección es obligatoria")
    if "activo" in datos and tipo != "clientes":
        row.activo = bool(datos["activo"])
        if tipo == "sucursales": row.estado = "activa" if row.activo else "inactiva"


@router.get("/{tipo}")
def listar(tipo: str, scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    _permiso(scope, tipo, "ver")
    query = (db.query(RegistroComplementario).filter_by(tenant_id=scope.tenant_id, tipo=tipo)
             if tipo in COMPLEMENTARIOS else db.query(MODELOS[tipo]).filter_by(tenant_id=scope.tenant_id))
    filas = [_salida(db, scope.tenant_id, tipo, r) for r in query.all()]
    return [r for r in filas if r.get("activo", True)] if tipo in {"tallas", "colores", "colecciones", "ciudades"} else filas


@router.post("/{tipo}", status_code=201)
def crear(tipo: str, datos: dict, scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    _permiso(scope, tipo, "crear")
    if tipo == "sucursales": exigir_capacidad(db, scope.tenant_id, "sucursales")
    if tipo in COMPLEMENTARIOS:
        row = RegistroComplementario(tenant_id=scope.tenant_id, tipo=tipo, activo=True, datos={})
    elif tipo == "sucursales":
        row = Sucursal(tenant_id=scope.tenant_id, codigo=f"suc-{uuid4().hex[:12]}", activo=True, estado="activa")
    elif tipo == "clientes":
        row = Cliente(tenant_id=scope.tenant_id)
    else:
        row = MODELOS[tipo](tenant_id=scope.tenant_id, activo=True)
    _campos(db, scope.tenant_id, tipo, row, datos, True)
    db.add(row)
    try:
        db.flush()
        _guardar_extra(db, scope.tenant_id, tipo, row.id, datos)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Ya existe un registro con esos datos en esta empresa") from exc
    return _salida(db, scope.tenant_id, tipo, row)


@router.put("/{tipo}/{id}")
def actualizar(tipo: str, id: int, datos: dict, scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    _permiso(scope, tipo, "editar")
    row = _obtener(db, scope.tenant_id, tipo, id)
    _campos(db, scope.tenant_id, tipo, row, datos, False)
    _guardar_extra(db, scope.tenant_id, tipo, id, datos)
    try: db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Ya existe un registro con esos datos en esta empresa") from exc
    return _salida(db, scope.tenant_id, tipo, row)


@router.delete("/{tipo}/{id}")
def eliminar(tipo: str, id: int, scope: TenantScope = Depends(require_tenant), db: Session = Depends(get_db)):
    _permiso(scope, tipo, "eliminar")
    row = _obtener(db, scope.tenant_id, tipo, id)
    if tipo == "clientes": _guardar_extra(db, scope.tenant_id, tipo, id, {"activo": False})
    else: row.activo = False
    if tipo == "sucursales": row.estado = "inactiva"
    db.commit()
    return {"detail": "Registro archivado"}
