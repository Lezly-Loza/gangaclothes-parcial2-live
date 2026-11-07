from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core import permisos as catalogo
from ...models import Bitacora, Rol, User, UsuarioRol


def normalizar(nombre: str) -> str:
    nombre = nombre.strip().lower()
    return catalogo.ALIAS.get(nombre, nombre)


def asegurar_roles(db: Session, tenant_id: int) -> None:
    existentes = {r.nombre: r for r in db.query(Rol).filter_by(tenant_id=tenant_id).all()}
    for nombre, permisos in catalogo.PREDETERMINADOS.items():
        if nombre not in existentes:
            db.add(Rol(tenant_id=tenant_id, nombre=nombre, descripcion="Rol inicial de la empresa",
                       activo=True, permisos=list(permisos)))
    if "administrador" in existentes:
        existentes["administrador"].permisos = list(catalogo.PREDETERMINADOS["administrador"])
    db.flush()


def roles_usuario(db: Session, user: User) -> list[Rol]:
    asignados = (db.query(Rol).join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
                 .filter(UsuarioRol.tenant_id == user.tenant_id, UsuarioRol.usuario_id == user.id,
                         Rol.tenant_id == user.tenant_id).all())
    if asignados:
        return [rol for rol in asignados if rol.activo]
    if not user.rol:
        return []
    rol = db.query(Rol).filter_by(tenant_id=user.tenant_id, nombre=normalizar(user.rol), activo=True).first()
    return [rol] if rol else []


def permisos_usuario(db: Session, user: User) -> list[str]:
    roles = roles_usuario(db, user)
    return sorted({p for rol in roles for p in (rol.permisos or [])})


def asignar_roles(db: Session, user: User, nombres: list[str]) -> None:
    nombres = list(dict.fromkeys(normalizar(nombre) for nombre in nombres))
    roles = db.query(Rol).filter(Rol.tenant_id == user.tenant_id, Rol.nombre.in_(nombres), Rol.activo.is_(True)).all() if nombres else []
    encontrados = {r.nombre for r in roles}
    if len(encontrados) != len(nombres):
        raise HTTPException(422, f"Roles inexistentes o inactivos: {', '.join(n for n in nombres if n not in encontrados)}")
    db.query(UsuarioRol).filter_by(tenant_id=user.tenant_id, usuario_id=user.id).delete(synchronize_session=False)
    for rol in roles:
        db.add(UsuarioRol(tenant_id=user.tenant_id, usuario_id=user.id, rol_id=rol.id))
    principal = next((r for r in ("administrador", "encargado", "vendedor", "cliente", "proveedor") if r in nombres), None)
    user.rol = catalogo.ROL_BACKEND.get(principal, principal) if principal else (nombres[0] if nombres else "")
    db.flush()


def registrar(db: Session, tenant_id: int, user_id: int | None, modulo: str, accion: str,
              entidad: str, entidad_id: int | None, detalle: str) -> None:
    actor = db.query(User).filter_by(tenant_id=tenant_id, id=user_id).first() if user_id else None
    db.add(Bitacora(tenant_id=tenant_id, usuario_id=user_id, actor=actor.nombre if actor else "Sistema",
                    modulo=modulo, accion=accion, entidad=entidad, entidad_id=entidad_id, detalle=detalle))


def salida_rol(db: Session, rol: Rol) -> dict:
    usuarios = db.query(User).filter_by(tenant_id=rol.tenant_id).all()
    cantidad = sum(any(r.id == rol.id for r in roles_usuario(db, user)) for user in usuarios)
    return {"id": rol.id, "nombre": rol.nombre, "descripcion": rol.descripcion,
            "activo": rol.activo, "usuarios": cantidad, "permisos": sorted(rol.permisos or []),
            "editable": rol.nombre != "administrador"}


def _validar_permisos(permisos: list[str]) -> list[str]:
    desconocidos = set(permisos) - catalogo.codigos()
    if desconocidos:
        raise HTTPException(422, f"Permisos desconocidos: {', '.join(sorted(desconocidos))}")
    return sorted(set(permisos))


def crear_rol(db: Session, tenant_id: int, nombre: str, descripcion: str | None, permisos: list[str], actor: int | None):
    nombre = normalizar(nombre)
    if nombre in {"superadmin", "superadministrador"}:
        raise HTTPException(409, "El nombre está reservado para la plataforma")
    if db.query(Rol).filter(Rol.tenant_id == tenant_id, func.lower(Rol.nombre) == nombre).first():
        raise HTTPException(409, "Ya existe un rol con ese nombre en esta empresa")
    rol = Rol(tenant_id=tenant_id, nombre=nombre, descripcion=descripcion, activo=True,
              permisos=_validar_permisos(permisos))
    db.add(rol)
    db.flush()
    registrar(db, tenant_id, actor, "ROLES", "CREAR", "rol", rol.id, f"Rol {nombre} creado")
    db.commit()
    return rol


def actualizar_rol(db: Session, tenant_id: int, id: int, datos: dict, actor: int | None):
    rol = db.query(Rol).filter_by(tenant_id=tenant_id, id=id).first()
    if rol is None:
        raise HTTPException(404, "Rol no encontrado")
    if rol.nombre in catalogo.PREDETERMINADOS:
        # Mantener el nombre de roles usados por el backend; solo admin es inmutable.
        if rol.nombre == "administrador":
            raise HTTPException(409, "El rol administrador conserva acceso para administrar la empresa")
        if "nombre" in datos and datos["nombre"] != rol.nombre:
            raise HTTPException(409, "No se puede renombrar un rol inicial")
    if "nombre" in datos and datos["nombre"]:
        nuevo = normalizar(datos["nombre"])
        if nuevo in {"superadmin", "superadministrador"}:
            raise HTTPException(409, "El nombre está reservado para la plataforma")
        if db.query(Rol).filter(Rol.tenant_id == tenant_id, Rol.nombre == nuevo, Rol.id != id).first():
            raise HTTPException(409, "Ya existe un rol con ese nombre")
        datos["nombre"] = nuevo
    if datos.get("permisos") is not None:
        datos["permisos"] = _validar_permisos(datos["permisos"])
    for campo, valor in datos.items():
        if valor is not None:
            setattr(rol, campo, valor)
    registrar(db, tenant_id, actor, "ROLES", "EDITAR", "rol", rol.id, f"Rol {rol.nombre} actualizado")
    db.commit()
    return rol


def eliminar_rol(db: Session, tenant_id: int, id: int, actor: int | None):
    rol = db.query(Rol).filter_by(tenant_id=tenant_id, id=id).first()
    if rol is None:
        raise HTTPException(404, "Rol no encontrado")
    if rol.nombre in catalogo.PREDETERMINADOS:
        raise HTTPException(409, "No se puede eliminar un rol inicial")
    asignados = salida_rol(db, rol)["usuarios"]
    nombre = rol.nombre
    if asignados:
        rol.activo = False
        detalle = f"El rol lo usan {asignados} usuarios: se desactivó"
    else:
        db.delete(rol)
        detalle = "Rol eliminado"
    registrar(db, tenant_id, actor, "ROLES", "ELIMINAR", "rol", id, f"Rol {nombre}: {detalle}")
    db.commit()
    return {"detail": detalle}
