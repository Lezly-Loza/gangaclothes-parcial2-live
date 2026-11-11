import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';

const BASE_URL = process.env.BASE_URL || 'https://gangaclothes-parcial2-live.vercel.app';
const ARTIFACT_DIR = process.env.ARTIFACT_DIR || 'C:/Users/user/.gemini/antigravity/brain/1b23d13e-deb7-4aa5-8117-51adb4936368';

console.log('Iniciando prueba Playwright contra:', BASE_URL);

const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
});

const context = await browser.newContext({
  viewport: { width: 1366, height: 768 },
});

const page = await context.newPage();

async function capturar(nombre) {
  const ruta = path.join(ARTIFACT_DIR, nombre);
  await page.screenshot({ path: ruta, fullPage: true });
  console.log(`[CAPTURA GUARDADA] ${nombre}`);
}

try {
  // 1. Pantalla de Login
  console.log('1. Navegando al Login...');
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 30000 });
  await capturar('web_01_login.png');

  // 2. Login como Superadmin
  console.log('2. Iniciando sesión como Superadmin...');
  const btnSuper = page.getByRole('button', { name: 'Super', exact: true });
  if (await btnSuper.count() > 0) {
    await btnSuper.click();
    await page.getByRole('button', { name: /Iniciar sesion/i }).click();
  } else {
    await page.locator('input[formcontrolname="email"]').fill('root@plataforma.bo');
    await page.locator('input[formcontrolname="password"]').fill('SuperSegura123');
    await page.getByRole('button', { name: /Iniciar sesion/i }).click();
  }
  await page.waitForURL(/\/admin/, { timeout: 30000 });
  await page.waitForTimeout(2000);
  await capturar('web_02_superadmin_empresas.png');

  // 3. Superadmin Planes
  console.log('3. Visitando Planes globales...');
  await page.goto(`${BASE_URL}/admin/planes`, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(1500);
  await capturar('web_03_superadmin_planes.png');

  // 4. Cerrar sesión de Superadmin
  console.log('4. Cerrando sesión de Superadmin...');
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 30000 });

  // 5. Iniciar sesión como Admin Luna
  console.log('5. Iniciando sesión como Admin Luna...');
  const btnAdmin = page.getByRole('button', { name: 'Admin Luna', exact: true });
  if (await btnAdmin.count() > 0) {
    await btnAdmin.click();
    await page.getByRole('button', { name: /Iniciar sesion/i }).click();
  } else {
    await page.locator('input[formcontrolname="codigo_tenant"]').fill('luna');
    await page.locator('input[formcontrolname="email"]').fill('admin@gangaclothes.com');
    await page.locator('input[formcontrolname="password"]').fill('Admin123');
    await page.getByRole('button', { name: /Iniciar sesion/i }).click();
  }
  await page.waitForURL(/\/admin/, { timeout: 30000 });
  await page.waitForTimeout(2000);
  await capturar('web_04_admin_inicio.png');

  // 6. Reportes Oficiales y Dashboard
  console.log('6. Visitando Reportes Oficiales...');
  await page.goto(`${BASE_URL}/admin/reportes`, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);
  await capturar('web_05_admin_reportes.png');

  // 7. Catálogo de Cliente
  console.log('7. Visitando Catálogo de Tienda...');
  await page.goto(`${BASE_URL}/tienda/catalogo`, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2500);
  await capturar('web_06_tienda_catalogo.png');

  console.log('\n¡Todas las pruebas de Playwright de la web se completaron con éxito!');
} catch (err) {
  console.error('Error durante ejecución de Playwright:', err);
} finally {
  await browser.close();
}

