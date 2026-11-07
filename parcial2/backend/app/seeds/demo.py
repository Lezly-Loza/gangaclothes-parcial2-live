"""Semillas de demostracion.
Ejecucion:  python -m app.seeds.demo
Resultado:  3 planes, 1 superadmin, 2 empresas contratantes con sus admins,
            sucursales y suscripciones. Suficiente para probar aislamiento
            y limites.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..core.database import SessionLocal, init_db
from ..core.security import hash_password
from ..models import (Plan, Sucursal, SuperAdmin, Suscripcion, Tenant, User, Categoria, Talla,
                      Color, Temporada, Producto, Variante, Proveedor, Cliente, Inventario,
                      Venta, DetalleVenta, Pago, MovimientoInventario, Reserva, DetalleReserva)


PLANES = [
    dict(
        codigo="basico",
        nombre="Basico",
        descripcion="Plan de arranque: 1 sucursal, 3 usuarios, 100 productos.",
        max_sucursales=1,
        max_usuarios=3,
        max_productos=100,
        modulos=["ventas", "inventario"],
        precio_mensual=19.0,
    ),
    dict(
        codigo="profesional",
        nombre="Profesional",
        descripcion="Hasta 3 sucursales, 10 usuarios, 1000 productos.",
        max_sucursales=3,
        max_usuarios=10,
        max_productos=1000,
        modulos=["ventas", "inventario", "reportes", "promociones"],
        precio_mensual=49.0,
    ),
    dict(
        codigo="empresarial",
        nombre="Empresarial",
        descripcion="Hasta 10 sucursales, 50 usuarios, productos ilimitados en la practica.",
        max_sucursales=10,
        max_usuarios=50,
        max_productos=100000,
        modulos=["ventas", "inventario", "reportes", "promociones", "ia", "sincronizacion_offline"],
        precio_mensual=129.0,
    ),
]


SUPERADMIN = dict(
    email="root@plataforma.bo",
    password="SuperSegura123",
    nombre="Root Plataforma",
)


EMPRESAS = [
    dict(
        tenant=dict(
            razon_social="Boutique Luna SRL",
            nit="1023456789",
            correo="contacto@boutique-luna.bo",
            telefono="+591 70000001",
            codigo="luna",
        ),
        plan="profesional",
        admin=dict(nombre="Ana Luna", email="ana@boutique-luna.bo", password="Luna12345"),
        extra_users=[
            dict(nombre="Encargado Luna", email="encargado@boutique-luna.bo", password="Luna12345", rol="encargado"),
        ],
        sucursales=[
            dict(codigo="suc-01", nombre="Luna Centro", ciudad="Santa Cruz", direccion="Av. Monseñor Rivero 123", horario="10:00-20:00"),
            dict(codigo="suc-02", nombre="Luna Equipetrol", ciudad="Santa Cruz", direccion="Av. San Martin 500", horario="10:00-22:00"),
        ],
    ),
    dict(
        tenant=dict(
            razon_social="Moda Andina SA",
            nit="2098765432",
            correo="hola@modaandina.bo",
            telefono="+591 71111111",
            codigo="andina",
        ),
        plan="basico",
        admin=dict(nombre="Rodrigo Mamani", email="rodrigo@modaandina.bo", password="Andina12345"),
        extra_users=[],
        sucursales=[
            dict(codigo="suc-01", nombre="Andina La Paz", ciudad="La Paz", direccion="Calle Sagarnaga 456", horario="09:00-19:00"),
        ],
    ),
]


def _ensure_planes(db: Session) -> dict[str, Plan]:
    out: dict[str, Plan] = {}
    for p in PLANES:
        existing = db.query(Plan).filter(Plan.codigo == p["codigo"]).first()
        if existing:
            out[p["codigo"]] = existing
            continue
        plan = Plan(**p)
        db.add(plan)
        db.flush()
        out[p["codigo"]] = plan
    return out


def _ensure_super(db: Session) -> SuperAdmin:
    sa = db.query(SuperAdmin).filter(SuperAdmin.email == SUPERADMIN["email"]).first()
    if sa:
        return sa
    sa = SuperAdmin(
        email=SUPERADMIN["email"],
        password_hash=hash_password(SUPERADMIN["password"]),
        nombre=SUPERADMIN["nombre"],
        activo=True,
    )
    db.add(sa)
    db.flush()
    return sa


def _ensure_empresa(db: Session, data: dict, planes: dict[str, Plan]) -> Tenant:
    t_data = data["tenant"]
    tenant = db.query(Tenant).filter(Tenant.codigo == t_data["codigo"]).first()
    if not tenant:
        tenant = Tenant(**t_data, estado="activo", activo=True)
        db.add(tenant)
        db.flush()

    from ..modules.seguridad.service import asegurar_roles
    asegurar_roles(db, tenant.id)

    if not db.query(User).filter(User.tenant_id == tenant.id, User.email == data["admin"]["email"]).first():
        db.add(User(
            tenant_id=tenant.id,
            email=data["admin"]["email"],
            password_hash=hash_password(data["admin"]["password"]),
            nombre=data["admin"]["nombre"],
            rol="admin",
            estado="activo",
            activo=True,
        ))

    for extra in data.get("extra_users", []):
        if not db.query(User).filter(User.tenant_id == tenant.id, User.email == extra["email"]).first():
            db.add(User(
                tenant_id=tenant.id,
                email=extra["email"],
                password_hash=hash_password(extra["password"]),
                nombre=extra["nombre"],
                rol=extra.get("rol", "encargado"),
                estado="activo",
                activo=True,
            ))

    if not db.query(Suscripcion).filter(Suscripcion.tenant_id == tenant.id, Suscripcion.estado == "activa").first():
        plan = planes[data["plan"]]
        hoy = date.today()
        db.add(Suscripcion(
            tenant_id=tenant.id,
            plan_id=plan.id,
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=30),
            estado="activa",
        ))

    for s in data["sucursales"]:
        exists = (
            db.query(Sucursal)
            .filter(Sucursal.tenant_id == tenant.id, Sucursal.codigo == s["codigo"])
            .first()
        )
        if not exists:
            db.add(Sucursal(
                tenant_id=tenant.id,
                codigo=s["codigo"],
                nombre=s["nombre"],
                ciudad=s["ciudad"],
                direccion=s["direccion"],
                horario=s.get("horario"),
                estado="activa",
                activo=True,
            ))

    return tenant


def run() -> None:
    init_db()
    db = SessionLocal()
    try:
        planes = _ensure_planes(db)
        _ensure_super(db)
        for empresa in EMPRESAS:
            _ensure_empresa(db, empresa, planes)
        db.commit()
        from ..modules.catalogos.compatibilidad import asegurar_ciudades
        for tenant in db.query(Tenant).all():
            asegurar_ciudades(db, tenant.id)
        db.commit()
        _ensure_negocio(db)
        print("Semillas aplicadas:")
        print(f"  - {db.query(Plan).count()} planes")
        print(f"  - {db.query(SuperAdmin).count()} superadmin")
        print(f"  - {db.query(Tenant).count()} empresas")
        print(f"  - {db.query(User).count()} usuarios de tenant")
        print(f"  - {db.query(Sucursal).count()} sucursales")
        print(f"  - {db.query(Suscripcion).count()} suscripciones")
    finally:
        db.close()


def _ensure_negocio(db: Session) -> None:
    luna = db.query(Tenant).filter_by(codigo="luna").one()
    andina = db.query(Tenant).filter_by(codigo="andina").one()
    if db.query(Producto).filter_by(tenant_id=luna.id).first():
        return
    for nombre, correo, rol in (("Vendedora Luna", "vendedor@boutique-luna.bo", "vendedor"),
                                ("Cliente Luna", "cliente@boutique-luna.bo", "cliente")):
        if not db.query(User).filter_by(tenant_id=luna.id, email=correo).first():
            db.add(User(tenant_id=luna.id, nombre=nombre, email=correo, rol=rol,
                        password_hash=hash_password("Luna12345"), activo=True, estado="activo"))
    db.flush()
    usuario_cliente = db.query(User).filter_by(tenant_id=luna.id, rol="cliente").first()
    categorias = []
    for nombre in ("Poleras", "Pantalones", "Vestidos", "Chaquetas"):
        row = Categoria(tenant_id=luna.id, nombre=nombre, activo=True)
        db.add(row)
        categorias.append(row)
    tallas = []
    for nombre in ("S", "M", "L", "XL"):
        row = Talla(tenant_id=luna.id, nombre=nombre, activo=True)
        db.add(row)
        tallas.append(row)
    colores = []
    for nombre, hex_ in (("Negro", "#111111"), ("Blanco", "#FFFFFF"), ("Rojo", "#D43645"),
                         ("Azul", "#345CBA"), ("Verde", "#388A65")):
        row = Color(tenant_id=luna.id, nombre=nombre, codigo_hex=hex_, activo=True)
        db.add(row)
        colores.append(row)
    temporadas = []
    for nombre in ("Verano 2026", "Invierno 2026"):
        row = Temporada(tenant_id=luna.id, nombre=nombre, fecha_inicio=date.today() - timedelta(days=30),
                        fecha_fin=date.today() + timedelta(days=120), activo=True)
        db.add(row)
        temporadas.append(row)
    db.flush()
    for i in range(1, 4):
        db.add(Proveedor(tenant_id=luna.id, razon_social=f"Proveedor {i} SRL", nit=f"900000{i}",
                         contacto=f"Contacto {i}", telefono=f"7000000{i}", correo=f"proveedor{i}@ejemplo.bo", activo=True))
    for i in range(1, 7):
        db.add(Cliente(tenant_id=luna.id, nombre=f"Cliente Demo {i}", documento=f"10000{i}",
                       telefono=f"7100000{i}", correo=f"cliente{i}@ejemplo.bo",
                       user_id=usuario_cliente.id if i == 1 else None))
    db.flush()
    sucursales = db.query(Sucursal).filter_by(tenant_id=luna.id).order_by(Sucursal.id).all()
    variantes = []
    nombres = ("Polera clásica", "Jean recto", "Vestido floral", "Chaqueta denim", "Polera urbana",
               "Pantalón lino", "Vestido midi", "Chaqueta ligera", "Camisa básica", "Falda plisada")
    for i, nombre in enumerate(nombres):
        p = Producto(tenant_id=luna.id, nombre=nombre, descripcion=f"Prenda de temporada: {nombre}",
                     categoria_id=categorias[i % 4].id, temporada_id=temporadas[i % 2].id,
                     precio_base=80 + i * 12, activo=True)
        db.add(p)
        db.flush()
        for j in range(2 + i % 3):
            v = Variante(tenant_id=luna.id, producto_id=p.id, talla_id=tallas[j].id,
                         color_id=colores[(i + j) % 5].id, sku=f"LUN-{i+1:02d}-{j+1:02d}",
                         precio=80 + i * 12 + j * 3, activo=True)
            db.add(v)
            variantes.append(v)
    db.flush()
    for sucursal in sucursales:
        for index, variante in enumerate(variantes):
            db.add(Inventario(tenant_id=luna.id, sucursal_id=sucursal.id, variante_id=variante.id,
                              stock=2 if index == 0 else 12, reservado=0, stock_min=4, stock_max=30))
    db.flush()
    cliente = db.query(Cliente).filter_by(tenant_id=luna.id, documento="100001").one()
    vendedor = db.query(User).filter_by(tenant_id=luna.id, rol="vendedor").one()
    for i in range(4):
        v = variantes[i + 1]
        fecha = datetime.now(timezone.utc) - timedelta(days=10 if i == 0 else i)
        venta = Venta(tenant_id=luna.id, codigo=f"DEMO-V-{i+1}", sucursal_id=sucursales[0].id,
                      usuario_id=vendedor.id, cliente_id=cliente.id, forma_pago="EFECTIVO",
                      total=v.precio, estado="CONFIRMADA", fecha=fecha)
        db.add(venta)
        db.flush()
        db.add(DetalleVenta(tenant_id=luna.id, venta_id=venta.id, variante_id=v.id,
                            cantidad=1, precio_unitario=v.precio, subtotal=v.precio))
        db.add(Pago(tenant_id=luna.id, venta_id=venta.id, metodo="EFECTIVO", monto=v.precio, estado="APROBADO"))
        db.add(MovimientoInventario(tenant_id=luna.id, sucursal_id=sucursales[0].id,
                                    variante_id=v.id, tipo="VENTA", cantidad=1, motivo=venta.codigo))
        db.query(Inventario).filter_by(tenant_id=luna.id, sucursal_id=sucursales[0].id,
                                       variante_id=v.id).one().stock -= 1
    for i in range(2):
        v = variantes[i + 6]
        reserva = Reserva(tenant_id=luna.id, codigo=f"DEMO-R-{i+1}", sucursal_id=sucursales[0].id,
                          cliente_id=cliente.id, estado="PENDIENTE")
        db.add(reserva)
        db.flush()
        db.add(DetalleReserva(tenant_id=luna.id, reserva_id=reserva.id, variante_id=v.id, cantidad=1))
        db.query(Inventario).filter_by(tenant_id=luna.id, sucursal_id=sucursales[0].id,
                                       variante_id=v.id).one().reservado += 1
    # Catálogo pequeño aislado para probar 404 cruzados.
    p = Producto(tenant_id=andina.id, nombre="Poncho Andino", precio_base=120, activo=True)
    db.add(p)
    db.commit()


if __name__ == "__main__":
    run()
