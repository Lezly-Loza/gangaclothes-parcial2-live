// API 8012 y Angular 4305 con una base de demostración aislada.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';

const browser = await chromium.launch({headless: true, executablePath: process.env.PLAYWRIGHT_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const context = await browser.newContext({acceptDownloads: true});
await context.route('http://127.0.0.1:8000/api/v1/**', route => route.continue({url: route.request().url().replace('127.0.0.1:8000', '127.0.0.1:8012')}));
await context.addInitScript(() => {
  const ReconocimientoSimulado = class {
    start() { setTimeout(() => { this.onresult({results: [[{transcript: 'Resume mis ventas'}]]}); this.onend(); }, 10); }
  };
  window.SpeechRecognition = ReconocimientoSimulado;
  window.webkitSpeechRecognition = ReconocimientoSimulado;
  window.speechSynthesis.speak = () => { window.__hablo = true; };
});
const page = await context.newPage();
try {
  await page.goto('http://127.0.0.1:4305/login');
  await page.locator('input[formcontrolname="codigo_tenant"]').fill('luna');
  await page.locator('input[formcontrolname="email"]').fill('ana@boutique-luna.bo');
  await page.locator('input[formcontrolname="password"]').fill('Luna12345');
  await page.getByRole('button', {name: 'Iniciar sesion'}).click();
  await page.waitForURL('**/admin');
  await page.goto('http://127.0.0.1:4305/admin/reportes');
  await page.getByRole('button', {name: 'Dictar pregunta'}).click();
  await page.getByLabel('Tu pregunta').waitFor();
  await page.waitForFunction(() => document.querySelector('#pregunta-reporte').value === 'Resume mis ventas');
  await page.getByRole('button', {name: 'Generar reporte'}).click();
  await page.getByRole('heading', {name: 'Ventas reales por día del período seleccionado'}).waitFor();
  await page.getByRole('img', {name: 'Ventas reales por día'}).waitFor();
  await page.getByRole('button', {name: 'Escuchar respuesta'}).click();
  assert.equal(await page.evaluate(() => window.__hablo), true);
  await page.getByRole('button', {name: 'Abrir el asistente'}).click();
  await page.getByRole('button', {name: 'Dictar pregunta'}).last().click();
  await page.waitForFunction(() => document.querySelector('.asistente input')?.value === 'Resume mis ventas');
  await page.getByRole('button', {name: 'Enviar', exact: true}).click();
  await page.locator('.asistente .turno:not(.mio) .globo').first().waitFor();
  await page.goto('http://127.0.0.1:4305/admin/respaldos');
  await page.getByRole('heading', {name: 'Respaldos automáticos'}).waitFor();
  await page.locator('input[type=time]').fill('03:15');
  const proximoMinuto = (Math.floor(Date.now() / 60000) + 1) * 60000;
  const citaBolivia = new Date(proximoMinuto - 4 * 3600000).toISOString().slice(0, 16);
  await page.locator('input[type=datetime-local]').fill(citaBolivia);
  await page.getByRole('button', {name: 'Guardar programación'}).click();
  await page.getByText('Programación guardada.').waitFor();
  await page.reload();
  await page.waitForFunction(() => document.querySelector('input[type=time]')?.value === '03:15');
  await page.waitForTimeout(Math.max(1000, proximoMinuto - Date.now() + 31000));
  await page.reload();
  await page.getByText(/respaldo-unico-.*json/).waitFor({timeout: 30000});
  const copiaProgramada = page.waitForEvent('download');
  await page.getByRole('button', {name: 'Descargar', exact: true}).first().click();
  const stream = await (await copiaProgramada).createReadStream();
  const partes = []; for await (const parte of stream) partes.push(parte);
  assert.equal(JSON.parse(Buffer.concat(partes).toString('utf8')).empresa.codigo, 'luna');
  const descarga = page.waitForEvent('download');
  await page.getByRole('button', {name: 'Descargar respaldo'}).click();
  assert.ok((await descarga).suggestedFilename().endsWith('.json'));
  await page.goto('http://127.0.0.1:4305/admin/dashboard');
  await page.getByRole('heading', {name: 'Predicciones y segmentos'}).waitFor();
  console.log('OK: dictado simulado, reporte con gráfica, lectura simulada, asistente, copia programada ejecutada y descargada, respaldo manual y dashboard.');
} finally { await browser.close(); }
