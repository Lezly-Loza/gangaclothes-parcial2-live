// Pruebas de la interfaz contra una API de demostración aislada en el puerto 8012.
// Iniciar Angular en 4200 y el backend de prueba en 8012 antes de ejecutarlo.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';

const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.PLAYWRIGHT_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
});
const context = await browser.newContext({viewport: {width: 1366, height: 768}});
await context.route('http://127.0.0.1:8000/api/v1/**', async (route) => {
  await route.continue({url: route.request().url().replace('127.0.0.1:8000', '127.0.0.1:8012')});
});
const page = await context.newPage();
const sufijo = Date.now().toString(36);

async function entrar(cuenta) {
  await page.goto('http://localhost:4200/login');
  await page.getByRole('button', {name: cuenta, exact: true}).click();
  await page.getByRole('button', {name: 'Iniciar sesion', exact: true}).click();
  await page.waitForURL(/\/admin(?:\/|$)/);
}

try {
  await entrar('Super');
  await page.getByRole('link', {name: 'Planes y precios'}).click();
  await page.getByRole('heading', {name: 'Planes y precios'}).waitFor();
  const profesional = page.locator('article').filter({has: page.getByRole('heading', {name: 'Profesional', exact: true})});
  await profesional.getByRole('button', {name: 'Editar'}).click();
  await page.locator('input[formcontrolname="precio_mensual"]').fill('59');
  await page.getByRole('button', {name: 'Guardar cambios'}).click();
  await page.getByText('Plan "Profesional" actualizado.').waitFor();
  assert.match(await profesional.innerText(), /59/);
  assert.equal(await page.getByRole('link', {name: 'Usuarios', exact: true}).count(), 0);
  console.log('OK superadministrador: empresas, planes y cambio de precio');

  await page.getByRole('button', {name: 'Cerrar sesion'}).click();
  await entrar('Admin Luna');
  assert.equal(await page.getByRole('link', {name: 'Planes y precios'}).count(), 0);
  await page.getByRole('link', {name: 'Roles y permisos'}).click();
  await page.getByRole('heading', {name: 'Roles y permisos'}).waitFor();
  await page.getByRole('button', {name: '+ Nuevo rol'}).click();
  await page.locator('#r-nombre').fill(`supervisor-${sufijo}`);
  await page.locator('#r-descripcion').fill('Rol de prueba aislada');
  await page.getByRole('button', {name: 'Crear rol'}).click();
  await page.getByText(`Rol supervisor-${sufijo} creado.`, {exact: false}).first().waitFor();
  console.log('OK administrador: crear rol y cargar permisos');

  await page.getByRole('link', {name: 'Usuarios', exact: true}).click();
  await page.getByRole('heading', {name: 'Usuarios'}).waitFor();
  await page.getByRole('button', {name: '+ Nuevo usuario'}).click();
  await page.locator('#u-nombre').fill('Prueba sin rol');
  await page.locator('#u-email').fill(`sinrol-${sufijo}@ejemplo.bo`);
  await page.locator('#u-password').fill('Prueba2026!');
  await page.getByRole('button', {name: 'Guardar', exact: true}).click();
  await page.getByText(`sinrol-${sufijo}@ejemplo.bo`).waitFor();
  console.log('OK administrador: crear usuario sin asignar rol');

  await page.getByRole('link', {name: 'Clientes', exact: true}).click();
  await page.getByRole('heading', {name: 'Clientes'}).waitFor();
  await page.getByText('Cliente Demo 1').waitFor();
  await page.getByRole('link', {name: 'Mi suscripcion'}).click();
  await page.getByText('Plan vigente').waitFor();
  assert.match(await page.locator('main').innerText(), /Profesional/);
  console.log('OK administrador: clientes y estado de suscripción');

  await page.getByRole('link', {name: 'Oferta de proveedores'}).click();
  await page.getByRole('heading', {name: 'Oferta de proveedores'}).waitFor();
  await page.getByText('Ningun proveedor cargo productos todavia.', {exact: false}).waitFor();
  await page.getByRole('link', {name: 'Compras', exact: true}).click();
  await page.getByRole('heading', {name: /Compras/}).waitFor();
  await page.getByRole('button', {name: '+ Nueva compra'}).click();
  await page.locator('#c-proveedor option').nth(1).waitFor({state: 'attached'});
  await page.locator('#c-proveedor').selectOption({index: 1});
  await page.getByText('no tiene oferta registrada', {exact: false}).waitFor();
  await page.getByLabel('Variante de la linea 1').selectOption({index: 1});
  await page.getByLabel('Cantidad de la linea 1').fill('2');
  await page.getByLabel('Precio unitario de la linea 1').fill('20');
  await page.getByRole('button', {name: 'Registrar compra'}).click();
  await page.getByText(/Compra #\d+ a .* registrada/).waitFor();
  await page.getByRole('button', {name: 'Recibir', exact: true}).first().click();
  await page.getByRole('heading', {name: /¿Recibir la compra/}).waitFor();
  await page.getByRole('button', {name: 'Si, recibir'}).click();
  await page.getByText(/Compra #\d+ recibida/).waitFor();
  console.log('OK administrador: oferta, compra y recepción de inventario');

  await page.getByRole('link', {name: 'Caja', exact: true}).click();
  await page.getByRole('heading', {name: /Caja/}).waitFor();
  await page.getByLabel('Buscar variante por SKU o nombre').fill('Polera');
  await page.locator('button.resultado').first().click();
  await page.locator('#caja-recibido').fill('1000');
  await page.getByRole('button', {name: /Cobrar Bs/}).click();
  await page.getByText('Venta cobrada', {exact: false}).first().waitFor();
  const codigoVentaCaja = (await page.locator('.ticket .nro').textContent()).trim();
  console.log('OK administrador: cobro en efectivo desde caja');

  await page.getByRole('link', {name: 'Envios a domicilio'}).click();
  await page.getByRole('heading', {name: /Envios a domicilio/}).waitFor();
  await page.getByRole('button', {name: '+ Registrar envío'}).click();
  await page.locator('#envio-codigo').fill(codigoVentaCaja);
  await page.locator('#envio-direccion').fill('Avenida Principal 123');
  await page.locator('#envio-lat').fill('-17.78');
  await page.locator('#envio-lng').fill('-63.18');
  await page.getByRole('button', {name: 'Guardar envío'}).click();
  const filaEnvio = page.getByRole('row').filter({hasText: codigoVentaCaja});
  await filaEnvio.waitFor();
  await filaEnvio.getByRole('button', {name: 'Asignar repartidor'}).click();
  await page.locator('#a-repartidor').fill('Repartidor de prueba');
  await page.getByRole('button', {name: 'Asignar', exact: true}).click();
  await filaEnvio.getByRole('button', {name: 'Marcar en camino'}).click();
  await filaEnvio.getByRole('button', {name: 'Marcar entregado'}).click();
  await page.getByText('entregado a', {exact: false}).first().waitFor();
  console.log('OK administrador: registrar y entregar envío');

  await page.getByRole('link', {name: 'Dashboard', exact: true}).click();
  await page.getByRole('heading', {name: /Dashboard/}).waitFor();
  await page.getByText('Las ganancias y el valor a costo incluyen', {exact: false}).waitFor();
  await page.getByRole('heading', {name: 'Ventas por dia'}).waitFor();
  await page.getByRole('link', {name: 'Reportes', exact: true}).click();
  await page.getByRole('heading', {name: /Reportes/}).waitFor();
  await page.getByRole('heading', {name: 'Detalle de ventas'}).waitFor();
  await page.getByRole('button', {name: 'Inventario y movimientos'}).click();
  await page.getByRole('heading', {name: 'Stock por prenda y sucursal'}).waitFor();
  await page.getByRole('button', {name: 'Ganancia por prenda'}).click();
  await page.getByRole('heading', {name: 'Ganancia por prenda'}).waitFor();
  console.log('OK administrador: dashboard y tres reportes');

  await page.getByRole('link', {name: 'Reservas', exact: true}).click();
  await page.getByRole('heading', {name: /Reservas/}).waitFor();
  await page.getByRole('link', {name: 'Ciudades', exact: true}).click();
  await page.getByRole('heading', {name: 'Ciudades'}).waitFor();
  await page.getByRole('link', {name: 'Sucursales', exact: true}).click();
  await page.getByRole('heading', {name: 'Sucursales'}).waitFor();
  console.log('OK administrador: reservas, ciudades y sucursales cargan');

  await page.getByRole('link', {name: 'Prendas y variantes'}).click();
  await page.getByRole('heading', {name: 'Prendas y variantes'}).waitFor();
  const prendaDemo = page.getByRole('row').filter({hasText: 'Polera clásica'}).first();
  await prendaDemo.waitFor();
  await prendaDemo.getByRole('button', {name: 'Variantes y stock'}).click();
  await page.locator('#detalle-variantes').getByText('Polera clásica', {exact: false}).first().waitFor();
  console.log('OK administrador: prendas y variantes de la misma base');

  await page.getByRole('link', {name: 'Inventario', exact: true}).click();
  await page.getByRole('heading', {name: /Inventario/}).waitFor();
  await page.getByText('Polera clásica', {exact: false}).first().waitFor();
  await page.getByRole('link', {name: 'Movimientos', exact: true}).click();
  await page.getByRole('heading', {name: /Movimientos/}).waitFor();
  await page.getByRole('button', {name: '+ Registrar movimiento'}).waitFor();
  console.log('OK administrador: inventario e historial de movimientos');

  const token = await page.evaluate(() => localStorage.getItem('gc_token'));
  const headers = {Authorization: `Bearer ${token}`};
  const sucursales = await (await context.request.get('http://127.0.0.1:8012/api/v1/admin/sucursales', {headers})).json();
  const sucursal = sucursales[0].id;
  const filas = await (await context.request.get(`http://127.0.0.1:8012/api/v1/inventario?sucursal_id=${sucursal}`, {headers})).json();
  const disponibles = filas.filter(f => f.disponible > 1);
  assert.ok(disponibles.length >= 2, 'Se necesitan dos variantes con stock en la demo');
  async function crearVenta() {
    const r = await context.request.post('http://127.0.0.1:8012/api/v1/ventas', {headers, data: {
      sucursal_id: sucursal, forma_pago: 'EFECTIVO', items: [{variante_id: disponibles[0].variante_id, cantidad: 1}],
    }});
    assert.equal(r.status(), 201, await r.text());
    return r.json();
  }
  const ventaCambio = await crearVenta();
  await page.getByRole('link', {name: 'Cambios de prendas'}).click();
  await page.getByRole('heading', {name: 'Cambio de prenda'}).waitFor();
  await page.locator('#codigo').fill(ventaCambio.codigo);
  await page.getByRole('button', {name: 'Buscar'}).click();
  await page.getByText(`Venta ${ventaCambio.codigo}`, {exact: false}).waitFor();
  await page.locator('#devuelta').selectOption({index: 1});
  const opcionNueva = await page.locator('#nueva option').filter({hasText: disponibles[1].sku}).getAttribute('value');
  await page.locator('#nueva').selectOption(opcionNueva);
  await page.locator('#motivo').fill('Cambio de talla');
  await page.getByRole('button', {name: 'Registrar cambio'}).click();
  await page.getByText(/Cambio \d+ registrado/).waitFor();

  const ventaAnular = await crearVenta();
  await page.getByRole('link', {name: 'Anular operación'}).click();
  await page.getByRole('heading', {name: 'Anular venta o reserva'}).waitFor();
  await page.locator('#codigo').fill(ventaAnular.codigo);
  await page.getByRole('button', {name: 'Buscar'}).click();
  await page.getByText(`Operación ${ventaAnular.codigo}`, {exact: false}).waitFor();
  await page.locator('#motivo').fill('Prueba de anulación');
  await page.getByRole('button', {name: 'Anular operación'}).click();
  await page.getByText(`${ventaAnular.codigo}: ANULADA`).waitFor();
  console.log('OK administrador: cambio de prenda y anulación de venta');
} finally {
  await browser.close();
}
