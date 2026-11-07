import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BarraTienda } from '../../shared/tienda/barra-tienda';
import { OfflineService, CopiaOffline, OpcionOffline } from '../../services/offline.service';

@Component({ selector: 'app-modo-offline', imports: [FormsModule, BarraTienda], template: `
  <app-barra-tienda />
  <main class="contenido">
    <h1>Catálogo sin conexión</h1>
    <p>Descarga una copia mientras tengas internet. Luego podrás consultar esta selección en este dispositivo.</p>
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
            @for (v of variantes(p.id); track v.id) { <p>{{ v.sku }} · Bs {{ v.precio }} · {{ v.stock }} disponibles al descargar</p> }
          </article>
        } @empty { <p>La selección descargada no contiene prendas.</p> }
      </section>
    } @else { <p>Aún no hay un catálogo descargado para esta cuenta en este dispositivo.</p> }
    <p>La copia permite consultar, no reservar ni comprar sin conexión. Para abrir la aplicación sin internet, instálala y ábrela al menos una vez con conexión.</p>
  </main>
`, styles: [`.contenido{max-width:950px;margin:28px auto;padding:0 20px}h1{font-size:24px;font-weight:800}h2{font-size:17px;font-weight:800}.tarjeta{background:white;border:1px solid var(--linea);border-radius:12px;padding:18px;margin:16px 0}label{display:inline-flex;flex-direction:column;gap:5px;margin:8px 12px 8px 0}.tarjeta>button{margin-top:12px}article{border-top:1px solid var(--linea);padding:10px 0}article span{float:right}article p{font-size:13px;color:var(--gris)}`] })
export class ModoOfflinePage {
  private servicio = inject(OfflineService);
  readonly copia = signal<CopiaOffline | null>(null); readonly sucursales = signal<OpcionOffline[]>([]);
  readonly categorias = signal<OpcionOffline[]>([]); readonly temporadas = signal<OpcionOffline[]>([]);
  readonly cargando = signal(false); readonly mensaje = signal('');
  sucursalId = ''; categoria = ''; temporada = '';
  constructor() { void this.abrirModoOffline(); }
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
    } catch { this.mensaje.set('No se pudo consultar la conexión o la copia local. Intenta nuevamente con internet.'); }
  }
  async prepararOffline(categoria: string, temporada: string) {
    const sucursal = this.sucursales().find(s => s.id === Number(this.sucursalId));
    if (!sucursal) return;
    this.cargando.set(true); this.mensaje.set('');
    try {
      const catalogo = await this.servicio.descargarCatalogo(sucursal.id, categoria, temporada);
      const copia = { catalogo, sucursal, sucursales: this.sucursales(), categoria, temporada };
      await this.servicio.guardarCatalogoLocal(copia); this.copia.set(copia);
      this.mensaje.set('Selección guardada en este dispositivo.'); this.mostrarDisponibles();
    } catch { this.mensaje.set('No se pudo descargar o guardar. La copia anterior se conserva.'); }
    finally { this.cargando.set(false); }
  }
  mostrarDisponibles() { return this.copia()?.catalogo.productos.length ?? 0; }
  variantes(id: number) { return this.copia()?.catalogo.variantes.filter(v => v.producto_id === id) ?? []; }
}
