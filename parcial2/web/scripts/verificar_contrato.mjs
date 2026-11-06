#!/usr/bin/env node
/**
 * Verificador del contrato UML del parcial 2.
 * Busca cada clase y cada metodo de la tabla de la seccion 2 del prompt
 * dentro de `src/`. Falla si falta alguno.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'src');

const CONTRATO = [
  { clase: 'LoginPage',                metodos: ['entrar'] },
  { clase: 'RegistrarEmpresaForm',     metodos: ['listar', 'registrarEmpresa'] },
  { clase: 'EmpresasList',             metodos: ['listar', 'registrarEmpresa'] },
  { clase: 'UsuariosList',             metodos: ['listar'] },
  { clase: 'UsuarioForm',              metodos: ['crear'] },
  { clase: 'SucursalesList',           metodos: ['listar', 'nuevaSucursal', 'crearSucursal', 'mostrarConfirmacion'] },
  { clase: 'SucursalForm',             metodos: ['nuevaSucursal', 'crearSucursal', 'mostrarConfirmacion'] },
  { clase: 'ContratarPlanForm',        metodos: ['elegirPlan', 'contratarPlan', 'mostrarResumen'] },
  { clase: 'MiSuscripcion',            metodos: ['verMiSuscripcion', 'cambiarPlan', 'mostrarNuevoPlan'] },
  { clase: 'CambiarPlanDialog',        metodos: ['cambiarPlan', 'mostrarNuevoPlan'] },
  { clase: 'ProductosList',            metodos: ['listar'] },
  { clase: 'ProductoForm',             metodos: ['crear'] },
  { clase: 'CatalogosPage',            metodos: ['listar', 'guardar'] },
  { clase: 'ProveedoresList',          metodos: ['listar'] },
  { clase: 'ProveedorForm',            metodos: ['crear'] },
  { clase: 'ClientesList',             metodos: ['buscar'] },
  { clase: 'ClienteForm',              metodos: ['crear'] },
  { clase: 'InventarioPage',           metodos: ['abrirInventario', 'registrarMovimiento', 'mostrarStock'] },
  { clase: 'MovimientoForm',           metodos: ['registrarMovimiento'] },
  { clase: 'AvisoInstalacionComponent',metodos: ['abrirAplicacion', 'instalarApp', 'mostrarAppInstalada'] },
  { clase: 'ReservarPrendaPage',       metodos: ['elegirPrenda', 'reservar', 'mostrarCodigo'] },
  { clase: 'CarritoPage',              metodos: ['agregarItem', 'calcularTotal', 'confirmarVenta', 'mostrarComprobante'] },
  { clase: 'PuntoVentaPage',           metodos: ['agregarItem', 'calcularTotal', 'confirmarVenta', 'mostrarComprobante'] },
  { clase: 'CambioPrendaPage',         metodos: ['buscarVenta', 'cambiar', 'mostrarComprobante'] },
  { clase: 'AnularOperacionDialog',    metodos: ['buscarOperacion', 'anular', 'mostrarAnulada'] },
  { clase: 'ModoOfflinePage',          metodos: ['abrirModoOffline', 'prepararOffline', 'mostrarDisponibles'] },
];

const SERVICIOS = [
  { clase: 'AuthService',          metodos: ['login', 'superLogin', 'logout'] },
  { clase: 'TenantsService',       metodos: ['crear', 'listar'] },
  { clase: 'UsuariosService',      metodos: ['listar', 'crear'] },
  { clase: 'SucursalesService',    metodos: ['listar', 'crear'] },
  { clase: 'SuscripcionesService', metodos: ['estado', 'contratar', 'cambiar', 'renovar'] },
  { clase: 'ProductosService',     metodos: ['listar', 'crear'] },
  { clase: 'CatalogosService',     metodos: ['listar', 'guardar'] },
  { clase: 'ProveedoresService',   metodos: ['listar', 'crear'] },
  { clase: 'ClientesService',      metodos: ['buscar', 'crear'] },
  { clase: 'InventarioService',    metodos: ['registrarMovimiento'] },
  { clase: 'ReservasService',      metodos: ['crearReserva'] },
  { clase: 'VentasService',        metodos: ['registrarVenta', 'anular'] },
  { clase: 'CambiosService',       metodos: ['obtenerVenta', 'registrarCambio'] },
  { clase: 'OfflineService',       metodos: ['descargarCatalogo'] },
  { clase: 'PwaService',           metodos: ['registrarServiceWorker', 'guardarRecursos', 'mostrarAppInstalada'] },
];

function listarArchivos(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...listarArchivos(p));
    else if (entry.isFile() && /\.(ts|html)$/.test(entry.name)) out.push(p);
  }
  return out;
}

function leerTodo() {
  const fuentes = listarArchivos(RAIZ);
  return fuentes.map((p) => ({ p, src: fs.readFileSync(p, 'utf8') }));
}

function encontrarClase(fuentes, clase) {
  const re = new RegExp(`class\\s+${clase}\\b`);
  return fuentes.find(({ src }) => re.test(src));
}

function cuerpoDeClase(fuentes, clase) {
  const archivoClase = encontrarClase(fuentes, clase);
  if (!archivoClase) return null;
  const idx = archivoClase.src.search(new RegExp(`class\\s+${clase}\\b`));
  const resto = archivoClase.src.slice(idx);
  const finSiguiente = resto.slice(1).search(/\nexport\s+class\s+\w/);
  const cuerpo = finSiguiente > 0 ? resto.slice(0, finSiguiente + 1) : resto;
  return { cuerpo, archivo: archivoClase.p };
}

function padreDe(cuerpo) {
  const m = cuerpo.match(/class\s+\w+\s+extends\s+(\w+)/);
  return m ? m[1] : null;
}

function encontrarMetodo(fuentes, clase, metodo, visitadas = new Set()) {
  if (visitadas.has(clase)) return null;
  visitadas.add(clase);
  const info = cuerpoDeClase(fuentes, clase);
  if (!info) return null;
  const reMetodo = new RegExp(`(?:async\\s+)?${metodo}\\s*\\(`);
  if (reMetodo.test(info.cuerpo)) return info.archivo;
  // Buscar en la clase padre (inheritance de un nivel + recursion acotada)
  const padre = padreDe(info.cuerpo);
  if (padre) return encontrarMetodo(fuentes, padre, metodo, visitadas);
  return null;
}

const fuentes = leerTodo();
let fallos = 0;
const faltantes = [];

function verificar(lista, titulo) {
  console.log(`\n== ${titulo} ==`);
  for (const { clase, metodos } of lista) {
    const archivo = encontrarClase(fuentes, clase);
    if (!archivo) {
      console.log(`  ❌ Falta la clase ${clase}`);
      faltantes.push(`clase ${clase}`);
      fallos++;
      continue;
    }
    const metodosFaltantes = metodos.filter((m) => !encontrarMetodo(fuentes, clase, m));
    if (metodosFaltantes.length === 0) {
      console.log(`  ✓ ${clase}  [${metodos.join(', ')}]`);
    } else {
      console.log(`  ❌ ${clase}  faltan: ${metodosFaltantes.join(', ')}  (archivo: ${path.relative(RAIZ, archivo.p)})`);
      metodosFaltantes.forEach((m) => faltantes.push(`${clase}.${m}`));
      fallos += metodosFaltantes.length;
    }
  }
}

verificar(CONTRATO, 'Contrato UML — pantallas y componentes');
verificar(SERVICIOS, 'Contrato UML — servicios');

console.log(`\nResumen: ${fallos === 0 ? '✓ todas las clases y metodos existen' : `❌ ${fallos} elementos faltantes`}`);
if (fallos > 0) {
  console.log('\nFaltantes:\n  - ' + faltantes.join('\n  - '));
  process.exit(1);
}
