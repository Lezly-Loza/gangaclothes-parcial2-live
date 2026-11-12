# Punto 2 — Relación entre CU, Robustez, Secuencia/Comunicación y Clases
## CU elegido: **CU-20 Registrar venta de contado sin conexión**

**Por qué este CU.** Toca las tres capas del sistema (vista, controlador, modelo),
tiene un endpoint real y una regla de negocio no trivial (bloqueo de stock entre
dispositivos). Cada participante del diagrama de robustez es un método/clase
real del código; se puede verificar línea por línea.

---

## 1. Caso de uso — redacción (resumen)

**Actor principal:** Cajero (rol `vendedor` con permiso `ventas:crear`).
**Precondición:** Cajero autenticado y en la pantalla *Caja*; el chip de red
indica **local**.
**Flujo básico:**

1. El cajero arma el carrito (agrega variantes y cantidades).
2. Elige **efectivo** e ingresa el monto recibido.
3. Presiona **Cobrar**.
4. La aplicación valida el carrito **localmente** (stock de la copia, monto
   suficiente, 2 decimales) y encola la venta en IndexedDB con un UUID.
5. La aplicación muestra el toast *"Venta registrada en local"* y la tarjeta
   aparece en *Operaciones en cola* con badge **Pendiente**.
6. Cuando el navegador recibe el evento `online` (o el cajero apaga el chip),
   la aplicación envía `POST /offline/sincronizar` con cada operación
   pendiente.
7. El servidor valida reloj, variante, precio y stock (`FOR UPDATE`), crea la
   `Venta` + `DetalleVenta` + `Pago` y descuenta `Inventario`.
8. La aplicación actualiza la operación local a **confirmada** (o
   **conflicto** con el motivo del backend).

**Postcondición exitosa:** existe una `Venta` en el servidor con su código
`V-XXXXXXXXXX`, el inventario fue descontado una sola vez.

---

## 2. Diagrama de robustez

> Cada nodo lleva el **nombre exacto del método o clase del código**, para
> que la trazabilidad sea objetiva. Entre paréntesis, la ruta
> `archivo:línea`.

### 2.1 Elementos

| Estereotipo | Nombre en el diagrama | Rol en el flujo |
| --- | --- | --- |
| Actor | **Cajero** | arma el carrito y cobra |
| «boundary» | **CajaPage** (`web/src/app/features/caja/caja.ts:140`) | pantalla de caja |
| «control» | **cobrar()** (`caja.ts:380`) | decide si va al servidor o a la cola |
| «control» | **OfflineService.encolarVentaCaja()** (`offline.service.ts:109`) | escritura en IndexedDB |
| «entity» | **IndexedDB.operaciones** (store `operaciones`) | cola local de ventas |
| «control» | **OfflineService.sincronizarPendientes()** (`offline.service.ts:49`) | dispara el envío al servidor |
| «control» | **OfflineService.sincronizar()** (`offline.service.ts:181`) | envía UNA operación |
| «boundary» | **POST /offline/sincronizar** (`backend/app/modules/offline/sincronizacion.py:35`) | endpoint FastAPI |
| «control» | **offline.sincronizacion.sincronizar()** (`sincronizacion.py:36`) | orquesta la transacción |
| «control» | **ventas.service.registrar_venta()** (`backend/app/modules/ventas/service.py`) | crea `Venta`, `DetalleVenta`, `Pago`, descuenta `Inventario` |
| «entity» | **OperacionLog** (`backend/app/models/operacion.py:9`) | log idempotente por UUID |
| «entity» | **Venta** (`backend/app/models/negocio.py:163`) | registro oficial |
| «entity» | **DetalleVenta** (`backend/app/models/negocio.py:200`) | líneas de la venta |
| «entity» | **Pago** (`backend/app/models/negocio.py:210`) | cobro (EFECTIVO) |
| «entity» | **Inventario** (`backend/app/models/inventario.py` *o* `negocio.py`) | stock de la variante con `FOR UPDATE` |
| «control» | **OfflineService.actualizarOperacion()** (`offline.service.ts:135`) | marca local como confirmada o conflicto |

### 2.2 Flechas numeradas (así te queda idéntico al ejemplo de la ingeniera)

```
Cajero
 │ 1.1 ingresarItems(variante_id, cantidad, monto_recibido)
 ▼
«boundary» CajaPage
 │ 1.1.1 cobrar()                                         (caja.ts:380)
 ▼
«control» cobrar()  ─── 1.1.2 modoOffline() === true ───► bifurcación
                                                          │
                                                          ▼
                              «control» OfflineService.encolarVentaCaja(datos)
                                                          │ 1.1.3 crypto.randomUUID()
                                                          │ 1.1.4 tx.objectStore('operaciones').add(nueva)
                                                          ▼
                                      «entity» IndexedDB.operaciones
                                                          │
                                        (más tarde)       │ 1.1.5 navegador emite 'online'
                                                          ▼
                              «control» OfflineService.sincronizarPendientes()
                                                          │ 1.1.6 por cada op pendiente
                                                          ▼
                              «control» OfflineService.sincronizar(op)
                                                          │ 1.1.7 POST /api/v1/offline/sincronizar
                                                          ▼
«boundary» POST /offline/sincronizar  ──────────────►  «control» offline.sincronizacion.sincronizar()
                                                          │ 1.1.8 verifica idempotencia (OperacionLog)
                                                          │ 1.1.9 valida variante, precio, reloj
                                                          │ 1.1.10 SELECT Inventario FOR UPDATE
                                                          │ 1.1.11 ventas.service.registrar_venta(...)
                                                          ├─────► «entity» OperacionLog  (uuid UNIQUE)
                                                          ├─────► «entity» Venta
                                                          ├─────► «entity» DetalleVenta
                                                          ├─────► «entity» Pago
                                                          └─────► «entity» Inventario (stock -= cantidad)
                                                                                │
                                      ◄── 1.1.12 { codigo, estado=CONFIRMADA } ─┘
                                                          │ ó 409 "Stock insuficiente..."
                                                          ▼
                              «control» OfflineService.actualizarOperacion(op)
                                                          │ 1.1.13 IndexedDB.put(estado='confirmada'|'conflicto')
                                                          ▼
«boundary» CajaPage     ◄──── 1.1.14 effect(revision) refresca ventasPendientes()
```

### 2.3 Reglas de robustez que se respetan (y cómo comprobarlo)

- **Actor ↔ solo Boundary.** `Cajero` llega a `CajaPage` (plantilla
  `caja.html`), nunca directo a `OfflineService`.
- **Boundary ↔ solo Control.** `CajaPage` llama `cobrar()`, que a su vez
  invoca a `OfflineService`. El HTML no habla con IndexedDB.
- **Control ↔ Control.** Permitido: `cobrar()` → `encolarVentaCaja()`,
  `sincronizarPendientes()` → `sincronizar()`.
- **Entity ↔ solo Control.** `IndexedDB.operaciones` solo se toca dentro de
  métodos de `OfflineService`. `Venta`, `Inventario`, etc. solo desde las
  funciones del backend.

---

## 3. Diagrama de secuencia (sd CU-20)

Mismo caso, visto en el tiempo. Mantiene los nombres del código.

```
Cajero   CajaPage       cobrar()     OfflineService       IndexedDB   (red cae)   /offline/sincronizar   OperacionLog   Inventario   Venta
  │         │               │              │                  │                          │                    │             │          │
  │ 1 agregar carrito        │              │                  │                          │                    │             │          │
  │─────────►│              │              │                  │                          │                    │             │          │
  │ 2 clic Cobrar            │              │                  │                          │                    │             │          │
  │─────────►│─2.1 cobrar()─►│              │                  │                          │                    │             │          │
  │          │              │ 2.2 modoOffline()==true          │                          │                    │             │          │
  │          │              │─2.3 encolarVentaCaja(datos)─────►│                          │                    │             │          │
  │          │              │              │ 2.4 crypto.randomUUID()                      │                    │             │          │
  │          │              │              │ 2.5 tx.add(operaciones, OperacionLocal{pendiente})                 │             │          │
  │          │              │              │─────────────────►│                          │                    │             │          │
  │          │              │              │ 2.6 revision+1   │                          │                    │             │          │
  │          │              ◄── 2.7 toast "Venta registrada en local"                     │                    │             │          │
  │         ◄───────────────│              │                  │                          │                    │             │          │
  │                                                                                                                                      │
  │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
  │                                               reconexion                                                                             │
  │                        3 window.addEventListener('online') dispara OfflineService.sincronizarPendientes()                             │
  │                                        │─3.1 sincronizar(op)──────────────────►│                                                     │
  │                                        │              │ 3.2 POST /offline/sincronizar                                                 │
  │                                        │              │─────────────────────────────────────────────────►│                           │
  │                                                                                                              3.3 SELECT OperacionLog │
  │                                                                                                              por uuid (idempotencia) │
  │                                                                                                              3.4 valida variante,    │
  │                                                                                                              precio actual, reloj    │
  │                                                                                                              3.5 SELECT FOR UPDATE   │
  │                                                                                                                 Inventario           │
  │                                                                                                                 ├────────────►│      │
  │                                                                                                              3.6 ventas.service.registrar_venta()
  │                                                                                                                 ├────────────────────────────►│
  │                                                                                                                 │ INSERT Venta + Detalle + Pago
  │                                                                                                                 │ UPDATE Inventario (stock -= cantidad)
  │                                                                                                              3.7 200 {codigo: V-XXX, estado: CONFIRMADA}
  │                                                              ◄──────────────────────────────────────────────── │
  │                                        │              │ 3.8 actualizarOperacion(estado='confirmada', codigo)
  │                                        │              │────►│                                                                        │
  │                                                             3.9 revision+1 → effect(caja.ts) refresca ventasPendientes()
  │     Toast verde "Venta confirmada: V-XXX"                                                                                             │
  ◄──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  │
```

**Camino alternativo (conflicto por stock):** paso 3.5 devuelve
`stock - reservado < cantidad` → el servidor lanza
`HTTPException(409, "Stock insuficiente: quedan N unidades en la sucursal")`
→ `sincronizar()` cae al catch con `err.status === 409` →
`actualizarOperacion(estado='conflicto', error=detalle)` → la tarjeta se
pinta roja con **"Pago rechazado"**.

---

## 4. Diagrama de comunicación (colaboración)

Mismo contenido que el de secuencia pero sin eje temporal; se enumeran los
mensajes. Se dibuja así en Enterprise Architect / draw.io:

```
                        1 agregarItem, 2 cobrar()
          Cajero ───────────────────────────────────► CajaPage
                                                          │
                                                 3 cobrar() [modoOffline]
                                                          ▼
                                                        cobrar()
                                                          │
                                           4 encolarVentaCaja(datos)
                                                          ▼
                                                 OfflineService
                   5 add(operaciones, OperacionLocal)      │
                    ┌─────────────────────────────────────┤
                    ▼                                     │
            IndexedDB.operaciones                         │
                                                          │
                     6 window.online → sincronizarPendientes()
                                                          ▼
                                                 OfflineService
                                                          │
                      7 POST /offline/sincronizar         │
                                                          ▼
                                          POST /offline/sincronizar
                                                          │
                                 8 offline.sincronizacion.sincronizar()
                                                          │
                            9 SELECT OperacionLog (uuid)   10 SELECT FOR UPDATE Inventario
                                   ▼                                 ▼
                              OperacionLog                        Inventario
                                                          │
                                11 ventas.service.registrar_venta()
                                              │
                                 ┌────────────┼─────────────┐
                                 ▼            ▼             ▼
                               Venta     DetalleVenta      Pago
                                                          │
                 12 { codigo, estado=CONFIRMADA }  ◄──────┘
                                                          ▼
                                         OfflineService.actualizarOperacion()
                                                          │
                              13 put(operaciones, estado='confirmada')
                                                          ▼
                                                 IndexedDB.operaciones
                                                          │
                                 14 revision++  → effect refresca
                                                          ▼
                                                      CajaPage
                                                          │
                                   15 "Venta confirmada: V-XXX"
                                                          ▼
                                                        Cajero
```

---

## 5. Diagrama de clases (fragmento relevante al CU-20)

> Solo las clases que colaboran en este caso de uso. Las flechas son
> referencias reales (imports y claves foráneas del esquema).

```
                 ┌──────────────────────────────────────┐
                 │               CajaPage               │   (Angular, standalone)
                 │  file: caja.ts:140                   │
                 │ ─────────────────────────────────── │
                 │ - modoOffline: Signal<boolean>       │
                 │ - ventasPendientes: Signal<OperacionLocal[]>│
                 │ - lineas: Signal<LineaCaja[]>        │
                 │ ─────────────────────────────────── │
                 │ + cobrar(): void                     │   ← decide branch offline
                 │ + toggleOffline(): void              │
                 │ + sincronizarCola(): Promise<void>   │
                 │ + cargarPendientes(): Promise<void>  │
                 └────────────────┬─────────────────────┘
                                  │ 1 ── usa (DI)
                                  ▼
                 ┌──────────────────────────────────────┐
                 │            OfflineService            │   (@Injectable)
                 │  file: offline.service.ts:26         │
                 │ ─────────────────────────────────── │
                 │ - revision: Signal<number>           │
                 │ ─────────────────────────────────── │
                 │ + encolarVentaCaja(datos): string    │
                 │ + sincronizarPendientes(): Promise<void>│
                 │ + sincronizar(op): Promise<void>     │
                 │ + actualizarOperacion(op): Promise<void>│
                 │ + guardarOperacion(datos): Promise<void>│   (flow alterno)
                 │ - abrir(): Promise<IDBDatabase>      │
                 │ - clave(): string   // tenant:user   │
                 └────────────────┬─────────────────────┘
                                  │ 1 ── persiste en
                                  ▼
                 ┌──────────────────────────────────────┐
                 │   «indexeddb»  operaciones (store)   │
                 │   type: OperacionLocal               │
                 │ ─────────────────────────────────── │
                 │ uuid_operacion: string               │
                 │ tipo: 'venta' | 'reserva'            │
                 │ sucursal_id: number                  │
                 │ variante_id: number                  │
                 │ cantidad: number                     │
                 │ precio_unitario: number              │
                 │ monto_recibido: number | null        │
                 │ fecha_local: string                  │
                 │ estado: 'pendiente'|'confirmada'|'conflicto'│
                 │ error, codigo, confirmada_en         │
                 │ cuenta: string  // tenant:user       │
                 └──────────────────────────────────────┘

                 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ (red)
                                  │
                                  ▼
                 ┌──────────────────────────────────────┐
                 │  offline.sincronizacion.sincronizar  │   (FastAPI handler)
                 │  file: sincronizacion.py:36          │
                 │ ─────────────────────────────────── │
                 │ (body: OperacionOfflineIn,           │
                 │  scope: TenantScope,                 │
                 │  db: Session) → dict                 │
                 │ ─────────────────────────────────── │
                 │ orquesta: idempotencia, bloqueo,     │
                 │ validaciones, delegación a           │
                 │ ventas.service.registrar_venta       │
                 └────────────────┬─────────────────────┘
                                  │ usa
                     ┌────────────┼────────────┬─────────────────────────┐
                     ▼            ▼            ▼                         ▼
          ┌─────────────┐  ┌──────────────┐ ┌──────────────┐  ┌────────────────────────┐
          │ OperacionLog│  │  Inventario  │ │   Variante   │  │ ventas.service         │
          │ (model)     │  │  (model)     │ │   (model)    │  │ .registrar_venta()     │
          │ operacion.py│  │              │ │              │  │ ventas/service.py      │
          │ :9          │  │ FK sucursal, │ │ FK producto  │  │                        │
          │ UNIQUE      │  │ FK variante  │ │ precio       │  │ crea:                  │
          │(tenant_id,  │  │ stock        │ │              │  │   Venta                │
          │ uuid_op)    │  │ reservado    │ │              │  │   DetalleVenta         │
          └─────────────┘  └──────┬───────┘ └──────────────┘  │   Pago                 │
                                  │                          │ descuenta Inventario   │
                                  │                          └──────┬─────────────────┘
                                  │                                 │
                                  │                     ┌───────────┼────────────┐
                                  │                     ▼           ▼            ▼
                                  │              ┌───────────┐ ┌────────────┐ ┌─────────┐
                                  │              │   Venta   │ │DetalleVenta│ │  Pago   │
                                  │              │ negocio.py│ │ negocio.py │ │negocio.py│
                                  │              │ :163      │ │ :200       │ │ :210    │
                                  │              │ codigo    │ │ venta_id FK│ │ venta_id│
                                  │              │ sucursal_id│ │ variante_id│ │ metodo  │
                                  │              │ cliente_id│ │ cantidad   │ │ monto   │
                                  │              │ uuid_op   │ │ subtotal   │ │ estado  │
                                  │              │ total     │ │            │ │         │
                                  │              │ estado    │ │            │ │         │
                                  │              └─────┬─────┘ └────────────┘ └─────────┘
                                  │                    │
                                  └── descuento stock ─┘
```

### Relaciones de cardinalidad relevantes

- `Venta 1 ── * DetalleVenta` (una venta tiene muchas líneas).
- `Venta 1 ── * Pago` (en EFECTIVO normalmente es 1, pero el modelo permite más).
- `DetalleVenta * ── 1 Variante` (una línea referencia a una variante).
- `Inventario * ── 1 Variante` y `Inventario * ── 1 Sucursal`
  (stock por combinación variante-sucursal).
- `OperacionLog 1 ── 1 Venta` por UUID (`Venta.uuid_operacion` === `OperacionLog.uuid_operacion`).

---

## 6. La **relación** entre los cuatro diagramas (respuesta al punto 2)

ICONIX **encadena** los artefactos — cada uno se deriva del anterior y los
cuatro deben ser consistentes. Sobre nuestro CU-20:

| Diagrama | Qué aporta | Deriva de | Resultado concreto en CU-20 |
| --- | --- | --- | --- |
| **Caso de uso** | QUÉ pasa, en lenguaje del usuario | Documento de requisitos | Flujo de 8 pasos del §1 |
| **Robustez** | QUIÉN participa y evita que las responsabilidades mezclen UI, lógica y datos | Caso de uso | 2 Boundaries, 5 Controls, 5 Entities del §2 |
| **Secuencia / Comunicación** | CUÁNDO y en QUÉ ORDEN se envían los mensajes entre participantes | Robustez | Trazas con nombres de métodos reales del §3-§4 |
| **Clases** | CÓMO se implementa cada participante (atributos, operaciones, relaciones) | Secuencia | Diagrama del §5 |

**Comprobación de consistencia que la ingeniera puede hacer al vuelo:**

- Cada «control» del diagrama de robustez (`cobrar`, `encolarVentaCaja`,
  `sincronizarPendientes`, `sincronizar`, `offline.sincronizacion.sincronizar`,
  `actualizarOperacion`) **existe como método** en el diagrama de clases.
- Cada mensaje numerado de la secuencia **es exactamente** una invocación
  de esos métodos (no hay métodos inventados).
- Cada «entity» del robustez **existe como clase o store** en el de clases
  (`OperacionLog`, `Venta`, `DetalleVenta`, `Pago`, `Inventario`, `Variante`,
  `IndexedDB.operaciones`).
- Cada paso del caso de uso tiene **al menos un mensaje** en el diagrama de
  secuencia.

Un cambio en el CU (por ejemplo: pedir también DNI del cliente) obliga a
tocar los tres diagramas y la implementación; ICONIX hace esa dependencia
visible, en vez de dejarla implícita.

---

## 7. Cómo demostrar la consistencia frente a la ingeniera

Abrir en pantalla, en este orden:

1. **Robustez** (impreso o PDF del §2).
2. **VSCode** → abrir estos archivos y buscar los métodos subrayados en
   amarillo del robustez:
   - `parcial2/web/src/app/features/caja/caja.ts` → `cobrar`,
     `toggleOffline`, `sincronizarCola`.
   - `parcial2/web/src/app/services/offline.service.ts` →
     `encolarVentaCaja`, `sincronizarPendientes`, `sincronizar`,
     `actualizarOperacion`.
   - `parcial2/backend/app/modules/offline/sincronizacion.py` →
     función `sincronizar`.
   - `parcial2/backend/app/models/operacion.py`, `models/negocio.py`.
3. **Secuencia** (§3): leer la traza mensaje por mensaje y compararla con el
   código abierto.
4. **Prueba automática** del punto 4 que corrí antes:
   ```bash
   cd parcial2/backend
   DATABASE_URL="sqlite:///./ganga_saas_local.db" \
     .venv-run/Scripts/python -m tests.prueba_venta_offline_contado
   ```
   Imprime en pantalla cada paso del diagrama ejecutándose contra la DB.

---

## 8. Archivos citados (referencia rápida)

| Diagrama | Elemento | Archivo | Línea |
| --- | --- | --- | --- |
| Robustez | Boundary `CajaPage` | `parcial2/web/src/app/features/caja/caja.ts` | 140 |
| Robustez | Control `cobrar` | `parcial2/web/src/app/features/caja/caja.ts` | 380 |
| Robustez | Control `encolarVentaCaja` | `parcial2/web/src/app/services/offline.service.ts` | 109 |
| Robustez | Control `sincronizarPendientes` | `parcial2/web/src/app/services/offline.service.ts` | 49 |
| Robustez | Control `sincronizar` (cliente) | `parcial2/web/src/app/services/offline.service.ts` | 181 |
| Robustez | Control `actualizarOperacion` | `parcial2/web/src/app/services/offline.service.ts` | 135 |
| Robustez | Boundary `POST /offline/sincronizar` | `parcial2/backend/app/modules/offline/sincronizacion.py` | 35 |
| Robustez | Control `offline.sincronizacion.sincronizar` | `parcial2/backend/app/modules/offline/sincronizacion.py` | 36 |
| Clases | Entity `OperacionLog` | `parcial2/backend/app/models/operacion.py` | 9 |
| Clases | Entity `Venta` | `parcial2/backend/app/models/negocio.py` | 163 |
| Clases | Entity `DetalleVenta` | `parcial2/backend/app/models/negocio.py` | 200 |
| Clases | Entity `Pago` | `parcial2/backend/app/models/negocio.py` | 210 |
| Clases | Entity `OperacionLocal` (interface) | `parcial2/web/src/app/services/offline.service.ts` | 15 |
