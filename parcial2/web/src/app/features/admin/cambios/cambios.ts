import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { API_URL } from '../../../core/api';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { FilaInventario } from '../../inventario/inventario/inventario';

interface VentaCambio { id: number; codigo: string; sucursal_id: number; estado: string; total: number; detalles: { variante_id: number; cantidad: number }[]; }
interface VentaReciente { codigo: string; estado: string; sucursal: string; total: number; fecha: string | null; }
interface Cotizacion { precio_pagado: number; precio_nuevo: number; diferencia: number; cobrar: number; devolver: number; plazo_dias: number; aviso: string; }

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
        <select id="devuelta" class="campo" [(ngModel)]="varianteDevuelta" (ngModelChange)="solicitarCotizacion()">
          <option [ngValue]="null">Selecciona una prenda</option>
          @for (detalle of actual.detalles; track $index) {
            <option [ngValue]="detalle.variante_id">{{ nombreVariante(detalle.variante_id) }} · {{ detalle.cantidad }} unidad(es)</option>
          }
        </select>
        <label class="etiqueta" for="nueva">Prenda que recibe o tipo de compensación</label>
        <select id="nueva" class="campo" [(ngModel)]="varianteNueva" (ngModelChange)="solicitarCotizacion()">
          <option [ngValue]="null">Selecciona una opción</option>
          <option [ngValue]="-1">● Devolución monetaria en efectivo (reembolso directo al cliente en caja)</option>
          @for (fila of inventario(); track fila.variante_id) {
            @if (fila.disponible > 0) { <option [ngValue]="fila.variante_id">{{ fila.sku }} · {{ fila.prenda }} · {{ fila.talla }} · {{ fila.color }} ({{ fila.disponible }} disponibles)</option> }
          }
        </select>
        @if (cotizando()) { <p>Calculando diferencia…</p> }
        @if (errorCotizacion()) { <p role="alert">{{ errorCotizacion() }}</p> }
        @if (cotizacion(); as c) {
          <div class="resultado" role="status">
            <p>Pagó por la prenda devuelta: <b>Bs {{ c.precio_pagado.toFixed(2) }}</b> · Prenda nueva: <b>Bs {{ c.precio_nuevo.toFixed(2) }}</b></p>
            @if (c.devolver > 0) { <p><b>Devolver al cliente: Bs {{ c.devolver.toFixed(2) }}</b> (en efectivo de caja)</p> }
            @else if (c.cobrar > 0) { <p><b>Cobrar al cliente: Bs {{ c.cobrar.toFixed(2) }}</b></p> }
            @else { <p><b>Sin diferencia de precio.</b></p> }
            <p>Plazo de la empresa: {{ c.plazo_dias }} días. {{ c.aviso }}</p>
          </div>
        }
        <label class="etiqueta" for="motivo">Motivo</label><input id="motivo" class="campo" [(ngModel)]="motivo">
        <button class="btn rosa" (click)="cambiar(actual, varianteNueva, motivo)" [disabled]="guardando() || cotizando() || !cotizacion() || !varianteDevuelta || varianteNueva === null || !motivo.trim()">{{ guardando() ? 'Procesando…' : (varianteNueva === -1 ? 'Registrar devolución en efectivo' : 'Registrar cambio') }}</button>
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
  readonly cotizando = signal(false); readonly cotizacion = signal<Cotizacion | null>(null); readonly errorCotizacion = signal('');
  private versionCotizacion = 0;
  readonly recientes = signal<VentaReciente[]>([]); readonly errorRecientes = signal('');
  constructor() { this.http.get<VentaReciente[]>(`${API_URL}/operaciones/recientes?tipo=ventas`).subscribe({
    next: filas => this.recientes.set(filas), error: e => this.errorRecientes.set(mensajeDeError(e, 'No se pudieron cargar las ventas recientes.')) }); }
  seleccionarVenta(codigo: string) { if (codigo) { this.codigo = codigo; this.buscarVenta(codigo); } }
  buscarVenta(codigo: string) {
    if (!codigo.trim()) return;
    this.venta.set(null); this.comprobante.set(''); this.cotizacion.set(null); this.errorCotizacion.set(''); this.versionCotizacion++;
    this.http.get<VentaCambio>(`${API_URL}/ventas/${encodeURIComponent(codigo.trim())}`).subscribe({
      next: venta => this.http.get<FilaInventario[]>(`${API_URL}/inventario`, { params: { sucursal_id: venta.sucursal_id } }).subscribe({
        next: filas => { this.inventario.set(filas); this.venta.set(venta); this.varianteDevuelta = null; this.varianteNueva = null; },
        error: e => this.avisos.error(mensajeDeError(e, 'No se pudo cargar el inventario de la sucursal')),
      }), error: e => this.avisos.error(mensajeDeError(e, 'Venta no encontrada')),
    });
  }
  nombreVariante(id: number) { const f = this.inventario().find(x => x.variante_id === id); return f ? `${f.sku} · ${f.prenda} · ${f.talla} · ${f.color}` : `Variante #${id}`; }
  solicitarCotizacion() {
    const version = ++this.versionCotizacion; const venta = this.venta();
    this.cotizacion.set(null); this.errorCotizacion.set('');
    if (!venta || !this.varianteDevuelta || this.varianteNueva === null) { this.cotizando.set(false); return; }
    this.cotizando.set(true);
    const nuevaId = this.varianteNueva === -1 ? null : this.varianteNueva;
    this.http.post<Cotizacion>(`${API_URL}/cambios/cotizar`, { venta_id: venta.id, variante_devuelta_id: this.varianteDevuelta, variante_nueva_id: nuevaId }).subscribe({
      next: r => { if (version === this.versionCotizacion) { this.cotizacion.set(r); this.cotizando.set(false); } },
      error: e => { if (version === this.versionCotizacion) { this.errorCotizacion.set(mensajeDeError(e, 'No se pudo calcular la diferencia')); this.cotizando.set(false); } },
    });
  }
  cambiar(item: VentaCambio, nueva: number | null, motivo: string) {
    const cotizacion = this.cotizacion();
    if (!this.varianteDevuelta || nueva === null || !motivo.trim() || !cotizacion) return;
    const nuevaId = nueva === -1 ? null : nueva;
    this.guardando.set(true);
    this.http.post<{ id: number; diferencia: number; cobrar: number; devolver: number }>(`${API_URL}/cambios`, { venta_id: item.id, variante_devuelta_id: this.varianteDevuelta, variante_nueva_id: nuevaId, motivo: motivo.trim(), diferencia_esperada: cotizacion.diferencia }).subscribe({
      next: r => {
        this.guardando.set(false); this.venta.set(null);
        const accion = nuevaId === null ? 'Devolución monetaria en efectivo' : 'Cambio de prenda';
        const ajuste = r.devolver > 0 ? `Devolver al cliente en efectivo Bs ${r.devolver.toFixed(2)}` : r.cobrar > 0 ? `Cobrar al cliente Bs ${r.cobrar.toFixed(2)}` : 'Sin diferencia de precio';
        this.comprobante.set(`${accion} #${r.id} registrado con éxito. ${ajuste}.`);
        this.avisos.ok(`${accion} #${r.id} registrado correctamente.`);
      },
      error: e => { this.guardando.set(false); this.avisos.error(mensajeDeError(e, 'No se pudo registrar la operación')); this.solicitarCotizacion(); },
    });
  }
  mostrarComprobante() { return this.comprobante(); }
}
