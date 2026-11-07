"""Script para enriquecer masivamente los datos de demostracion de GangaClothes SaaS (Parcial 2).
Añade productos, variantes, clientes, reservas, movimientos y ventas distribuidas en los ultimos 90 dias
para Boutique Luna SRL (luna) y Moda Andina SA (andina).
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models import (
    Categoria,
    Cliente,
    Color,
    DetalleReserva,
    DetalleVenta,
    Inventario,
    MovimientoInventario,
    Pago,
    Producto,
    Proveedor,
    Reserva,
    Sucursal,
    Talla,
    Temporada,
    Tenant,
    User,
    Variante,
    Venta,
)

PRENDAS_LUNA = [
    ("Blusa seda satinada", "Blusa formal de tacto suave para oficina o cóctel", "Poleras", 145.0, "Verano 2026"),
    ("Blazer ejecutivo", "Blazer entallado clásico con forro interior", "Chaquetas", 290.0, "Invierno 2026"),
    ("Vestido de gala noche", "Vestido largo elegante con caída fluida", "Vestidos", 340.0, "Invierno 2026"),
    ("Jean slouchy tiro alto", "Denim rígido 100% algodón, corte relaxed fit", "Pantalones", 185.0, "Verano 2026"),
    ("Short denim veraniego", "Short con dobladillo y detalles desflecados", "Pantalones", 110.0, "Verano 2026"),
    ("Top tejido rib", "Crop top elástico en tejido rib de punto fino", "Poleras", 75.0, "Verano 2026"),
    ("Pantalón palazzo lino", "Pantalón holgado fresco con cintura elastizada", "Pantalones", 165.0, "Verano 2026"),
    ("Camisa lino oversize", "Camisa ligera de cuello francés para clima cálido", "Poleras", 155.0, "Verano 2026"),
    ("Cardigan tejido botones", "Cardigan de manga larga con botones de carey", "Chaquetas", 195.0, "Invierno 2026"),
    ("Falda midi satén", "Falda corte al bies en satén con brillo sutil", "Vestidos", 170.0, "Verano 2026"),
    ("Trench coat impermeable", "Gabardina clásica cruzada con cinturón", "Chaquetas", 380.0, "Invierno 2026"),
    ("Enterizo casual verano", "Jumpsuit fresco sin mangas con lazo a la cintura", "Vestidos", 220.0, "Verano 2026"),
]

CLIENTES_NOMBRES = [
    ("María René Antelo", "7891234", "70011223", "mrene@correo.bo"),
    ("Carlos Mesa Gisbert", "4567890", "71122334", "cmesa@correo.bo"),
    ("Valeria Justiniano", "8901234", "72233445", "vjustiniano@correo.bo"),
    ("Diego Cuéllar Roca", "5678901", "73344556", "dcuellar@correo.bo"),
    ("Sebastián Banegas", "6789012", "74455667", "sbanegas@correo.bo"),
    ("Luciana Aguilera", "9012345", "75566778", "laguilera@correo.bo"),
    ("Fernando Camacho", "3456789", "76677889", "fcamacho@correo.bo"),
    ("Camila Paz Soldán", "2345678", "77788990", "cpaz@correo.bo"),
    ("Alejandro Daza", "1234567", "78899001", "adaza@correo.bo"),
    ("Natalia Cronenbold", "8765432", "79900112", "ncronenbold@correo.bo"),
    ("Jorge Wilstermann", "7654321", "70112233", "jw@correo.bo"),
    ("Paola Andrea Beltrán", "6543210", "71223344", "pbeltran@correo.bo"),
    ("Rodrigo Mercado", "5432109", "72334455", "rmercado@correo.bo"),
    ("Gabriela Zeballos", "4321098", "73445566", "gzeballos@correo.bo"),
]


def poblar_empresa_luna(db: Session) -> None:
    luna = db.query(Tenant).filter_by(codigo="luna").first()
    if not luna:
        print("Tenant 'luna' no encontrado.")
        return

    categorias_dict = {c.nombre: c for c in db.query(Categoria).filter_by(tenant_id=luna.id).all()}
    temporadas_dict = {t.nombre: t for t in db.query(Temporada).filter_by(tenant_id=luna.id).all()}
    tallas = db.query(Talla).filter_by(tenant_id=luna.id).all()
    colores = db.query(Color).filter_by(tenant_id=luna.id).all()
    sucursales = db.query(Sucursal).filter_by(tenant_id=luna.id).all()
    vendedor = db.query(User).filter_by(tenant_id=luna.id, rol="vendedor").first() or db.query(User).filter_by(tenant_id=luna.id).first()

    # 1. Crear clientes adicionales
    clientes = list(db.query(Cliente).filter_by(tenant_id=luna.id).all())
    for nombre, doc, tel, correo in CLIENTES_NOMBRES:
        if not db.query(Cliente).filter_by(tenant_id=luna.id, documento=doc).first():
            c = Cliente(tenant_id=luna.id, nombre=nombre, documento=doc, telefono=tel, correo=correo)
            db.add(c)
            clientes.append(c)
    db.flush()

    # 2. Crear prendas adicionales
    variantes_luna: list[Variante] = list(db.query(Variante).filter_by(tenant_id=luna.id).all())
    for idx, (nombre, desc, cat_nom, precio_base, temp_nom) in enumerate(PRENDAS_LUNA, start=100):
        if db.query(Producto).filter_by(tenant_id=luna.id, nombre=nombre).first():
            continue
        cat = categorias_dict.get(cat_nom) or list(categorias_dict.values())[0]
        temp = temporadas_dict.get(temp_nom) or list(temporadas_dict.values())[0]
        p = Producto(
            tenant_id=luna.id,
            nombre=nombre,
            descripcion=desc,
            categoria_id=cat.id,
            temporada_id=temp.id,
            precio_base=Decimal(str(precio_base)),
            activo=True,
        )
        db.add(p)
        db.flush()

        for j in range(len(tallas)):
            t = tallas[j]
            c = colores[j % len(colores)]
            precio_var = Decimal(str(precio_base + (j * 5)))
            sku = f"LUN-{idx:03d}-{t.nombre}-{c.nombre[:2].upper()}"
            v = Variante(
                tenant_id=luna.id,
                producto_id=p.id,
                talla_id=t.id,
                color_id=c.id,
                sku=sku,
                precio=precio_var,
                activo=True,
            )
            db.add(v)
            variantes_luna.append(v)
    db.flush()

    # 3. Asegurar inventarios en todas las sucursales
    for suc in sucursales:
        for idx, var in enumerate(variantes_luna):
            inv = db.query(Inventario).filter_by(tenant_id=luna.id, sucursal_id=suc.id, variante_id=var.id).first()
            if not inv:
                # Los primeros 2 tendrán stock bajo para ver alertas
                stock_val = 2 if idx in (3, 7) else random.randint(10, 35)
                db.add(
                    Inventario(
                        tenant_id=luna.id,
                        sucursal_id=suc.id,
                        variante_id=var.id,
                        stock=stock_val,
                        reservado=0,
                        stock_min=4,
                        stock_max=50,
                    )
                )
    db.flush()

    # 4. Generar 75 ventas históricas distribuidas en los últimos 90 días
    ventas_existentes = db.query(Venta).filter_by(tenant_id=luna.id).count()
    if ventas_existentes < 20:
        print(f"Generando ventas históricas para {luna.razon_social}...")
        now = datetime.now(timezone.utc)
        formas_pago = ["QR", "EFECTIVO", "TARJETA"]

        # Generar 70 ventas en fechas entre -90 días y hoy
        for n in range(1, 71):
            dias_atras = int((70 - n) * 1.25)  # distribución a lo largo de 90 días
            fecha_venta = now - timedelta(days=dias_atras, hours=random.randint(1, 10), minutes=random.randint(0, 59))
            cli = random.choice(clientes)
            suc = random.choice(sucursales)
            forma = random.choice(formas_pago)

            # 1 a 3 variantes por venta
            num_prendas = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
            vars_venta = random.sample(variantes_luna, num_prendas)

            total_venta = Decimal("0.00")
            detalles_data = []
            for v in vars_venta:
                cant = 1 if random.random() > 0.15 else 2
                subt = v.precio * cant
                total_venta += subt
                detalles_data.append((v, cant, v.precio, subt))

            codigo_v = f"VEN-{fecha_venta.strftime('%y%m')}-{n:04d}"
            venta = Venta(
                tenant_id=luna.id,
                codigo=codigo_v,
                sucursal_id=suc.id,
                usuario_id=vendedor.id if vendedor else None,
                cliente_id=cli.id,
                origen="EN_LINEA" if n % 3 == 0 else "TIENDA",
                fecha=fecha_venta,
                forma_pago=forma,
                total=total_venta,
                estado="CONFIRMADA",
            )
            db.add(venta)
            db.flush()

            for v, cant, precio_u, subt in detalles_data:
                db.add(
                    DetalleVenta(
                        tenant_id=luna.id,
                        venta_id=venta.id,
                        variante_id=v.id,
                        cantidad=cant,
                        precio_unitario=precio_u,
                        subtotal=subt,
                    )
                )
                db.add(
                    MovimientoInventario(
                        tenant_id=luna.id,
                        sucursal_id=suc.id,
                        variante_id=v.id,
                        tipo="VENTA",
                        cantidad=cant,
                        motivo=f"Venta {codigo_v}",
                        fecha=fecha_venta,
                    )
                )

            db.add(
                Pago(
                    tenant_id=luna.id,
                    venta_id=venta.id,
                    metodo=forma,
                    monto=total_venta,
                    referencia_pasarela=f"REF-{random.randint(100000, 999999)}",
                    estado="APROBADO",
                )
            )

    # 5. Generar 4 Reservas activas y recientes (CU-14 / CU-17 / CU-20)
    reservas_count = db.query(Reserva).filter_by(tenant_id=luna.id).count()
    if reservas_count < 6:
        now = datetime.now(timezone.utc)
        for i in range(1, 5):
            codigo_res = f"RES-260{i:03d}"
            if db.query(Reserva).filter_by(tenant_id=luna.id, codigo=codigo_res).first():
                continue
            cli = random.choice(clientes)
            suc = sucursales[0]
            var = variantes_luna[i + 2]
            reserva = Reserva(
                tenant_id=luna.id,
                codigo=codigo_res,
                sucursal_id=suc.id,
                cliente_id=cli.id,
                origen="EN_LINEA",
                fecha_limite=now + timedelta(hours=48),
                estado="PENDIENTE",
            )
            db.add(reserva)
            db.flush()
            db.add(DetalleReserva(tenant_id=luna.id, reserva_id=reserva.id, variante_id=var.id, cantidad=1))
            inv = db.query(Inventario).filter_by(tenant_id=luna.id, sucursal_id=suc.id, variante_id=var.id).first()
            if inv:
                inv.reservado += 1

    db.commit()
    print("Boutique Luna enriquecida exitosamente con datos realistas.")


def poblar_empresa_andina(db: Session) -> None:
    andina = db.query(Tenant).filter_by(codigo="andina").first()
    if not andina:
        return

    # Verificar si ya tiene sucursales y categorías
    sucursales = db.query(Sucursal).filter_by(tenant_id=andina.id).all()
    if len(sucursales) < 2:
        db.add(
            Sucursal(
                tenant_id=andina.id,
                codigo="suc-andina-cbba",
                nombre="Andina Cochabamba",
                ciudad="Cochabamba",
                direccion="Av. Heroínas 450",
                horario="09:00-19:00",
                estado="activa",
                activo=True,
            )
        )
        db.flush()
        sucursales = db.query(Sucursal).filter_by(tenant_id=andina.id).all()

    # Categorias para andina
    cats = {}
    for nom in ["Ponchos y Tejidos", "Aguayos y Frazadas", "Prendas de Alpaca"]:
        c = db.query(Categoria).filter_by(tenant_id=andina.id, nombre=nom).first()
        if not c:
            c = Categoria(tenant_id=andina.id, nombre=nom, activo=True)
            db.add(c)
            db.flush()
        cats[nom] = c

    tallas_andina = db.query(Talla).filter_by(tenant_id=andina.id).all()
    if not tallas_andina:
        for t_nom in ["Única", "M", "L"]:
            t = Talla(tenant_id=andina.id, nombre=t_nom, activo=True)
            db.add(t)
        db.flush()
        tallas_andina = db.query(Talla).filter_by(tenant_id=andina.id).all()

    colores_andina = db.query(Color).filter_by(tenant_id=andina.id).all()
    if not colores_andina:
        for col_nom, hx in [("Tierra", "#8B4513"), ("Rojo Andino", "#B22222"), ("Natural", "#F5F5DC")]:
            co = Color(tenant_id=andina.id, nombre=col_nom, codigo_hex=hx, activo=True)
            db.add(co)
        db.flush()
        colores_andina = db.query(Color).filter_by(tenant_id=andina.id).all()

    prendas_andina = [
        ("Poncho Tarabuco Tradicional", "Poncho tejido en telar artesanal con motivos andinos", "Ponchos y Tejidos", 280.0),
        ("Chalina de Alpaca Fina", "Bufanda 100% fibra de baby alpaca extra suave", "Prendas de Alpaca", 160.0),
        ("Aguayo Decorativo Grande", "Manta tejida tradicional para uso ornamental o vestir", "Aguayos y Frazadas", 130.0),
        ("Chaqueta Étnica Andina", "Chaqueta artesanal con aplicaciones bordadas a mano", "Prendas de Alpaca", 320.0),
        ("Saco Trenzado de Lana", "Abrigo tejido a mano en lana virgen de oveja", "Ponchos y Tejidos", 240.0),
    ]

    vars_andina = []
    for idx, (p_nom, p_desc, c_nom, p_base) in enumerate(prendas_andina, start=200):
        p = db.query(Producto).filter_by(tenant_id=andina.id, nombre=p_nom).first()
        if not p:
            p = Producto(
                tenant_id=andina.id,
                nombre=p_nom,
                descripcion=p_desc,
                categoria_id=cats[c_nom].id,
                precio_base=Decimal(str(p_base)),
                activo=True,
            )
            db.add(p)
            db.flush()
            for t in tallas_andina:
                v = Variante(
                    tenant_id=andina.id,
                    producto_id=p.id,
                    talla_id=t.id,
                    color_id=colores_andina[0].id,
                    sku=f"AND-{idx:03d}-{t.nombre[:1]}",
                    precio=Decimal(str(p_base)),
                    activo=True,
                )
                db.add(v)
                vars_andina.append(v)
        else:
            vars_andina.extend(db.query(Variante).filter_by(tenant_id=andina.id, producto_id=p.id).all())
    db.flush()

    for suc in sucursales:
        for v in vars_andina:
            inv = db.query(Inventario).filter_by(tenant_id=andina.id, sucursal_id=suc.id, variante_id=v.id).first()
            if not inv:
                db.add(
                    Inventario(
                        tenant_id=andina.id,
                        sucursal_id=suc.id,
                        variante_id=v.id,
                        stock=random.randint(8, 25),
                        reservado=0,
                        stock_min=3,
                        stock_max=40,
                    )
                )
    db.commit()
    print("Moda Andina enriquecida exitosamente con datos realistas.")


def main():
    init_db()
    db = SessionLocal()
    try:
        poblar_empresa_luna(db)
        poblar_empresa_andina(db)
        print("Enriquecimiento completo de base de datos finalizado.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
