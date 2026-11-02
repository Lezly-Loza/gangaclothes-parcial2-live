"""Compara nombres de las secciones 3 y 3b con rutas y código entregado."""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend" / "app"
WEB = (ROOT / "web" / "src" / "app" / "screens.ts").read_text(encoding="utf-8")
MOBILE = (ROOT / "mobile" / "lib" / "main.dart").read_text(encoding="utf-8")

CASES = [
    ("01", "tenants", "crear_empresa_contratante", "crear_tenant", "RegistrarEmpresaForm", None),
    ("02", "auth", "login", "login_tenant", "LoginPage", "LoginScreen"),
    ("03", "usuarios", "listar", "listar", "UsuariosList", None),
    ("04", "sucursales", "crear", "crear", "SucursalesList", None),
    ("05", "suscripciones", "contratar", "contratar_plan", "ContratarPlanForm", None),
    ("06", "suscripciones", "cambiar", "cambiar_plan", "MiSuscripcion", None),
    ("07", "suscripciones", "consultar_estado", "consumo", "MiSuscripcion", None),
    ("08", "productos", "crear", "crear", "ProductosList", None),
    ("09", "catalogos", "guardar_registro", "guardar_registro", "CatalogosPage", None),
    ("10", "proveedores", "crear", "crear", "ProveedoresList", None),
    ("11", "clientes", "buscar", "buscar", "ClientesList", "ClientesScreen"),
    ("12", "inventario", "registrar_movimiento", "registrar_movimiento", "InventarioPage", None),
    ("13", None, None, None, "AvisoInstalacionComponent", None),
    ("14", "reservas", "crear", "crear", "ReservarPrendaPage", "ReservarPrendaScreen"),
    ("15", "ventas", "registrar", "registrar_venta", "PuntoVentaPage", "CarritoScreen"),
    ("16", "cambios", "registrar", "registrar_cambio", "CambioPrendaPage", None),
    ("17", "ventas", "anular", "anular_venta", "AnularOperacionDialog", "AnularOperacionScreen"),
    ("18", "offline", "catalogo", "obtener_catalogo_sucursal", "ModoOfflinePage", "ModoOfflineScreen"),
]

errors = []
for cu, module, route, service, component, screen in CASES:
    if module:
        for filename, name in (("router.py", route), ("service.py", service)):
            path = BACKEND / "modules" / module / filename
            names = {n.name for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n, ast.FunctionDef)}
            if name not in names:
                errors.append(f"CU-{cu}: falta {path}:{name}")
    if not re.search(rf"export class {component}\b", WEB):
        errors.append(f"CU-{cu}: falta componente {component}")
    if screen and not re.search(rf"class {screen}\b", MOBILE):
        errors.append(f"CU-{cu}: falta pantalla {screen}")

entity_methods = [
    ("Sucursal", "verificarYGuardar"), ("Suscripcion", "activarSuscripcion"),
    ("Suscripcion", "validarUsoYGuardar"), ("Inventario", "validarStockYGuardar"),
    ("Reserva", "validarStockYApartar"), ("Venta", "validarCobrarYGuardar"),
    ("CambioPrenda", "verificarPlazoYGuardar"), ("Venta", "validarYRevertirStock"),
]
import sys
sys.path.insert(0, str(ROOT / "backend"))
from app import models  # noqa: E402

for cls, method in entity_methods:
    if not hasattr(getattr(models, cls), method):
        errors.append(f"Falta {cls}.{method}")

for path, name in ((ROOT / "web" / "src" / "app" / "services" / "pwa.service.ts", "guardarRecursos"),
                   (ROOT / "web" / "src" / "app" / "services" / "offline.service.ts", "guardarCatalogoLocal"),
                   (ROOT / "mobile" / "lib" / "producto_local_dao.dart", "guardarCatalogoLocal")):
    if name not in path.read_text(encoding="utf-8"):
        errors.append(f"Falta {path.name}:{name}")

captures = sorted((ROOT / "docs" / "capturas").glob("CU-*.png"))
if len(captures) != 24:
    errors.append(f"Capturas: {len(captures)}/24")
for capture in captures:
    data = capture.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        errors.append(f"PNG inválido: {capture.name}")
        continue
    width = int.from_bytes(data[16:20], "big")
    if width != (390 if capture.stem.endswith("_movil") else 1366):
        errors.append(f"Viewport inválido: {capture.name} ({width})")

if errors:
    raise SystemExit("\n".join(errors))
print(f"Nombres: {len(CASES)}/{len(CASES)} CU; entidades: {len(entity_methods)}/{len(entity_methods)}; capturas: {len(captures)}/24 PNG")
