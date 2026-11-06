import { Component, inject, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ProveedoresService } from '../../../services/proveedores.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

@Component({
  selector: 'app-proveedor-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="fondo" (click)="cerrar.emit()">
      <div class="modal angosto" (click)="$event.stopPropagation()">
        <h2>Nuevo proveedor</h2>
        <label class="etiqueta">Razon social</label><input class="campo" [(ngModel)]="datos.razon_social">
        <label class="etiqueta" style="margin-top:12px">NIT</label><input class="campo" [(ngModel)]="datos.nit">
        <label class="etiqueta" style="margin-top:12px">Contacto</label><input class="campo" [(ngModel)]="datos.contacto">
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
export class ProveedorForm {
  private api = inject(ProveedoresService);
  private avisos = inject(Notificaciones);
  readonly cerrar = output<void>();
  readonly creado = output<void>();
  readonly error = signal('');
  readonly guardando = signal(false);
  datos: any = { razon_social: 'Nuevo proveedor', nit: '9000010', contacto: 'Contacto' };

  async crear() {
    this.error.set(''); this.guardando.set(true);
    try { await firstValueFrom(this.api.crear(this.datos)); this.avisos.ok('Proveedor creado'); this.creado.emit(); this.cerrar.emit(); }
    catch (e: any) { this.error.set(mensajeDeError(e, 'No se pudo crear')); }
    finally { this.guardando.set(false); }
  }
}

@Component({
  selector: 'app-proveedores',
  standalone: true,
  imports: [CommonModule, FormsModule, ProveedorForm],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-10 Proveedores</div><h1>Proveedores</h1></div>
      <button class="btn rosa" (click)="form.set(true)">+ Nuevo proveedor</button>
    </div>
    <div class="marco-tabla">
      @if (cargando()) { <p class="mensaje">Cargando…</p> }
      @else if (proveedores().length === 0) { <div class="mensaje vacio"><h2>Aun no hay proveedores</h2></div> }
      @else {
        <table>
          <thead><tr><th class="col-indice">#</th><th>Razon social</th><th>NIT</th><th>Contacto</th></tr></thead>
          <tbody>
            @for (p of proveedores(); track p.id; let i = $index) {
              <tr><td class="col-indice">{{ i + 1 }}</td><td><b>{{ p.razon_social }}</b></td><td class="mono">{{ p.nit }}</td><td>{{ p.contacto || '—' }}</td></tr>
            }
          </tbody>
        </table>
      }
    </div>
    @if (form()) { <app-proveedor-form (cerrar)="form.set(false)" (creado)="listar()"></app-proveedor-form> }
  `,
  styles: [`.cabecera{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;} h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;} h2{font-size:18px;font-weight:800;}`],
})
export class ProveedoresList {
  private api = inject(ProveedoresService);
  readonly proveedores = signal<any[]>([]);
  readonly cargando = signal(true);
  readonly form = signal(false);
  constructor() { this.listar(); }
  async listar() {
    this.cargando.set(true);
    try { this.proveedores.set(await firstValueFrom(this.api.listar())); }
    finally { this.cargando.set(false); }
  }
}
