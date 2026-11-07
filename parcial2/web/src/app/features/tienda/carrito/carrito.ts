import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { moneda } from '../../../shared/formato';
import { BarraTienda } from '../../../shared/tienda/barra-tienda';

interface Linea { id: number; prenda: string; talla: string; color: string; cantidad: number; precio_final: number; subtotal: number; disponible: number; alcanza: boolean; }
interface CarritoDatos { sucursal: string; unidades: number; total: number; detalle: Linea[]; }

@Component({ selector: 'app-carrito', imports: [RouterLink, BarraTienda], templateUrl: './carrito.html', styleUrl: './carrito.css' })
export class Carrito {
  private http = inject(HttpClient);
  readonly moneda = moneda;
  readonly carrito = signal<CarritoDatos | null>(null);
  readonly cargando = signal(true);
  readonly ocupado = signal(false);
  readonly error = signal<string | null>(null);
  readonly compra = signal<{codigo: string; total: number} | null>(null);
  readonly delivery = signal(false);
  readonly direccion = signal('');
  readonly latitud = signal('');
  readonly longitud = signal('');
  readonly referencia = signal('');
  readonly telefono = signal('');
  constructor() { this.cargar(); }
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
    if (this.delivery() && (!this.direccion().trim() || !this.latitud().trim() || !this.longitud().trim() || !Number.isFinite(Number(this.latitud())) || !Number.isFinite(Number(this.longitud())))) {
      this.error.set('Para el envío indica la dirección y coordenadas válidas.'); return;
    }
    const body = this.delivery() ? { direccion: this.direccion(), latitud: Number(this.latitud()), longitud: Number(this.longitud()), referencia: this.referencia() || null, telefono: this.telefono() || null } : {};
    this.ocupado.set(true); this.error.set(null);
    this.http.post<{codigo: string; total: number}>(`${API_URL}/tienda/carrito/comprar`, body).subscribe({
      next: r => { this.compra.set(r); this.carrito.set(null); this.ocupado.set(false); },
      error: e => { this.error.set(mensajeDeError(e, 'No se pudo registrar la compra.')); this.ocupado.set(false); },
    });
  }
}
