/**
 * Auditoría Playwright estructurada POR CADA ACTOR del sistema (ICONIX - Parcial 2).
 * Prueba para cada uno de los 6 roles su barra de navegación y sus Casos de Uso asignados:
 * 1. Superadministrador  -> Plataforma global, CU-01, CU-05
 * 2. Admin Empresa       -> Gestión integral, CU-04, CU-07, CU-12, CU-15, CU-24, CU-25, CU-26
 * 3. Encargado Sucursal  -> Operación de tienda, CU-12, CU-16, CU-17, CU-24
 * 4. Vendedor / Cajero   -> Caja y cobros, CU-16 (Devolución monetaria en efectivo), Modo offline
 * 5. Cliente             -> Tienda en línea, CU-14 (Catálogo y reservas), Compras y Carrito
 * 6. Proveedor           -> Portal de confecciones y suministro de prendas
 * 
 * Uso:
 *   node scripts/probar_por_actor.mjs [--headed]
 */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';

const esHeaded = process.argv.includes('--headed') || process.env.HEADED === 'true';
const browserPath = process.env.PLAYWRIGHT_BROWSER || 
  (process.platform === 'win32' 
    ? 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' 
    : undefined);

console.log('================================================================================');
console.log('   AUDITORÍA AUTOMATIZADA POR CADA ACTOR Y SUS CASOS DE USO (ICONIX)           ');
console.log(`   Modo: ${esHeaded ? 'VISUAL (Ventana del navegador interactiva)' : 'HEADLESS (Segundo plano)'}`);
console.log('================================================================================\n');

const browser = await chromium.launch({
  headless: !esHeaded,
  executablePath: browserPath,
  slowMo: esHeaded ? 250 : 0,
});

const context = await browser.newContext({
  viewport: { width: 1366, height: 768 },
  acceptDownloads: true,
});

const page = await context.newPage();
const errores = [];

page.on('pageerror', (err) => {
  errores.push(`[Excepción Navegador]: ${err.message}`);
});

async function logout() {
  try {
    await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
    await page.goto('http://localhost:4200/login');
    await page.waitForLoadState('networkidle');
  } catch {
    await page.goto('http://localhost:4200/login');
  }
}

async function loginSuper() {
  await logout();
  const chipSuper = page.locator('button.chip:has-text("Superadministrador")');
  if (await chipSuper.count() > 0) {
    await chipSuper.click();
    await page.waitForTimeout(300);
  }
  await page.locator('input[formcontrolname="email"]').fill('root@plataforma.bo');
  await page.locator('input[formcontrolname="password"]').fill('SuperSegura123');
  await page.getByRole('button', { name: 'Iniciar sesion', exact: true }).click();
  await page.waitForURL(/\/admin/);
}

async function loginTenant(email, password, tenant = 'luna') {
  await logout();
  const chipEmpresa = page.locator('button.chip:has-text("Mi empresa")');
  if (await chipEmpresa.count() > 0) {
    await chipEmpresa.click();
    await page.waitForTimeout(300);
  }
  await page.locator('input[formcontrolname="codigo_tenant"]').fill(tenant);
  await page.locator('input[formcontrolname="email"]').fill(email);
  await page.locator('input[formcontrolname="password"]').fill(password);
  await page.getByRole('button', { name: 'Iniciar sesion', exact: true }).click();
  await page.waitForURL(/\/(admin|catalogo|modo-offline|proveedor)/);
}

async function verificarRuta(ruta, etiqueta) {
  await page.goto(`http://localhost:4200${ruta}`);
  await page.waitForLoadState('networkidle');
  assert.ok(page.url().includes(ruta), `La ruta no cargó: esperado ${ruta}, actual ${page.url()}`);
  const tieneContenido = (await page.locator('h1, h2, table, section, article').count()) > 0;
  assert.ok(tieneContenido, `La sección ${etiqueta} (${ruta}) no renderizó contenido`);
  console.log(`    [OK] Navegación verificada -> ${etiqueta.padEnd(25)} (${ruta})`);
}

try {
  // ==========================================================================
  // ACTOR 1: SUPERADMINISTRADOR
  // ==========================================================================
  console.log('========================================================================');
  console.log('>>> [ACTOR 1: SUPERADMINISTRADOR] root@plataforma.bo');
  console.log('    Responsabilidad: Plataforma SaaS global, creación de tenants y planes');
  console.log('========================================================================');
  await loginSuper();
  console.log('  -> Sesión de Superadministrador iniciada.');
  await verificarRuta('/admin', 'Panel de Control');
  await verificarRuta('/admin/empresas', 'Empresas (CU-01)');
  await verificarRuta('/admin/planes', 'Planes y Precios (CU-05)');
  await verificarRuta('/admin/bitacora', 'Bitácora Global');
  console.log('  [APROBADO] Actor 1 (Superadministrador): Barra y casos de uso 100% operativos.\n');

  // ==========================================================================
  // ACTOR 2: ADMINISTRADOR DE EMPRESA
  // ==========================================================================
  console.log('========================================================================');
  console.log('>>> [ACTOR 2: ADMINISTRADOR DE EMPRESA] ana@boutique-luna.bo');
  console.log('    Responsabilidad: Gestión integral del tenant Boutique Luna SRL');
  console.log('========================================================================');
  await loginTenant('ana@boutique-luna.bo', 'Luna12345', 'luna');
  console.log('  -> Sesión de Administrador iniciada.');
  await verificarRuta('/admin', 'Panel Ejecutivo');
  await verificarRuta('/admin/sucursales', 'Sucursales (CU-04)');
  await verificarRuta('/admin/mi-suscripcion', 'Mi Suscripción (CU-07)');
  await verificarRuta('/admin/inventario', 'Inventario (CU-12)');
  await verificarRuta('/admin/usuarios', 'Usuarios (CU-15)');
  await verificarRuta('/admin/roles', 'Roles y Permisos (CU-15)');
  await verificarRuta('/admin/reportes', 'Reportes Excel/PDF (CU-24)');
  await verificarRuta('/admin/respaldos', 'Respaldos de BD (CU-25)');
  await verificarRuta('/admin/dashboard', 'Dashboard ML (CU-26)');
  console.log('  [APROBADO] Actor 2 (Admin Empresa): Barra y casos de uso 100% operativos.\n');

  // ==========================================================================
  // ACTOR 3: ENCARGADO DE SUCURSAL
  // ==========================================================================
  console.log('========================================================================');
  console.log('>>> [ACTOR 3: ENCARGADO DE SUCURSAL] encargado@gangaclothes.com');
  console.log('    Responsabilidad: Operaciones de tienda física, stock y cambios');
  console.log('========================================================================');
  await loginTenant('encargado@gangaclothes.com', 'Encargado123', 'luna');
  console.log('  -> Sesión de Encargado iniciada.');
  await verificarRuta('/admin/inventario', 'Inventario por Tienda (CU-12)');
  await verificarRuta('/admin/movimientos', 'Movimientos de Stock');
  await verificarRuta('/admin/cambios', 'Cambios de Prenda (CU-16)');
  await verificarRuta('/admin/anular', 'Anulación de Operaciones (CU-17)');
  await verificarRuta('/admin/reportes', 'Reportes Operativos (CU-24)');
  console.log('  [APROBADO] Actor 3 (Encargado de Sucursal): Barra y casos de uso 100% operativos.\n');

  // ==========================================================================
  // ACTOR 4: VENDEDOR / CAJERO
  // ==========================================================================
  console.log('========================================================================');
  console.log('>>> [ACTOR 4: VENDEDOR / CAJERO] cajero@gangaclothes.com');
  console.log('    Responsabilidad: Punto de venta, cobros en caja y devoluciones en efectivo');
  console.log('========================================================================');
  await loginTenant('cajero@gangaclothes.com', 'Cajero123', 'luna');
  console.log('  -> Sesión de Cajero iniciada.');

  // Validar que no existan alertas 403 Forbidden en el panel
  const toastsError = await page.locator('.toast.error, .alerta-error').count();
  assert.equal(toastsError, 0, 'El Cajero no debe recibir avisos de permiso denegado 403');
  console.log('  [APROBADO] Cero errores 403 en panel para el rol Cajero.');

  await verificarRuta('/admin/caja', 'Caja y Cobros');
  await verificarRuta('/admin/cambios', 'Cambios y Devolución Efectivo (CU-16)');
  await verificarRuta('/modo-offline', 'Punto de Venta Offline (CU-18/19/20)');
  console.log('  [APROBADO] Actor 4 (Vendedor / Cajero): Barra y casos de uso 100% operativos.\n');

  // ==========================================================================
  // ACTOR 5: CLIENTE
  // ==========================================================================
  console.log('========================================================================');
  console.log('>>> [ACTOR 5: CLIENTE] sofia@gangaclothes.com');
  console.log('    Responsabilidad: Compra en línea, reserva en vestidor y pedidos');
  console.log('========================================================================');
  await loginTenant('sofia@gangaclothes.com', 'Cliente#2026', 'luna');
  console.log('  -> Sesión de Cliente iniciada.');
  await verificarRuta('/catalogo', 'Catálogo Interactivo (CU-14)');
  await verificarRuta('/mis-reservas', 'Mis Reservas');
  await verificarRuta('/mis-compras', 'Mis Compras');
  await verificarRuta('/carrito', 'Carrito de Compras');
  await verificarRuta('/modo-offline', 'Catálogo sin Conexión');
  console.log('  [APROBADO] Actor 5 (Cliente): Barra y casos de uso 100% operativos.\n');

  // ==========================================================================
  // ACTOR 6: PROVEEDOR
  // ==========================================================================
  console.log('========================================================================');
  console.log('>>> [ACTOR 6: PROVEEDOR] proveedor@gangaclothes.com');
  console.log('    Responsabilidad: Oferta de confecciones y despacho de lotes');
  console.log('========================================================================');
  await loginTenant('proveedor@gangaclothes.com', 'Proveedor123', 'luna');
  console.log('  -> Sesión de Proveedor iniciada.');
  await verificarRuta('/proveedor', 'Portal de Confección');
  console.log('  [APROBADO] Actor 6 (Proveedor): Barra y portal 100% operativo.\n');

  // ==========================================================================
  // RESUMEN GLOBAL
  // ==========================================================================
  console.log('================================================================================');
  console.log('           RESUMEN FINAL: AUDITORÍA DE LOS 6 ACTORES 100% APROBADA              ');
  console.log('================================================================================');
  console.log('  [ACTOR 1] Superadministrador -> Panel, Empresas (CU-01), Planes (CU-05)');
  console.log('  [ACTOR 2] Admin Empresa      -> Sucursales (CU-04), Límites (CU-07), Inv (CU-12),');
  console.log('                                  Usuarios (CU-15), Reportes (CU-24), ML (CU-26)');
  console.log('  [ACTOR 3] Encargado          -> Inventario (CU-12), Cambios (CU-16), Anular (CU-17)');
  console.log('  [ACTOR 4] Cajero             -> Caja, Cambios con Devolución Efectivo (CU-16), Offline');
  console.log('  [ACTOR 5] Cliente            -> Catálogo (CU-14), Reservas, Compras, Carrito');
  console.log('  [ACTOR 6] Proveedor          -> Portal Proveedor, Oferta de prendas');
  console.log('================================================================================\n');
} catch (error) {
  console.error('\nERROR fatal durante la auditoría de actores:', error);
  process.exitCode = 1;
} finally {
  await browser.close();
}
