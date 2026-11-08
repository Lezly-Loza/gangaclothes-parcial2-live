// Comprueba una reapertura real del navegador con el mismo perfil y sin red.
import { chromium } from 'playwright';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import assert from 'node:assert/strict';
const perfil = await mkdtemp(join(tmpdir(), 'gc-pwa-reinicio-'));
const executablePath = process.env.PLAYWRIGHT_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
async function abrir(offline = false) {
  const ctx = await chromium.launchPersistentContext(perfil, {headless: true, executablePath, offline});
  await ctx.route('http://127.0.0.1:8000/api/v1/**', route => route.abort());
  return ctx;
}
let context = await abrir();
try {
  let page = context.pages()[0] || await context.newPage();
  await page.goto('http://127.0.0.1:4306/login');
  await page.locator('input[formcontrolname="codigo_tenant"]').fill('luna');
  await page.locator('input[formcontrolname="email"]').fill('cliente@boutique-luna.bo');
  await page.locator('input[formcontrolname="password"]').fill('Luna12345');
  await page.getByRole('button', {name: 'Iniciar sesion'}).click();
  await page.getByRole('heading', {name: 'Catálogo sin conexión'}).waitFor();
  await page.getByRole('button', {name: 'Descargar selección'}).click();
  await page.getByText('Selección guardada en este dispositivo.').first().waitFor();
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload(); await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  await page.getByLabel('Prenda y variante').waitFor();
  const id = await page.getByLabel('Prenda y variante').locator('option').evaluateAll(nodes => nodes.find(n => /· [1-9]\d* disponibles/.test(n.textContent))?.value);
  assert.ok(id);
  await context.setOffline(true);
  await page.getByLabel('Prenda y variante').selectOption(id);
  const manana = new Date(Date.now() + 86400000);
  await page.getByLabel('Fecha de visita').fill(new Date(manana.getTime() - manana.getTimezoneOffset() * 60000).toISOString().slice(0,16));
  await page.getByRole('button', {name: 'Guardar operación pendiente'}).click();
  await page.locator('article').filter({hasText: 'Reserva ·'}).last().getByText(/Pendiente/).waitFor();
  await context.close();
  context = await abrir(true);
  page = context.pages()[0] || await context.newPage();
  page.on('response', r => { if (r.url().includes('/api/v1/')) console.log('API', r.status(), new URL(r.url()).pathname); });
  await page.goto('http://127.0.0.1:4306/modo-offline');
  await page.getByRole('heading', {name: 'Catálogo sin conexión'}).waitFor();
  const op = page.locator('article').filter({hasText: 'Reserva ·'}).last();
  await op.getByText(/Pendiente/).waitFor();
  await context.setOffline(false);
  console.log('Conexión después de reabrir:', await page.evaluate(() => navigator.onLine));
  await op.getByText(/Código RES-/).waitFor({timeout: 30000});
  console.log('OK: se cerró el navegador, se reabrió la PWA sin red y la reserva persistió hasta confirmarse al reconectar');
} catch (error) {
  const page = context.pages()[0];
  if (page) console.error('Estado:', (await page.locator('body').innerText()).slice(-2000));
  throw error;
} finally { await context.close(); }
