# Punto 4 — Venta de contado sin conexión a Internet

**Informe para la defensa del Parcial 2 SI2 · UAGRM**

Pregunta del examen: *"Suponga que se registra una venta al contado cuando no
existe conexión a Internet. Explique paso a paso cómo se registra la venta
localmente, qué información se almacena y qué sucede cuando vuelve la
conectividad."*

Ruta: **Menú → Caja**. Módulo backend `app/modules/offline`.

---

## 1. Visión general del flujo

```
            Cajero                    Dispositivo                 Servidor
               │                           │                         │
               │  1. Carrito + efectivo    │                         │
               │ ─────────────────────────►│                         │
               │                           │  (sin red)              │
               │                           │  2. Encola en IndexedDB │
               │                           │     con UUID local      │
               │  ◄── "Venta en local"  ───│                         │
               │                           │                         │
               │  … tiempo pasa, se recupera la red …                │
               │                           │                         │
               │                           │  3. online / toggle OFF │
               │                           │ ───────────────────────►│  POST /offline/sincronizar
               │                           │                         │  (idempotente por UUID,
               │                           │                         │   FOR UPDATE sobre stock)
               │                           │  ◄──── 200 / 409 ───────│
               │  ◄── Confirmada  V-99…    │                         │
               │     ó Pago rechazado      │                         │
```

Hay **dos piezas** que hacen posible esto:

- **Angular Service Worker** de la PWA, que mantiene el shell cargado aun sin
  red (`parcial2/web/src/app/app.config.ts:16` registra `ngsw-worker.js`, con
  la configuración en `parcial2/web/ngsw-config.json`).
- **Cola local idempotente** en IndexedDB (web) / sqflite (móvil) orquestada
  por `OfflineService`, con un endpoint servidor que serializa la confirmación
  para evitar duplicados.

---

## 2. Paso a paso cuando NO hay internet

### 2.1 El cajero arma la venta y presiona *Cobrar*

Archivo: **`parcial2/web/src/app/features/caja/caja.ts`**

- El método `cobrar()` ([`caja.ts:380`](../web/src/app/features/caja/caja.ts))
  detecta que estamos trabajando en local (chip de red apagado) y
  **desvía el flujo** antes de pegar a `/api/v1/ventas`:

  ```ts
  // caja.ts  (ruta real: parcial2/web/src/app/features/caja/caja.ts)
  if (this.modoOffline() && this.metodo() === 'efectivo') {           // ~linea 396
    const fechaLocal = new Date().toISOString();
    Promise.all(lineas.map(l => this.offline.encolarVentaCaja({
      tipo: 'venta',
      sucursal_id: sucursalId,
      variante_id: l.variante.id,
      cantidad: l.cantidad,
      precio_unitario: l.variante.precio,           // precio con promo ya aplicada
      monto_recibido: l.variante.precio * l.cantidad,
      fecha_hora_prueba: null,
      fecha_local: fechaLocal,                      // ISO 8601 con zona
      nombre: l.variante.prenda,
      sku: l.variante.sku,
      sucursal: nombreSucursal,
    }))).then(() => { … toast "Venta registrada en local" … });
    return;                                         // nunca llama a /ventas
  }
  ```

- Validaciones **locales** que se corren antes (`caja.ts` cálculos
  `bloqueo`, `errorMonto`, `hayExcesos` en líneas 216-221 y 201-209):
  - Debe haber al menos una línea en el carrito.
  - Ninguna línea excede el stock conocido por la caja.
  - El efectivo recibido cubre el total y tiene como máximo dos decimales.

### 2.2 El encolado real en IndexedDB

Archivo: **`parcial2/web/src/app/services/offline.service.ts`**

El método `encolarVentaCaja()`
([`offline.service.ts:109`](../web/src/app/services/offline.service.ts)):

```ts
// offline.service.ts
async encolarVentaCaja(datos: Omit<OperacionLocal, …>): Promise<string> {
  const db = await this.abrir();            // abre IndexedDB 'ganga-catalogos-offline'
  const cuenta = this.clave();              // tenant_id:user_id — aísla por sesión
  const uuid = crypto.randomUUID();         // identificador único de la operación
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction('operaciones', 'readwrite');
    const nueva: OperacionLocal = {
      ...datos,
      uuid_operacion: uuid,
      cuenta,
      estado: 'pendiente',                  // ← se queda así hasta sincronizar
      error: null, codigo: null, confirmada_en: null,
    };
    tx.objectStore('operaciones').add(nueva, `${cuenta}:${uuid}`);
    tx.oncomplete = () => resolve();
    tx.onerror    = () => reject(tx.error);
  });
  this.revision.update(n => n + 1);         // notifica a la UI
  return uuid;
}
```

### 2.3 Qué información queda almacenada

**Store IndexedDB:** `ganga-catalogos-offline` → `operaciones`  
**Clave:** `tenant_id:user_id:uuid_operacion` (así cada cuenta tiene su cola).  
**Esquema real** (de `OperacionLocal` en
[`offline.service.ts:15-23`](../web/src/app/services/offline.service.ts)):

| Campo | Ejemplo | Razón de guardarlo |
| --- | --- | --- |
| `uuid_operacion` | `195957cf-e251-4045-ae14-1968a023fb62` | Idempotencia cliente↔servidor. |
| `tipo` | `"venta"` | El endpoint también atiende `"reserva"`. |
| `sucursal_id` | `4` | El servidor valida que siga activa. |
| `variante_id` | `33` | SKU exacto a descontar del inventario. |
| `cantidad` | `1` | Se compara con el stock real al sincronizar. |
| `precio_unitario` | `145.00` | Si el precio cambió al reconectar, se devuelve 409. |
| `monto_recibido` | `150.00` | Debe cubrir `precio_unitario × cantidad`. |
| `fecha_local` | `2026-11-11T22:04:17.123Z` | Fecha real del cobro; se guarda como `Venta.fecha`. |
| `nombre`, `sku`, `sucursal` | textos | Mostrar la operación en la UI sin volver a consultar el catálogo. |
| `cuenta` | `"1:8"` | Tenant y usuario; impide que otra cuenta vea esta cola. |
| `estado` | `"pendiente"` | Pasa a `confirmada` o `conflicto` al sincronizar. |
| `error`, `codigo`, `confirmada_en` | `null` al crear | Se llenan tras la respuesta del servidor. |

En **móvil** la información es la misma, sobre `sqflite`
(ver `parcial2/mobile/lib/operaciones_offline.dart`).

### 2.4 Qué UI ve el cajero sin red

- Chip discreto abajo a la derecha con el estado de la red
  ([`caja.html` sección "Interruptor de red local"](../web/src/app/features/caja/caja.html)).
- Toast informativo: *"Venta registrada en local por Bs X. Se confirmará al
  restablecer la red."* (`caja.ts:411`).
- Sección **"Operaciones en cola"** con una tarjeta por cada venta pendiente
  (`caja.html`, bloque `<section class="cola-caja">`), con badge amarillo
  *Pendiente*.

---

## 3. Qué pasa cuando vuelve la conectividad

### 3.1 Disparo automático de la sincronización

Archivo: **`parcial2/web/src/app/services/offline.service.ts`**

El `OfflineService` escucha dos eventos
([`offline.service.ts:34-47`](../web/src/app/services/offline.service.ts)):

```ts
window.addEventListener('online', intentar);
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') intentar();
});
effect(() => { this.sesion.usuario(); intentar(); });
```

Función `intentar()`: si hay red Y hay sesión con `tenant_id`, llama a
`sincronizarPendientes()` ([`offline.service.ts:49-62`](../web/src/app/services/offline.service.ts)).
Además, la caja expone un botón ↻ manual que hace lo mismo y un `effect` que
refresca el catálogo al terminar (`caja.ts:252-256`).

`sincronizarPendientes()` recorre todas las operaciones en estado `pendiente`
y para cada una llama a `sincronizar(op)` que hace
**POST `/api/v1/offline/sincronizar`** con todo el objeto `OperacionLocal`
([`offline.service.ts:181-194`](../web/src/app/services/offline.service.ts)).

### 3.2 Qué hace el servidor

Archivo: **`parcial2/backend/app/modules/offline/sincronizacion.py`**

Endpoint: `POST /api/v1/offline/sincronizar`
([`sincronizacion.py:35-134`](../backend/app/modules/offline/sincronizacion.py)).

Dentro de **una sola transacción**:

1. **Idempotencia** ([`sincronizacion.py:40-44`](../backend/app/modules/offline/sincronizacion.py)):
   si ya existe `OperacionLog` con ese `uuid_operacion`, devuelve el resultado
   previo con `repetida: true`. Esto permite reintentos seguros de parte del
   cliente sin duplicar la venta.

   ```python
   previa = db.query(OperacionLog).filter_by(tenant_id=tid, uuid_operacion=uid_op).first()
   if previa:
       if previa.payload.get('usuario_id') != uid or previa.payload.get('datos') != datos:
           raise HTTPException(409, 'El identificador ya fue usado para otra operación')
       return {**previa.payload['resultado'], 'repetida': True}
   ```

2. **Autorización** ([`sincronizacion.py:46-49`](../backend/app/modules/offline/sincronizacion.py)):
   ventas sin conexión requieren rol de personal (no cliente, no proveedor) y
   permiso `ventas:crear`. Si falta, 403.

3. **Reloj del cliente** ([`sincronizacion.py:51-54`](../backend/app/modules/offline/sincronizacion.py)):
   si la fecha del dispositivo está adelantada más de 5 minutos respecto al
   servidor, 409.

4. **Variante y precio actuales**
   ([`sincronizacion.py:88-97`](../backend/app/modules/offline/sincronizacion.py)):

   ```python
   variante = db.query(Variante).filter_by(tenant_id=tid, id=body.variante_id, activo=True).first()
   if not variante: raise HTTPException(409, 'La variante ya no está disponible')
   # ...
   precio_actual, _ = precio_promocional(db, tid, variante.producto_id, variante.precio)
   if precio_actual != body.precio_unitario:
       raise HTTPException(409, f'El precio cambió: registrado Bs {body.precio_unitario}, actual Bs {precio_actual}.')
   if body.monto_recibido is None or body.monto_recibido < precio_actual * body.cantidad:
       raise HTTPException(409, 'El efectivo registrado no cubre el total actual')
   ```

5. **Stock bloqueado**
   ([`sincronizacion.py:99-103`](../backend/app/modules/offline/sincronizacion.py)):

   ```python
   inv = db.query(Inventario).filter_by(tenant_id=tid, sucursal_id=body.sucursal_id,
                                        variante_id=body.variante_id).with_for_update().first()
   if not inv or inv.stock - inv.reservado < body.cantidad:
       disponible = max(0, inv.stock - inv.reservado) if inv else 0
       raise HTTPException(409, f'Stock insuficiente: quedan {disponible} unidades en la sucursal')
   ```

   `with_for_update()` serializa dos clientes que intenten vender la misma
   unidad: solo uno obtiene el lock, el otro recibe 409.

6. **Persistencia final**
   ([`sincronizacion.py:107-127`](../backend/app/modules/offline/sincronizacion.py)):
   usa el servicio existente `ventas.registrar_venta(...)` dentro de la misma
   transacción, lo que crea `Venta` + `DetalleVenta` + `Pago` y descuenta
   `Inventario`. Si cualquier paso falla, todo se revierte.

Respuesta exitosa:

```json
{
  "uuid_operacion": "195957cf-…",
  "tipo": "venta",
  "codigo": "V-38FBDEAD83",      // ← comprobante oficial
  "estado": "CONFIRMADA",
  "confirmada_en": "2026-11-12T00:36:21.523833+00:00",
  "repetida": false
}
```

### 3.3 Qué hace el cliente con la respuesta

Archivo: **`parcial2/web/src/app/services/offline.service.ts`**
método `sincronizar(op)`
([`offline.service.ts:181-194`](../web/src/app/services/offline.service.ts)):

```ts
try {
  const resultado = await firstValueFrom(this.http.post<…>(`${API_URL}/offline/sincronizar`, { … }));
  await this.actualizarOperacion({ ...o, estado: 'confirmada', codigo: resultado.codigo,
                                   confirmada_en: resultado.confirmada_en });
} catch (err: any) {
  if ([403, 409, 422].includes(err?.status)) {
    const detalle = typeof err?.error?.detail === 'string' ? err.error.detail : 'Operación rechazada.';
    await this.actualizarOperacion({ ...o, estado: 'conflicto', error: detalle });
  } else { throw err; }                 // error de red → queda 'pendiente' para reintentar
}
```

Y en `sincronizarPendientes` ([`offline.service.ts:56-59`](../web/src/app/services/offline.service.ts))
se dispara un toast al operador por cada operación:

- `estado === 'confirmada'` → *"Venta confirmada: V-99BF84C99E"* (verde).
- `estado === 'conflicto'` → *"Venta no confirmada: {motivo del servidor}"* (rojo).

### 3.4 Qué queda visible en la caja después de sincronizar

Sección `<section class="cola-caja">` en
[`caja.html` línea 48 en adelante](../web/src/app/features/caja/caja.html),
clases CSS en [`caja.css` "cola-caja"](../web/src/app/features/caja/caja.css):

- **Pendiente** → tarjeta blanca borde amarillo, badge amarillo "Pendiente".
- **Confirmada** → tarjeta fondo verde claro, badge verde "Confirmada · V-XXX".
- **Pago rechazado** → tarjeta fondo rojo claro, badge rojo "Pago rechazado",
  bloque rojo con el motivo exacto del backend y la instrucción:
  *"Si recibiste efectivo, devolvelo al cliente o registra otra venta con el
  stock real."*

---

## 4. Escenario crítico — dos cajeros, un solo stock

### 4.1 ¿Qué pasa en la realidad?

Dos cajas (A y B) del mismo tenant pierden Internet al mismo tiempo. Ambas
tienen la misma variante con **1 unidad disponible**. Cada una cobra esa unidad
en efectivo y queda `pendiente` en su IndexedDB local. Cuando vuelve la red,
las dos dispararán la sincronización casi simultáneamente. El sistema debe
garantizar que **solo una venta sobrevive** y la otra reciba un rechazo claro
para que el cajero pueda devolver el efectivo al cliente.

### 4.2 Las tres líneas de código que hacen esto posible

Todo el blindaje contra la doble venta y la doble sincronización son estos
tres puntos del backend:

**① UNIQUE sobre `uuid_operacion` — la operación no puede entrar dos veces**

Archivo: `parcial2/backend/app/models/operacion.py:16-18`

```python
__table_args__ = (
    UniqueConstraint("tenant_id", "uuid_operacion", name="uq_operacion_tenant_uuid"),
)
```

Cada venta local nace con un `uuid_operacion` generado en el cliente
(`crypto.randomUUID()` en `offline.service.ts:109`). El `UNIQUE` del backend
hace que, si el cajero A reintenta su misma venta (por red inestable, por
ejemplo), el servidor devuelva la MISMA confirmación anterior en vez de
crear una segunda venta.

**② Chequeo de idempotencia al inicio del endpoint**

Archivo: `parcial2/backend/app/modules/offline/sincronizacion.py:40-44`

```python
previa = db.query(OperacionLog).filter_by(tenant_id=tid, uuid_operacion=uid_op).first()
if previa:
    if previa.payload.get('usuario_id') != uid or previa.payload.get('datos') != datos:
        raise HTTPException(409, 'El identificador ya fue usado para otra operación')
    return {**previa.payload['resultado'], 'repetida': True}
```

Si ya se había procesado esa operación antes (mismo uuid), responde
inmediatamente con el resultado previo y marca `repetida: True`. No se
duplica ninguna venta, ni siquiera si el cliente reintenta 100 veces.

**③ Bloqueo pesimista sobre `Inventario` — el que llega primero gana**

Archivo: `parcial2/backend/app/modules/offline/sincronizacion.py:99-103`

```python
inv = db.query(Inventario).filter_by(tenant_id=tid, sucursal_id=body.sucursal_id,
                                     variante_id=body.variante_id).with_for_update().first()
if not inv or inv.stock - inv.reservado < body.cantidad:
    disponible = max(0, inv.stock - inv.reservado) if inv else 0
    raise HTTPException(409, f'Stock insuficiente: quedan {disponible} unidades en la sucursal')
```

`with_for_update()` emite un `SELECT … FOR UPDATE` que **bloquea esa fila
de inventario** hasta que termine la transacción. Si dos transacciones llegan
juntas, la segunda queda esperando a que la primera haga commit. Cuando
desbloquea, lee el stock YA descontado y falla con `HTTPException 409`.

### 4.3 Lo que hace el cliente al recibir el 409

Archivo: `parcial2/web/src/app/services/offline.service.ts:181-194`

```typescript
try {
  const resultado = await firstValueFrom(this.http.post<…>(`${API_URL}/offline/sincronizar`, { … }));
  await this.actualizarOperacion({ ...o, estado: 'confirmada', codigo: resultado.codigo,
                                   confirmada_en: resultado.confirmada_en });
} catch (err: any) {
  if ([403, 409, 422].includes(err?.status)) {
    const detalle = typeof err?.error?.detail === 'string'
                    ? err.error.detail : 'Operación rechazada. Revisa los datos.';
    await this.actualizarOperacion({ ...o, estado: 'conflicto', error: detalle });
  } else { throw err; }                 // error de red → queda 'pendiente' para reintentar
}
```

El 409 hace que la operación local pase a `estado='conflicto'` con el motivo
exacto que devolvió el backend (`"Stock insuficiente: quedan 0 unidades en la
sucursal"`). Nunca se pierde el registro y nunca se marca como confirmada.

### 4.4 Lo que ve el cajero perdedor

Archivo: `parcial2/web/src/app/features/caja/caja.html` (sección
`<section class="cola-caja">`) y estilos en `caja.css` (`.cola-caja article.conf-rech`):

```html
@if (op.estado === 'conflicto' && op.error) {
  <div class="motivo-rech">
    <strong>No se proceso el pago:</strong> {{ op.error }}
    <div class="ayuda">Si recibiste efectivo, devolvelo al cliente o
         registra otra venta con el stock real.</div>
  </div>
}
```

La tarjeta de la venta se pinta con fondo rojo, badge **"Pago rechazado"** y
la instrucción explícita para el cajero.

### 4.5 Script que demuestra todo lo anterior automáticamente

Archivo: **`parcial2/backend/tests/prueba_venta_offline_contado.py`** (versionado
en la rama). Reproduce el escenario completo sin UI, útil si la red del día
de la demo falla.

Ejecución:

```bash
cd parcial2/backend
DATABASE_URL="sqlite:///./ganga_saas_local.db" \
    .venv-run/Scripts/python -m tests.prueba_venta_offline_contado
```

Qué hace, paso por paso (todo verificable en el código del script):

1. Logea dos tokens del mismo cajero (simula dos navegadores abiertos).
2. Elige una variante con stock y la **normaliza a 1 unidad** para forzar la
   colisión.
3. Arma dos venta offline con **UUIDs distintos** (simulando dos IndexedDB
   locales independientes).
4. Dispara los dos `POST /offline/sincronizar` casi simultáneos.
5. Verifica que uno sea `200 CONFIRMADA` y el otro `409 Stock insuficiente`.
6. Verifica que el stock final queda en 0 (una sola venta aplicada).
7. **Reenvía** la operación A con el MISMO uuid y verifica que el servidor
   devuelva `repetida: True` sin duplicarla.

### 4.6 Resultado real de la última corrida

Salida del script contra la DB local poblada (ejecutada antes de este
informe):

```
[1] Login de dos cajeros                   roles=['vendedor'] ventas:crear=True
[2] Variante disputada: SKU LUN-11-M-BL    Bs 290    stock disponible = 30
[3] Normalizo el stock a 1 unidad          para forzar la colision real
[4] Ambos cajeros pierden Internet         guardan la venta en IndexedDB local
[5] Reconectan y disparan /offline/sincronizar:
      Cajero A → HTTP 200   V-38FBDEAD83   CONFIRMADA
      Cajero B → HTTP 409   "Stock insuficiente: quedan 0 unidades"
[6] UI en cada dispositivo:
      A → IndexedDB estado='confirmada'  toast verde "Venta confirmada: V-38FBDEAD83"
      B → IndexedDB estado='conflicto'   banner rojo "Pago rechazado: Stock insuficiente..."
[7] Stock final                           0  (se descontó UNA sola vez)
[8] Reintento idempotente de A            HTTP 200 + repetida: True  (NO duplica)
[9] VEREDICTO                             PRUEBA SUPERADA
```

### 4.7 Mini guion para explicar frente a la ingeniera (30 seg)

> "Cuando dos cajas sincronizan sus ventas al mismo tiempo, el servidor usa
> dos defensas: un **índice UNIQUE** sobre `uuid_operacion` en la tabla
> `operaciones_log` ([`operacion.py:16`](../backend/app/models/operacion.py#L16))
> que impide que la misma operación entre dos veces aunque el cliente
> reintente, y un **SELECT FOR UPDATE** sobre la fila de inventario
> ([`sincronizacion.py:99`](../backend/app/modules/offline/sincronizacion.py#L99))
> que serializa a las dos cajas. La primera transacción hace commit y descuenta
> el stock; la segunda, al leer, ve 0 y recibe un `409 Stock insuficiente`.
> Esa respuesta viaja al cliente, que marca la operación local como
> `conflicto` ([`offline.service.ts:181`](../web/src/app/services/offline.service.ts#L181))
> y muestra un banner rojo *'Pago rechazado'* en la caja del segundo cajero
> con la instrucción de devolver el efectivo. El script
> `tests/prueba_venta_offline_contado.py` reproduce este escenario y
> comprueba que el stock final es 0 y que una sola venta llega a la base."

---

## 5. Dónde demostrarlo frente a la ingeniera

| # | Paso | Dónde se ve |
| - | ---- | ----------- |
| 1 | Login cajero en http://127.0.0.1:4300 | caja normal operando |
| 2 | Chip abajo a la derecha: clic para pasar a *local* | el único indicador visible, muy sutil |
| 3 | Cobrar una venta de efectivo | toast "Venta registrada en local" |
| 4 | Aparece "Operaciones en cola" con badge Pendiente | sección entre encabezado y catálogo |
| 5 | Chip clic para volver a *red* | sync automático dispara |
| 6 | La venta pasa a verde "Confirmada · V-…" | tarjeta en la misma lista |
| 7 | (Opcional) Abrir otra ventana incógnito, repetir, cobrar la misma prenda sin stock | la segunda se marca "Pago rechazado" |
| 8 | Correr el script de pruebas | evidencia reproducible sin UI |

---

## 6. Archivos que soportan esta implementación

**Backend**

- `parcial2/backend/app/modules/offline/sincronizacion.py` – endpoint
  `/offline/sincronizar`, idempotencia y bloqueo de stock.
- `parcial2/backend/app/modules/offline/service.py` – construcción del
  catálogo offline que consume la pantalla original.
- `parcial2/backend/app/models/operacion.py` – modelo `OperacionLog` con
  `UNIQUE(tenant_id, uuid_operacion)`.
- `parcial2/backend/tests/prueba_venta_offline_contado.py` – script de
  prueba automatizada (adjuntado en esta rama).

**Frontend web**

- `parcial2/web/src/app/features/caja/caja.ts` – `cobrar()` desvía a la cola
  cuando el chip está en *local*; `cargarPendientes`, `toggleOffline`,
  `sincronizarCola`.
- `parcial2/web/src/app/features/caja/caja.html` – chip de red y sección
  *Operaciones en cola*.
- `parcial2/web/src/app/features/caja/caja.css` – estilos del chip y la cola.
- `parcial2/web/src/app/services/offline.service.ts` –
  `encolarVentaCaja()`, `sincronizarPendientes()`, listeners `online` y
  `visibilitychange`.
- `parcial2/web/src/app/app.config.ts` – registro del service worker Angular.
- `parcial2/web/ngsw-config.json` – shells y assets precacheados.

**Frontend móvil** (equivalente, no modificado en esta rama)

- `parcial2/mobile/lib/operaciones_offline.dart` – cola en sqflite.
- `parcial2/mobile/lib/sincronizador.dart` – sincronización automática al
  recuperar conectividad.
