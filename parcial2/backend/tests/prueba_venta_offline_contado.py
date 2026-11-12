"""Prueba automatica del punto 4: venta de contado offline y conflicto por stock.

Simula lo que haria la pantalla de caja si tuviera el flujo offline integrado:
- 2 cajeros, dos dispositivos distintos
- El servidor pierde conectividad para los clientes
- Ambos cobran al mismo tiempo la MISMA ultima unidad del mismo SKU
- Reconectan: el que sincroniza primero gana, el otro recibe "pago rechazado"

Uso:
    python -m tests.prueba_venta_offline_contado
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models import Inventario, Variante


BOLD = "\x1b[1m"; GREEN = "\x1b[32m"; RED = "\x1b[31m"; YELLOW = "\x1b[33m"; DIM = "\x1b[2m"; END = "\x1b[0m"


def paso(n: int, texto: str) -> None:
    print(f"\n{BOLD}[{n}] {texto}{END}")


def _login(c: TestClient, email: str, pwd: str) -> dict[str, Any]:
    r = c.post("/api/v1/auth/login", json={"codigo_tenant": "luna", "email": email, "password": pwd})
    r.raise_for_status()
    return r.json()


def _pick_variante_con_stock(sucursal_id: int) -> tuple[int, int, float, str]:
    db = SessionLocal()
    try:
        fila = (
            db.query(Inventario, Variante)
            .join(Variante, Variante.id == Inventario.variante_id)
            .filter(Inventario.sucursal_id == sucursal_id, Inventario.stock - Inventario.reservado >= 1,
                    Variante.activo.is_(True))
            .order_by(Inventario.stock.desc())
            .first()
        )
        if not fila:
            raise RuntimeError(f"No hay variantes con stock en sucursal {sucursal_id}")
        inv, var = fila
        return var.id, inv.stock - inv.reservado, float(var.precio), var.sku
    finally:
        db.close()


def _stock(sucursal_id: int, variante_id: int) -> int:
    db = SessionLocal()
    try:
        inv = db.query(Inventario).filter_by(sucursal_id=sucursal_id, variante_id=variante_id).first()
        return (inv.stock - inv.reservado) if inv else 0
    finally:
        db.close()


def ejecutar() -> int:
    c = TestClient(app)
    SUCURSAL_ID = 4  # Luna Equipetrol

    paso(1, "Login de dos cajeros (como si estuvieran en dos computadoras de caja)")
    sesion_a = _login(c, "cajero@gangaclothes.com", "Cajero123")
    sesion_b = _login(c, "cajero@gangaclothes.com", "Cajero123")
    tok_a = sesion_a["access_token"]; tok_b = sesion_b["access_token"]
    print(f"  cajero A -> roles={sesion_a['roles']} ventas:crear={'ventas:crear' in sesion_a['permisos']}")
    print(f"  cajero B -> roles={sesion_b['roles']} ventas:crear={'ventas:crear' in sesion_b['permisos']}")

    paso(2, f"Pick de la variante que vamos a disputar (sucursal {SUCURSAL_ID})")
    variante_id, stock_antes, precio, sku = _pick_variante_con_stock(SUCURSAL_ID)
    print(f"  variante_id={variante_id} sku={sku} precio=Bs {precio:.2f} stock_disponible={stock_antes}")

    # Agotamos el stock hasta 1 unidad para que la carrera sea exacta.
    if stock_antes > 1:
        paso(3, f"Normalizo stock a 1 unidad (de {stock_antes}) para forzar la colision real")
        for _ in range(stock_antes - 1):
            r = c.post("/api/v1/offline/sincronizar",
                       headers={"Authorization": f"Bearer {tok_a}"},
                       json={"uuid_operacion": str(uuid.uuid4()), "tipo": "venta", "sucursal_id": SUCURSAL_ID,
                             "variante_id": variante_id, "cantidad": 1, "precio_unitario": precio,
                             "monto_recibido": precio, "fecha_local": datetime.now(timezone.utc).isoformat()})
            if r.status_code != 200:
                print(f"  {RED}no pude normalizar: {r.status_code} {r.json()}{END}"); return 1
        print(f"  stock actual = {_stock(SUCURSAL_ID, variante_id)}")

    paso(4, "ESCENARIO: ambos cajeros pierden Internet. Cada uno guarda su venta localmente.")
    # Esto es lo que pasaria en IndexedDB/sqflite de cada dispositivo:
    fecha = datetime.now(timezone.utc).isoformat()
    venta_local_a = {"uuid_operacion": str(uuid.uuid4()), "tipo": "venta", "sucursal_id": SUCURSAL_ID,
                     "variante_id": variante_id, "cantidad": 1, "precio_unitario": precio,
                     "monto_recibido": precio, "fecha_local": fecha}
    venta_local_b = {**venta_local_a, "uuid_operacion": str(uuid.uuid4())}
    print(f"  {DIM}Cajero A IndexedDB.add(operaciones, {{uuid={venta_local_a['uuid_operacion'][:8]}, estado=pendiente}}){END}")
    print(f"  {DIM}Cajero B IndexedDB.add(operaciones, {{uuid={venta_local_b['uuid_operacion'][:8]}, estado=pendiente}}){END}")

    paso(5, "Ambos reconectan. El OfflineService escucha 'online' y dispara POST /offline/sincronizar")
    r_a = c.post("/api/v1/offline/sincronizar", headers={"Authorization": f"Bearer {tok_a}"}, json=venta_local_a)
    r_b = c.post("/api/v1/offline/sincronizar", headers={"Authorization": f"Bearer {tok_b}"}, json=venta_local_b)

    resultado_a, resultado_b = r_a.json(), r_b.json()
    print(f"  Cajero A -> HTTP {r_a.status_code}")
    print(f"           -> {GREEN if r_a.status_code == 200 else RED}{resultado_a}{END}")
    print(f"  Cajero B -> HTTP {r_b.status_code}")
    print(f"           -> {GREEN if r_b.status_code == 200 else RED}{resultado_b}{END}")

    paso(6, "Lo que el cliente hace en cada caso con el estado de la operacion local:")
    for etiqueta, resp, status in [("A", resultado_a, r_a.status_code), ("B", resultado_b, r_b.status_code)]:
        if status == 200:
            print(f"  Cajero {etiqueta}: IndexedDB.put(uuid, estado='confirmada', codigo={resp.get('codigo')!r})")
            print(f"           Toast verde: 'Venta confirmada: {resp.get('codigo')}'")
        else:
            motivo = resp.get('detail') if isinstance(resp.get('detail'), str) else resp
            print(f"  Cajero {etiqueta}: IndexedDB.put(uuid, estado='conflicto', error={motivo!r})")
            print(f"           Banner rojo en pantalla: 'Pago rechazado: {motivo}'")

    paso(7, "Stock final (el servidor descuenta UNA sola vez)")
    print(f"  stock disponible ahora = {_stock(SUCURSAL_ID, variante_id)}")

    paso(8, "Idempotencia: el cajero A reintenta su misma venta (p. ej. perdio la respuesta)")
    r_repeat = c.post("/api/v1/offline/sincronizar", headers={"Authorization": f"Bearer {tok_a}"}, json=venta_local_a)
    print(f"  HTTP {r_repeat.status_code} -> {r_repeat.json()}")
    if r_repeat.json().get("repetida"):
        print(f"  {GREEN}OK: el servidor devuelve la MISMA confirmacion sin duplicar la venta.{END}")

    paso(9, "VEREDICTO")
    ok = r_a.status_code == 200 and r_b.status_code == 409 and r_repeat.json().get("repetida") is True
    if ok:
        print(f"  {GREEN}{BOLD}PRUEBA SUPERADA{END}: una sola venta sobrevive, el otro cajero ve 'pago rechazado'.")
        return 0
    print(f"  {RED}{BOLD}FALLO{END}: revisa las respuestas de arriba.")
    return 1


if __name__ == "__main__":
    sys.exit(ejecutar())
