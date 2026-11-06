import { Component, inject, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ProductosService } from '../../../services/productos.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { moneda } from '../../../shared/formato';

@Component({
  selector: 'app-producto-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="fondo" (click)="cerrar.emit()">
      <div class="modal" (click)="$event.stopPropagation()">
        <h2>Nueva prenda</h2>
        <div class="rejilla">
          <div class="grupo"><label class="etiqueta">Nombre</label><input class="campo" [(ngModel)]="datos.nombre"></div>
          <div class="grupo"><label class="etiqueta">Precio base (Bs)</label><input type="number" step="0.01" class="campo" [(ngModel)]="datos.precio_base"></div>
          <div class="grupo completo"><label class="etiqueta">Descripcion</label><input class="campo" [(ngModel)]="datos.descripcion"></div>
          <div class="grupo"><label class="etiqueta">SKU variante inicial</label><input class="campo" [(ngModel)]="sku"></div>
        </div>
        @if (error()) { <p class="error-servidor">{{ error() }}</p> }
        <div class="acciones">
          <button class="btn linea" (click)="cerrar.emit()">Cancelar</button>
          <button class="btn rosa" (click)="crear()" [disabled]="guardando()">{{ guardando() ? 'Guardando…' : 'Crear' }}</button>
        </div>
      </div>
    </div>
  `,
  styles: [`h2{font-size:18px;font-weight:800;margin:3px 0 16px;}`],
})
export class ProductoForm {
  private api = inject(ProductosService);
  private avisos = inject(Notificaciones);
  readonly cerrar = output<void>();
  readonly creado = output<void>();
  readonly error = signal('');
  readonly guardando = signal(false);
  datos: any = { nombre: 'Nueva prenda', descripcion: '', precio_base: 90 };
  sku = 'LUN-NUEVA';

  async crear() {
    this.error.set(''); this.guardando.set(true);
    try {
      await firstValueFrom(this.api.crear({ ...this.datos, variantes: [{ sku: this.sku, precio: this.datos.precio_base }] }));
      this.avisos.ok('Prenda creada');
      this.creado.emit(); this.cerrar.emit();
    } catch (e: any) { this.error.set(mensajeDeError(e, 'No se pudo crear')); }
    finally { this.guardando.set(false); }
  }
}

@Component({
  selector: 'app-productos',
  standalone: true,
  imports: [CommonModule, FormsModule, ProductoForm],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-08 Productos</div><h1>Prendas y variantes</h1></div>
      <button class="btn rosa" (click)="form.set(true)">+ Nueva prenda</button>
    </div>

    <div class="marco-tabla">
      @if (cargando()) { <p class="mensaje">Cargando…</p> }
      @else if (productos().length === 0) {
        <div class="mensaje vacio"><h2>Aun no hay prendas</h2></div>
      } @else {
        <table>
          <thead><tr><th class="col-indice">#</th><th>Nombre</th><th>Descripcion</th><th>Precio base</th><th>Variantes</th></tr></thead>
          <tbody>
            @for (p of productos(); track p.id; let i = $index) {
              <tr>
                <td class="col-indice">{{ i + 1 }}</td>
                <td><b>{{ p.nombre }}</b></td>
                <td>{{ p.descripcion || '—' }}</td>
                <td class="mono">Bs {{ dinero(p.precio_base) }}</td>
                <td>{{ p.variantes?.length || 0 }}</td>
              </tr>
            }
          </tbody>
        </table>
      }
    </div>

    @if (form()) { <app-producto-form (cerrar)="form.set(false)" (creado)="listar()"></app-producto-form> }
  `,
  styles: [`.cabecera{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;} h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;} h2{font-size:18px;font-weight:800;}`],
})
export class ProductosList {
  private api = inject(ProductosService);
  readonly productos = signal<any[]>([]);
  readonly cargando = signal(true);
  readonly form = signal(false);

  constructor() { this.listar(); }
  async listar() {
    this.cargando.set(true);
    try { this.productos.set(await firstValueFrom(this.api.listar())); }
    finally { this.cargando.set(false); }
  }
  dinero(v: unknown) { return moneda(v); }
}
