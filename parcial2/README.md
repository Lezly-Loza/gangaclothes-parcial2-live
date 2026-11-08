# GangaSaaS — Parcial 2 SI2 · UAGRM

SaaS multitenant para tiendas de ropa. Esta carpeta reúne la interfaz del primer
parcial con las funciones nuevas de empresas y suscripciones del segundo.
Metodología ICONIX. Stack FastAPI + SQLAlchemy + PostgreSQL (SQLite local
por defecto) · Angular · Flutter.

## Estado de la integración

### Reportes por voz, analítica y respaldos programados

En **Reportes**, dicta o escribe una pregunta y genera el reporte: se muestra
una gráfica de las ventas reales del periodo seleccionado y se puede escuchar
la respuesta. El dictado usa el reconocimiento del navegador, necesita su
permiso de micrófono y puede requerir Internet; no todos los navegadores lo
admiten. En el asistente del negocio también se puede dictar. Gemini requiere
una clave `GEMINI_API` en el backend; sin ella se muestra un resumen de datos
reales, identificado como tal, que no interpreta libremente la pregunta.

En **Dashboard**, la predicción usa ventas pagadas de la empresa y sucursal
seleccionadas. Con al menos 21 días se compara la regresión lineal con un
promedio por día de semana, probando ambos en los últimos siete días antes de
entrenar el elegido sobre todo el periodo. Se muestra el error absoluto medio.
Es un pronóstico exploratorio, no una garantía; con poca historia puede no
estar disponible. El análisis no envía datos personales a Gemini.

En **Respaldos**, además de descargar una copia manual, cada empresa dispone
de una copia diaria a las 02:00 (hora de Bolivia) por defecto y puede cambiar
esa hora, desactivar el respaldo diario o programar una copia adicional en una
fecha concreta. Se guardan en `parcial2/backend/.respaldos/<empresa>/` (o el
directorio definido por `RESPALDOS_DIRECTORIO`); contienen datos privados y
deben protegerse y descargarse a otro dispositivo. La aplicación debe estar
encendida para ejecutar el programador, que revisa cada 30 segundos; si estuvo
apagada durante la hora programada, intenta crear la copia al arrancar. Se
recomienda ejecutar un único proceso servidor para evitar ejecuciones dobles.
Las operaciones offline no sincronizadas no se incluyen.

Las copias en el mismo disco no protegen contra una pérdida de ese disco. El
disco efímero del plan gratuito de Render tampoco garantiza conservarlas al
reiniciar o redesplegar y el servicio puede dormirse: **no es un respaldo
automático confiable en producción** sin almacenamiento externo persistente y
un programador que funcione aun con la aplicación dormida. No se ha conectado
ese servicio externo. La restauración disponible es en una base SQLite nueva
mediante la herramienta documentada abajo, no una restauración automática de
PostgreSQL.

Para trabajar en la versión integrada, inicia el backend y la web de esta
carpeta. La aplicación original de la raíz se conserva como referencia y usa
otra base de datos; sus datos no se han migrado automáticamente a `parcial2`.
No borres la versión anterior hasta comprobar y migrar los datos que necesites.

En el backend de `parcial2` están conectados empresas, planes y precios,
suscripciones, usuarios sin rol o con varios roles, permisos por empresa,
clientes, catálogos, prendas, variantes, inventario, movimientos, oferta de
proveedores, compras, recepción de stock, reservas de sucursal, caja en
efectivo, envíos registrados desde una venta pagada, dashboard, reportes, cambios y
anulación. La opción de instalar como PWA está habilitada en compilación de
producción; con `ng serve` no se instala el service worker.

El cliente puede reservar desde el catálogo, consultar y cancelar sus reservas,
agregar prendas al carrito y registrar una compra de prueba con retiro o envío.
El pago del carrito es siempre **simulado**, sin cobro real: la prueba sí registra
una venta, descuenta existencias y aparece en los reportes. Para un envío se pide
la dirección y las coordenadas, y la sucursal actualiza su estado; todavía no se
calculan distancia ni tarifa. Usa una base de prueba para ensayar estas acciones.

La caja solo admite efectivo por ahora; el comprobante se
puede imprimir desde el navegador. Para publicar oferta, el administrador debe
vincular el usuario con su proveedor al asignarle el rol de proveedor.
Los envíos se registran manualmente con el código de una venta pagada y las
coordenadas del destino; este registro no cobra una tarifa ni calcula distancia.
Los reportes incluyen solo prendas con costo registrado en los cálculos de
ganancia y valor a costo, utilizando el costo actual y no el histórico.
Las promociones vigentes se aplican en caja y quedan registradas en el detalle
de la venta; para ver precios nuevos en una copia offline, vuelve a descargarla.
La promoción ganadora es la que deja el menor precio; no se acumulan descuentos.

El registro de clientes solicita código de empresa y documento. Para probar
con la demo existente usa empresa `luna`, correo `cliente@boutique-luna.bo` y
contraseña `Luna12345`. Al entrar abre «Catálogo sin conexión»: elige sucursal,
categoría y temporada, y descarga la selección. La copia queda en IndexedDB,
separada por empresa y cuenta, y muestra precios y existencias del momento de
la descarga. También permite guardar reservas y ventas de contado pendientes
para sincronizarlas al recuperar la conexión. Para abrir
la app tras cerrar el navegador sin internet se requiere una compilación PWA
de producción instalada y abierta previamente con conexión; `ng serve` no
registra el service worker.

En «Cambios de prendas» y «Anular operación» se puede seleccionar una venta o
reserva reciente. El código de venta también figura en el comprobante de caja
y en el motivo del movimiento de inventario; el de reserva aparece en su
confirmación. Un cambio está sujeto al plazo configurado de la empresa.
El catálogo web muestra las prendas publicadas y disponibles de la empresa
de la sesión; es necesario iniciar sesión para identificar esa empresa.
Los pagos en línea sin clave de Stripe se simulan; incluso
con clave solo se acepta el modo de prueba. No son cobros reales.

Los módulos elegidos en el plan son actualmente descriptivos: el acceso se
controla por permisos del usuario y los límites de sucursales, usuarios y
productos sí se verifican en el backend. Sucursales y ciudades se administran
en Red de tiendas; el límite de sucursales corresponde al plan contratado.

Las pruebas de interfaz `web/scripts/probar_integracion.mjs` usan una API y una
base de demostración separadas en el puerto 8012; requieren Angular en 4200.
No usan ni reinician la base normal de la aplicación.

### Inicio rápido en PowerShell

En una terminal, desde la raíz del repositorio:

```powershell
cd parcial2/backend
.\.venv-run\Scripts\python.exe -m uvicorn app.main:app --reload
```

En otra terminal:

```powershell
cd parcial2/web
npm start
```

Abre `http://localhost:4200`. Si es una instalación nueva, consulta las
instrucciones de instalación de la sección 4 y crea la demo con
`python -m app.seeds.demo`. Evita volver a sembrar o borrar tu base si contiene
datos que quieras conservar. Cierra sesión y vuelve a entrar para actualizar
los permisos guardados por la interfaz después de una modificación de roles.

## 1. Cómo se garantiza el aislamiento entre tenants

Esquema compartido con discriminador `tenant_id`. El aislamiento se aplica
**en el motor del ORM**, no en cada consulta:


- `TenantMixin` ([backend/app/core/database.py:22](backend/app/core/database.py#L22))
  marca los modelos que tienen `tenant_id`. Lo heredan: `User`, `Sucursal`,
  `Suscripcion`, `OperacionLog`.
- Un listener de SQLAlchemy sobre `do_orm_execute`
  ([backend/app/core/database.py:46](backend/app/core/database.py#L46))
  intercepta todo `SELECT`, `UPDATE` y `DELETE` del ORM y le mete, vía
  `with_loader_criteria`, un `WHERE tenant_id = scope.tenant_id`.
- El `tenant_id` sale del JWT en
  [backend/app/core/deps.py](backend/app/core/deps.py) y queda guardado en
  `session.info["tenant_scope"]` antes de ejecutar la query.
- El superadmin (`kind="super"`) no tiene `tenant_id` y el filtro **no se
  aplica** — opera por encima de todas las empresas.
- Todas las UNIQUE son por tenant: `UNIQUE(tenant_id, email)`,
  `UNIQUE(tenant_id, codigo)`, `UNIQUE(tenant_id, uuid_operacion)`. Nunca
  globales (excepto NIT del propio tenant y email del superadmin).

**Por qué "imposible por diseño"**: olvidarse del filtro en un servicio no
tiene efecto. El filtro no vive en el servicio, vive en la ejecución del
ORM. Para saltearlo habría que usar SQL en crudo o entrar sin JWT —
cualquiera de las dos deja huella y no pasa por la capa normal.

## 2. Cómo se identifica el tenant al iniciar sesión (CU-02)

**Decisión**: `codigo_tenant` + `email` + `password` en el formulario de
login (`POST /api/v1/auth/login`).

Comparación:

| Opción | Pro | Contra |
|---|---|---|
| **Código de tenant en el form** ✅ | Explícito, se defiende en vivo. No necesita infra extra. Permite que **el mismo correo** exista en dos empresas distintas. | Un campo más en el form. |
| Subdominio (`luna.saas.com`) | Elegante, "SaaS clásico". | Exige DNS + wildcard + reverse proxy local. En una demo rompe más que ayuda. |
| Correo globalmente único | Un solo campo, muy limpio. | Rompe la premisa real: Ana puede trabajar en Boutique Luna y además en Moda Andina — y en multitenant se asume que un correo pertenece a una empresa, no al SaaS. |

El superadministrador se autentica aparte en `POST /api/v1/auth/super/login`,
sin tenant.

## 3. Arquitectura por módulos

```
backend/app/
├── core/
│   ├── config.py        settings (DATABASE_URL, JWT, CORS)
│   ├── database.py      engine, Base, TenantMixin, listener multitenant
│   ├── security.py      bcrypt + JWT
│   └── deps.py          get_db, get_scope, require_super, require_tenant, require_roles
├── models/              Tenant, Plan, Suscripcion, User, SuperAdmin, Sucursal, OperacionLog
├── modules/
│   ├── tenants/         CU-01 (super crea empresa + admin + plan)
│   ├── auth/            CU-02 (login tenant/super + /me)
│   ├── sucursales/      CU-04 (CRUD + rechazo por límite)
│   ├── planes/          catálogo público (autenticado)
│   └── suscripciones/   CU-05 contratar + CU-07 estado y consumo
└── seeds/demo.py        2 empresas + 3 planes + superadmin
```

## 4. Correr en local

```bash
cd parcial2/backend
python -m venv .venv
.venv\Scripts\activate         # Windows PowerShell
pip install -r requirements.txt
python -m app.seeds.demo       # crea tablas y semillas
uvicorn app.main:app --reload  # http://127.0.0.1:8000/docs
```

Config por variables de entorno (opcional):

```
DATABASE_URL=postgresql+psycopg2://user:pass@host/db  # dev local usa sqlite
JWT_SECRET=algo-largo-y-aleatorio
CORS_ORIGINS=http://localhost:4200,http://localhost:5173
```

## 5. Credenciales de la demo

- **Superadmin**: `root@plataforma.bo` / `SuperSegura123`
- **Tenant `luna`** (plan Profesional): admin `ana@boutique-luna.bo` / `Luna12345`
- **Tenant `andina`** (plan Básico, 1 sucursal máx.): admin `rodrigo@modaandina.bo` / `Andina12345`

## 6. Verificación de los cimientos (lo que se enseña en vivo)

1. **Registrar un tenant** — super hace `POST /api/v1/tenants` con razón
   social, NIT, código, admin inicial y `plan_codigo="profesional"`.
2. **Aislamiento** — login en `luna` y en `andina`:
   `GET /api/v1/sucursales` devuelve **solo las propias**; pedir por id una
   sucursal del otro tenant devuelve **404** (no 403 — ni enteramos de que
   el id existe en otra empresa).
3. **Estado y consumo** — `GET /api/v1/suscripciones/estado` del tenant
   muestra `plan`, `fecha_fin` y `consumos: [{recurso:"sucursales",
   actual:2, limite:3, disponible:1}, ...]`.
4. **Rechazo por límite** — con el plan Básico (1 sucursal), crear una
   segunda sucursal responde `409 CONFLICT` con mensaje:
   `"Limite alcanzado para sucursales: 1 de 1 segun el plan 'Basico'.
   Contrata un plan superior para seguir dando de alta sucursales."`
5. **Superadmin** — `GET /api/v1/tenants` lista todas las empresas con su
   plan vigente y fecha de fin.

## 7. Operación sin conexión y reportes analíticos (CU-19 a CU-26)

En web y móvil inicia sesión con conexión y abre **Catálogo sin conexión**.
Elige una sucursal y descarga la selección antes de desconectarte. El catálogo
guardado muestra los precios y existencias de la descarga. Una cuenta de cliente
puede registrar una reserva local y el personal con permiso de venta puede
registrar una venta de contado con efectivo recibido. Cada operación contiene
una sola variante; para otra variante se registra otra operación.

Las operaciones se guardan por empresa y cuenta en el dispositivo, aparecen en
**Operaciones locales** y no están confirmadas hasta sincronizar. Si la pantalla
offline está abierta, la web intenta sincronizar cuando vuelve la conexión; en ambas plataformas se puede usar el
botón **Sincronizar pendientes**. Si se pierde la respuesta, reintenta con el
mismo identificador: el backend evita duplicados. El servidor revisa permisos,
stock y precio; si cambian, la operación queda en conflicto. Revisa el efectivo
con el cliente, descarta el conflicto y vuelve a descargar antes de crear otra
operación. Los pendientes no se pueden descartar si su resultado es incierto.
Vuelve a iniciar sesión con la misma cuenta si el token ha vencido.
Las ventas sincronizadas usan en los reportes la fecha indicada por el reloj del
dispositivo al registrar el cobro; el servidor conserva también la fecha de
sincronización y rechaza relojes adelantados más de cinco minutos.

El stock local solo orienta: otros dispositivos pueden vender o reservar las
mismas unidades y provocar conflictos. Una operación confirmada sigue descontada
de la copia antigua hasta volver a descargarla. Borrar datos del navegador o de
la app antes de sincronizar también borra sus operaciones locales; no son una
copia de seguridad. Para abrir la web desconectada debe usarse la PWA de
producción, instalada y abierta previamente con conexión; `ng serve` no instala
el service worker. El móvil guarda estos datos sin cifrado adicional.

Para probar la PWA local en PowerShell, con el backend de `parcial2` ya iniciado:

```powershell
cd parcial2/web
npm run build -- --configuration production
..\backend\.venv-run\Scripts\python.exe scripts/servir_pwa.py
```

Abre `http://127.0.0.1:4300`, inicia sesión y descarga el catálogo antes de
desconectarte. Ese servidor es solo para pruebas en la computadora.

Los reportes convencionales permiten filtrar y exportar CSV o imprimir PDF. En
**Reportes** puedes escribir o dictar una consulta: Gemini recibe la pregunta y
datos agregados de la empresa, sin enviar datos personales de clientes. Utiliza
`GEMINI_API` del entorno o del `.env` de `parcial2/backend`; si falta, intenta
reutilizar la clave del `.env` del backend del primer parcial. Si el servicio o
la clave falla, se identifica el resultado como resumen sin modelo. El dictado
depende del navegador y de su servicio de reconocimiento de voz.

El dashboard calcula un pronóstico exploratorio por regresión lineal y agrupa
clientes con K-means usando recencia, frecuencia y monto. La pantalla indica
cuando faltan datos y muestra el error retrospectivo cuando hay historia
suficiente. Son estimaciones, no garantías; las ventas de prueba registradas
también forman parte de los reportes.

## 8. Reparto de CUs

Ver [docs/Reparto.md](docs/Reparto.md).

---

## 9. Guía para la compañera — ponerlo en tu compu y consumir la API

Esta sección es la que te deja arrancar de cero sin preguntarle nada a Ariany.

### 9.1 Prerrequisitos

- **Python 3.12** (3.11 también anda) — [python.org/downloads](https://www.python.org/downloads/).
- **Git** — [git-scm.com/downloads](https://git-scm.com/downloads).
- Un editor cualquiera (VS Code, PyCharm…).

Verificar en consola:

```bash
python --version   # Python 3.12.x
git --version
```

### 9.2 Clonar el repo y cambiar a la rama

El backend vive **dentro del repo GangaClothes**, en la carpeta `parcial2/`,
en la rama `ariany-ciclo`.

```bash
git clone https://github.com/ary10220/GangaClothes.git
cd GangaClothes
git fetch origin
git checkout ariany-ciclo
cd parcial2/backend
```

Cuando Ariany haga nuevos cambios, tirar:

```bash
git pull origin ariany-ciclo
```

### 9.3 Levantar el backend en tu máquina

```bash
# 1) Virtualenv aislado para no mezclar paquetes
python -m venv .venv
.venv\Scripts\activate         # Windows PowerShell
# source .venv/bin/activate    # Linux/Mac

# 2) Dependencias
pip install -r requirements.txt

# 3) Crear tablas + semillas (2 empresas, 3 planes, superadmin)
python -m app.seeds.demo

# 4) Levantar la API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El `--host 0.0.0.0` es importante: deja que tu **móvil físico** o un
emulador vean la API. Si solo vas a probar desde el navegador en la misma
compu, podés dejar `--host 127.0.0.1`.

**Comprobación**: abrir [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
→ aparece Swagger con todos los endpoints. Clickeá "Try it out" en
`POST /api/v1/auth/login` y mandá el body de ejemplo de 9.6.

### 9.4 Cómo conectar tu app a esta API

**Base URL**: todas las rutas cuelgan de `/api/v1/`. La URL completa
depende de desde dónde consumas:

| Cliente | Base URL |
|---|---|
| Angular en la misma PC (`ng serve`) | `http://localhost:8000/api/v1` |
| Flutter — emulador Android | `http://10.0.2.2:8000/api/v1` (el emulador mapea `10.0.2.2` → tu PC) |
| Flutter — emulador iOS | `http://localhost:8000/api/v1` |
| Flutter — móvil físico en la misma Wi-Fi | `http://<IP-LAN-de-tu-PC>:8000/api/v1` (buscar con `ipconfig`) |

**CORS**: por defecto el backend acepta `*`. Si querés restringir, levantalo así:

```bash
set CORS_ORIGINS=http://localhost:4200,http://localhost:5173
uvicorn app.main:app --reload --host 0.0.0.0
```

### 9.5 Autenticación — qué guardar y qué mandar

1. El cliente hace `POST /api/v1/auth/login` con `codigo_tenant`, `email` y `password`.
2. La respuesta trae `access_token` (JWT). **Lo guardás** (localStorage / secure storage).
3. En cada request posterior mandás el header:

   ```
   Authorization: Bearer <access_token>
   ```

4. Si el server responde `401`, el token venció o es inválido → mandás al login.

El token expira a las **8 horas** (configurable con `JWT_EXP_MINUTES`).

### 9.6 Ejemplos de request/response

**Login como tenant** — `POST /api/v1/auth/login`

```json
// Request
{
  "codigo_tenant": "luna",
  "email": "ana@boutique-luna.bo",
  "password": "Luna12345"
}
// Response 200
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
  "token_type": "bearer",
  "kind": "tenant",
  "tenant_id": 1,
  "tenant_codigo": "luna",
  "user_id": 1,
  "nombre": "Ana Luna",
  "roles": ["admin"]
}
```

**Login como superadmin** — `POST /api/v1/auth/super/login`

```json
{ "email": "root@plataforma.bo", "password": "SuperSegura123" }
```

**Quién soy** — `GET /api/v1/auth/me` (header con Bearer)

**Listar sucursales del tenant logueado** — `GET /api/v1/sucursales`

```json
// Response 200
[
  { "id": 1, "codigo": "suc-01", "nombre": "Luna Centro", "ciudad": "Santa Cruz",
    "direccion": "Av. Monseñor Rivero 123", "horario": "10:00-20:00",
    "estado": "activa", "activo": true, "created_at": "2026-10-23T18:30:00Z" }
]
```

**Crear sucursal** — `POST /api/v1/sucursales` (rol `admin`)

```json
{ "codigo": "suc-02", "nombre": "Luna Equipetrol", "ciudad": "Santa Cruz",
  "direccion": "Av. San Martin 500", "horario": "10:00-22:00" }
```

**Estado y consumo del plan (CU-07)** — `GET /api/v1/suscripciones/estado`

```json
{
  "tiene_suscripcion": true,
  "plan": { "codigo": "profesional", "nombre": "Profesional",
            "max_sucursales": 3, "max_usuarios": 10, "max_productos": 1000,
            "modulos": ["ventas","inventario","reportes","promociones"],
            "precio_mensual": 49.0, "activo": true },
  "fecha_inicio": "2026-10-23", "fecha_fin": "2026-11-22", "estado": "activa",
  "consumos": [
    { "recurso": "sucursales", "actual": 2, "limite": 3, "disponible": 1 },
    { "recurso": "usuarios",   "actual": 2, "limite": 10, "disponible": 8 }
  ],
  "modulos_habilitados": ["ventas","inventario","reportes","promociones"]
}
```

**Contratar un plan (CU-05)** — `POST /api/v1/suscripciones/contratar` (rol `admin`)

```json
{ "plan_codigo": "empresarial", "duracion_dias": 30 }
```

**Catálogo de planes** — `GET /api/v1/planes` → útil para armar el combo
de "contratar plan" en pantalla.

**Flujo completo con curl**:

```bash
# 1) Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"codigo_tenant":"luna","email":"ana@boutique-luna.bo","password":"Luna12345"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2) Pedir las sucursales con el token
curl http://localhost:8000/api/v1/sucursales -H "Authorization: Bearer $TOKEN"

# 3) Estado del plan
curl http://localhost:8000/api/v1/suscripciones/estado -H "Authorization: Bearer $TOKEN"
```

### 9.7 Códigos de error que tu UI debe manejar

| Código | Qué pasó | Qué mostrar al usuario |
|---|---|---|
| **401** | Sin token, token malo o vencido | "Tu sesión expiró, iniciá sesión de nuevo." → al login |
| **403** | Rol insuficiente (ej. `encargado` creando sucursal) | "No tenés permiso para esta acción." |
| **404** | Recurso inexistente **o de otro tenant** | "No se encontró el recurso." (no decir "es de otra empresa") |
| **409** | Conflicto de negocio — **lo más importante**: límite del plan superado | Mostrar `detail` tal cual: `"Limite alcanzado para sucursales: 1 de 1 segun el plan 'Basico'. Contrata un plan superior..."` |
| **422** | Validación de pydantic (campo faltante o mal formato) | Resaltar el campo que viene en `detail[0].loc` |

El cuerpo de un error siempre es:

```json
{ "detail": "mensaje humano" }
// o para 422:
{ "detail": [ { "type": "value_error", "loc": ["body","email"], "msg": "..." } ] }
```

### 9.8 Credenciales para probar

- Super: `root@plataforma.bo` / `SuperSegura123`
- Admin Luna (Profesional, 3 sucursales): `ana@boutique-luna.bo` / `Luna12345`
- Encargado Luna: `encargado@boutique-luna.bo` / `Luna12345`
- Admin Andina (Básico, 1 sucursal — probar rechazo por límite): `rodrigo@modaandina.bo` / `Andina12345`

Ambos tenants usan el campo `codigo_tenant`: `"luna"` o `"andina"`.

### 9.9 Troubleshooting

- **`pip install` falla con `bcrypt`** — ya está pineado a `4.0.1` en
  `requirements.txt`. Si igual rompe: `pip install bcrypt==4.0.1 --force-reinstall`.
- **`email-validator` rechaza correos con `.local`** — es a propósito, usá
  TLDs reales (`.bo`, `.com`).
- **Puerto 8000 ocupado** — `uvicorn ... --port 8001` y actualizá la base URL.
- **El móvil no se conecta** — chequear que la PC y el móvil estén en la
  misma Wi-Fi, firewall abierto en el puerto, y usar la IP de LAN
  (`ipconfig` en Windows) en vez de `localhost`.
- **"Token invalido: Subject must be a string"** — ya está arreglado: el
  JWT guarda `sub` como string. Si lo ves, estás contra una versión vieja
  del backend: `git pull`.

### 9.10 Para tus CU-03 / 08 / 09 / 10 / 11

Cuando armes tus endpoints:

- Hereda tus modelos de `TenantMixin` si deben aislarse por empresa
  (todo lo que no sea catálogo global).
- Usá `Depends(require_tenant)` o `Depends(require_roles("admin"))` en los
  routers; el `scope.tenant_id` queda listo para filtrar.
- Si un recurso tiene un límite por plan (productos, usuarios, lo que sea),
  llamá a `exigir_capacidad(db, scope.tenant_id, "<recurso>")` antes de
  crear — devuelve 409 con mensaje consistente al resto del sistema.
- Agregá tus endpoints documentándolos acá debajo cuando los termines.

## 10. Parcial 2 completo: CU-01 a CU-18

Los módulos nuevos siguen `router.py` → `service.py` → modelos SQLAlchemy con
`TenantMixin`. Están registrados en `app/main.py`. La venta guarda venta,
detalles, pago y movimientos con un solo `commit`; la reserva aparta inventario
en la misma transacción. Stripe se usa solo si se configura una clave
`STRIPE_SECRET_KEY=sk_test_...`; sin ella la pasarela simula la aprobación.

| CU | Módulo / ruta principal |
|---|---|
| 03 | `GET/POST /api/v1/usuarios` |
| 06 | `POST /api/v1/suscripciones/cambiar`, `/renovar` |
| 08 | `GET/POST /api/v1/productos` |
| 09 | `GET/POST /api/v1/catalogos/{tipo}` |
| 10 | `GET/POST /api/v1/proveedores` |
| 11 | `GET/POST /api/v1/clientes` |
| 12 | `GET /api/v1/inventario`, `POST /api/v1/inventario/movimientos` |
| 14 | `POST /api/v1/reservas` |
| 15 | `POST /api/v1/ventas` |
| 16 | `GET /api/v1/ventas/{codigo}`, `POST /api/v1/cambios` |
| 17 | `POST /api/v1/ventas/{id}/anular`, `/reservas/{id}/anular` |
| 18 | `GET /api/v1/offline/catalogo?sucursal_id=...&desde=...` |

CU-13 vive en `web/`: PWA Angular con service worker, manifest e íconos.
El cliente móvil vive en `mobile/` y usa SQLite (`sqflite`) para el catálogo
offline. Para una instalación ya existente de SQLite, usa una base nueva o
aplica una migración: `Tenant` ahora tiene `plazo_cambio_dias` y `create_all`
no modifica tablas preexistentes.

### Ejecutar y verificar

```powershell
cd parcial2/backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m app.seeds.demo
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

En otra terminal:

```powershell
cd parcial2/web
npm install
npm start
```

Para Flutter:

```powershell
cd parcial2/mobile
flutter pub get
flutter run
```

Las 24 capturas están en `docs/capturas/`. Las seis `_movil` se tomaron con
Flutter web a 390×844 porque no había emulador Android; las `_web` con Angular
a 1366×768. El script `docs/capturas/capturar_web.ts` las repite con Playwright
tras iniciar backend, Angular y el servidor de `mobile/build/web` en los
puertos 8000, 4200 y 8002 respectivamente. Para repetir los flujos de escritura
con los mismos datos, empieza con una base SQLite nueva y ejecuta las semillas.

## Respaldo de una empresa y operaciones sin conexión

En el panel de la empresa, **Seguridad → Respaldos** permite a un administrador
descargar y verificar una copia JSON de esa empresa. Contiene datos privados y
hashes de contraseñas: guárdala de forma segura. El código SHA-256 permite detectar
cambios accidentales, pero no es una firma digital. La descarga es manual y no
incluye las operaciones aún pendientes en teléfonos o navegadores: sincronízalas
antes. No incluye secretos globales ni otras empresas.

Para ensayar una recuperación, desde `parcial2/backend` ejecuta:

```powershell
.\.venv-run\Scripts\python.exe -m app.modules.respaldos.restaurar --archivo 'C:\ruta\respaldo-empresa.json' --destino 'C:\ruta\empresa-restaurada.db'
```

El destino debe ser un archivo SQLite nuevo: la herramienta no sobrescribe una
base ni incorpora datos a una base compartida ya existente. La copia recupera
los datos de la empresa y los planes que usa, no la cuenta de superadministrador.
Prueba periódicamente la restauración en una base separada.

Las reservas y ventas locales permanecen pendientes hasta que el servidor las
confirme. Si otra operación agotó el stock o cambió el precio, quedan en conflicto
y no se creó la reserva o venta. La aplicación intenta sincronizar al reconectar
o al abrirla con sesión y conexión; la cola y su resultado permanecen en el
dispositivo. Cerrar sesión o borrar datos antes de sincronizar puede impedir el
acceso a la cola; vuelve a entrar con la cuenta original.

Los cambios de prendas muestran el precio pagado, el precio actual de la variante
nueva y la diferencia a cobrar o devolver antes de confirmar. Se valida el plazo
configurado para la empresa (siete días por defecto). El sistema registra el
cambio de inventario; la entrega o cobro del dinero se hace fuera del sistema.

El reporte en lenguaje natural usa datos agregados de la empresa y el período
seleccionado. Con Gemini configurado envía la pregunta y agregados al proveedor;
sin modelo disponible solo muestra un resumen calculado, no una respuesta
generativa libre. La voz depende del servicio del navegador.


