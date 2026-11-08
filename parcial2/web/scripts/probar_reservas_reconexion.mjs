// Ejecutar con la PWA en 4305 y una API con datos de prueba en 8012.
import { chromium, request } from 'playwright';
import assert from 'node:assert/strict';

const api = await request.newContext({baseURL: 'http://127.0.0.1:8012/api/v1/'});
const login = await api.post('auth/login', {data: {codigo_tenant: 'luna', email: 'ana@boutique-luna.bo', password: 'Luna12345'}});
assert.equal(login.status(), 200);
const headers = {Authorization: `Bearer ${(await login.json()).access_token}`};
const inv = await (await api.get('inventario?sucursal_id=1', {headers})).json();
const prendas = inv.filter(x => x.prenda_publicada && x.disponible > 0).slice(0, 2);
assert.equal(prendas.length, 2);
for (const item of prendas) {
  const r = await api.post('inventario/movimientos', {headers, data: {sucursal_id: 1, variante_id: item.variante_id, tipo: 'AJUSTE', cantidad: item.reservado + 1, motivo: 'Prueba aislada'}});
  assert.equal(r.status(), 201, await r.text());
}
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
  const manana = new Date(Date.now() + 86400000);
  const local = new Date(manana.getTime() - manana.getTimezoneOffset() * 60000).toISOString().slice(0,16);
  async function crear(item) {
    await page.getByLabel('Prenda y variante').selectOption(String(item.variante_id));
    await page.getByLabel('Fecha de visita').fill(local);
    await page.getByRole('button', {name: 'Guardar operación pendiente'}).click();
    const op = page.locator('article').filter({hasText: `Reserva · ${item.prenda} · ${item.sku}`}).last();
    await op.getByText(/Pendiente: aún no confirmada/).waitFor();
    return op;
  }
  await context.setOffline(true); await page.reload();
  await page.getByRole('heading', {name: 'Catálogo sin conexión'}).waitFor();
  await crear(prendas[0]);
  await page.reload();
  let op = page.locator('article').filter({hasText: `Reserva · ${prendas[0].prenda} · ${prendas[0].sku}`}).last();
  await op.getByText(/Pendiente: aún no confirmada/).waitFor();
  await context.setOffline(false);
  await op.getByText(/Confirmada.*Código RES-/).waitFor({timeout: 30000});
  const texto = await op.innerText();
  const codigo = texto.match(/Código (RES-[\w-]+)/)?.[1]; assert.ok(codigo);
  console.log(`OK: reserva persistida tras reiniciar y confirmada automáticamente: ${codigo}`);
  await context.setOffline(true);
  await crear(prendas[1]);
  await page.reload();
  op = page.locator('article').filter({hasText: `Reserva · ${prendas[1].prenda} · ${prendas[1].sku}`}).last();
  await op.getByText(/Pendiente: aún no confirmada/).waitFor();
  const venta = await api.post('ventas', {headers, data: {sucursal_id: 1, forma_pago: 'EFECTIVO', monto_recibido: 10000, items: [{variante_id: prendas[1].variante_id, cantidad: 1}]}});
  assert.equal(venta.status(), 201, await venta.text());
  await page.goto('http://127.0.0.1:4305/catalogo');
  await context.setOffline(false);
  await page.getByText(/Reserva no confirmada/).first().waitFor({timeout: 30000});
  await page.goto('http://127.0.0.1:4305/modo-offline');
  op = page.locator('article').filter({hasText: `Reserva · ${prendas[1].prenda} · ${prendas[1].sku}`}).last();
  await op.getByText(/No confirmada/).waitFor({timeout: 30000});
  assert.match(await op.innerText(), /stock/i);
  assert.doesNotMatch(await op.innerText(), /Código RES-/);
  console.log('OK: última unidad vendida por otra persona; reserva rechazada y aviso visible fuera de la pantalla offline');
} catch (e) { console.error('Pantalla:', (await page.locator('body').innerText()).slice(0,2500)); throw e; }
finally { await browser.close(); await api.dispose(); }
