import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { API_URL } from '../../../core/api';
import { SesionStore } from '../../../core/sesion';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

interface Operacion { id: number; codigo: string; estado: string; }
interface OperacionReciente { codigo: string; estado: string; sucursal: string; total: number | null; fecha: string | null; }

@Component({ selector: 'app-anular', imports: [FormsModule],
  template: `
    <div class="cabecera"><div class="ceja">Anular operación</div><h1>Anular venta o reserva</h1></div>
    <section class="tarjeta">
      <label class="etiqueta" for="tipo">Tipo de operación</label>
      <select id="tipo" class="campo" [(ngModel)]="tipo" (ngModelChange)="cargarRecientes()">
        @if (puedeVenta) { <option value="ventas">Venta</option> }
        @if (puedeReserva) { <option value="reservas">Reserva</option> }
      </select>
      <p>El código aparece en el comprobante o en la confirmación de la reserva. También puedes elegir una operación reciente.</p>
      <label class="etiqueta" for="recientes">Operaciones recientes</label>
      <select id="recientes" class="campo" (change)="seleccionarOperacion($any($event.target).value)">
        <option value="">Selecciona una operación</option>
        @for (r of recientes(); track r.codigo) { <option [value]="r.codigo">{{ r.codigo }} · {{ tipo === 'reservas' ? 'vence ' : '' }}{{ r.fecha?.slice(0, 10) }} · {{ r.sucursal }} · {{ r.estado }}</option> }
      </select>
      @if (errorRecientes()) { <p>{{ errorRecientes() }}</p> }
      <label class="etiqueta" for="codigo">Código</label>
      <div class="fila"><input id="codigo" class="campo" [(ngModel)]="codigo" (keydown.enter)="buscarOperacion()" placeholder="Código de venta o reserva"><button class="btn linea" (click)="buscarOperacion()">Buscar</button></div>
      @if (operacion(); as actual) {
        <p>Operación {{ actual.codigo }} · Estado: {{ actual.estado }}</p>
        <label class="etiqueta" for="motivo">Motivo</label><textarea id="motivo" class="campo" [(ngModel)]="motivo" rows="3"></textarea>
        <button class="btn peligro" [disabled]="guardando() || !motivo.trim() || actual.estado === 'ANULADA'" (click)="anular(actual.id, motivo)">{{ guardando() ? 'Anulando…' : 'Anular operación' }}</button>
      }
      @if (mensaje()) { <p class="resultado">{{ mensaje() }}</p> }
    </section>
  `,
  styles: [`.cabecera{margin-bottom:16px}h1{font-size:22px;font-weight:800}.tarjeta{background:white;border:1px solid var(--linea);border-radius:12px;padding:18px;max-width:620px}.fila{display:flex;gap:8px}.fila input{flex:1}.etiqueta{display:block;margin:12px 0 5px}.tarjeta>.btn{margin-top:16px}.resultado{padding:12px;background:#e4f2ec}`],
})
export class AnularOperacionDialog {
  private http = inject(HttpClient); private avisos = inject(Notificaciones); private sesion = inject(SesionStore);
  readonly puedeVenta = this.sesion.permisos().includes('ventas:anular');
  readonly puedeReserva = this.sesion.permisos().includes('reservas:anular');
  tipo: 'ventas' | 'reservas' = this.puedeVenta ? 'ventas' : 'reservas'; codigo = ''; motivo = '';
  readonly operacion = signal<Operacion | null>(null); readonly mensaje = signal(''); readonly guardando = signal(false);
  readonly recientes = signal<OperacionReciente[]>([]); readonly errorRecientes = signal('');
  constructor() { this.cargarRecientes(); }
  cargarRecientes() {
    this.operacion.set(null); this.errorRecientes.set('');
    this.http.get<OperacionReciente[]>(`${API_URL}/operaciones/recientes`, { params: { tipo: this.tipo } }).subscribe({
      next: filas => this.recientes.set(filas), error: e => { this.recientes.set([]); this.errorRecientes.set(mensajeDeError(e, 'No se pudieron cargar las operaciones recientes.')); },
    });
  }
  seleccionarOperacion(codigo: string) { if (codigo) { this.codigo = codigo; this.buscarOperacion(); } }
  buscarOperacion() {
    if (!this.codigo.trim()) return;
    this.operacion.set(null); this.mensaje.set('');
    const codigo = encodeURIComponent(this.codigo.trim());
    const ruta = this.tipo === 'ventas' ? `ventas/${codigo}` : `reservas/buscar/${codigo}`;
    this.http.get<Operacion>(`${API_URL}/${ruta}`).subscribe({ next: r => this.operacion.set(r), error: e => this.avisos.error(mensajeDeError(e, 'Operación no encontrada')) });
  }
  anular(id: number, motivo: string) {
    if (!motivo.trim()) return;
    this.guardando.set(true);
    this.http.post<Operacion>(`${API_URL}/${this.tipo}/${id}/anular`, { motivo: motivo.trim() }).subscribe({
      next: r => { this.guardando.set(false); this.cargarRecientes(); this.operacion.set(r); this.mensaje.set(`${r.codigo}: ${r.estado}`); this.mostrarAnulada(); },
      error: e => { this.guardando.set(false); this.avisos.error(mensajeDeError(e, 'No se pudo anular la operación')); },
    });
  }
  mostrarAnulada() { this.avisos.ok('Operación anulada'); return this.mensaje(); }
}
