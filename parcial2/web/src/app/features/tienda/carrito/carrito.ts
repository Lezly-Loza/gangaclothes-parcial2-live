import { HttpClient } from '@angular/common/http';
import { Component, OnDestroy, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { moneda } from '../../../shared/formato';
import { BarraTienda } from '../../../shared/tienda/barra-tienda';
import { Comprobantes } from '../../../shared/comprobante';

interface Linea { id: number; prenda: string; talla: string; color: string; cantidad: number; precio_final: number; subtotal: number; disponible: number; alcanza: boolean; }
interface CarritoDatos { sucursal: string; unidades: number; total: number; detalle: Linea[]; }
interface QrDatos { qr_id: string; venta_id: number; estado: string; pendiente: boolean; aprobado: boolean; rechazado: boolean; imagen_base64: string; expira: string; codigo?: string; total?: number; }
interface CompraExitosa { codigo: string; total: number; venta_id?: number; }

@Component({ selector: 'app-carrito', imports: [RouterLink, BarraTienda], templateUrl: './carrito.html', styleUrl: './carrito.css' })
export class Carrito implements OnDestroy {
  private http = inject(HttpClient);
  private comprobantes = inject(Comprobantes);
  readonly moneda = moneda;
  readonly carrito = signal<CarritoDatos | null>(null);
  readonly cargando = signal(true);
  readonly ocupado = signal(false);
  readonly error = signal<string | null>(null);
  readonly compra = signal<CompraExitosa | null>(null);
  readonly metodo = signal<'tarjeta' | 'qr'>('tarjeta');
  readonly numeroTarjeta = signal('');
  readonly qr = signal<QrDatos | null>(null);
  private consultaQrId: number | null = null;
  private consultandoQr = false;
  readonly delivery = signal(false);
  readonly direccion = signal('');
  readonly latitud = signal('');
  readonly longitud = signal('');
  readonly referencia = signal('');
  readonly telefono = signal('');
  constructor() { this.cargar(); }
  ngOnDestroy(): void { this.detenerConsultaQr(); }
  private detenerConsultaQr(): void { if (this.consultaQrId !== null) window.clearInterval(this.consultaQrId); this.consultaQrId = null; }
  cargar(): void {
    this.cargando.set(true); this.error.set(null);
    this.http.get<CarritoDatos | null>(`${API_URL}/tienda/carrito`).subscribe({
      next: c => { this.carrito.set(c); this.cargando.set(false); },
      error: e => { this.error.set(mensajeDeError(e, 'No se pudo cargar el carrito.')); this.cargando.set(false); },
    });
  }
  cantidad(l: Linea, valor: number): void {
    if (valor < 1 || this.ocupado()) return;
    this.actualizar(this.http.put<CarritoDatos>(`${API_URL}/tienda/carrito/items/${l.id}`, { cantidad: valor }));
  }
  quitar(l: Linea): void { this.actualizar(this.http.delete<CarritoDatos>(`${API_URL}/tienda/carrito/items/${l.id}`)); }
  private actualizar(peticion: import('rxjs').Observable<CarritoDatos>): void {
    this.ocupado.set(true); this.error.set(null);
    peticion.subscribe({next: c => { this.carrito.set(c); this.ocupado.set(false); }, error: e => { this.error.set(mensajeDeError(e, 'No se pudo actualizar el carrito.')); this.ocupado.set(false); }});
  }
  ubicar(): void {
    if (!navigator.geolocation) { this.error.set('El navegador no permite obtener la ubicación. Escribe las coordenadas.'); return; }
    navigator.geolocation.getCurrentPosition(p => { this.latitud.set(String(p.coords.latitude)); this.longitud.set(String(p.coords.longitude)); this.error.set(null); }, () => this.error.set('No se pudo obtener la ubicación. Escribe las coordenadas.'));
  }
  comprar(): void {
    if (this.ocupado()) return;
    if (this.metodo() === 'tarjeta' && !this.tarjetaValida(this.numeroTarjeta())) {
      this.error.set('Ingresa un número de prueba válido. 4242 4242 4242 4242 aprueba y 4000 0000 0000 0002 rechaza.'); return;
    }
    if (this.delivery() && (!this.direccion().trim() || !this.latitud().trim() || !this.longitud().trim() || !Number.isFinite(Number(this.latitud())) || !Number.isFinite(Number(this.longitud())))) {
      this.error.set('Para el envío indica la dirección y coordenadas válidas.'); return;
    }
    const body = this.delivery() ? { direccion: this.direccion(), latitud: Number(this.latitud()), longitud: Number(this.longitud()), referencia: this.referencia() || null, telefono: this.telefono() || null } : {};
    this.ocupado.set(true); this.error.set(null);
    const esQr = this.metodo() === 'qr';
    this.http.post<QrDatos | CompraExitosa>(`${API_URL}/pagos/${esQr ? 'qr' : 'tarjeta'}`,
      esQr ? body : {...body, numero_tarjeta: this.numeroTarjeta()}).subscribe({
      next: r => {
        if (esQr) {
          this.qr.set(r as QrDatos);
          this.detenerConsultaQr();
          this.consultaQrId = window.setInterval(() => this.consultarQr(), 4000);
        } else { this.compra.set(r as CompraExitosa); this.carrito.set(null); }
        this.ocupado.set(false);
      },
      error: e => { this.error.set(mensajeDeError(e, 'No se pudo procesar el pago.')); this.ocupado.set(false); },
    });
  }
  consultarQr(): void {
    const actual = this.qr();
    if (!actual || this.consultandoQr) return;
    this.consultandoQr = true;
    this.http.get<QrDatos>(`${API_URL}/pagos/qr/${encodeURIComponent(actual.qr_id)}`).subscribe({
      next: r => {
        this.qr.set({...actual, ...r}); this.error.set(null);
        if (r.aprobado) {
          this.detenerConsultaQr(); this.compra.set({codigo: r.codigo!, total: r.total!, venta_id: r.venta_id});
          this.carrito.set(null); this.qr.set(null);
        } else if (r.rechazado) {
          this.detenerConsultaQr(); this.qr.set(null);
          this.error.set('El QR venció o fue anulado. Puedes intentarlo otra vez.');
        }
        this.consultandoQr = false;
      },
      error: e => { this.error.set(mensajeDeError(e, 'No se pudo consultar el QR.')); this.consultandoQr = false; },
    });
  }
  imprimirComprobante(): void {
    const vId = this.compra()?.venta_id;
    if (vId) this.comprobantes.imprimir(vId);
  }
  descargarComprobante(): void {
    const c = this.compra();
    if (c?.venta_id) this.comprobantes.descargar(c.venta_id, c.codigo);
  }
  private tarjetaValida(valor: string): boolean {
    const digitos = valor.replace(/\s/g, '');
    if (!/^\d{13,19}$/.test(digitos)) return false;
    let suma = 0, doble = false;
    for (let i = digitos.length - 1; i >= 0; i--) {
      let n = Number(digitos[i]); if (doble) { n *= 2; if (n > 9) n -= 9; }
      suma += n; doble = !doble;
    }
    return suma % 10 === 0;
  }
}
