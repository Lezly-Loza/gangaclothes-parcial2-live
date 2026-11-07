import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';

interface DetalleVenta {
  detalle_id: number;
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_unitario: number;
}

interface VentaParaCambio {
  venta_id: number;
  estado: string;
  fecha: string;
  sucursal: string;
  sucursal_id: number;
  total: number;
  dias_desde_compra: number;
  dias_restantes_plazo: number;
  detalle: DetalleVenta[];
}

interface VarianteDisponible {
  id: number;
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  color_hex: string | null;
  disponible: number;
  precio_venta: number;
}

interface ResultadoCambio {
  cambio_id: number;
  venta_id: number;
  devuelta: { variante_id: number; sku: string; prenda: string; talla: string; color: string; precio: number };
  nueva: { variante_id: number; sku: string; prenda: string; talla: string; color: string; precio: number };
  saldo: number;
  saldo_tipo: 'cobrar' | 'devolver' | 'sin_diferencia';
  motivo: string;
  fecha: string;
}

type Paso = 1 | 2 | 3;

/**
 * CU-16: Flujo guiado de 3 pasos para cambio de prendas.
 * Boundary: Este componente expone el formulario reactivo y las interacciones.
 * Paso 1: Buscar venta previa por código/ID.
 * Paso 2: Seleccionar ítem a devolver y motivo.
 * Paso 3: Seleccionar nueva prenda con cálculo en vivo de diferencia monetaria.
 */
@Component({
  selector: 'app-cambios',
  imports: [ReactiveFormsModule],
  templateUrl: './cambios.html',
  styleUrl: './cambios.css',
  host: { '(document:keydown.escape)': 'reiniciar()' },
})
export class Cambios {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private avisos = inject(Notificaciones);

  readonly Math = Math;

  readonly paso = signal<Paso>(1);
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly resultado = signal<ResultadoCambio | null>(null);

  // Paso 1: Búsqueda
  readonly ventaId = signal('');
  readonly ventaData = signal<VentaParaCambio | null>(null);

  // Paso 2: Selección ítem a devolver
  readonly itemSeleccionado = signal<DetalleVenta | null>(null);
  readonly variantesDisponibles = signal<VarianteDisponible[]>([]);
  
  // Paso 3: Selección nueva prenda
  readonly varianteNuevaId = signal<number | null>(null);
  readonly buscador = signal('');

  readonly formMotivo = this.fb.nonNullable.group({
    motivo: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(200)]],
  });

  readonly varianteNueva = computed(() =>
    this.variantesDisponibles().find((v) => v.variante_id === this.varianteNuevaId()) ?? null,
  );

  readonly diferenciaMonetaria = computed(() => {
    const devuelta = this.itemSeleccionado();
    const nueva = this.varianteNueva();
    if (!devuelta || !nueva) return null;
    return nueva.precio_venta - devuelta.precio_unitario;
  });

  readonly variantesFiltradas = computed(() => {
    const texto = this.buscador().toLowerCase().trim();
    const devuelta = this.itemSeleccionado()?.variante_id;
    return this.variantesDisponibles()
      .filter((v) => v.variante_id !== devuelta && v.disponible > 0)
      .filter((v) =>
        !texto || [v.sku, v.prenda, v.talla, v.color].join(' ').toLowerCase().includes(texto),
      );
  });

  // Paso 1: buscar venta
  buscarVenta(): void {
    const id = this.ventaId().trim();
    if (!id || isNaN(Number(id))) {
      this.error.set('Ingresa un número de venta válido.');
      return;
    }
    this.error.set(null);
    this.cargando.set(true);
    this.http.get<VentaParaCambio>(`${API_URL}/ventas/cambio/venta/${id}`).subscribe({
      next: (venta) => {
        this.cargando.set(false);
        this.ventaData.set(venta);
        this.paso.set(2);
      },
      error: (err) => {
        this.cargando.set(false);
        this.error.set(mensajeDeError(err, 'No se encontró la venta o no es apta para cambio.'));
      },
    });
  }

  // Paso 2: seleccionar ítem
  seleccionarItem(item: DetalleVenta): void {
    this.itemSeleccionado.set(item);
    this.error.set(null);
    this.cargando.set(true);
    const sucursalId = this.ventaData()?.sucursal_id;
    this.http
      .get<VarianteDisponible[]>(`${API_URL}/inventario`, {
        params: { sucursal_id: sucursalId! },
      })
      .subscribe({
        next: (variantes) => {
          this.cargando.set(false);
          this.variantesDisponibles.set(variantes);
          this.paso.set(3);
        },
        error: (err) => {
          this.cargando.set(false);
          this.error.set(mensajeDeError(err, 'No se pudo cargar el inventario de la sucursal.'));
        },
      });
  }

  // Paso 3: registrar cambio atómico
  registrarCambio(): void {
    this.formMotivo.markAllAsTouched();
    if (this.formMotivo.invalid || !this.varianteNuevaId() || !this.itemSeleccionado()) {
      if (!this.varianteNuevaId()) this.error.set('Selecciona la nueva prenda antes de continuar.');
      return;
    }
    this.error.set(null);
    this.cargando.set(true);
    const datos = {
      venta_id: this.ventaData()!.venta_id,
      variante_devuelta_id: this.itemSeleccionado()!.variante_id,
      variante_nueva_id: this.varianteNuevaId(),
      motivo: this.formMotivo.value.motivo?.trim(),
    };
    this.http.post<ResultadoCambio>(`${API_URL}/ventas/cambio`, datos).subscribe({
      next: (r) => {
        this.cargando.set(false);
        this.resultado.set(r);
        const msg =
          r.saldo_tipo === 'cobrar'
            ? `Cambio registrado. Cliente abona diferencia: Bs ${r.saldo.toFixed(2)}`
            : r.saldo_tipo === 'devolver'
              ? `Cambio registrado. Saldo a favor del cliente: Bs ${Math.abs(r.saldo).toFixed(2)}`
              : 'Cambio registrado sin diferencia de precio.';
        this.avisos.ok(msg);
      },
      error: (err) => {
        this.cargando.set(false);
        this.error.set(mensajeDeError(err, 'No se pudo registrar el cambio.'));
      },
    });
  }

  seleccionarVarianteNueva(id: number): void {
    this.varianteNuevaId.set(this.varianteNuevaId() === id ? null : id);
    this.error.set(null);
  }

  reiniciar(): void {
    this.paso.set(1);
    this.ventaId.set('');
    this.ventaData.set(null);
    this.itemSeleccionado.set(null);
    this.varianteNuevaId.set(null);
    this.buscador.set('');
    this.error.set(null);
    this.resultado.set(null);
    this.formMotivo.reset();
  }

  volver(): void {
    if (this.paso() === 2) this.paso.set(1);
    else if (this.paso() === 3) { this.paso.set(2); this.varianteNuevaId.set(null); }
  }

  hex(val: string | null): string {
    return /^#[0-9a-f]{6}$/i.test(val ?? '') ? val! : '#cccccc';
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleString('es-BO', { dateStyle: 'medium', timeStyle: 'short' });
  }
}

