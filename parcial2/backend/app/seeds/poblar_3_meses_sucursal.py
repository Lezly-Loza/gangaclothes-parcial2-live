"""Poblar 3 meses de ventas historicas distribuidas por sucursal.

Se usa para el CU-24 (Reportes oficiales) y CU-28 (Reportes generativos). Resuelve
la consulta en lenguaje natural "mostrar los 10 productos mas vendidos durante
los ultimos 3 meses agrupados por sucursal".

Idempotente: cada venta se crea con un codigo estable (VEN-3M-<nnn>); si ya
existe, se omite. Se puede ejecutar varias veces sin duplicar datos.

Uso:
    python -m app.seeds.poblar_3_meses_sucursal
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.database import SessionLocal, init_db
from app.models import (
    Cliente,
    DetalleVenta,
    Inventario,
    Pago,
    Sucursal,
    Tenant,
    User,
    Variante,
    Venta,
)


TENANT_CODIGO = "luna"
# Codigos de sucursal oficiales del CU-10 (tres sucursales activas de Luna).
SUCURSALES_OBJETIVO = ["suc-luna-equipetrol", "suc-luna-centro", "suc-luna-sanmiguel"]
DIAS_ATRAS = 95         # cubre mas de 3 meses, para que el reporte con rango
                        # "ultimos 90 dias" siempre encuentre ventas en todos los meses
VENTAS_POR_DIA = (1, 3)  # minimo, maximo (por dia, por sucursal)
SEMILLA = 2026


def ejecutar():
    init_db()
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter_by(codigo=TENANT_CODIGO).first()
        if not tenant:
            raise RuntimeError(f"No existe el tenant '{TENANT_CODIGO}'. Corre primero el seed oficial.")

        sucursales = (
            db.query(Sucursal)
            .filter(Sucursal.tenant_id == tenant.id, Sucursal.codigo.in_(SUCURSALES_OBJETIVO))
            .order_by(Sucursal.codigo)
            .all()
        )
        if not sucursales:
            raise RuntimeError("No encuentro las sucursales oficiales de Luna. Corre poblar_completo_evaluacion primero.")

        variantes = (
            db.query(Variante)
            .filter(Variante.tenant_id == tenant.id, Variante.activo == True)  # noqa: E712
            .order_by(Variante.id)
            .all()
        )
        if not variantes:
            raise RuntimeError("No hay variantes activas para el tenant Luna.")

        cajero = db.query(User).filter_by(tenant_id=tenant.id, email="cajero@gangaclothes.com").first()
        if cajero is None:
            cajero = db.query(User).filter_by(tenant_id=tenant.id, rol="vendedor").first()

        clientes = (
            db.query(Cliente)
            .filter(Cliente.tenant_id == tenant.id)
            .order_by(Cliente.id)
            .all()
        )

        rnd = random.Random(SEMILLA)
        ahora = datetime.now(timezone.utc).replace(microsecond=0)
        formas_pago = ["QR", "EFECTIVO", "TARJETA"]
        origenes = ["PRESENCIAL", "EN_LINEA"]

        # Favoritos por sucursal: cada sucursal tiene prendas que se venden mas.
        # Esto hace que el reporte "top 10 agrupado por sucursal" muestre
        # rankings DISTINTOS por sucursal, no la misma lista repetida.
        rnd_fav = random.Random(SEMILLA + 1)
        favoritos_por_suc = {}
        for suc in sucursales:
            escogidas = rnd_fav.sample(variantes, k=min(8, len(variantes)))
            favoritos_por_suc[suc.id] = escogidas

        contador = 0
        creadas = 0
        omitidas = 0
        for dias_atras in range(DIAS_ATRAS, 0, -1):
            fecha_base = ahora - timedelta(days=dias_atras)
            for suc in sucursales:
                cuantas = rnd.randint(*VENTAS_POR_DIA)
                for _ in range(cuantas):
                    contador += 1
                    codigo = f"VEN-3M-{contador:04d}"
                    if db.query(Venta).filter_by(tenant_id=tenant.id, codigo=codigo).first():
                        omitidas += 1
                        continue

                    # 70% del tiempo elegimos un favorito de la sucursal, 30% otro
                    # cualquiera. Asi el ranking por sucursal queda marcado pero
                    # sigue habiendo variedad en el catalogo de ventas.
                    favoritos = favoritos_por_suc[suc.id]
                    if rnd.random() < 0.7:
                        variante = rnd.choice(favoritos)
                    else:
                        variante = rnd.choice(variantes)

                    cantidad = rnd.choice([1, 1, 1, 2, 2, 3])
                    precio = Decimal(str(variante.precio))
                    subtotal = (precio * cantidad).quantize(Decimal("0.01"))

                    hora = datetime.combine(
                        fecha_base.date(),
                        datetime.min.time(),
                        tzinfo=timezone.utc,
                    ) + timedelta(hours=rnd.randint(10, 19), minutes=rnd.choice([5, 17, 29, 41, 53]))

                    cliente = rnd.choice(clientes) if clientes else None
                    metodo = rnd.choices(formas_pago, weights=[5, 3, 2])[0]
                    origen = rnd.choices(origenes, weights=[7, 3])[0]

                    venta = Venta(
                        tenant_id=tenant.id,
                        codigo=codigo,
                        sucursal_id=suc.id,
                        usuario_id=cajero.id if cajero else None,
                        cliente_id=cliente.id if cliente else None,
                        origen=origen,
                        fecha=hora,
                        forma_pago=metodo,
                        total=subtotal,
                        estado="CONFIRMADA",
                    )
                    db.add(venta)
                    db.flush()

                    db.add(DetalleVenta(
                        tenant_id=tenant.id,
                        venta_id=venta.id,
                        variante_id=variante.id,
                        cantidad=cantidad,
                        precio_unitario=precio,
                        subtotal=subtotal,
                    ))
                    db.add(Pago(
                        tenant_id=tenant.id,
                        venta_id=venta.id,
                        metodo=metodo,
                        monto=subtotal,
                        referencia_pasarela=f"REF-{codigo}",
                        estado="APROBADO",
                    ))
                    creadas += 1

        db.commit()
        print(f"Ventas creadas: {creadas}")
        print(f"Ventas omitidas (ya existian): {omitidas}")
        print(f"Rango: {DIAS_ATRAS} dias atras hasta hoy, por sucursal: {[s.nombre for s in sucursales]}")
    finally:
        db.close()


if __name__ == "__main__":
    ejecutar()
