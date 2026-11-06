# Tarea para Claude Code: volver a la interfaz del parcial 1 en `parcial2/web`, con los CU del parcial 2

## Objetivo

La interfaz actual de `parcial2/web` es una barra superior con formularios sueltos. Quiero que vuelva a verse y sentirse como la web del parcial 1 (`GangaClothes/web`, desplegada en https://ganga-clothes.vercel.app, por ejemplo `/admin/reportes`), pero con los casos de uso, la API y los nombres del parcial 2.

Trabaja sin pedirme confirmación en cada paso. Solo pregúntame antes de borrar algo que esté fuera de `parcial2/web`.

## 1. Qué hay en el repo (léelo primero)

### Interfaz del parcial 1, la referencia de diseño: `GangaClothes/web/`

- Angular standalone con signals y control flow `@if`/`@for`. El CSS es propio, sin Material.
- `src/styles.css`: el sistema visual. Variables `--papel #f2f2ed`, `--tinta #14161a`, `--ganga #e8175d`, `--ok`, `--alerta`, `--linea`, `--gris`, `--suave`, `--mono` y `--sans`, más las clases `.logo`, `.ceja`, `.mono`, `.btn`, `.btn.linea`, tarjetas, tablas y chips.
- `src/app/features/admin/shell.(ts|html|css)` y `menu.ts`: panel con barra lateral oscura ("Ganga**Clothes** · panel interno"), menú agrupado por secciones y filtrado por rol, y barra superior con "nombre · rol" y el botón "Cerrar sesion".
- `src/app/shared/`: `crud/` (lista + formulario genérico con `config.ts`), `avisos/`, `estado/` (chips de estado), `formato.ts` (montos en Bs y fechas), `comprobante.ts`, `graficos/` (`barras-h`, `serie-dias`), `sucursal/selector-sucursal.ts`, `tienda/barra-tienda.ts`.
- `src/app/core/`: `auth.service`, `sesion`, `jwt.interceptor`, `errores.interceptor`, `notificaciones`.
- Pantallas que sirven de modelo:
  - `features/auth/login`.
  - `features/admin/usuarios`, `prendas`, `inicio` y `catalogos`.
  - `features/inventario/inventario` y `movimientos`.
  - `features/caja`: "Caja · Sucursal …", con la búsqueda por SKU a la izquierda y el ticket a la derecha (métodos Efectivo / Tarjeta / QR y botón "Cobrar Bs").
  - `features/reportes/dashboard` (tarjetas KPI).
  - `features/catalogo` y `features/tienda/*` (la tienda del cliente: catálogo, carrito y mis reservas).

### Web actual del parcial 2, la que se rehace: `parcial2/web/`

- Angular 19, generada por Codex.
- Todas las pantallas están en `src/app/screens.ts` y el menú en `src/app/app.component.ts`.
- Los servicios HTTP están en `src/app/services/*.ts`.
- La PWA (`ngsw-config.json`, manifest, `provideServiceWorker`) y el almacenamiento offline con `idb` ya funcionan.
- El script de capturas es `parcial2/docs/capturas/capturar_web.ts`.

### Backend

- `parcial2/backend` (FastAPI). No cambies nombres ni rutas.
- Si una pantalla necesita un endpoint de solo lectura que no existe (por ejemplo, listar ventas o reservas), puedes agregarlo en su módulo sin tocar lo existente. Avísame en el resumen.
- Los usuarios de prueba están en `backend/app/seeds/demo.py`: superadmin `root@plataforma.bo` / `SuperSegura123`; tenant `luna` con admin `ana@boutique-luna.bo`, encargado, vendedor y cliente, todos con clave `Luna12345`.

## 2. Regla más importante: no romper los nombres de los diagramas UML

La docente revisa que los nombres de los diagramas de comunicación y secuencia existan en el código.

- **Lo que sí puedes hacer:**
  - Mover cada componente a su propia carpeta `features/...`, con archivos `.ts`, `.html` y `.css` separados.
  - Agregar métodos, inputs y signals.
  - Cambiar el diseño de las plantillas.
- **Lo que NO puedes hacer:**
  - Renombrar ni quitar estas clases ni sus métodos públicos.
  - Cambiar los nombres de los métodos de los servicios.

| Clase | Métodos que deben seguir existiendo y usarse |
|---|---|
| `LoginPage` | `entrar()` |
| `RegistrarEmpresaForm`, `EmpresasList` | `listar()`, `registrarEmpresa(datos)` |
| `UsuariosList`, `UsuarioForm` | `listar()`, `crear()` |
| `SucursalesList`, `SucursalForm` | `listar()`, `nuevaSucursal(...)`, `crearSucursal(datos)`, `mostrarConfirmacion()` |
| `ContratarPlanForm` | `elegirPlan(codigo, duracion_dias)`, `contratarPlan(dto)`, `mostrarResumen()` |
| `MiSuscripcion`, `CambiarPlanDialog` | `verMiSuscripcion()`, `cambiarPlan(plan_codigo)`, `mostrarNuevoPlan()` |
| `ProductosList`, `ProductoForm` | `listar()`, `crear()` |
| `CatalogosPage` | `listar()`, `guardar()` |
| `ProveedoresList`, `ProveedorForm` | `listar()`, `crear()` |
| `ClientesList`, `ClienteForm` | `buscar()`, `crear()` |
| `InventarioPage`, `MovimientoForm` | `abrirInventario()`, `registrarMovimiento(variante, tipo, cantidad, motivo)`, `mostrarStock()` |
| `AvisoInstalacionComponent` | `abrirAplicacion()`, `instalarApp()`, `mostrarAppInstalada()` |
| `ReservarPrendaPage` | `elegirPrenda()`, `reservar(datos)`, `mostrarCodigo()` |
| `CarritoPage`, `PuntoVentaPage` | `agregarItem(variante, cantidad)`, `calcularTotal()`, `confirmarVenta(cliente_id, forma_pago)`, `mostrarComprobante()` |
| `CambioPrendaPage` | `buscarVenta(codigo)`, `cambiar(item, variante_nueva, motivo)`, `mostrarComprobante()` |
| `AnularOperacionDialog` | `buscarOperacion()`, `anular(venta_id, motivo)`, `mostrarAnulada()` |
| `ModoOfflinePage` | `abrirModoOffline()`, `prepararOffline(categorias, temporada)`, `mostrarDisponibles()` |
| Servicios en `services/*.ts` | Todos sus métodos actuales, por ejemplo `suscripciones.estado/contratar/cambiar/renovar`, `ventas.registrarVenta/anular`, `inventario.registrarMovimiento`, `cambios.obtenerVenta/registrarCambio`, `reservas.crearReserva`, `offline.descargarCatalogo` y `pwa.registrarServiceWorker/guardarRecursos/mostrarAppInstalada` |

Al terminar, crea `parcial2/web/scripts/verificar_contrato.mjs`.
- El script busca cada clase y cada método de esta tabla dentro de `src/` y falla si falta alguno.
- Córrelo y muéstrame el resultado.

## 3. Diseño a reproducir

1. **Estilos:** copia `GangaClothes/web/src/styles.css` como base de `parcial2/web/src/styles.css`. Quita Angular Material de `parcial2/web` si ya no se usa.
   - Mantén la versión de Angular 19.
   - Si algo copiado del parcial 1 usa una API más nueva, adáptalo en vez de actualizar Angular.
2. **Shell:** replica `features/admin/shell` y `menu.ts`.
   - Barra lateral oscura con "Ganga**Clothes**" y una ceja con "panel interno", o "plataforma" para el superadmin.
   - Grupos de menú filtrados por rol (`superadmin`, `admin`, `encargado`, `vendedor`).
   - Barra superior con: "nombre · rol", el tenant, un chip "En línea / Sin conexión", el botón "Instalar app" (CU-13, usa `AvisoInstalacionComponent`) y "Cerrar sesion".
3. **Menú del parcial 2** (rutas con prefijo `/admin`, como en el parcial 1):

   | Grupo | Ítems |
   |---|---|
   | Plataforma (superadmin) | Empresas (CU-01) |
   | General | Panel (KPIs: plan, días restantes y consumo de sucursales y usuarios, de `/suscripciones/estado`) |
   | Suscripción (admin) | Contratar plan (CU-05) · Mi suscripción (CU-07, con el diálogo Cambiar o renovar del CU-06) |
   | Seguridad (admin) | Usuarios y roles (CU-03) |
   | Red de tiendas (admin) | Sucursales (CU-04) |
   | Catálogos base (admin) | Categorías · Tallas · Colores · Temporadas (CU-09; los cuatro abren `CatalogosPage` con el tipo en la ruta) |
   | Productos (admin) | Prendas y variantes (CU-08) · Proveedores (CU-10) |
   | Operación | Inventario (CU-12, admin y encargado) · Caja (CU-15, admin y vendedor) · Cambios de prendas (CU-16, admin y vendedor) · Anular reserva o venta (CU-17, encargado) · Clientes (CU-11, admin y vendedor) · Modo offline (CU-18, vendedor) |

4. **Cliente:** el cliente NO usa el panel. Usa la tienda (`/tienda`) con el estilo de `features/catalogo` y `features/tienda` del parcial 1.
   - Catálogo en grilla con su foto o un placeholder, selección de talla y color, y sucursal.
   - Botón "Reservar" (CU-14, `ReservarPrendaPage`), que muestra el código de la reserva como en "mis-reservas".
   - Carrito y compra en línea (CU-15, `CarritoPage`).
5. **Pantallas, según su modelo del parcial 1:**

   | Pantalla | Cómo debe verse |
   |---|---|
   | Login | Como `features/auth/login`, con los campos Código de empresa, correo y contraseña, y un enlace "Soy superadministrador" que usa `/auth/super/login`. |
   | Listas con formulario (Empresas, Usuarios, Sucursales, Proveedores, Clientes, Productos, Catálogos) | Estilo `shared/crud` y `admin/usuarios`: tabla con encabezado ceja, chips de estado, botón "Nuevo" que abre el formulario lateral y búsqueda. Productos con sus variantes como en `admin/prendas`. |
   | Mi suscripción / Contratar plan | Tarjetas de plan (Básico, Profesional, Empresarial) con precio y límites, barras de consumo estilo `graficos/barras-h` y el diálogo de cambio de plan. Se muestran los mensajes 409 del backend (por ejemplo "El uso actual supera el plan elegido"). |
   | Inventario | Como `inventario/inventario` + `movimientos`: selector de sucursal, tabla por variante (SKU, talla, color, stock, reservado, mín/máx) y chip rojo cuando hay stock bajo el mínimo. Formulario de movimiento con selects de variante y tipo, nunca con IDs escritos a mano. |
   | Caja | Igual a `features/caja`: buscar por SKU o nombre a la izquierda, ticket a la derecha con total en Bs, métodos de pago (Efectivo → `EFECTIVO`; Tarjeta y QR → `EN_LINEA`), monto recibido y cambio, botón "Cobrar Bs …" y comprobante con `shared/comprobante.ts`. |
   | Cambios de prendas | Mismo estilo de caja: buscar la venta por código, ver sus líneas, elegir la prenda a devolver y la nueva variante, ver la diferencia y el comprobante. Muestra "Fuera de plazo" si el backend responde 409. |
   | Anular | Diálogo modal con el resumen de la venta o reserva y un motivo obligatorio. El estado queda ANULADA con su chip. |
   | Modo offline | Tarjeta KPI "N productos disponibles offline", fecha de la última descarga, filtros de categoría y temporada, y botón "Preparar modo offline". |

6. **Calidad:**
   - Nada de `location.reload()`: refresca las listas con signals.
   - Avisos (toasts) de éxito y error con `notificaciones` y `avisos` del parcial 1.
   - Montos con `formato.ts`.
   - Estados vacíos con texto ("Sin ventas todavía").
   - Mínimo responsive: la barra lateral se colapsa en pantallas angostas.
7. **PWA:** sigue funcionando. Manifest con nombre "GangaClothes", `theme_color #14161a`, íconos actuales, y `ngsw-config.json` incluyendo los nuevos assets.

## 4. Verificación y entrega

1. `cd parcial2/web && npm run build` sin errores.
2. Levanta el backend con el seed y la web. Recorre cada CU con el usuario de su rol y corrige lo que falle.
3. Corre `node scripts/verificar_contrato.mjs` (debe pasar).
4. Actualiza los selectores de `parcial2/docs/capturas/capturar_web.ts` y regenera las 18 capturas `_web` en `parcial2/docs/capturas/`, con datos del seed y sin pantallas vacías. No toques las `_movil`.
5. Muéstrame 3 capturas (Caja, Inventario y Mi suscripción) y un resumen: archivos creados o movidos, endpoints de lectura agregados (si hubo) y el resultado del verificador de contrato.
6. **Git:** no hagas commit. Nunca agregues `Co-Authored-By` ni "Generated with". No toques `GangaClothes/web` (es solo la referencia).
