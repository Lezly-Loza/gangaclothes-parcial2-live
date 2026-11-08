// PWA 4305 y API de demostración 8012; nunca usar contra una base real.
import { chromium, request } from 'playwright';
import assert from 'node:assert/strict';
const api = await request.newContext({baseURL: 'http://127.0.0.1:8012/api/v1/'});
const login = await api.post('auth/login', {data: {codigo_tenant: 'luna', email: 'ana@boutique-luna.bo', password: 'Luna12345'}});
const headers = {Authorization: `Bearer ${(await login.json()).access_token}`};
const venta = await api.post('ventas', {headers, data: {sucursal_id: 1, forma_pago: 'EFECTIVO', monto_recibido: 1000, items: [{variante_id: 4, cantidad: 1}]}});
assert.equal(venta.status(), 201, await venta.text());
const codigo = (await venta.json()).codigo;
const browser = await chromium.launch({headless: true, executablePath: process.env.PLAYWRIGHT_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const context = await browser.newContext({acceptDownloads: true});
await context.route('http://127.0.0.1:8000/api/v1/**', route => route.continue({url: route.request().url().replace('127.0.0.1:8000', '127.0.0.1:8012')}));
const page = await context.newPage();
try {
  await page.goto('http://127.0.0.1:4305/login');
  await page.locator('input[formcontrolname="codigo_tenant"]').fill('luna');
  await page.locator('input[formcontrolname="email"]').fill('ana@boutique-luna.bo');
  await page.locator('input[formcontrolname="password"]').fill('Luna12345');
  await page.getByRole('button', {name: 'Iniciar sesion'}).click();
  await page.waitForURL('**/admin');
  await page.getByRole('link', {name: 'Respaldos'}).click();
  const promesa = page.waitForEvent('download');
  await page.getByRole('button', {name: 'Descargar respaldo'}).click();
  const descarga = await promesa;
  const stream = await descarga.createReadStream();
  const partes = []; for await (const parte of stream) partes.push(parte);
  const contenido = Buffer.concat(partes);
  assert.equal(JSON.parse(contenido.toString('utf8')).empresa.codigo, 'luna');
  await page.locator('input[type=file]').setInputFiles({name: 'empresa.json', mimeType: 'application/json', buffer: contenido});
  await page.getByText(/Copia válida para luna/).waitFor();
  console.log('OK: descarga y verificación del respaldo en el panel');
  await page.goto('http://127.0.0.1:4305/admin/cambios');
  await page.getByLabel('Código de venta').fill(codigo);
  await page.getByRole('button', {name: 'Buscar', exact: true}).click();
  await page.getByRole('heading', {name: new RegExp(codigo)}).waitFor();
  for (const [id, sku] of [['devuelta', 'LUN-02-02'], ['nueva', 'LUN-02-01']]) {
    const valor = await page.locator(`#${id} option`).filter({hasText: sku}).getAttribute('value');
    assert.ok(valor); await page.locator(`#${id}`).selectOption(valor);
  }
  await page.getByText('Devolver al cliente: Bs 3.00').waitFor();
  await page.getByLabel('Motivo').fill('Cambio de talla');
  await page.getByRole('button', {name: 'Registrar cambio'}).click();
  await page.getByText(/Cambio .* registrado. Devolver al cliente Bs 3.00/).waitFor();
  console.log('OK: cambio de talla calcula y muestra Bs 3.00 a devolver');
} catch (e) { console.error('Pantalla:', (await page.locator('body').innerText()).slice(0,2500)); throw e; }
finally { await browser.close(); await api.dispose(); }
