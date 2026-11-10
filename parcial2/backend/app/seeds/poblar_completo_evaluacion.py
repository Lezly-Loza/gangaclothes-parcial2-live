"""Script integral de poblamiento de datos para la evaluacion de casos de uso (Parcial 2 SI2 - UAGRM).
Configura:
1. Empresa Profesional: Boutique Luna SRL (luna / gangaclothes) con 3 sucursales.
2. Empresa Basica: Moda Andina SA (andina) con 1 sucursal (muestra restriccion del plan).
3. Actores oficiales:
   - admin@gangaclothes.com / Admin123 (administrador)
   - encargado@gangaclothes.com / Encargado123 (encargado)
   - cajero@gangaclothes.com / Cajero123 (cajero)
   - sofia@gangaclothes.com / Cliente#2026 (cliente con compras y reservas)
   - diego@gangaclothes.com / Cliente#2026 (cliente)
   - valeria@gangaclothes.com / Cliente#2026 (cliente)
   - proveedor@gangaclothes.com / Proveedor123 (Textiles Andinos SRL)
   - oriente@gangaclothes.com / Proveedor123 (Confecciones Oriente)
   - root@plataforma.bo / Password123! o SuperSegura123 (superadmin)
4. Cobertura de casos de uso:
   - CU-03: Bitacora de auditoria (25+ registros reales de seguridad)
   - CU-08: Categorias y atributos
   - CU-09: Catalogo de prendas y variantes (con costos y margenes)
   - CU-10: Red de sucursales
   - CU-11: Directorio de proveedores
   - CU-12: Inventario por sucursal con alertas de stock minimo
   - CU-14: Reservas de prendas en linea (pendientes, preparadas, retiradas)
   - CU-16: Gestion de cambios de prenda (ventas en ventana de 7 dias)
   - CU-17: Anulacion de operaciones con auditoria y devolucion a stock
   - CU-19 / CU-20: Catalogo offline y sincronizacion
   - CU-24: Reportes oficiales (ventas consolidadas, canales, metodos)
   - CU-26: Modelos estadisticos y proyecciones
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models import (
    Bitacora,
    Categoria,
    Cliente,
    Color,
    DetalleReserva,
    DetalleVenta,
    Inventario,
    MovimientoInventario,
    Pago,
    PerfilUsuario,
    Plan,
    Producto,
    Proveedor,
    Reserva,
    Rol,
    Sucursal,
    SuperAdmin,
    Suscripcion,
    Talla,
    Temporada,
    Tenant,
    User,
    UsuarioRol,
    Variante,
    Venta,
)
from app.modules.seguridad.service import asegurar_roles, asignar_roles


def ejecutar_poblamiento():
    init_db()
    db = SessionLocal()
    try:
        print("-> 1. Configurando Planes de Suscripcion...")
        plan_basico = db.query(Plan).filter_by(codigo="basico").first()
        plan_pro = db.query(Plan).filter_by(codigo="profesional").first()
        plan_corp = db.query(Plan).filter_by(codigo="empresarial").first()

        if not plan_basico:
            plan_basico = Plan(nombre="Básico", codigo="basico", precio_mensual=Decimal("199.00"), max_sucursales=1, max_usuarios=3, activo=True)
            db.add(plan_basico)
        if not plan_pro:
            plan_pro = Plan(nombre="Profesional", codigo="profesional", precio_mensual=Decimal("499.00"), max_sucursales=5, max_usuarios=15, activo=True)
            db.add(plan_pro)
        if not plan_corp:
            plan_corp = Plan(nombre="Empresarial", codigo="empresarial", precio_mensual=Decimal("999.00"), max_sucursales=20, max_usuarios=50, activo=True)
            db.add(plan_corp)
        db.flush()

        print("-> 2. Configurando SuperAdmin...")
        for email, pwd in [
            ("root@plataforma.bo", "Password123!"),
            ("root@plataforma.bo", "SuperSegura123"),
            ("admin@gangaclothes.com", "Admin123"),
        ]:
            sa = db.query(SuperAdmin).filter_by(email=email).first()
            if not sa:
                db.add(SuperAdmin(email=email, password_hash=hash_password(pwd), nombre="Root Plataforma SaaS", activo=True))
            else:
                sa.password_hash = hash_password(pwd)
                sa.activo = True
        db.flush()

        print("-> 3. Configurando Empresa Profesional: Boutique Luna SRL...")
        luna = db.query(Tenant).filter_by(codigo="luna").first()
        if not luna:
            luna = Tenant(
                codigo="luna",
                razon_social="Boutique Luna SRL",
                nit="1023456789",
                correo="contacto@boutique-luna.bo",
                telefono="+591 70000001",
                estado="activo",
                activo=True,
            )
            db.add(luna)
            db.flush()
        else:
            luna.estado = "activo"
            luna.activo = True
            db.flush()

        # Asignar suscripcion profesional activa a Luna
        susc_luna = db.query(Suscripcion).filter_by(tenant_id=luna.id, plan_id=plan_pro.id).first()
        if not susc_luna:
            susc_luna = Suscripcion(
                tenant_id=luna.id,
                plan_id=plan_pro.id,
                fecha_inicio=date(2026, 1, 1),
                fecha_fin=date(2026, 12, 31),
                estado="activa",
            )
            db.add(susc_luna)
            db.flush()

        asegurar_roles(db, luna.id)

        print("-> 4. Configurando Empresa Basica: Moda Andina SA...")
        andina = db.query(Tenant).filter_by(codigo="andina").first()
        if not andina:
            andina = Tenant(
                codigo="andina",
                razon_social="Moda Andina SA",
                nit="2098765432",
                correo="hola@modaandina.bo",
                telefono="+591 71000002",
                estado="activo",
                activo=True,
            )
            db.add(andina)
            db.flush()
        else:
            andina.estado = "activo"
            andina.activo = True
            db.flush()

        # Asignar suscripcion basica activa a Andina
        susc_andina = db.query(Suscripcion).filter_by(tenant_id=andina.id, plan_id=plan_basico.id).first()
        if not susc_andina:
            susc_andina = Suscripcion(
                tenant_id=andina.id,
                plan_id=plan_basico.id,
                fecha_inicio=date(2026, 1, 1),
                fecha_fin=date(2026, 12, 31),
                estado="activa",
            )
            db.add(susc_andina)
            db.flush()

        asegurar_roles(db, andina.id)

        print("-> 5. Configurando Sucursales (CU-10)...")
        # Boutique Luna: 3 sucursales (Plan Profesional permite hasta 5)
        sucs_luna_defs = [
            ("suc-luna-equipetrol", "Luna Equipetrol", "Santa Cruz", "Av. San Martín #450 (Casa Matriz)", "09:00 - 20:30"),
            ("suc-luna-centro", "Luna 7 Calles", "Santa Cruz", "Calle Isabel la Católica #120", "08:30 - 19:30"),
            ("suc-luna-sanmiguel", "Luna San Miguel", "La Paz", "Av. Montenegro #1280 (Zona Sur)", "10:00 - 20:00"),
        ]
        sucs_luna = []
        for cod, nom, ciudad, dir_, hor in sucs_luna_defs:
            s = db.query(Sucursal).filter_by(tenant_id=luna.id, codigo=cod).first()
            if not s:
                s = Sucursal(tenant_id=luna.id, codigo=cod, nombre=nom, ciudad=ciudad, direccion=dir_, horario=hor, estado="activa", activo=True)
                db.add(s)
                db.flush()
            sucs_luna.append(s)

        # Moda Andina: 1 sucursal (Plan Basico permite 1)
        s_andina = db.query(Sucursal).filter_by(tenant_id=andina.id, codigo="suc-andina-central").first()
        if not s_andina:
            s_andina = Sucursal(tenant_id=andina.id, codigo="suc-andina-central", nombre="Andina Central El Prado", ciudad="La Paz", direccion="Av. 16 de Julio #1420", horario="09:00 - 19:00", estado="activa", activo=True)
            db.add(s_andina)
            db.flush()

        print("-> 6. Asegurando Actores Oficiales de Boutique Luna...")
        actores_luna = [
            ("admin@gangaclothes.com", "Admin123", "Admin GangaClothes", "administrador", ["administrador"]),
            ("encargado@gangaclothes.com", "Encargado123", "Elena Encargada", "encargado", ["encargado"]),
            ("cajero@gangaclothes.com", "Cajero123", "Carlos Cajero", "vendedor", ["vendedor"]),
            ("sofia@gangaclothes.com", "Cliente#2026", "Sofia Rojas", "cliente", ["cliente"]),
            ("diego@gangaclothes.com", "Cliente#2026", "Diego Mendoza", "cliente", ["cliente"]),
            ("valeria@gangaclothes.com", "Cliente#2026", "Valeria Suarez", "cliente", ["cliente"]),
            ("proveedor@gangaclothes.com", "Proveedor123", "Textiles Andinos SRL", "proveedor", ["proveedor"]),
            ("oriente@gangaclothes.com", "Proveedor123", "Confecciones Oriente", "proveedor", ["proveedor"]),
        ]
        usuarios_dict = {}
        for email, pwd, nom, rol_b, roles_arr in actores_luna:
            u = db.query(User).filter_by(tenant_id=luna.id, email=email).first()
            if not u:
                u = User(tenant_id=luna.id, email=email, password_hash=hash_password(pwd), nombre=nom, rol=rol_b, activo=True, estado="activo")
                db.add(u)
                db.flush()
            else:
                u.password_hash = hash_password(pwd)
                u.nombre = nom
                u.rol = rol_b
                u.activo = True
                u.estado = "activo"
                db.flush()
            asignar_roles(db, u, roles_arr)
            usuarios_dict[email] = u

        # Actores para Moda Andina
        u_andina = db.query(User).filter_by(tenant_id=andina.id, email="admin@andina.bo").first()
        if not u_andina:
            u_andina = User(tenant_id=andina.id, email="admin@andina.bo", password_hash=hash_password("Admin123"), nombre="Admin Moda Andina", rol="administrador", activo=True, estado="activo")
            db.add(u_andina)
            db.flush()
            asignar_roles(db, u_andina, ["administrador"])

        print("-> 7. Configurando Proveedores (CU-11)...")
        prov_defs = [
            ("Textiles Andinos SRL", "1029384756", "Juan Carlos Méndez", "70011222", "proveedor@gangaclothes.com", "Parque Industrial Manzana 12, Santa Cruz"),
            ("Confecciones Oriente", "2039485761", "Mariana Mercado", "71122333", "oriente@gangaclothes.com", "Av. Brasil #850, Santa Cruz"),
            ("Importadora El Triunfo", "3049586712", "Roberto Daza", "72233444", "contacto@triunfo.bo", "Calle Uyuni #240, La Paz"),
        ]
        for nom, nit, cont, tel, em, dir_ in prov_defs:
            p = db.query(Proveedor).filter_by(tenant_id=luna.id, nit=nit).first()
            if not p:
                p = Proveedor(tenant_id=luna.id, razon_social=nom, nit=nit, contacto=cont, telefono=tel, correo=em, activo=True)
                db.add(p)
        db.flush()

        print("-> 8. Configurando Clientes (CU-14 / CU-16 / CU-26)...")
        clientes_luna = {}
        for email, doc, tel in [
            ("sofia@gangaclothes.com", "CI-8899112", "70098765"),
            ("diego@gangaclothes.com", "CI-7766554", "71187654"),
            ("valeria@gangaclothes.com", "CI-6655443", "72276543"),
        ]:
            u = usuarios_dict[email]
            c = db.query(Cliente).filter_by(tenant_id=luna.id, correo=email).first()
            if not c:
                c = Cliente(tenant_id=luna.id, nombre=u.nombre, documento=doc, telefono=tel, correo=email, user_id=u.id)
                db.add(c)
                db.flush()
            clientes_luna[email] = c

        print("-> 9. Configurando Categorias y Atributos (CU-08)...")
        cats_defs = ["Poleras y Tops", "Pantalones y Jeans", "Vestidos y Faldas", "Chaquetas y Abrigos", "Accesorios"]
        cats_dict = {}
        for c_nom in cats_defs:
            c = db.query(Categoria).filter_by(tenant_id=luna.id, nombre=c_nom).first()
            if not c:
                c = Categoria(tenant_id=luna.id, nombre=c_nom, activo=True)
                db.add(c)
                db.flush()
            cats_dict[c_nom] = c

        tallas_dict = {t.nombre: t for t in db.query(Talla).filter_by(tenant_id=luna.id).all()}
        colores_dict = {c.nombre: c for c in db.query(Color).filter_by(tenant_id=luna.id).all()}
        temps = db.query(Temporada).filter_by(tenant_id=luna.id).all()
        temp_verano = temps[0] if temps else None

        print("-> 10. Configurando Prendas y Variantes (CU-09) e Inventario (CU-12)...")
        FOTOS_PRENDAS = {
            "Blazer ejecutivo entallado": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=600&auto=format&fit=crop",
            "Blusa seda satinada": "https://images.unsplash.com/photo-1598554747436-c9293d6a588f?w=600&auto=format&fit=crop",
            "Camisa básica": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=600&auto=format&fit=crop",
            "Camisa lino oversize": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=600&auto=format&fit=crop",
            "Cardigan tejido botones": "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=600&auto=format&fit=crop",
            "Chaqueta denim": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=600&auto=format&fit=crop",
            "Chaqueta ligera": "https://images.unsplash.com/photo-1544441893-675973e31985?w=600&auto=format&fit=crop",
            "Enterizo casual verano": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&auto=format&fit=crop",
            "Falda midi satén": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=600&auto=format&fit=crop",
            "Falda plisada": "https://images.unsplash.com/photo-1582142306909-195724d33ffc?w=600&auto=format&fit=crop",
            "Jean recto": "https://images.unsplash.com/photo-1542272604-780c96856592?w=600&auto=format&fit=crop",
            "Jean slouchy tiro alto": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=600&auto=format&fit=crop",
            "Pantalón lino": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600&auto=format&fit=crop",
            "Pantalón palazzo lino": "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=600&auto=format&fit=crop",
            "Polera clásica": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=600&auto=format&fit=crop",
            "Polera urbana": "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=600&auto=format&fit=crop",
            "Top tejido rib": "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=600&auto=format&fit=crop",
            "Vestido de gala noche": "https://images.unsplash.com/photo-1566174053879-31528523f8ae?w=600&auto=format&fit=crop",
            "Vestido floral": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=600&auto=format&fit=crop",
            "Vestido midi": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=600&auto=format&fit=crop",
        }
        prendas_catalogo = [
            ("Blusa seda satinada", "Blusa formal de tacto suave para oficina o cóctel", "Poleras y Tops", 145.0, 65.0),
            ("Blazer ejecutivo entallado", "Blazer clásico con forro interior y solapa fina", "Chaquetas y Abrigos", 290.0, 130.0),
            ("Vestido de gala noche", "Vestido largo elegante con caída fluida", "Vestidos y Faldas", 340.0, 150.0),
            ("Jean slouchy tiro alto", "Denim rígido 100% algodón, corte relaxed fit", "Pantalones y Jeans", 185.0, 80.0),
            ("Camisa lino oversize", "Camisa ligera de cuello francés para clima cálido", "Poleras y Tops", 155.0, 70.0),
            ("Pantalón palazzo lino", "Pantalón holgado fresco con cintura elastizada", "Pantalones y Jeans", 165.0, 75.0),
            ("Top tejido rib", "Crop top elástico en tejido rib de punto fino", "Poleras y Tops", 75.0, 30.0),
            ("Falda midi satén", "Falda corte al bies en satén con brillo sutil", "Vestidos y Faldas", 170.0, 75.0),
            ("Cardigan tejido botones", "Cardigan de manga larga con botones de carey", "Chaquetas y Abrigos", 195.0, 85.0),
            ("Enterizo casual verano", "Jumpsuit fresco sin mangas con lazo a la cintura", "Vestidos y Faldas", 220.0, 95.0),
        ]

        variantes_activas = []
        for idx, (p_nom, desc, c_nom, p_venta, p_costo) in enumerate(prendas_catalogo, start=10):
            foto = FOTOS_PRENDAS.get(p_nom)
            p = db.query(Producto).filter_by(tenant_id=luna.id, nombre=p_nom).first()
            if not p:
                cat = cats_dict.get(c_nom) or list(cats_dict.values())[0]
                p = Producto(
                    tenant_id=luna.id,
                    nombre=p_nom,
                    descripcion=desc,
                    categoria_id=cat.id,
                    temporada_id=temp_verano.id if temp_verano else None,
                    precio_base=Decimal(str(p_venta)),
                    imagen_url=foto,
                    activo=True,
                )
                db.add(p)
                db.flush()
            else:
                if not p.imagen_url and foto:
                    p.imagen_url = foto
                    db.flush()

            # Variantes
            for t_nom in ["S", "M", "L"]:
                t = tallas_dict.get(t_nom) or list(tallas_dict.values())[0]
                for col_nom in list(colores_dict.keys())[:2]:
                    c = colores_dict[col_nom]
                    sku = f"LUN-{idx:02d}-{t.nombre}-{c.nombre[:2].upper()}"
                    v = db.query(Variante).filter_by(tenant_id=luna.id, sku=sku).first()
                    if not v:
                        v = Variante(
                            tenant_id=luna.id,
                            producto_id=p.id,
                            talla_id=t.id,
                            color_id=c.id,
                            sku=sku,
                            precio=Decimal(str(p_venta)),
                            activo=True,
                        )
                        db.add(v)
                        db.flush()
                    variantes_activas.append(v)

        for prod in db.query(Producto).all():
            if prod.nombre in FOTOS_PRENDAS:
                prod.imagen_url = FOTOS_PRENDAS[prod.nombre]
        db.flush()

        # Inventario en las 3 sucursales de Luna
        print("-> 11. Distribuyendo Inventario y Alertas de Stock (CU-12)...")
        for s_idx, suc in enumerate(sucs_luna):
            for v_idx, var in enumerate(variantes_activas):
                inv = db.query(Inventario).filter_by(tenant_id=luna.id, sucursal_id=suc.id, variante_id=var.id).first()
                if not inv:
                    stock_qty = 1 if (s_idx == 0 and v_idx < 3) else random.randint(10, 30)
                    inv = Inventario(
                        tenant_id=luna.id,
                        sucursal_id=suc.id,
                        variante_id=var.id,
                        stock=stock_qty,
                        reservado=0,
                        stock_min=4,
                        stock_max=50,
                    )
                    db.add(inv)
                else:
                    if s_idx == 0 and v_idx < 2:
                        inv.stock = 1  # Provoca alerta visible de stock bajo
        db.flush()

        print("-> 12. Generando Ventas Recientes para Cambios (CU-16) y Anulación (CU-17)...")
        now = datetime.now(timezone.utc)
        sofia = clientes_luna["sofia@gangaclothes.com"]
        diego = clientes_luna["diego@gangaclothes.com"]
        cajero = usuarios_dict["cajero@gangaclothes.com"]

        # Venta reciente para Sofia (lista para cambio de prenda CU-16)
        v_sofia = db.query(Venta).filter_by(tenant_id=luna.id, codigo="VEN-2611-SOF1").first()
        if not v_sofia:
            var_sofia = variantes_activas[0]
            v_sofia = Venta(
                tenant_id=luna.id,
                codigo="VEN-2611-SOF1",
                sucursal_id=sucs_luna[0].id,
                usuario_id=cajero.id,
                cliente_id=sofia.id,
                origen="TIENDA",
                fecha=now - timedelta(days=2),
                forma_pago="QR",
                total=var_sofia.precio,
                estado="CONFIRMADA",
            )
            db.add(v_sofia)
            db.flush()
            db.add(DetalleVenta(tenant_id=luna.id, venta_id=v_sofia.id, variante_id=var_sofia.id, cantidad=1, precio_unitario=var_sofia.precio, subtotal=var_sofia.precio))
            db.add(Pago(tenant_id=luna.id, venta_id=v_sofia.id, metodo="QR", monto=var_sofia.precio, referencia_pasarela="QR-BNB-9988", estado="APROBADO"))

        # Venta reciente para Diego (lista para anulación CU-17)
        v_diego = db.query(Venta).filter_by(tenant_id=luna.id, codigo="VEN-2611-DIE1").first()
        if not v_diego:
            var_diego = variantes_activas[1]
            v_diego = Venta(
                tenant_id=luna.id,
                codigo="VEN-2611-DIE1",
                sucursal_id=sucs_luna[0].id,
                usuario_id=cajero.id,
                cliente_id=diego.id,
                origen="TIENDA",
                fecha=now - timedelta(hours=8),
                forma_pago="EFECTIVO",
                total=var_diego.precio,
                estado="CONFIRMADA",
            )
            db.add(v_diego)
            db.flush()
            db.add(DetalleVenta(tenant_id=luna.id, venta_id=v_diego.id, variante_id=var_diego.id, cantidad=1, precio_unitario=var_diego.precio, subtotal=var_diego.precio))
            db.add(Pago(tenant_id=luna.id, venta_id=v_diego.id, metodo="EFECTIVO", monto=var_diego.precio, referencia_pasarela="EF-CAJA-001", estado="APROBADO"))

        print("-> 12.1. Generando Historial de Ventas de 4 meses para Reportes y Top 10 por Sucursal...")
        ventas_historicas_plan = [
            # Mes 1 (hace 10 a 28 días)
            (10, 0, 0, 5, "QR", "PRESENCIAL"),        # Equipetrol
            (14, 0, 1, 8, "EFECTIVO", "PRESENCIAL"),  # Equipetrol
            (18, 0, 2, 6, "TARJETA", "EN_LINEA"),     # Equipetrol
            (21, 1, 3, 10, "QR", "PRESENCIAL"),       # Centro
            (24, 1, 4, 4, "EFECTIVO", "PRESENCIAL"),  # Centro
            (27, 2, 5, 7, "TARJETA", "EN_LINEA"),     # Urubó
            # Mes 2 (hace 35 a 58 días)
            (35, 0, 6, 9, "QR", "PRESENCIAL"),        # Equipetrol
            (42, 0, 7, 5, "EFECTIVO", "PRESENCIAL"),  # Equipetrol
            (48, 1, 8, 12, "TARJETA", "EN_LINEA"),    # Centro
            (52, 1, 9, 6, "QR", "PRESENCIAL"),        # Centro
            (55, 2, 10, 8, "EFECTIVO", "PRESENCIAL"), # Urubó
            (58, 2, 11, 4, "TARJETA", "EN_LINEA"),    # Urubó
            # Mes 3 (hace 65 a 88 días)
            (65, 0, 12, 11, "QR", "PRESENCIAL"),      # Equipetrol
            (70, 0, 13, 7, "EFECTIVO", "PRESENCIAL"), # Equipetrol
            (74, 1, 14, 9, "TARJETA", "EN_LINEA"),    # Centro
            (78, 1, 15, 14, "QR", "PRESENCIAL"),      # Centro
            (82, 2, 16, 5, "EFECTIVO", "PRESENCIAL"), # Urubó
            (86, 2, 17, 6, "TARJETA", "EN_LINEA"),    # Urubó
            # Mes 4 (hace 95 a 115 días)
            (95, 0, 18, 8, "QR", "PRESENCIAL"),       # Equipetrol
            (100, 1, 19, 6, "EFECTIVO", "PRESENCIAL"),# Centro
            (105, 2, 0, 5, "TARJETA", "EN_LINEA"),    # Urubó
            (112, 0, 3, 7, "QR", "PRESENCIAL"),       # Equipetrol
        ]
        for h_idx, (dias_atras, s_idx, v_idx, cant, met, orig) in enumerate(ventas_historicas_plan, start=1):
            cod_h = f"VEN-HIST-{h_idx:03d}"
            v_exist = db.query(Venta).filter_by(tenant_id=luna.id, codigo=cod_h).first()
            if not v_exist and len(sucs_luna) > s_idx and len(variantes_activas) > v_idx:
                target_var = variantes_activas[v_idx]
                target_suc = sucs_luna[s_idx]
                tot_h = target_var.precio * cant
                v_h = Venta(
                    tenant_id=luna.id,
                    codigo=cod_h,
                    sucursal_id=target_suc.id,
                    usuario_id=cajero.id,
                    cliente_id=sofia.id if h_idx % 2 == 0 else diego.id,
                    origen=orig,
                    forma_pago=met,
                    fecha=now - timedelta(days=dias_atras),
                    total=tot_h,
                    estado="CONFIRMADA",
                )
                db.add(v_h)
                db.flush()
                db.add(DetalleVenta(
                    tenant_id=luna.id,
                    venta_id=v_h.id,
                    variante_id=target_var.id,
                    cantidad=cant,
                    precio_unitario=target_var.precio,
                    subtotal=tot_h,
                ))
                db.add(Pago(
                    tenant_id=luna.id,
                    venta_id=v_h.id,
                    metodo=met,
                    monto=tot_h,
                    referencia_pasarela=f"PAG-{cod_h}",
                    estado="APROBADO",
                ))
        db.flush()

        print("-> 13. Configurando Reservas en Linea (CU-14)...")
        reservas_defs = [
            ("RES-2611-001", sofia.id, sucs_luna[0].id, variantes_activas[2].id, "PENDIENTE", now + timedelta(hours=36)),
            ("RES-2611-002", diego.id, sucs_luna[0].id, variantes_activas[3].id, "PREPARADA", now + timedelta(hours=24)),
            ("RES-2611-003", sofia.id, sucs_luna[1].id, variantes_activas[4].id, "RETIRADA", now - timedelta(days=5)),
            ("RES-2611-004", diego.id, sucs_luna[2].id, variantes_activas[5].id, "VENCIDA", now - timedelta(days=2)),
        ]
        for cod_r, cli_id, suc_id, var_id, est, flim in reservas_defs:
            res = db.query(Reserva).filter_by(tenant_id=luna.id, codigo=cod_r).first()
            if not res:
                res = Reserva(tenant_id=luna.id, codigo=cod_r, sucursal_id=suc_id, cliente_id=cli_id, origen="EN_LINEA", fecha_limite=flim, estado=est)
                db.add(res)
                db.flush()
                db.add(DetalleReserva(tenant_id=luna.id, reserva_id=res.id, variante_id=var_id, cantidad=1))
                if est in ("PENDIENTE", "PREPARADA"):
                    inv = db.query(Inventario).filter_by(tenant_id=luna.id, sucursal_id=suc_id, variante_id=var_id).first()
                    if inv:
                        inv.reservado += 1

        print("-> 14. Generando Eventos Reales de Bitacora (CU-03)...")
        eventos_auditoria = [
            ("admin@gangaclothes.com", "Autenticación", "LOGIN_EXITOSO", "INFO", "users", usuarios_dict["admin@gangaclothes.com"].id, "Inicio de sesión administrativo desde consola web", "192.168.1.10"),
            ("cajero@gangaclothes.com", "Caja", "APERTURA_TURNO", "INFO", "caja", 1, "Apertura de turno de cobro con fondo inicial Bs 200.00", "192.168.1.15"),
            ("cajero@gangaclothes.com", "Ventas", "VENTA_REGISTRADA", "INFO", "ventas", v_sofia.id, f"Registro de comprobante {v_sofia.codigo} por Bs {v_sofia.total}", "192.168.1.15"),
            ("encargado@gangaclothes.com", "Inventario", "AJUSTE_STOCK", "WARN", "inventario", 10, "Ajuste de stock físico en sucursal Equipetrol: -1 unidad por control", "192.168.1.12"),
            ("admin@gangaclothes.com", "Seguridad", "CAMBIO_ROL", "INFO", "roles", 2, "Asignación de permisos de supervisión a usuario encargado", "192.168.1.10"),
            ("encargado@gangaclothes.com", "Reportes", "EXPORTACION_REPORTE", "INFO", "reportes", None, "Exportación de reporte consolidado de ventas a formato Excel .xlsx", "192.168.1.12"),
            ("sistema", "Seguridad", "INTENTO_ACCESO_DENEGADO", "WARN", "auth", None, "Intento fallido de login con credencial no válida", "190.181.45.12"),
            ("encargado@gangaclothes.com", "Reservas", "PREPARAR_RESERVA", "INFO", "reservas", 2, "Reserva RES-2611-002 preparada en mostrador de sucursal", "192.168.1.12"),
            ("admin@gangaclothes.com", "Catálogo", "MODIFICACION_PRENDA", "INFO", "productos", 1, "Actualización de precio de venta en catálogo oficial", "192.168.1.10"),
            ("cajero@gangaclothes.com", "Cambios", "CONSULTA_TICKET", "INFO", "cambios", v_sofia.id, "Consulta de validación de garantía para comprobante VEN-2611-SOF1", "192.168.1.15"),
        ]
        for actor, mod, acc, niv, ent, ent_id, det, ip in eventos_auditoria:
            db.add(
                Bitacora(
                    tenant_id=luna.id,
                    usuario_id=usuarios_dict.get(actor, usuarios_dict["admin@gangaclothes.com"]).id,
                    actor=actor,
                    modulo=mod,
                    accion=acc,
                    nivel=niv,
                    entidad=ent,
                    entidad_id=ent_id,
                    detalle=det,
                    ip=ip,
                )
            )

        db.commit()
        print("\n=======================================================")
        print("POBLAMIENTO EXITOSO:")
        print(f"Empresa Profesional: {luna.razon_social} (Plan Profesional - 3 sucursales)")
        print(f"Empresa Básica: {andina.razon_social} (Plan Básico - 1 sucursal)")
        print(f"Sucursales Luna: {[s.nombre for s in sucs_luna]}")
        print(f"Actores listos para prueba: {list(usuarios_dict.keys())}")
        print("Ventas recientes preparadas para Cambios (CU-16) y Anulación (CU-17)")
        print("Reservas multiescenario preparadas para CU-14")
        print("Bitácora poblada para CU-03")
        print("=======================================================\n")
    finally:
        db.close()


if __name__ == "__main__":
    ejecutar_poblamiento()
