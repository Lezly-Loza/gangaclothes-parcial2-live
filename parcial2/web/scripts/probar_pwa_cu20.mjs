// Verifica instalación lógica del service worker, reapertura y cola offline.
// Requiere PWA en 4305 y la base de pruebas aislada en 8012.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
const browser = await chromium.launch({headless: true, executablePath: process.env.PLAYWRIGHT_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const context = await browser.newContext();
await context.route('http://127.0.0.1:8000/api/v1/**', route => route.continue({url: route.request().url().replace('127.0.0.1:8000', '127.0.0.1:8012')}));
const page = await context.newPage();
try {
  await page.goto('http://127.0.0.1:4305/');
  await page.locator('input[formcontrolname="codigo_tenant"]').fill('luna');
  await page.locator('input[formcontrolname="email"]').fill('cliente@boutique-luna.bo');
  await page.locator('input[formcontrolname="password"]').fill('Luna12345');
  await page.getByRole('button', {name: 'Iniciar sesion'}).click();
  await page.getByRole('heading', {name: 'Catálogo sin conexión'}).waitFor();
  await page.getByRole('button', {name: 'Descargar selección'}).click();
  await page.getByText('Selección guardada en este dispositivo.').first().waitFor();
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload(); await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  await context.setOffline(true); await page.reload();
  await page.getByRole('heading', {name: 'Catálogo sin conexión'}).waitFor();
  const id = await page.getByLabel('Prenda y variante').locator('option').evaluateAll(nodes => nodes.find(n => /· [1-9]\d* disponibles/.test(n.textContent))?.value);
  assert.ok(id, 'La selección descargada debe permanecer disponible');
  await page.getByLabel('Prenda y variante').selectOption(id);
  const manana = new Date(Date.now() + 86400000); const local = new Date(manana.getTime() - manana.getTimezoneOffset() * 60000).toISOString().slice(0,16);
  await page.getByLabel('Fecha de visita').fill(local);
  await page.getByRole('button', {name: 'Guardar operación pendiente'}).click();
  await page.locator('article').filter({hasText: 'Reserva ·'}).last().getByText(/pendiente/i).waitFor();
  await page.reload();
  const op = page.locator('article').filter({hasText: 'Reserva ·'}).last();
  await op.getByText(/pendiente/i).waitFor();
  await context.setOffline(false);
  await op.getByText(/Código RES-/).waitFor({timeout: 30000});
  assert.match(await op.innerText(), /RES-/);
  console.log('OK PWA abre sin conexión, conserva y sincroniza una reserva tras reiniciar');
} catch (e) { console.error('Pantalla:', (await page.locator('body').innerText()).slice(0,2000)); throw e; }
finally { await browser.close(); }
