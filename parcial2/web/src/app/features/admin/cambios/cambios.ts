import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { API_URL } from '../../../core/api';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { FilaInventario } from '../../inventario/inventario/inventario';

interface VentaCambio { id: number; codigo: string; sucursal_id: number; estado: string; total: number; detalles: { variante_id: number; cantidad: number }[]; }
interface VentaReciente { codigo: string; estado: string; sucursal: string; total: number; fecha: string | null; }

@Component({
  selector: 'app-cambios', imports: [FormsModule],
  template: `
    <div class="cabecera"><div class="ceja">Cambios de prendas</div><h1>Cambio de prenda</h1></div>
    <section class="tarjeta">
      <p>El código aparece en el comprobante de caja. También puedes elegir una venta reciente:</p>
      <label class="etiqueta" for="recientes">Ventas recientes</label>
      <select id="recientes" class="campo" (change)="seleccionarVenta($any($event.target).value)">
        <option value="">Selecciona una venta</option>
        @for (v of recientes(); track v.codigo) { <option [value]="v.codigo">{{ v.codigo }} · {{ v.fecha?.slice(0, 10) }} · {{ v.sucursal }} · Bs {{ v.total }} · {{ v.estado }}</option> }
      </select>
      @if (errorRecientes()) { <p>{{ errorRecientes() }}</p> }
      <label class="etiqueta" for="codigo">Código de venta</label>
      <div class="fila"><input id="codigo" class="campo" [(ngModel)]="codigo" (keydown.enter)="buscarVenta(codigo)" placeholder="Código del comprobante">
      <button class="btn linea" (click)="buscarVenta(codigo)">Buscar</button></div>
    </section>
    @if (venta(); as actual) {
      <section class="tarjeta">
        <h2>Venta {{ actual.codigo }} · {{ actual.estado }}</h2>
        <label class="etiqueta" for="devuelta">Prenda que devuelve</label>
        <select id="devuelta" class="campo" [(ngModel)]="varianteDevuelta">
          <option [ngValue]="null">Selecciona una prenda</option>
          @for (detalle of actual.detalles; track $index) {
            <option [ngValue]="detalle.variante_id">{{ nombreVariante(detalle.variante_id) }} · {{ detalle.cantidad }} unidad(es)</option>
          }
        </select>
        <label class="etiqueta" for="nueva">Prenda que recibe</label>
        <select id="nueva" class="campo" [(ngModel)]="varianteNueva">
          <option [ngValue]="null">Selecciona una prenda disponible</option>
          @for (fila of inventario(); track fila.variante_id) {
            @if (fila.disponible > 0) { <option [ngValue]="fila.variante_id">{{ fila.sku }} · {{ fila.prenda }} · {{ fila.talla }} · {{ fila.color }} ({{ fila.disponible }} disponibles)</option> }
          }
        </select>
        <label class="etiqueta" for="motivo">Motivo</label><input id="motivo" class="campo" [(ngModel)]="motivo">
        <button class="btn rosa" (click)="cambiar(actual, varianteNueva, motivo)" [disabled]="guardando() || !varianteDevuelta || !varianteNueva || !motivo.trim()">{{ guardando() ? 'Procesando…' : 'Registrar cambio' }}</button>
      </section>
    }
    @if (comprobante()) { <p class="resultado">{{ comprobante() }}</p> }
  `,
  styles: [`.cabecera{margin-bottom:16px} h1{font-size:22px;font-weight:800} h2{font-size:16px}.tarjeta{background:white;border:1px solid var(--linea);border-radius:12px;padding:18px;margin-bottom:14px;max-width:720px}.fila{display:flex;gap:8px}.fila input{flex:1}.etiqueta{display:block;margin:12px 0 5px}.tarjeta>.btn{margin-top:16px}.resultado{padding:12px;background:#e4f2ec}`],
})
export class CambioPrendaPage {
  private http = inject(HttpClient); private avisos = inject(Notificaciones);
  codigo = ''; motivo = ''; varianteDevuelta: number | null = null; varianteNueva: number | null = null;
  readonly venta = signal<VentaCambio | null>(null); readonly inventario = signal<FilaInventario[]>([]);
  readonly guardando = signal(false); readonly comprobante = signal('');
  readonly recientes = signal<VentaReciente[]>([]); readonly errorRecientes = signal('');
  constructor() { this.http.get<VentaReciente[]>(`${API_URL}/operaciones/recientes?tipo=ventas`).subscribe({
    next: filas => this.recientes.set(filas), error: e => this.errorRecientes.set(mensajeDeError(e, 'No se pudieron cargar las ventas recientes.')) }); }
  seleccionarVenta(codigo: string) { if (codigo) { this.codigo = codigo; this.buscarVenta(codigo); } }
  buscarVenta(codigo: string) {
    if (!codigo.trim()) return;
    this.venta.set(null); this.comprobante.set('');
    this.http.get<VentaCambio>(`${API_URL}/ventas/${encodeURIComponent(codigo.trim())}`).subscribe({
      next: venta => this.http.get<FilaInventario[]>(`${API_URL}/inventario`, { params: { sucursal_id: venta.sucursal_id } }).subscribe({
        next: filas => { this.inventario.set(filas); this.venta.set(venta); this.varianteDevuelta = null; this.varianteNueva = null; },
        error: e => this.avisos.error(mensajeDeError(e, 'No se pudo cargar el inventario de la sucursal')),
      }), error: e => this.avisos.error(mensajeDeError(e, 'Venta no encontrada')),
    });
  }
  nombreVariante(id: number) { const f = this.inventario().find(x => x.variante_id === id); return f ? `${f.sku} · ${f.prenda} · ${f.talla} · ${f.color}` : `Variante #${id}`; }
  cambiar(item: VentaCambio, nueva: number | null, motivo: string) {
    if (!this.varianteDevuelta || !nueva || !motivo.trim()) return;
    this.guardando.set(true);
    this.http.post<{ id: number; diferencia: number }>(`${API_URL}/cambios`, { venta_id: item.id, variante_devuelta_id: this.varianteDevuelta, variante_nueva_id: nueva, motivo: motivo.trim() }).subscribe({
      next: r => { this.guardando.set(false); this.venta.set(null); this.comprobante.set(`Cambio ${r.id} registrado. Diferencia de precio: Bs ${Number(r.diferencia).toFixed(2)}.`); this.mostrarComprobante(); },
      error: e => { this.guardando.set(false); this.avisos.error(mensajeDeError(e, 'No se pudo registrar el cambio')); },
    });
  }
  mostrarComprobante() { return this.comprobante(); }
}
