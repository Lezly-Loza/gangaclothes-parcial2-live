import { chromium } from 'playwright';
import assert from 'node:assert/strict';

const browser = await chromium.launch({ headless: true,
  executablePath: process.env.PLAYWRIGHT_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' });
const context = await browser.newContext();
await context.route('http://127.0.0.1:8000/api/v1/**', route =>
  route.continue({ url: route.request().url().replace('127.0.0.1:8000', '127.0.0.1:8012') }));
const page = await context.newPage();
try {
  await page.goto('http://127.0.0.1:4300/');
  await page.locator('input[formcontrolname="codigo_tenant"]').fill('luna');
  await page.locator('input[formcontrolname="email"]').fill('cliente@boutique-luna.bo');
  await page.locator('input[formcontrolname="password"]').fill('Luna12345');
  await page.getByRole('button', {name: 'Iniciar sesion'}).click();
  await page.getByRole('heading', {name: 'Catálogo sin conexión'}).waitFor();
  await page.getByRole('button', {name: 'Descargar selección'}).click();
  await page.getByText('Selección guardada en este dispositivo.').waitFor();
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  await context.setOffline(true);
  await page.reload();
  await page.getByRole('heading', {name: 'Catálogo sin conexión'}).waitFor();
  assert.ok(await page.getByText('disponibles al descargar', {exact: false}).count() > 0);
  console.log('OK PWA reabre y muestra el catálogo guardado con la red desconectada');
} finally { await browser.close(); }
