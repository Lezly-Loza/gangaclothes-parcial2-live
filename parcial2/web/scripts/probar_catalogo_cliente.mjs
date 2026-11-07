// Sólo lectura: comprueba el catálogo de la cuenta de demostración existente.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
const browser = await chromium.launch({headless: true,
  executablePath: process.env.PLAYWRIGHT_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const page = await browser.newPage({viewport: {width: 1366, height: 768}});
try {
  await page.goto('http://localhost:4200/login');
  await page.getByRole('button', {name: 'Cliente Luna', exact: true}).click();
  await page.getByRole('button', {name: 'Iniciar sesion', exact: true}).click();
  await page.getByRole('heading', {name: 'Catálogo sin conexión'}).waitFor();
  await page.getByRole('link', {name: 'Catalogo', exact: true}).click();
  await page.getByRole('heading', {name: 'Catalogo', exact: true}).waitFor();
  await page.locator('main .tarjeta').first().waitFor();
  const opciones = page.locator('aside.filtros select option');
  await opciones.nth(2).waitFor({state: 'attached'});
  const selector = page.locator('aside.filtros select');
  await selector.selectOption({index: 1});
  await page.getByText('con stock en Luna Centro', {exact: false}).waitFor();
  assert.ok(await page.locator('main .tarjeta').count() > 0);
  await selector.selectOption({index: 2});
  await page.getByText('con stock en Luna Equipetrol', {exact: false}).waitFor();
  assert.ok(await page.locator('main .tarjeta').count() > 0);
  await page.locator('main .tarjeta').first().click();
  await page.getByRole('dialog').waitFor();
  console.log('OK catálogo cliente: Luna Centro y Luna Equipetrol muestran prendas y detalle');
} finally { await browser.close(); }
