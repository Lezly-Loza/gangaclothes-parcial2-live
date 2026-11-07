"""Catálogo compartido de permisos de las pantallas por empresa."""

MODULOS = {
    "USUARIOS": ("Usuarios", ("ver", "crear", "editar", "eliminar")),
    "ROLES": ("Roles y permisos", ("ver", "crear", "editar", "eliminar")),
    "BITACORA": ("Bitácora", ("ver",)),
    "CATALOGOS": ("Catálogos", ("ver", "crear", "editar", "eliminar")),
    "SUCURSALES": ("Sucursales", ("ver", "crear", "editar", "eliminar")),
    "PRENDAS": ("Prendas", ("ver", "crear", "editar", "eliminar")),
    "CLIENTES": ("Clientes", ("ver", "crear", "editar", "eliminar")),
    "PROVEEDORES": ("Proveedores", ("ver", "crear", "editar", "eliminar")),
    "INVENTARIO": ("Inventario", ("ver", "crear", "editar", "eliminar")),
    "RESERVAS": ("Reservas", ("ver", "crear", "editar", "eliminar", "anular")),
    "VENTAS": ("Ventas", ("ver", "crear", "editar", "eliminar", "anular")),
    "PAGOS": ("Pagos", ("ver", "crear", "editar")),
    "CAMBIOS": ("Cambios", ("ver", "crear")),
    "PROMOCIONES": ("Promociones", ("ver", "crear", "editar", "eliminar")),
    "REPORTES": ("Reportes", ("ver",)),
    "ENVIOS": ("Envíos", ("ver", "crear", "editar")),
    "OFERTA": ("Oferta del proveedor", ("ver", "crear", "editar", "eliminar")),
    "SUSCRIPCION": ("Suscripción", ("ver", "gestionar")),
}


def catalogo():
    return [{"modulo": modulo, "etiqueta": etiqueta, "descripcion": etiqueta,
             "permisos": [{"codigo": f"{modulo.lower()}:{accion}", "accion": accion.upper(),
                           "nombre": f"{accion.capitalize()} {etiqueta.lower()}", "descripcion": None}
                          for accion in acciones]}
            for modulo, (etiqueta, acciones) in MODULOS.items()]


def codigos():
    return {p["codigo"] for m in catalogo() for p in m["permisos"]}


PREDETERMINADOS = {
    "administrador": sorted(codigos()),
    "encargado": ["inventario:ver", "inventario:crear", "inventario:editar", "reservas:ver",
                   "reservas:anular", "ventas:anular", "reportes:ver", "sucursales:ver", "proveedores:ver"],
    "vendedor": ["prendas:ver", "inventario:ver", "clientes:ver", "clientes:crear",
                  "clientes:editar", "ventas:ver", "ventas:crear", "pagos:crear", "cambios:crear"],
    "cliente": ["reservas:crear", "ventas:crear"],
    "proveedor": ["oferta:ver", "oferta:crear", "oferta:editar"],
}

ALIAS = {"admin": "administrador", "cajero": "vendedor"}
ROL_BACKEND = {"administrador": "admin"}
