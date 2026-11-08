import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

from app.core.database import SessionLocal, init_db
from app.models import (
    Categoria,
    DatosComplementarios,
    Producto,
    ProductoProveedor,
    Proveedor,
    Temporada,
    Tenant,
    User,
)


def enlazar():
    init_db()
    db = SessionLocal()
    try:
        luna = db.query(Tenant).filter_by(codigo="luna").first()
        if not luna:
            print("No se encontro tenant luna")
            return

        # 1. Buscar proveedores
        p_textiles = db.query(Proveedor).filter_by(tenant_id=luna.id, nit="1029384756").first()
        if not p_textiles:
            p_textiles = db.query(Proveedor).filter(Proveedor.tenant_id == luna.id, Proveedor.razon_social.like("%Textiles%")).first()

        p_oriente = db.query(Proveedor).filter_by(tenant_id=luna.id, nit="2039485761").first()
        if not p_oriente:
            p_oriente = db.query(Proveedor).filter(Proveedor.tenant_id == luna.id, Proveedor.razon_social.like("%Oriente%")).first()

        print(f"Proveedor Textiles: {p_textiles.id if p_textiles else None} - {p_textiles.razon_social if p_textiles else None}")
        print(f"Proveedor Oriente: {p_oriente.id if p_oriente else None} - {p_oriente.razon_social if p_oriente else None}")

        # 2. Buscar usuarios
        u_textiles = db.query(User).filter_by(tenant_id=luna.id, email="proveedor@gangaclothes.com").first()
        u_oriente = db.query(User).filter_by(tenant_id=luna.id, email="oriente@gangaclothes.com").first()

        print(f"Usuario Textiles: {u_textiles.id if u_textiles else None}")
        print(f"Usuario Oriente: {u_oriente.id if u_oriente else None}")

        # 3. Enlazar en DatosComplementarios
        if u_textiles and p_textiles:
            dc1 = db.query(DatosComplementarios).filter_by(tenant_id=luna.id, tipo="usuario_proveedor", registro_id=u_textiles.id).first()
            if not dc1:
                dc1 = DatosComplementarios(tenant_id=luna.id, tipo="usuario_proveedor", registro_id=u_textiles.id, datos={"proveedor_id": p_textiles.id})
                db.add(dc1)
            else:
                dc1.datos = {"proveedor_id": p_textiles.id}
            print("Enlazado proveedor@gangaclothes.com -> Textiles Andinos SRL")

        if u_oriente and p_oriente:
            dc2 = db.query(DatosComplementarios).filter_by(tenant_id=luna.id, tipo="usuario_proveedor", registro_id=u_oriente.id).first()
            if not dc2:
                dc2 = DatosComplementarios(tenant_id=luna.id, tipo="usuario_proveedor", registro_id=u_oriente.id, datos={"proveedor_id": p_oriente.id})
                db.add(dc2)
            else:
                dc2.datos = {"proveedor_id": p_oriente.id}
            print("Enlazado oriente@gangaclothes.com -> Confecciones Oriente")

        db.flush()

        # 4. Poblar productos ofrecidos para Confecciones Oriente
        cats = db.query(Categoria).filter_by(tenant_id=luna.id).all()
        cat_tops = cats[0] if cats else None
        cat_pantalones = cats[1] if len(cats) > 1 else cat_tops

        temps = db.query(Temporada).filter_by(tenant_id=luna.id).all()
        temp_ids = [t.id for t in temps[:2]] if temps else []

        prenda_blusa = db.query(Producto).filter(Producto.tenant_id == luna.id, Producto.nombre.like("%Blusa%")).first()
        prenda_pantalon = db.query(Producto).filter(Producto.tenant_id == luna.id, Producto.nombre.like("%Jean%")).first()

        if p_oriente:
            ofertas_oriente = [
                ("Confección Blusa Seda Satinada (Lote x10)", "Corte, confección y terminación fina con costura invisible", cat_tops.id if cat_tops else None, prenda_blusa.id if prenda_blusa else None, Decimal("45.00"), 10),
                ("Confección Jean Denim Clásico (Lote x20)", "Denim rígido 12oz, remaches de cobre y costuras reforzadas", cat_pantalones.id if cat_pantalones else None, prenda_pantalon.id if prenda_pantalon else None, Decimal("65.00"), 20),
                ("Servicio de Planchado y Etiquetado", "Control de calidad final, planchado al vapor y colocado de etiquetas", cat_tops.id if cat_tops else None, None, Decimal("8.50"), 50),
            ]
            for nom, desc, cid, pid, prec, cant_min in ofertas_oriente:
                po = db.query(ProductoProveedor).filter_by(tenant_id=luna.id, proveedor_id=p_oriente.id, nombre=nom).first()
                if not po:
                    po = ProductoProveedor(
                        tenant_id=luna.id,
                        proveedor_id=p_oriente.id,
                        nombre=nom,
                        descripcion=desc,
                        categoria_id=cid,
                        prenda_id=pid,
                        precio_referencial=prec,
                        cantidad_minima=cant_min,
                        disponible=True,
                        temporada_ids=temp_ids,
                        fecha_actualizacion=datetime.now(timezone.utc),
                    )
                    db.add(po)
            print("Ofertas creadas para Confecciones Oriente")

        # 5. Poblar productos ofrecidos para Textiles Andinos SRL
        if p_textiles:
            ofertas_textiles = [
                ("Rollo Tela Seda Satinada 50m", "Seda poliéster brillante de primera calidad, ancho 1.50m", cat_tops.id if cat_tops else None, None, Decimal("320.00"), 2),
                ("Fardo Lino Natural 100m", "Fibra de lino puro prelavada especial para blusas y camisas", cat_tops.id if cat_tops else None, None, Decimal("580.00"), 1),
                ("Rollo Denim Indigo 14oz 40m", "Tejido denim pesado color índigo intenso para jeans y chaquetas", cat_pantalones.id if cat_pantalones else None, None, Decimal("450.00"), 2),
            ]
            for nom, desc, cid, pid, prec, cant_min in ofertas_textiles:
                pt = db.query(ProductoProveedor).filter_by(tenant_id=luna.id, proveedor_id=p_textiles.id, nombre=nom).first()
                if not pt:
                    pt = ProductoProveedor(
                        tenant_id=luna.id,
                        proveedor_id=p_textiles.id,
                        nombre=nom,
                        descripcion=desc,
                        categoria_id=cid,
                        prenda_id=pid,
                        precio_referencial=prec,
                        cantidad_minima=cant_min,
                        disponible=True,
                        temporada_ids=temp_ids,
                        fecha_actualizacion=datetime.now(timezone.utc),
                    )
                    db.add(pt)
            print("Ofertas creadas para Textiles Andinos SRL")

        db.commit()
        print("Enlace y ofertas guardadas exitosamente.")
    finally:
        db.close()


if __name__ == "__main__":
    enlazar()
