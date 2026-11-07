// Usa exclusivamente una base aislada en el puerto 8012.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
const browser = await chromium.launch({headless: true, executablePath: process.env.PLAYWRIGHT_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const context = await browser.newContext({viewport: {width: 1366, height: 768}});
await context.route('http://127.0.0.1:8000/api/v1/**', route => route.continue({url: route.request().url().replace('127.0.0.1:8000', '127.0.0.1:8012')}));
const page = await context.newPage();
try {
  await page.goto('http://localhost:4200/login');
  await page.getByRole('button', {name: 'Cliente Luna', exact: true}).click();
  await page.getByRole('button', {name: 'Iniciar sesion', exact: true}).click();
  await page.getByRole('link', {name: 'Catalogo', exact: true}).click();
  await page.locator('main .tarjeta').first().click();
  await page.getByRole('dialog').getByRole('button', {name: 'Reservar para probar en tienda'}).click();
  await page.getByRole('button', {name: 'Confirmar reserva'}).click();
  const mensajeReserva = page.getByText(/Reserva RES-.*confirmada/);
  await mensajeReserva.waitFor();
  const codigoReserva = (await mensajeReserva.innerText()).match(/RES-[A-F0-9]+/)[0];
  await page.getByRole('link', {name: /Ver mis reservas/}).click();
  await page.getByRole('heading', {name: 'Mis reservas'}).waitFor();
  await page.getByText(/RES-/).first().waitFor();
  await page.getByRole('button', {name: 'Cancelar reserva'}).first().click();
  await page.getByRole('button', {name: 'Si, cancelar'}).click();
  await page.getByRole('button', {name: /Todas/}).click();
  await page.locator('article.reserva').filter({hasText: codigoReserva}).getByText('cancelada', {exact: true}).waitFor();
  console.log('OK reservar, consultar y cancelar');
  await page.getByRole('link', {name: 'Catalogo', exact: true}).click();
  await page.locator('main .tarjeta').first().click();
  await page.getByRole('button', {name: 'Agregar al carrito'}).click();
  await page.getByText(/Agregado al carrito/).waitFor();
  await page.getByRole('link', {name: /Ir al carrito/}).click();
  await page.getByRole('heading', {name: 'Carrito'}).waitFor();
  await page.getByLabel('Envío a domicilio').check();
  await page.getByLabel('Dirección').fill('Calle de prueba 123');
  await page.getByLabel('Latitud').fill('-17.78');
  await page.getByLabel('Longitud').fill('-63.18');
  await page.getByRole('button', {name: 'Confirmar compra de prueba'}).click();
  await page.getByRole('heading', {name: 'Compra de prueba registrada'}).waitFor();
  const texto = await page.locator('.ticket').innerText();
  assert.match(texto, /V-[A-F0-9]+/); assert.match(texto, /No se cobró dinero real/);
  await page.getByRole('link', {name: 'Ver mis compras'}).click();
  await page.getByRole('heading', {name: 'Mis compras'}).waitFor();
  await page.getByText('Simulado (sin cobro real)', {exact: false}).waitFor();
  await page.getByRole('link', {name: 'Mis pedidos', exact: true}).click();
  await page.getByRole('heading', {name: 'Mis pedidos'}).waitFor();
  await page.getByText('Calle de prueba 123', {exact: false}).first().waitFor();
  console.log('OK carrito, compra simulada e historial de pedido');
} catch(e) { console.error('Pantalla:', (await page.locator('body').innerText()).slice(0,2500)); throw e; }
finally { await browser.close(); }
