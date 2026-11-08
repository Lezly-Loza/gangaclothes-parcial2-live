import { Component, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BarraTienda } from '../../shared/tienda/barra-tienda';
import { SesionStore } from '../../core/sesion';
import { OfflineService, CopiaOffline, OpcionOffline, OperacionLocal, ocupaCopia } from '../../services/offline.service';

@Component({ selector: 'app-modo-offline', imports: [FormsModule, BarraTienda], template: `
  <app-barra-tienda />
  <main class="contenido">
    <h1>Catálogo sin conexión</h1>
    <p>Descarga una copia mientras tengas internet. Los precios y existencias pueden cambiar.</p>
    <section class="tarjeta">
      <label>Sucursal <select class="campo" [(ngModel)]="sucursalId"><option value="">Elige una sucursal</option>
        @for (s of sucursales(); track s.id) { <option [value]="s.id">{{ s.nombre }}</option> }</select></label>
      <label>Categoría <select class="campo" [(ngModel)]="categoria"><option value="">Todas</option>
        @for (c of categorias(); track c.id) { <option [value]="c.id">{{ c.nombre }}</option> }</select></label>
      <label>Temporada <select class="campo" [(ngModel)]="temporada"><option value="">Todas</option>
        @for (t of temporadas(); track t.id) { <option [value]="t.id">{{ t.nombre }}</option> }</select></label>
      <button class="btn rosa" (click)="prepararOffline(categoria, temporada)" [disabled]="cargando() || !sucursalId">{{ cargando() ? 'Descargando…' : 'Descargar selección' }}</button>
      @if (mensaje()) { <p role="status">{{ mensaje() }}</p> }
    </section>
    @if (copia(); as guardado) {
      <section class="tarjeta"><h2>{{ guardado.catalogo.productos.length }} prendas guardadas · {{ guardado.sucursal.nombre }}</h2>
        <p>Última descarga: {{ guardado.catalogo.fecha_descarga }}. El precio y stock son de ese momento y pueden cambiar.</p>
        @for (p of guardado.catalogo.productos; track p.id) {
          <article><b>{{ p.nombre }}</b><span>Desde Bs {{ p.precio_base }}</span>
            @for (v of variantes(p.id); track v.id) { <p>{{ v.sku }} · Bs {{ v.precio }} · {{ disponibleLocal(v.id) }} disponibles localmente</p> }
          </article>
        } @empty { <p>La selección descargada no contiene prendas.</p> }
      </section>
      <section class="tarjeta"><h2>Registrar operación local</h2>
        <p>Se guarda en este dispositivo y queda pendiente hasta sincronizar. El stock y precio pueden cambiar.</p>
        <label>Operación <select class="campo" [(ngModel)]="tipoOperacion">
          @if (esCliente) { <option value="reserva">Reserva</option> }
          @if (esPersonal) { <option value="venta">Venta de contado</option> }
        </select></label>
        <label>Prenda y variante <select class="campo" [(ngModel)]="varianteId"><option value="">Elige una variante</option>
          @for (v of guardado.catalogo.variantes; track v.id) { <option [value]="v.id">{{ nombrePrenda(v.producto_id) }} · {{ v.sku }} · Bs {{ v.precio }} · {{ disponibleLocal(v.id) }} disponibles</option> }
        </select></label>
        <label>Cantidad <input class="campo" type="number" min="1" [(ngModel)]="cantidad" /></label>
        @if (tipoOperacion === 'reserva') { <label>Fecha de visita <input class="campo" type="datetime-local" [(ngModel)]="fechaPrueba" /></label> }
        @if (tipoOperacion === 'venta') { <label>Efectivo recibido <input class="campo" type="number" min="0" step="0.01" [(ngModel)]="montoRecibido" /></label>
          <p>Registra solo efectivo realmente recibido. Si cambia el precio o el stock, la operación quedará en conflicto y requiere revisión.</p> }
        <button class="btn rosa" [disabled]="guardando() || !varianteId" (click)="registrarLocal()">Guardar operación pendiente</button>
        @if (mensaje()) { <p role="status">{{ mensaje() }}</p> }
      </section>
    } @else { <p>Aún no hay un catálogo descargado para esta cuenta en este dispositivo.</p> }
    <section class="tarjeta"><h2>Operaciones locales</h2>
      <p>Las operaciones y sus resultados pertenecen a esta cuenta y dispositivo. Se sincronizan al recuperar conexión o volver a abrir la aplicación.</p>
      <button class="btn rosa" (click)="sincronizar()" [disabled]="sincronizando() || operaciones().length === 0">{{ sincronizando() ? 'Sincronizando…' : 'Sincronizar pendientes' }}</button>
      @if (mensaje()) { <p role="status">{{ mensaje() }}</p> }
      @for (op of operaciones(); track op.uuid_operacion) {
        <article><b>{{ op.tipo === 'venta' ? 'Venta de contado' : 'Reserva' }} · {{ op.nombre }} · {{ op.sku }}</b>
          <p>{{ op.sucursal }} · {{ op.cantidad }} × Bs {{ op.precio_unitario }} · {{ op.estado === 'pendiente' ? 'Pendiente: aún no confirmada' : op.estado === 'conflicto' ? 'No confirmada' : 'Confirmada' }} @if (op.codigo) { · Código {{ op.codigo }} }</p>
          @if (op.error) { <p role="alert">{{ op.error }}</p> }
          @if (op.estado === 'conflicto') { <p>Revisa el stock o precio en línea. Puedes descartar esta operación y crear otra con datos actualizados.</p> }
          @if (op.estado !== 'pendiente') { <button class="btn linea" (click)="quitar(op)">{{ op.estado === 'conflicto' ? 'Descartar conflicto' : 'Quitar del historial local' }}</button> }
        </article>
      } @empty { <p>No hay operaciones guardadas.</p> }
    </section>
    <p>Para abrir la aplicación sin internet, instálala y ábrela al menos una vez con conexión.</p>
  </main>
`, styles: [`.contenido{max-width:950px;margin:28px auto;padding:0 20px}h1{font-size:24px;font-weight:800}h2{font-size:17px;font-weight:800}.tarjeta{background:white;border:1px solid var(--linea);border-radius:12px;padding:18px;margin:16px 0}label{display:inline-flex;flex-direction:column;gap:5px;margin:8px 12px 8px 0}.tarjeta>button{margin-top:12px}article{border-top:1px solid var(--linea);padding:10px 0}article span{float:right}article p{font-size:13px;color:var(--gris)}`] })
export class ModoOfflinePage {
  private servicio = inject(OfflineService); private sesion = inject(SesionStore);
  readonly esCliente = this.sesion.tieneAlgunRol('cliente') && this.sesion.tienePermiso('reservas:crear');
  readonly esPersonal = this.sesion.roles().some(r => r !== 'cliente' && r !== 'proveedor') && this.sesion.tienePermiso('ventas:crear');
  readonly copia = signal<CopiaOffline | null>(null); readonly sucursales = signal<OpcionOffline[]>([]);
  readonly categorias = signal<OpcionOffline[]>([]); readonly temporadas = signal<OpcionOffline[]>([]);
  readonly cargando = signal(false); readonly mensaje = signal(''); readonly guardando = signal(false);
  readonly sincronizando = signal(false); readonly operaciones = signal<OperacionLocal[]>([]);
  tipoOperacion: 'reserva' | 'venta' = this.esCliente ? 'reserva' : 'venta'; varianteId = ''; cantidad = 1;
  montoRecibido: number | null = null; fechaPrueba = ''; sucursalId = ''; categoria = ''; temporada = '';
  constructor() {
    void this.abrirModoOffline(); void this.cargarOperaciones();
    effect(() => { this.servicio.revision(); void this.cargarOperaciones(); });
  }
  async abrirModoOffline() {
    try {
      const guardado = await this.servicio.obtenerCatalogoLocal();
      if (guardado) { this.copia.set(guardado); this.sucursales.set(guardado.sucursales); this.sucursalId = String(guardado.sucursal.id);
        this.categoria = guardado.categoria; this.temporada = guardado.temporada;
        this.categorias.set(guardado.catalogo.categorias); this.temporadas.set(guardado.catalogo.temporadas); }
      if (navigator.onLine) {
        const [sucursales, opciones] = await Promise.all([this.servicio.sucursales(), this.servicio.opciones()]);
        this.sucursales.set(sucursales); this.categorias.set(opciones.categorias); this.temporadas.set(opciones.temporadas);
        if (!this.sucursalId && sucursales.length) this.sucursalId = String(sucursales[0].id);
      }
    } catch { this.mensaje.set('No se pudo consultar la conexión o la copia local.'); }
  }
  async prepararOffline(categoria: string, temporada: string) {
    const sucursal = this.sucursales().find(s => s.id === Number(this.sucursalId)); if (!sucursal) return;
    this.cargando.set(true); this.mensaje.set('');
    try { const confirmadasAntes = (await this.servicio.operaciones()).filter(o => o.estado === 'confirmada').map(o => o.uuid_operacion);
      const catalogo = await this.servicio.descargarCatalogo(sucursal.id, categoria, temporada);
      const copia = { catalogo, sucursal, sucursales: this.sucursales(), categoria, temporada };
      await this.servicio.guardarCatalogoLocal(copia, confirmadasAntes); await this.cargarOperaciones(); this.copia.set(copia); this.mensaje.set('Selección guardada en este dispositivo.'); this.mostrarDisponibles();
    } catch { this.mensaje.set('No se pudo descargar o guardar. La copia anterior se conserva.'); }
    finally { this.cargando.set(false); }
  }
  mostrarDisponibles() { return this.copia()?.catalogo.productos.length ?? 0; }
  variantes(id: number) { return this.copia()?.catalogo.variantes.filter(v => v.producto_id === id) ?? []; }
  nombrePrenda(id: number) { return this.copia()?.catalogo.productos.find(p => p.id === id)?.nombre ?? 'Prenda'; }
  disponibleLocal(id: number) {
    const v = this.copia()?.catalogo.variantes.find(v => v.id === id); const sucursal = this.copia()?.sucursal.id;
    const apartados = this.operaciones().filter(o => o.sucursal_id === sucursal && o.variante_id === id && ocupaCopia(o)).reduce((n, o) => n + o.cantidad, 0);
    return Math.max(0, (v?.stock ?? 0) - apartados);
  }
  async cargarOperaciones() { try { this.operaciones.set(await this.servicio.operaciones()); } catch { this.mensaje.set('No se pudieron leer las operaciones guardadas.'); } }
  async registrarLocal() {
    const copia = this.copia(); const v = copia?.catalogo.variantes.find(x => x.id === Number(this.varianteId));
    if (!copia || !v || !Number.isInteger(Number(this.cantidad)) || Number(this.cantidad) < 1 || Number(this.cantidad) > 100) { this.mensaje.set('Elige una variante y una cantidad entre 1 y 100.'); return; }
    if ((this.tipoOperacion === 'reserva' && !this.esCliente) || (this.tipoOperacion === 'venta' && !this.esPersonal)) { this.mensaje.set('Tu cuenta no puede registrar esta operación.'); return; }
    if (this.tipoOperacion === 'reserva' && (!this.fechaPrueba || new Date(this.fechaPrueba).getTime() <= Date.now())) { this.mensaje.set('Elige una fecha de visita futura.'); return; }
    if (this.tipoOperacion === 'venta' && (this.montoRecibido === null || !Number.isFinite(Number(this.montoRecibido)) || Number(this.montoRecibido) < v.precio * Number(this.cantidad) || Math.abs(Number(this.montoRecibido) * 100 - Math.round(Number(this.montoRecibido) * 100)) > 0.00001)) { this.mensaje.set('El efectivo debe cubrir el total y tener hasta dos decimales.'); return; }
    this.guardando.set(true);
    try {
      await this.servicio.guardarOperacion({ tipo: this.tipoOperacion, sucursal_id: copia.sucursal.id, variante_id: v.id,
        cantidad: Number(this.cantidad), precio_unitario: v.precio, monto_recibido: this.tipoOperacion === 'venta' ? Number(this.montoRecibido) : null,
        fecha_hora_prueba: this.tipoOperacion === 'reserva' ? this.fechaPrueba : null, fecha_local: new Date().toISOString(),
        nombre: this.nombrePrenda(v.producto_id), sku: v.sku, sucursal: copia.sucursal.nombre });
      await this.cargarOperaciones(); this.mensaje.set('Operación guardada localmente. Aún no está confirmada por el servidor.');
    } catch (err) { this.mensaje.set(err instanceof Error ? err.message : 'No se pudo guardar la operación.'); }
    finally { this.guardando.set(false); }
  }
  async sincronizar() {
    if (this.sincronizando()) return; this.sincronizando.set(true);
    try { await this.servicio.sincronizarPendientes(true);
      await this.cargarOperaciones(); this.mensaje.set('Sincronización terminada. Revisa los estados y conflictos.');
    } catch { await this.cargarOperaciones(); this.mensaje.set('No se pudo conectar o la sesión venció. Las operaciones se conservan para reintentar.'); }
    finally { this.sincronizando.set(false); }
  }
  async quitar(op: OperacionLocal) {
    if (!confirm(op.estado === 'conflicto' ? '¿Descartar esta operación en conflicto? Si recibiste efectivo, resuélvelo con el cliente.' : '¿Quitar este resultado confirmado del historial local?')) return;
    try { await this.servicio.quitarOperacion(op); await this.cargarOperaciones(); } catch (err) { this.mensaje.set(err instanceof Error ? err.message : 'No se pudo quitar la operación.'); }
  }
}
