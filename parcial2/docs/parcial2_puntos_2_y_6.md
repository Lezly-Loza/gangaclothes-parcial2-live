# Parcial 2 – Puntos 2, 4 y 6 (rama `feature/reportes-offline-poblar`)

Este documento acompaña los cambios de esta rama. Está pensado para la defensa
oral: cada afirmación tiene su archivo y línea.

## 1. Cambios incluidos en esta rama

| Archivo | Qué hace |
| --- | --- |
| `parcial2/backend/app/seeds/poblar_3_meses_sucursal.py` | Carga ~550 ventas confirmadas distribuidas en las 3 sucursales activas de Boutique Luna durante los últimos 95 días. Idempotente. |
| `parcial2/backend/app/modules/ventas/analitica.py` | Agrega `top_prendas_por_sucursal` al payload que `/api/v1/reportes/generativo` envía a Gemini, para que pueda responder consultas de ranking por sucursal. |
| `parcial2/backend/app/modules/ventas/router.py` | Corrección mínima: alias `require_tenant as require_auth` para que el backend arranque (había un import roto en `main` que impedía levantar el servidor). |

Pasos realizados en la DB local (`ganga_saas_local.db`):

```bash
cd parcial2/backend
DATABASE_URL="sqlite:///./ganga_saas_local.db" \
  .venv-run/Scripts/python -m app.seeds.poblar_3_meses_sucursal
# -> Ventas creadas: 552
```

Comprobación del reporte (modo `sin_modelo`, sin clave Gemini):

```
sucursales con top: 4
  Luna 7 Calles: 10 prendas, líder = Chaqueta denim
  Luna Centro:   4 prendas, líder = Camisa básica
  Luna Equipetrol: 10 prendas, líder = Blazer ejecutivo entallado
  Luna San Miguel: 10 prendas, líder = Cardigan tejido botones
```

---

## 2. Relación entre CU, diagrama de robustez, diagrama de secuencia y
### diagrama de clases dentro de ICONIX — usando el **CU-19 / CU-20 Catálogo
### offline y sincronización** como ejemplo

ICONIX es un proceso ligero que une análisis y diseño en una cadena de artefactos
donde **cada uno se deriva del anterior** y **todos tienen que ser consistentes**.
La relación es la siguiente, aplicada al CU elegido:

### 2.1 Caso de uso (CU-19 / CU-20)

*Actor:* Encargado / Cliente con sesión previa.
*Objetivo:* consultar y registrar operaciones (venta de contado o reserva) sin
conexión, y sincronizarlas al recuperar red.

Flujo básico (resumen, escrito con sustantivos y verbos del dominio):

1. El usuario, estando en línea, inicia sesión y descarga el catálogo de la
   sucursal elegida.
2. El sistema guarda el catálogo en el dispositivo (IndexedDB en web, SQLite
   en móvil).
3. El usuario pierde la red. Abre la pantalla *Catálogo sin conexión*.
4. El sistema muestra el catálogo guardado y permite registrar ventas o
   reservas, que quedan en estado `pendiente`.
5. El usuario recupera red. El sistema detecta el evento `online` y envía las
   operaciones pendientes al endpoint `/offline/sincronizar`.
6. El servidor confirma o rechaza cada operación (por stock o precio) y el
   cliente actualiza su estado local a `confirmada` o `conflicto`.

### 2.2 Diagrama de robustez (análisis)

El diagrama de robustez traduce las oraciones del CU a tres clases
estereotipadas, y es la **bisagra** entre análisis y diseño:

- **Boundary (frontera):** `ModoOfflinePage` (web, `features/offline/modo-offline.ts`)
  y `ModoOfflineScreen` (móvil, `mobile/lib/offline.dart`). Son las pantallas con
  las que interactúa el actor.
- **Control:** `OfflineService` (web, `services/offline.service.ts`) y
  `OperacionesOffline` + `Sincronizador` (móvil, `mobile/lib/operaciones_offline.dart`,
  `mobile/lib/sincronizador.dart`). Orquestan la cola local, la detección de
  reconexión y el llamado a la API.
- **Entity:** entidades del dominio: `CatalogoOffline`, `OperacionLocal`,
  `Venta`, `Reserva`, `Variante`, `Inventario`. Son los modelos que persisten
  tanto local (IndexedDB / SQLite) como en el servidor (SQLAlchemy).

Reglas de robustez que se respetan en el código:

- Un **boundary** no habla con **entity** directamente: siempre pasa por un
  **control** (`modo-offline.ts` nunca abre IndexedDB directamente; lo hace vía
  `OfflineService`).
- Un **control** puede llamar a otros controles y a entidades, pero no a
  boundaries (el sincronizador no toca la vista: emite señales/`Listener` que la
  vista consume).

### 2.3 Diagrama de secuencia (diseño detallado)

El diagrama de secuencia concreta el escenario del CU en mensajes temporales
entre instancias reales. Cada mensaje del diagrama se corresponde con una
llamada real en el código:

```
Usuario -> ModoOfflinePage : descargar selección
ModoOfflinePage -> OfflineService : descargarCatalogo(sucursal_id)
OfflineService -> API : GET /offline/catalogo
API -> OfflineService : CatalogoOffline
OfflineService -> IndexedDB : put(catalogos, copia)
Usuario -> ModoOfflinePage : registrar venta local (sin red)
ModoOfflinePage -> OfflineService : guardarOperacion(datos)
OfflineService -> IndexedDB : add(operaciones, OperacionLocal)
window event "online"
OfflineService -> API : POST /offline/sincronizar
API -> OfflineService : { codigo, confirmada_en } | 409 conflicto
OfflineService -> IndexedDB : put(operaciones, estado=confirmada|conflicto)
OfflineService -> ModoOfflinePage : revision++ (signal)
```

En el móvil el diagrama es equivalente, cambiando IndexedDB por `sqflite` y
`window.online` por el `Sincronizador` que escucha `connectivity_plus`.

### 2.4 Diagrama de clases (implementación)

Del diagrama de robustez salen las **candidatas a clase**; del de secuencia, los
**métodos** que debe tener cada una. Lo que termina implementado:

- `OfflineService` (web) con `descargarCatalogo`, `guardarCatalogoLocal`,
  `obtenerCatalogoLocal`, `guardarOperacion`, `sincronizar`, `sincronizarPendientes`.
- `OperacionLocal`, `CopiaOffline`, `CatalogoOffline` como *entities* locales
  (TypeScript interfaces y Dart classes).
- `Venta`, `DetalleVenta`, `Pago`, `Inventario`, `Sucursal` como entities del
  dominio en el backend (`app/models/negocio.py`, `app/models/tienda.py`).
- El endpoint `POST /offline/sincronizar` como *frontera* del lado servidor,
  delegando en el *control* `offline.service` del backend.

**La relación ICONIX, en una frase:** el CU describe *qué* pasa, el de robustez
descubre *quién* lo hace separando frontera/control/entidad, el de secuencia
define *cuándo* y *en qué orden* se envían los mensajes, y el de clases
documenta *cómo* se implementa cada uno de esos participantes. Un cambio en el
CU (p. ej. agregar "conflicto por precio") obliga a actualizar los tres
diagramas y la implementación, porque se derivan en cadena.

### 2.5 Cómo demostrarlo en vivo (web + móvil al mismo tiempo)

El problema que me contaste ("me decía que si o si debo tener conexión")
sucede porque `ng serve` corre en modo **dev**, donde el service worker
Angular está **desactivado** (`enabled: !isDevMode()` en
`parcial2/web/src/app/app.config.ts:17`). Hay que usar el build de producción:

**Terminal 1 – backend:**
```bash
cd parcial2/backend
DATABASE_URL="sqlite:///./ganga_saas_local.db" \
  .venv-run/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
(Escucha en `0.0.0.0` para que el emulador del celular lo alcance.)

**Terminal 2 – PWA web (producción):**
```bash
cd parcial2/web
npm run build -- --configuration production   # si ya existe `dist/`, se salta
.venv-run/Scripts/python scripts/servir_pwa.py # sirve en http://127.0.0.1:4300
```

**Terminal 3 – Móvil:**
```bash
cd parcial2/mobile
flutter run -d <android-id>        # o -d windows si es desktop
```

Luego:

1. En ambos clientes, inicia sesión **con red**:
   `admin@gangaclothes.com / Admin123` (empresa `luna`).
2. Ve a *Catálogo sin conexión* → elige sucursal (p. ej. **Luna Equipetrol**) →
   *Descargar selección*.
3. Apaga el Wi-Fi del PC y pon el móvil en modo avión.
4. En la web: registra una venta de contado. Queda en estado `pendiente`.
5. En el móvil, al mismo tiempo: registra una reserva. También queda
   `pendiente`.
6. Vuelve a encender la red. Ambos clientes detectan el evento `online` y
   sincronizan contra el backend. Cada operación obtiene su código (`VEN-...` o
   `RES-...`) o un conflicto si cambió el stock.

Ese flujo cubre, en una sola demostración, los cuatro diagramas ICONIX del
CU-19/CU-20.

---

## 2.6 Punto 4 — Venta de contado sin conexión: paso a paso

### a) Qué pasa cuando el cajero registra la venta (sin internet)

1. El cajero abre **Catálogo sin conexión** (web en `/offline` o pestaña
   *Sin conexión* del móvil). La pantalla funciona porque:
   - En web, el service worker Angular cachea la *shell* (ver
     `parcial2/web/ngsw-config.json` y `src/app/app.config.ts:16`).
   - En móvil, el shell está dentro del APK/EXE; no depende de red.
2. Elige variante, cantidad y escribe el efectivo recibido. Clic en
   **Guardar operación pendiente**.
3. Validaciones **locales** antes de persistir (todas corren sin servidor):
   - La copia local del catálogo debe seguir siendo la de esta sucursal
     y el precio de la variante no puede haber cambiado desde la descarga
     (`parcial2/web/src/app/services/offline.service.ts:117`).
   - La cantidad, entera entre 1 y 100 y descontando lo que ya consumen
     operaciones pendientes previas: `cantidad <= variante.stock - usados`
     (línea 124 del mismo archivo).
   - El efectivo recibido debe cubrir el total y tener como máximo dos
     decimales (`modo-offline.ts` líneas 110-115).
4. **Qué se guarda** (en IndexedDB `ganga-catalogos-offline`, store
   `operaciones`, clave `tenant:user:uuid`):

   ```jsonc
   {
     "uuid_operacion": "f3e5…",         // crypto.randomUUID() local
     "tipo": "venta",
     "sucursal_id": 4,
     "variante_id": 33,
     "cantidad": 1,
     "precio_unitario": 145.00,          // precio tal como estaba en la copia
     "monto_recibido": 150.00,
     "fecha_local": "2026-11-11T22:04:17.123Z",
     "estado": "pendiente",              // ← aún no confirmada
     "error": null, "codigo": null, "confirmada_en": null,
     "nombre": "Blusa seda satinada", "sku": "LUN-10-S-NE",
     "sucursal": "Luna Equipetrol",
     "cuenta": "1:8"                     // tenant_id:user_id
   }
   ```

   En móvil la misma información va en sqflite (tabla `operaciones_offline`
   en `mobile/lib/operaciones_offline.dart`). El UUID se genera local así
   que **la idempotencia se decide en el cliente**, no en el servidor.

### b) Cuando vuelve la conectividad

El `OfflineService` del web escucha dos eventos:

- `window.addEventListener('online', …)` — reconexión de red del SO.
- `document.visibilitychange` — cuando la pestaña vuelve a estar visible.

En cualquiera de los dos, si hay sesión activa dispara `sincronizarPendientes()`
(archivo `offline.service.ts:32-47`). Para cada operación en `pendiente`
hace **POST `/api/v1/offline/sincronizar`** con el payload de arriba.

El backend (`parcial2/backend/app/modules/offline/sincronizacion.py:35-134`)
hace la transacción atómica:

1. **Idempotencia** – si ya existe `OperacionLog` con ese `uuid_operacion`,
   devuelve el resultado previo marcado `repetida=True`. No duplica.
2. **Autorización** – la venta requiere rol distinto de cliente/proveedor y
   permiso `ventas:crear`.
3. **Reloj** – rechaza fechas adelantadas más de 5 minutos del servidor
   (previene fraudes de hora local).
4. **Sucursal viva** – `Sucursal.activo = True`.
5. **Variante y precio actuales** – la variante debe seguir publicada y el
   `precio_unitario` enviado debe coincidir con el precio actual (incluidas
   promociones aplicadas por `precio_promocional`). Si el precio cambió:
   `409 "El precio cambió: registrado Bs X, actual Bs Y"`.
6. **Efectivo suficiente** – `monto_recibido >= precio * cantidad`.
7. **Stock con bloqueo** – `SELECT … FOR UPDATE` sobre `Inventario`. Si
   `stock - reservado < cantidad`: `409 "Stock insuficiente: quedan N
   unidades"`.
8. Si todo pasa, crea la `Venta`, su `DetalleVenta`, el `Pago`
   (`metodo=EFECTIVO`) y descuenta el `Inventario`. Devuelve
   `{codigo:"V-XXXX", estado:"CONFIRMADA", confirmada_en}`.

El cliente marca la operación local según la respuesta
(`offline.service.ts:163-177`):
- **200** → `estado='confirmada'` + código y hora. Aparece el toast
  "Venta confirmada: V-99BF84…".
- **403/409/422** → `estado='conflicto'` + `error = detail` del backend.
  Aparece el toast "Venta no confirmada: {motivo}".
- Otros errores de red → queda `pendiente` y se reintenta en el próximo
  `online`/`visibilitychange`.

### c) Dos cajeros venden el mismo stock sin red — qué pasa a cada uno

Escenario real que probé con `TestClient` contra la DB local:
- Stock inicial de una variante: 11 unidades.
- Cajero A: sin red, registra venta de **11** (todo el stock).
- Cajero B: sin red, registra venta de **1** del mismo ítem.
- Reconexión de ambos, en ese orden:

| Cajero | HTTP | Resultado local |
| --- | --- | --- |
| A (sincroniza primero) | 200 | `confirmada`, código `V-99BF84C99E`, toast verde. |
| B (sincroniza después) | 409 `"Stock insuficiente: quedan 0 unidades en la sucursal"` | `conflicto`, banner rojo "Pago rechazado: Stock insuficiente. Esta operación quedó registrada localmente como rechazada. Si cobraste efectivo al cliente, devolvelo o bien registrá una nueva operación…" |

Es decir: **solo una se materializa**. La otra queda **registrada en el
dispositivo** como rechazada con la causa exacta del backend, visible al
cajero. No se duplica stock, no se duplica ingreso.

### d) Dónde ver/probar la demostración

- Pantalla: http://127.0.0.1:4300/offline (misma ruta en móvil).
- Botones habilitados: *Descargar selección* → simular red cortada → *Guardar
  operación pendiente* → restaurar red → *Sincronizar pendientes*.
- UI de conflicto: `parcial2/web/src/app/features/offline/modo-offline.ts`
  (bloque `article.conflicto` con badge rojo "Pago rechazado").
- Regla del servidor: `parcial2/backend/app/modules/offline/sincronizacion.py:99-103`.

---

## 3. Punto 6 — Reportes generativos: "Mostrar los 10 productos más vendidos
### durante los últimos 3 meses agrupados por sucursal"

### 3.1 Cómo interpreta el sistema la solicitud

El flujo completo, extremo a extremo:

1. **Frontend (web o móvil)** – pantalla *Reporte generativo*:
   - Archivo: `parcial2/web/src/app/features/reportes/reporte-generativo.ts`.
   - El administrador escribe o dicta la pregunta. Si usa voz, la convierte a
     texto con la API `webkitSpeechRecognition` del navegador (español Bolivia,
     `es-BO`).
   - Al pulsar *Generar reporte* envía `{ pregunta, desde, hasta, sucursal_id }`
     a `POST /api/v1/reportes/generativo`. **El texto de la pregunta nunca se
     interpreta en el navegador**: solo se adjunta al payload. La selección de
     fechas y sucursal se toma de los filtros de pantalla.

2. **Backend** – `POST /api/v1/reportes/generativo`
   (`parcial2/backend/app/modules/ventas/analitica.py:155`).
   El sistema **no hace parsing semántico del lenguaje natural**: usa el período
   explícito del body (si el usuario escribió "últimos 3 meses" sin mover los
   filtros, ese rango ya viene como `desde = hasta - 29 días` por defecto, y
   debería ajustarse desde la pantalla). Para la pregunta real que pediste, el
   frontend envía `desde = hasta - 90 días`.

3. **Agregados determinísticos** – el backend calcula los **datos del período**
   antes de contactar al modelo (función `reportes._datos` +
   `reportes._inventario`, y la nueva función `_top_por_sucursal` de
   `analitica.py`). El payload que se arma incluye:

   ```jsonc
   {
     "periodo":   { "desde": "2026-08-13", "hasta": "2026-11-11" },
     "ventas":    { "ventas": 536, "unidades": 882, "total": 171089.0, ... },
     "inventario":{ "unidades": 4141, "bajo_minimo": 0, ... },
     "por_dia":        [...],
     "por_sucursal":   [...],
     "por_canal":      [...],
     "top_prendas_por_sucursal": [
       { "sucursal": "Luna Equipetrol",
         "top": [ { "prenda": "Blazer ejecutivo entallado", "unidades": 66, ... }, ... 10 ] },
       { "sucursal": "Luna San Miguel", ... },
       { "sucursal": "Luna 7 Calles", ... }
     ]
   }
   ```

   Esta **tabla pre-calculada** es la pieza clave: el modelo no inventa el
   ranking, lo redacta a partir de los números reales del tenant.

4. **Llamado a Gemini** – `_generar_gemini` arma un `systemInstruction` estricto
   (`"Redacta en español un reporte breve basado exclusivamente en los datos
   dados. No inventes cifras ni causas. Si faltan datos, dilo."`) y envía
   `{ pregunta, datos }` a `generativelanguage.googleapis.com` con `temperature
   = 0.2`. Se itera sobre varios modelos (`gemini-2.5-flash`, `gemini-2.0-flash`,
   `gemini-1.5-flash`) hasta que uno responda.

5. **Respuesta** – el servidor devuelve `{ modo: 'gemini', respuesta, datos }`.
   El frontend muestra el texto del modelo y, abajo, el gráfico de ventas
   diarias construido con `datos.por_dia`. Si no hay clave o la API falla, cae
   a `modo: 'sin_modelo'` y devuelve un resumen determinístico ("Del … al …:
   N ventas por Bs …").

### 3.2 Cómo se **obtiene** la respuesta ante "top 10 agrupados por sucursal"

Con los datos ya poblados (ver §1):

- `GET /api/v1/reportes/dashboard?desde=…&hasta=…` — expone `top_prendas`
  global (no agrupado).
- `POST /api/v1/reportes/generativo` — incluye ahora `top_prendas_por_sucursal`
  en `datos`. Con clave Gemini, la respuesta en lenguaje natural describe los
  rankings por sucursal; sin clave, los datos siguen estando disponibles para la
  UI (la pantalla puede listarlos aunque Gemini no responda).

Ejemplo real de los **datos** (ya verificado contra la DB local):

```
Luna Equipetrol – líder: Blazer ejecutivo entallado (66 u, Bs 19 140)
Luna San Miguel – líder: Cardigan tejido botones (59 u, Bs 11 505)
Luna 7 Calles  – líder: Chaqueta denim (36 u, Bs 4 269)
Luna Centro    – (solo 4 ventas de demo histórica, para contraste)
```

### 3.3 Qué no hace el módulo (importante para la defensa)

- No usa RAG ni embeddings: la empresa es una tienda, no un corpus.
- No ejecuta SQL que venga del modelo: el SQL lo escribe el backend y el modelo
  **solo redacta**.
- No manda nombres de clientes ni comprobantes individuales a Google: el
  payload son agregados por día, por sucursal, por canal y por prenda.

---

## 4. Checklist antes del merge

- [ ] Correr `python -m app.seeds.poblar_3_meses_sucursal` **una vez** en la
      base que se vaya a demostrar.
- [ ] Comprobar en Swagger (`http://127.0.0.1:8001/docs`) que
      `/reportes/generativo` responde 200 con `top_prendas_por_sucursal`.
- [ ] Hacer el build de producción de la web antes de la demo para que la PWA
      funcione offline: `npm run build -- --configuration production`.
- [ ] Tener la clave `GEMINI_API` en `.env` para que la respuesta salga en
      lenguaje natural; sin ella sale el modo determinístico.
