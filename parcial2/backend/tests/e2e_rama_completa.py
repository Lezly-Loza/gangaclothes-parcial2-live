"""Suite E2E para verificar la rama feature/reportes-offline-poblar antes del merge.

Cubre:
- Smoke tests del backend y la PWA (puertos 8001 y 4300)
- Login de los 3 roles principales
- Datos poblados por el seed de 3 meses
- Endpoint /reportes/generativo con top_prendas_por_sucursal (cambio nuevo)
- Endpoint /offline/sincronizar: confirmacion e idempotencia
- Escenario de conflicto por stock: solo una venta sobrevive

Uso:
    cd parcial2/backend
    DATABASE_URL="sqlite:///./ganga_saas_local.db" \\
        .venv-run/Scripts/python -m tests.e2e_rama_completa

Imprime un reporte con PASS/FAIL por bloque. Exit code 0 = todo OK.
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models import Inventario, Variante, Venta


BOLD = "\x1b[1m"; GREEN = "\x1b[32m"; RED = "\x1b[31m"; YELLOW = "\x1b[33m"
DIM = "\x1b[2m"; END = "\x1b[0m"

resultados: list[tuple[str, bool, str]] = []  # (titulo, ok, detalle)


def bloque(titulo: str):
    print(f"\n{BOLD}── {titulo} ──{END}")


def paso(descr: str, ok: bool, detalle: str = "") -> bool:
    marca = f"{GREEN}OK{END}" if ok else f"{RED}FALLO{END}"
    print(f"  [{marca}] {descr}" + (f"  {DIM}({detalle}){END}" if detalle else ""))
    resultados.append((descr, ok, detalle))
    return ok


# ------------------------------------------------------------------ 1. SMOKE
def smoke_servidores_http():
    bloque("1. SMOKE (servidores HTTP vivos)")
    for url, nombre in [
        ("http://127.0.0.1:8001/docs", "Backend Swagger 8001"),
        ("http://127.0.0.1:4300/", "PWA Angular 4300"),
    ]:
        try:
            r = urllib.request.urlopen(url, timeout=3)
            paso(nombre, r.status == 200, f"HTTP {r.status}")
        except (urllib.error.URLError, TimeoutError) as e:
            paso(nombre, False, f"no responde: {e}")


# ------------------------------------------------------------------ 2. LOGIN
def login(c: TestClient, email: str, pwd: str) -> dict[str, Any] | None:
    r = c.post("/api/v1/auth/login", json={"codigo_tenant": "luna", "email": email, "password": pwd})
    return r.json() if r.status_code == 200 else None


def logins():
    bloque("2. AUTENTICACION (3 roles)")
    c = TestClient(app)
    for email, pwd, rol_esperado in [
        ("admin@gangaclothes.com", "Admin123", "admin"),
        ("cajero@gangaclothes.com", "Cajero123", "vendedor"),
        ("sofia@gangaclothes.com", "Cliente#2026", "cliente"),
    ]:
        sesion = login(c, email, pwd)
        ok = sesion is not None and rol_esperado in sesion.get("roles", [])
        paso(f"Login {email}", ok,
             f"roles={sesion.get('roles') if sesion else 'None'}")


# ----------------------------------------------- 3. DATOS POBLADOS (seed 3 meses)
def datos_poblados():
    bloque("3. DATOS POBLADOS (seed 3 meses)")
    db = SessionLocal()
    try:
        total = db.query(Venta).count()
        paso("Hay > 500 ventas totales en DB", total >= 500, f"{total} ventas")
        tres_meses = db.query(Venta).filter(
            Venta.fecha >= datetime.now(timezone.utc) - timedelta(days=95)
        ).count()
        paso("Ventas en ultimos 95 dias > 400", tres_meses >= 400, f"{tres_meses} ventas")
    finally:
        db.close()


# ---------------------------- 4. REPORTE GENERATIVO con top_prendas_por_sucursal
def reporte_generativo():
    bloque("4. REPORTE GENERATIVO (nueva funcionalidad)")
    c = TestClient(app)
    tok = login(c, "admin@gangaclothes.com", "Admin123")
    if not tok:
        paso("No se pudo loguear como admin", False); return
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    desde = (date.today() - timedelta(days=90)).isoformat()
    hasta = date.today().isoformat()
    r = c.post("/api/v1/reportes/generativo", headers=h, json={
        "pregunta": "Top 10 productos por sucursal en los ultimos 3 meses",
        "desde": desde, "hasta": hasta
    })
    paso("Endpoint responde 200", r.status_code == 200, f"HTTP {r.status_code}")
    if r.status_code != 200:
        return
    d = r.json()
    datos = d.get("datos", {})
    paso("Payload contiene 'top_prendas_por_sucursal'",
         "top_prendas_por_sucursal" in datos)
    top = datos.get("top_prendas_por_sucursal", [])
    paso("Al menos 3 sucursales con ranking", len(top) >= 3, f"{len(top)} sucursales")
    con_10 = sum(1 for s in top if len(s.get("top", [])) == 10)
    paso("Al menos 2 sucursales tienen top-10 completo", con_10 >= 2,
         f"{con_10} con top-10")
    # Rankings diferentes por sucursal (requisito de la consigna)
    lideres = {s["sucursal"]: (s["top"][0]["prenda"] if s["top"] else None) for s in top}
    unicos = len(set(lideres.values())) >= 3
    paso("Rankings DISTINTOS por sucursal (lideres unicos)", unicos,
         ", ".join(f"{k}→{v}" for k, v in lideres.items())[:120])


# --------------------------------- 5. OFFLINE: CONFIRMACION + IDEMPOTENCIA
def _pick_variante_con_stock(sucursal_id: int):
    db = SessionLocal()
    try:
        fila = (
            db.query(Inventario, Variante)
            .join(Variante, Variante.id == Inventario.variante_id)
            .filter(Inventario.sucursal_id == sucursal_id,
                    Inventario.stock - Inventario.reservado >= 2,
                    Variante.activo.is_(True))
            .order_by(Inventario.stock.desc()).first()
        )
        if not fila: return None
        inv, var = fila
        return var.id, inv.stock - inv.reservado, float(var.precio)
    finally:
        db.close()


def sincronizar_una_venta():
    bloque("5. OFFLINE SYNC (confirmacion e idempotencia)")
    c = TestClient(app)
    s = login(c, "cajero@gangaclothes.com", "Cajero123")
    if not s: paso("Login cajero", False); return
    h = {"Authorization": f"Bearer {s['access_token']}"}
    pick = _pick_variante_con_stock(4)
    if not pick: paso("Hay variante con stock en sucursal 4", False); return
    vid, stock, precio = pick
    paso("Hay variante con stock en sucursal 4", True, f"vid={vid} stock={stock}")
    uid_op = str(uuid.uuid4())
    body = {"uuid_operacion": uid_op, "tipo": "venta", "sucursal_id": 4,
            "variante_id": vid, "cantidad": 1, "precio_unitario": precio,
            "monto_recibido": precio,
            "fecha_local": datetime.now(timezone.utc).isoformat()}
    r1 = c.post("/api/v1/offline/sincronizar", json=body, headers=h)
    paso("POST /offline/sincronizar confirma (200)", r1.status_code == 200,
         f"HTTP {r1.status_code}")
    if r1.status_code == 200:
        j = r1.json()
        paso("Respuesta trae codigo V-XXX y estado CONFIRMADA",
             j.get("estado") == "CONFIRMADA" and (j.get("codigo") or "").startswith("V-"),
             f"codigo={j.get('codigo')} estado={j.get('estado')}")
    # Idempotencia: reintentar la misma venta no duplica
    r2 = c.post("/api/v1/offline/sincronizar", json=body, headers=h)
    paso("Reintento con mismo uuid devuelve 'repetida: true'",
         r2.status_code == 200 and r2.json().get("repetida") is True,
         f"HTTP {r2.status_code} repetida={r2.json().get('repetida')}")


# --------------------- 6. OFFLINE CONFLICT: 2 ventas sobre el mismo stock
def conflict_entre_cajeros():
    bloque("6. CONFLICTO DE STOCK (2 ventas simultaneas)")
    c = TestClient(app)
    s = login(c, "cajero@gangaclothes.com", "Cajero123")
    if not s: paso("Login cajero", False); return
    h = {"Authorization": f"Bearer {s['access_token']}"}
    pick = _pick_variante_con_stock(4)
    if not pick: paso("Hay variante con stock", False); return
    vid, stock, precio = pick
    if stock < 2:
        paso("Normalizo stock a 1", False, f"stock={stock}"); return
    # dejar exactamente 1 unidad disponible
    while True:
        db = SessionLocal()
        try:
            inv = db.query(Inventario).filter_by(sucursal_id=4, variante_id=vid).first()
            disp = inv.stock - inv.reservado
            if disp <= 1: break
            disp_real = disp
        finally:
            db.close()
        body = {"uuid_operacion": str(uuid.uuid4()), "tipo": "venta", "sucursal_id": 4,
                "variante_id": vid, "cantidad": min(disp_real - 1, 10),
                "precio_unitario": precio, "monto_recibido": precio * min(disp_real - 1, 10),
                "fecha_local": datetime.now(timezone.utc).isoformat()}
        r = c.post("/api/v1/offline/sincronizar", json=body, headers=h)
        if r.status_code != 200:
            paso("Normalizo stock", False, f"HTTP {r.status_code} {r.json()}"); return
    # Ahora stock = 1
    fecha = datetime.now(timezone.utc).isoformat()
    base = {"tipo": "venta", "sucursal_id": 4, "variante_id": vid, "cantidad": 1,
            "precio_unitario": precio, "monto_recibido": precio, "fecha_local": fecha}
    a = {**base, "uuid_operacion": str(uuid.uuid4())}
    b = {**base, "uuid_operacion": str(uuid.uuid4())}
    ra = c.post("/api/v1/offline/sincronizar", json=a, headers=h)
    rb = c.post("/api/v1/offline/sincronizar", json=b, headers=h)
    paso("Cajero A confirma (200)", ra.status_code == 200, f"HTTP {ra.status_code}")
    paso("Cajero B es rechazado (409)", rb.status_code == 409, f"HTTP {rb.status_code}")
    if rb.status_code == 409:
        det = rb.json().get("detail", "")
        paso("Motivo 'Stock insuficiente'",
             "Stock insuficiente" in det, det[:100])
    # Verificar stock final = 0
    db = SessionLocal()
    try:
        inv = db.query(Inventario).filter_by(sucursal_id=4, variante_id=vid).first()
        disp = (inv.stock - inv.reservado) if inv else -1
        paso("Stock queda en 0 (una sola venta aplicada)", disp == 0, f"disponible={disp}")
    finally:
        db.close()


# -------------------------------------------- 7. ENDPOINTS CLAVE (no rotos)
def endpoints_clave():
    bloque("7. ENDPOINTS CLAVE (no rotos por nuestros cambios)")
    c = TestClient(app)
    s_caj = login(c, "cajero@gangaclothes.com", "Cajero123")
    s_adm = login(c, "admin@gangaclothes.com", "Admin123")
    if not s_caj or not s_adm: paso("Login", False); return
    h_caj = {"Authorization": f"Bearer {s_caj['access_token']}"}
    h_adm = {"Authorization": f"Bearer {s_adm['access_token']}"}
    casos = [
        ("GET /sucursales [cajero]",       lambda: c.get("/api/v1/sucursales", headers=h_caj)),
        ("GET /productos [cajero]",        lambda: c.get("/api/v1/productos", headers=h_caj)),
        ("GET /offline/catalogo [cajero]", lambda: c.get("/api/v1/offline/catalogo", params={"sucursal_id": 4}, headers=h_caj)),
        ("GET /reportes/ventas [admin]",   lambda: c.get("/api/v1/reportes/ventas", headers=h_adm)),
        ("GET /reportes/dashboard [admin]",lambda: c.get("/api/v1/reportes/dashboard", headers=h_adm)),
        ("GET /ia/estado [cajero]",        lambda: c.get("/api/v1/ia/estado", headers=h_caj)),
        ("cajero NO ve reportes (403)",    lambda: c.get("/api/v1/reportes/ventas", headers=h_caj)),
    ]
    for nombre, fn in casos:
        r = fn()
        esperado = 403 if "NO ve" in nombre else 200
        paso(nombre, r.status_code == esperado, f"HTTP {r.status_code}")


# -------------------------------------------------- RESUMEN
def resumen() -> int:
    total = len(resultados)
    ok = sum(1 for _, o, _ in resultados if o)
    fail = total - ok
    print(f"\n{BOLD}════════════ RESUMEN ════════════{END}")
    print(f"  Total  : {total}")
    print(f"  {GREEN}OK     : {ok}{END}")
    print(f"  {RED if fail else DIM}FALLO  : {fail}{END}")
    if fail:
        print(f"\n{RED}Detalle de fallos:{END}")
        for t, o, d in resultados:
            if not o:
                print(f"  - {t}" + (f"  — {d}" if d else ""))
        return 1
    print(f"\n{GREEN}{BOLD}TODAS LAS PRUEBAS PASARON — rama lista para merge a main{END}")
    return 0


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    smoke_servidores_http()
    logins()
    datos_poblados()
    reporte_generativo()
    sincronizar_una_venta()
    conflict_entre_cajeros()
    endpoints_clave()
    sys.exit(resumen())


if __name__ == "__main__":
    main()
