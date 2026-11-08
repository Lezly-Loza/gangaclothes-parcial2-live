// Prueba en la API de demostración aislada del puerto 8012 y la PWA 4305.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
const browser = await chromium.launch({headless: true, executablePath: process.env.PLAYWRIGHT_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const context = await browser.newContext({viewport: {width: 1366, height: 850}});
await context.route('http://127.0.0.1:8000/api/v1/**', route => {
  if (route.request().url().endsWith('/reportes/generativo')) return route.fulfill({json: {modo: 'sin_modelo', aviso: 'Modelo de prueba', respuesta: 'Resumen de prueba'}});
  return route.continue({url: route.request().url().replace('127.0.0.1:8000', '127.0.0.1:8012')});
});
const page = await context.newPage();
try {
  await page.goto('http://127.0.0.1:4305/login');
  await page.locator('input[formcontrolname="codigo_tenant"]').fill('luna');
  await page.locator('input[formcontrolname="email"]').fill('cliente@boutique-luna.bo');
  await page.locator('input[formcontrolname="password"]').fill('Luna12345');
  await page.getByRole('button', {name: 'Iniciar sesion', exact: true}).click();
  await page.getByRole('heading', {name: 'Catálogo sin conexión'}).waitFor();
  await page.getByRole('button', {name: 'Descargar selección'}).click();
  await page.getByText('Selección guardada en este dispositivo.').first().waitFor();
  const options = page.getByLabel('Prenda y variante').locator('option');
  const disponible = await options.evaluateAll(nodes => nodes.find(n => /· [1-9]\d* disponibles/.test(n.textContent))?.value);
  assert.ok(disponible);
  await context.setOffline(true);
  await page.getByLabel('Prenda y variante').selectOption(disponible);
  const manana = new Date(Date.now() + 86400000); const local = new Date(manana.getTime() - manana.getTimezoneOffset() * 60000).toISOString().slice(0,16);
  await page.getByLabel('Fecha de visita').fill(local);
  await page.getByRole('button', {name: 'Guardar operación pendiente'}).click();
  const articulo = page.locator('article').filter({hasText: 'Reserva ·'}).last();
  await articulo.getByText(/pendiente/i).waitFor();
  await page.getByRole('button', {name: 'Sincronizar pendientes'}).click();
  await articulo.getByText(/pendiente/i).waitFor();
  await context.setOffline(false);
  await articulo.getByText(/Código RES-/).waitFor({timeout: 30000});
  assert.match(await articulo.innerText(), /RES-/);
  console.log('OK reserva offline, conservación sin red y sincronización');
  await page.getByRole('button', {name: 'Cerrar sesion'}).click();
  await page.locator('input[formcontrolname="codigo_tenant"]').fill('luna');
  await page.locator('input[formcontrolname="email"]').fill('ana@boutique-luna.bo');
  await page.locator('input[formcontrolname="password"]').fill('Luna12345');
  await page.getByRole('button', {name: 'Iniciar sesion', exact: true}).click();
  await page.waitForURL(/\/admin/);
  await page.goto('http://127.0.0.1:4305/modo-offline');
  await page.getByRole('button', {name: 'Descargar selección'}).click();
  await page.getByText('Selección guardada en este dispositivo.').first().waitFor();
  assert.equal(await page.locator('article').filter({hasText: 'Reserva ·'}).count(), 0, 'No se deben mezclar cuentas');
  const idVenta = await page.getByLabel('Prenda y variante').locator('option').evaluateAll(nodes =>
    nodes.map(n => ({value: n.value, stock: Number(n.textContent.match(/· (\d+) disponibles/)?.[1] ?? 0)}))
      .sort((a, b) => b.stock - a.stock).find(n => n.stock >= 2)?.value);
  assert.ok(idVenta, 'Se necesita una variante con al menos dos unidades');
  await context.setOffline(true);
  await page.getByLabel('Prenda y variante').selectOption(idVenta);
  await page.getByLabel('Efectivo recibido').fill('10000');
  await page.getByRole('button', {name: 'Guardar operación pendiente'}).click();
  const venta = page.locator('article').filter({hasText: 'Venta de contado ·'}).last();
  await venta.getByText(/pendiente/i).waitFor();
  await context.setOffline(false);
  await venta.getByText(/Código V-/).waitFor({timeout: 30000});
  assert.match(await venta.innerText(), /V-/);
  // La copia vieja sigue descontando la operación hasta volver a descargarla.
  const antes = await page.getByLabel('Prenda y variante').locator(`option[value="${idVenta}"]`).innerText();
  const descarga = page.waitForResponse(r => r.url().includes('/offline/catalogo') && r.status() === 200);
  await page.getByRole('button', {name: 'Descargar selección'}).click();
  await descarga;
  await page.getByText('Selección guardada en este dispositivo.').first().waitFor();
  const despues = await page.getByLabel('Prenda y variante').locator(`option[value="${idVenta}"]`).innerText();
  assert.equal(antes, despues, 'Una venta confirmada no debe devolver stock en la copia vieja');
  await page.getByLabel('Prenda y variante').selectOption(idVenta);
  await page.getByRole('button', {name: 'Guardar operación pendiente'}).click();
  const pendiente = page.locator('article').filter({hasText: 'Venta de contado ·'}).last();
  await pendiente.getByText(/pendiente/i).waitFor();
  const token = await page.evaluate(() => localStorage.getItem('gc_token'));
  const headers = {Authorization: `Bearer ${token}`};
  const sucursal = await page.locator('select').first().inputValue();
  const inventario = await (await context.request.get(`http://127.0.0.1:8012/api/v1/inventario?sucursal_id=${sucursal}`, {headers})).json();
  const fila = inventario.find(x => x.variante_id === Number(idVenta));
  const ajuste = await context.request.post('http://127.0.0.1:8012/api/v1/inventario/movimientos', {headers,
    data: {sucursal_id: Number(sucursal), variante_id: Number(idVenta), tipo: 'AJUSTE', cantidad: fila.reservado, motivo: 'Prueba aislada'}});
  assert.equal(ajuste.status(), 201);
  await page.getByRole('button', {name: 'Sincronizar pendientes'}).click();
  await pendiente.getByText(/conflicto/).first().waitFor();
  await pendiente.getByText(/Stock insuficiente/).waitFor();
  console.log('OK venta de contado offline y conflicto por stock');
  await page.goto('http://127.0.0.1:4305/admin/reportes');
  await page.getByRole('heading', {name: 'Reporte por lenguaje natural'}).waitFor();
  await page.evaluate(() => {
    window.SpeechRecognition = class {
      start() { this.onresult({results: [[{transcript: 'Resume las ventas del período'}]]}); this.onend(); }
    };
  });
  await page.getByRole('button', {name: 'Dictar pregunta'}).click();
  assert.equal(await page.getByLabel('Tu pregunta').inputValue(), 'Resume las ventas del período');
  await page.getByRole('button', {name: 'Generar reporte', exact: true}).click();
  await page.getByText('Resumen de prueba', {exact: true}).waitFor();
  await page.goto('http://127.0.0.1:4305/admin/dashboard');
  await page.getByRole('heading', {name: 'Predicciones y segmentos'}).waitFor();
  await page.getByRole('heading', {name: 'Estimación de ventas · próximos 7 días'}).waitFor();
  await page.getByText(/Se requieren al menos 14 días|Regresión lineal/).waitFor();
  console.log('OK reportes, formulario generativo y dashboard analítico');
} catch (e) { console.error('Pantalla:', (await page.locator('body').innerText()).slice(-2600)); throw e; }
finally { await browser.close(); }
