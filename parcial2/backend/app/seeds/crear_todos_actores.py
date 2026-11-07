"""Crea y asegura todos los actores oficiales con sus credenciales y roles exactos
para Boutique Luna (luna / gangaclothes):
- admin@gangaclothes.com / Admin123 (administrador)
- encargado@gangaclothes.com / Encargado123 (encargado)
- cajero@gangaclothes.com / Cajero123 (cajero)
- sofia@gangaclothes.com / Cliente#2026 (cliente con historial de compras y reservas)
- diego@gangaclothes.com / Cliente#2026 (cliente)
- valeria@gangaclothes.com / Cliente#2026 (cliente)
- proveedor@gangaclothes.com / Proveedor123 (proveedor Textiles Andinos SRL)
- oriente@gangaclothes.com / Proveedor123 (proveedor Confecciones Oriente)
- root@plataforma.bo / SuperSegura123 (superadministrador)
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models import (
    Cliente,
    DetalleReserva,
    DetalleVenta,
    Inventario,
    MovimientoInventario,
    Pago,
    PerfilUsuario,
    Proveedor,
    Reserva,
    Rol,
    Sucursal,
    SuperAdmin,
    Tenant,
    User,
    UsuarioRol,
    Variante,
    Venta,
)
from app.modules.seguridad.service import asegurar_roles, asignar_roles


def asegurar_actores():
    init_db()
    db = SessionLocal()
    try:
        # 1. Asegurar SuperAdmin root y admin alternativo
        for sa_email, sa_pwd, sa_nom in [
            ("root@plataforma.bo", "SuperSegura123", "Root Plataforma"),
            ("admin@gangaclothes.com", "Admin123", "Admin GangaClothes Global"),
        ]:
            sa = db.query(SuperAdmin).filter_by(email=sa_email).first()
            if not sa:
                db.add(SuperAdmin(email=sa_email, password_hash=hash_password(sa_pwd), nombre=sa_nom, activo=True))
            else:
                sa.password_hash = hash_password(sa_pwd)
                sa.activo = True
        db.flush()

        # 2. Asegurar Tenant Luna (inquilino principal)
        tenant = db.query(Tenant).filter_by(codigo="luna").first()
        if not tenant:
            tenant = Tenant(
                codigo="luna",
                razon_social="Boutique Luna SRL (GangaClothes)",
                nit="1023456789",
                correo="contacto@gangaclothes.com",
                telefono="+591 70000001",
                estado="activo",
                activo=True,
            )
            db.add(tenant)
            db.flush()

        asegurar_roles(db, tenant.id)
        sucursales = db.query(Sucursal).filter_by(tenant_id=tenant.id).all()
        sucursal = sucursales[0] if sucursales else None

        # 3. Definición de los actores
        actores = [
            ("admin@gangaclothes.com", "Admin123", "Admin GangaClothes", "administrador", ["administrador"]),
            ("encargado@gangaclothes.com", "Encargado123", "Elena Encargada", "encargado", ["encargado"]),
            ("cajero@gangaclothes.com", "Cajero123", "Carlos Cajero", "vendedor", ["vendedor"]),
            ("sofia@gangaclothes.com", "Cliente#2026", "Sofia Rojas", "cliente", ["cliente"]),
            ("diego@gangaclothes.com", "Cliente#2026", "Diego Mendoza", "cliente", ["cliente"]),
            ("valeria@gangaclothes.com", "Cliente#2026", "Valeria Suarez", "cliente", ["cliente"]),
            ("proveedor@gangaclothes.com", "Proveedor123", "Textiles Andinos SRL", "proveedor", ["proveedor"]),
            ("oriente@gangaclothes.com", "Proveedor123", "Confecciones Oriente", "proveedor", ["proveedor"]),
        ]

        usuarios_creados = {}
        for email, pwd, nombre, rol_base, roles_asignar in actores:
            u = db.query(User).filter_by(tenant_id=tenant.id, email=email).first()
            if not u:
                u = User(
                    tenant_id=tenant.id,
                    email=email,
                    password_hash=hash_password(pwd),
                    nombre=nombre,
                    rol=rol_base,
                    activo=True,
                    estado="activo",
                )
                db.add(u)
                db.flush()
            else:
                u.password_hash = hash_password(pwd)
                u.nombre = nombre
                u.rol = rol_base
                u.activo = True
                u.estado = "activo"
                db.flush()

            asignar_roles(db, u, roles_asignar)
            usuarios_creados[email] = u

            # Perfil
            perfil = db.query(PerfilUsuario).filter_by(tenant_id=tenant.id, usuario_id=u.id).first()
            if not perfil:
                db.add(PerfilUsuario(tenant_id=tenant.id, usuario_id=u.id, telefono="70012345"))

        db.flush()

        # 4. Asegurar Clientes vinculados
        clientes_def = [
            ("sofia@gangaclothes.com", "Sofia Rojas", "7654321 SC", "70099881"),
            ("diego@gangaclothes.com", "Diego Mendoza", "8123456 SC", "70099882"),
            ("valeria@gangaclothes.com", "Valeria Suarez", "6987452 CB", "70099883"),
        ]
        clientes_db = {}
        for email, nombre, doc, tel in clientes_def:
            u = usuarios_creados[email]
            cli = db.query(Cliente).filter_by(tenant_id=tenant.id, correo=email).first()
            if not cli:
                cli = db.query(Cliente).filter_by(tenant_id=tenant.id, documento=doc).first()
            if not cli:
                cli = Cliente(tenant_id=tenant.id, nombre=nombre, documento=doc, correo=email, telefono=tel, user_id=u.id)
                db.add(cli)
                db.flush()
            else:
                cli.user_id = u.id
                cli.nombre = nombre
                cli.documento = doc
                cli.correo = email
                cli.telefono = tel
                db.flush()
            clientes_db[email] = cli

        # 5. Asegurar Proveedores vinculados
        provs_def = [
            ("proveedor@gangaclothes.com", "Textiles Andinos SRL", "1029384756", "Ramiro Quispe", "70011221"),
            ("oriente@gangaclothes.com", "Confecciones Oriente", "5647382910", "Carla Justiniano", "70011222"),
        ]
        for email, razon, nit, contacto, tel in provs_def:
            p = db.query(Proveedor).filter_by(tenant_id=tenant.id, nit=nit).first()
            if not p:
                p = Proveedor(
                    tenant_id=tenant.id,
                    razon_social=razon,
                    nit=nit,
                    contacto=contacto,
                    correo=email,
                    telefono=tel,
                    activo=True,
                )
                db.add(p)
            else:
                p.razon_social = razon
                p.contacto = contacto
                p.correo = email
                p.telefono = tel
                p.activo = True
        db.flush()

        # 6. Historial de compras y reservas de Sofia Rojas (sofia@gangaclothes.com)
        sofia_cli = clientes_db["sofia@gangaclothes.com"]
        cajero_u = usuarios_creados["cajero@gangaclothes.com"]
        variantes = db.query(Variante).filter_by(tenant_id=tenant.id).all()

        if sucursal and variantes:
            # Compras de Sofia
            compras_sofia = db.query(Venta).filter_by(tenant_id=tenant.id, cliente_id=sofia_cli.id).count()
            if compras_sofia < 4:
                now = datetime.now(timezone.utc)
                for k in range(1, 5):
                    fecha_v = now - timedelta(days=k * 4)
                    v_item = variantes[(k * 2) % len(variantes)]
                    total = v_item.precio
                    cod_v = f"VEN-SOFIA-{k:03d}"
                    venta = Venta(
                        tenant_id=tenant.id,
                        codigo=cod_v,
                        sucursal_id=sucursal.id,
                        usuario_id=cajero_u.id,
                        cliente_id=sofia_cli.id,
                        forma_pago="QR" if k % 2 == 0 else "TARJETA",
                        total=total,
                        estado="CONFIRMADA",
                        fecha=fecha_v,
                    )
                    db.add(venta)
                    db.flush()
                    db.add(DetalleVenta(
                        tenant_id=tenant.id,
                        venta_id=venta.id,
                        variante_id=v_item.id,
                        cantidad=1,
                        precio_unitario=total,
                        subtotal=total,
                    ))
                    db.add(Pago(
                        tenant_id=tenant.id,
                        venta_id=venta.id,
                        metodo=venta.forma_pago,
                        monto=total,
                        estado="APROBADO",
                    ))
                    db.add(MovimientoInventario(
                        tenant_id=tenant.id,
                        sucursal_id=sucursal.id,
                        variante_id=v_item.id,
                        tipo="VENTA",
                        cantidad=1,
                        motivo=f"Compra cliente Sofia {cod_v}",
                        fecha=fecha_v,
                    ))

            # Reservas de Sofia
            reservas_sofia = db.query(Reserva).filter_by(tenant_id=tenant.id, cliente_id=sofia_cli.id).count()
            if reservas_sofia < 2:
                now = datetime.now(timezone.utc)
                v_res = variantes[1]
                res = Reserva(
                    tenant_id=tenant.id,
                    codigo="RES-SOFIA-01",
                    sucursal_id=sucursal.id,
                    cliente_id=sofia_cli.id,
                    origen="EN_LINEA",
                    fecha_limite=now + timedelta(hours=48),
                    estado="PENDIENTE",
                )
                db.add(res)
                db.flush()
                db.add(DetalleReserva(tenant_id=tenant.id, reserva_id=res.id, variante_id=v_res.id, cantidad=1))

        db.commit()
        print("Todos los 8 actores oficiales fueron creados y asegurados exitosamente en la base de datos.")
    finally:
        db.close()


if __name__ == "__main__":
    asegurar_actores()

