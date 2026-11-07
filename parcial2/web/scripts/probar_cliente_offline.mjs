// Usa exclusivamente la API de demostración aislada en el puerto 8012.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';

const browser = await chromium.launch({ headless: true,
  executablePath: process.env.PLAYWRIGHT_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' });
const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
await context.route('http://127.0.0.1:8000/api/v1/**', route =>
  route.continue({ url: route.request().url().replace('127.0.0.1:8000', '127.0.0.1:8012') }));
const page = await context.newPage();
const sufijo = Date.now().toString(36);
try {
  await page.goto('http://localhost:4200/login');
  await page.getByRole('button', {name: 'Admin Luna', exact: true}).click();
  await page.getByRole('button', {name: 'Iniciar sesion', exact: true}).click();
  await page.waitForURL(/\/admin(?:\/|$)/);
  await page.getByRole('link', {name: 'Promociones', exact: true}).click();
  await page.getByRole('heading', {name: 'Promociones', exact: true}).waitFor();
  await page.getByRole('button', {name: '+ Nueva promocion'}).click();
  await page.locator('#p-nombre').fill(`Promoción ${sufijo}`);
  await page.locator('#p-valor').fill('20');
  const opcionPrenda = page.getByRole('group', {name: 'Prendas en promocion'}).locator('label').filter({hasText: 'Polera clásica'}).first();
  const nombrePrenda = (await opcionPrenda.locator('.nombre-prenda').innerText()).trim();
  await opcionPrenda.locator('input').check();
  await page.getByRole('button', {name: 'Guardar', exact: true}).click();
  await page.getByRole('heading', {name: `Promoción ${sufijo}`}).waitFor();
  console.log('OK crear promoción desde la interfaz');

  const esperaCatalogo = page.waitForResponse(r => r.url().includes('/prendas/catalogo-interno') && r.status() === 200);
  await page.getByRole('link', {name: 'Caja', exact: true}).click();
  await page.getByRole('heading', {name: /Caja/}).waitFor();
  await esperaCatalogo;
  await page.getByText('No hay reservas preparadas en esta sucursal.').waitFor();
  await page.getByLabel('Buscar variante por SKU o nombre').fill(nombrePrenda);
  try { await page.locator('button.resultado:not([disabled])').first().click({timeout: 7000}); }
  catch (e) { console.error('Prenda elegida:', nombrePrenda, 'Pantalla:', (await page.locator('main').innerText()).slice(0, 1800)); throw e; }
  await page.locator('#caja-recibido').fill('10000');
  await page.getByRole('button', {name: /Cobrar Bs/}).click();
  await page.getByText('Venta cobrada', {exact: false}).first().waitFor();
  await page.locator('.ticket-promo').getByText(`Promoción ${sufijo}`, {exact: false}).waitFor();
  console.log('OK promoción cobrada y detallada en caja');

  await page.getByRole('link', {name: 'Cambios de prendas'}).click();
  await page.getByRole('heading', {name: 'Cambio de prenda'}).waitFor();
  await page.locator('#recientes option').nth(1).waitFor({state: 'attached'});
  const codigoElegido = await page.locator('#recientes option').nth(1).getAttribute('value');
  await page.locator('#recientes').selectOption(codigoElegido);
  await page.getByRole('heading', {name: `Venta ${codigoElegido}`, exact: false}).waitFor();
  await page.getByRole('link', {name: 'Anular operación'}).click();
  await page.getByRole('heading', {name: 'Anular venta o reserva'}).waitFor();
  await page.locator('#recientes option').nth(1).waitFor({state: 'attached'});
  console.log('OK selección de códigos recientes');

  await page.getByRole('button', {name: 'Cerrar sesion'}).click();
  await page.getByRole('link', {name: 'Crear cuenta'}).click();
  await page.locator('#r-empresa').fill('luna');
  await page.locator('#r-documento').fill(`DOC${sufijo}`);
  await page.locator('#r-nombre').fill('Cliente prueba');
  await page.locator('#r-email').fill(`cliente-${sufijo}@ejemplo.bo`);
  await page.locator('#r-password').fill('Prueba2026!');
  await page.locator('#r-confirmar').fill('Prueba2026!');
  await page.getByRole('button', {name: 'Crear cuenta', exact: true}).click();
  await page.getByRole('heading', {name: 'Catálogo sin conexión'}).waitFor();
  await page.getByRole('button', {name: 'Descargar selección'}).click();
  await page.getByText('Selección guardada en este dispositivo.').waitFor();
  const texto = await page.locator('main').innerText();
  assert.match(texto, /prendas guardadas/);
  const guardado = await page.evaluate(() => new Promise((resolve, reject) => {
    const request = indexedDB.open('ganga-catalogos-offline');
    request.onsuccess = () => { const tx = request.result.transaction('catalogos'); const get = tx.objectStore('catalogos').getAll();
      get.onsuccess = () => resolve(get.result); get.onerror = () => reject(get.error); };
    request.onerror = () => reject(request.error);
  }));
  assert.ok(guardado[0].catalogo.productos.length > 0);
  await context.setOffline(true);
  assert.ok(await page.getByText('disponibles al descargar', {exact: false}).count() > 0);
  await page.getByRole('button', {name: 'Descargar selección'}).click();
  await page.getByText('La copia anterior se conserva.', {exact: false}).waitFor();
  assert.ok(await page.getByText('disponibles al descargar', {exact: false}).count() > 0);
  console.log('OK registro de cliente y consulta sin conexión de la copia guardada');
} finally { await browser.close(); }
