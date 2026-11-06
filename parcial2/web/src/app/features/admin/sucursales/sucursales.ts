import { Component, inject, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { SucursalesService } from '../../../services/sucursales.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

@Component({
  selector: 'app-sucursal-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="fondo" (click)="cerrar.emit()">
      <div class="modal" (click)="$event.stopPropagation()">
        <h2>Nueva sucursal</h2>
        <div class="rejilla">
          <div class="grupo"><label class="etiqueta">Codigo <span class="req">*</span></label><input class="campo" [(ngModel)]="datos.codigo"></div>
          <div class="grupo"><label class="etiqueta">Nombre <span class="req">*</span></label><input class="campo" [(ngModel)]="datos.nombre"></div>
          <div class="grupo"><label class="etiqueta">Ciudad</label><input class="campo" [(ngModel)]="datos.ciudad"></div>
          <div class="grupo"><label class="etiqueta">Horario</label><input class="campo" [(ngModel)]="datos.horario" placeholder="09:00-19:00"></div>
          <div class="grupo completo"><label class="etiqueta">Direccion</label><input class="campo" [(ngModel)]="datos.direccion"></div>
        </div>
        @if (mensaje()) { <p class="error-servidor">{{ mensaje() }}</p> }
        <div class="acciones">
          <button class="btn linea" (click)="cerrar.emit()">Cancelar</button>
          <button class="btn rosa" (click)="crearSucursal(datos)" [disabled]="guardando()">{{ guardando() ? 'Guardando…' : 'Crear' }}</button>
        </div>
      </div>
    </div>
  `,
  styles: [`h2{font-size:18px;font-weight:800;margin:3px 0 16px;}`],
})
export class SucursalForm {
  private api = inject(SucursalesService);
  private avisos = inject(Notificaciones);
  readonly cerrar = output<void>();
  readonly creado = output<void>();
  readonly mensaje = signal('');
  readonly guardando = signal(false);
  datos: any = { codigo: 'suc-03', nombre: 'Luna Norte', ciudad: 'Santa Cruz', direccion: 'Av. Banzer', horario: '09:00-19:00' };

  nuevaSucursal() { this.datos = { codigo: '', nombre: '', ciudad: '', direccion: '', horario: '' }; }

  async crearSucursal(datos: any) {
    this.mensaje.set(''); this.guardando.set(true);
    try {
      await firstValueFrom(this.api.crear(datos));
      this.mostrarConfirmacion();
      this.creado.emit();
      this.cerrar.emit();
    } catch (e: any) { this.mensaje.set(mensajeDeError(e, 'No se pudo crear')); }
    finally { this.guardando.set(false); }
  }

  mostrarConfirmacion() { this.avisos.ok('Sucursal creada'); }
}

@Component({
  selector: 'app-sucursales',
  standalone: true,
  imports: [CommonModule, FormsModule, SucursalForm],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-04 Red de tiendas</div><h1>Sucursales</h1></div>
      <button class="btn rosa" (click)="nuevaSucursal()">+ Nueva sucursal</button>
    </div>

    <div class="marco-tabla">
      @if (cargando()) { <p class="mensaje">Cargando…</p> }
      @else if (sucursales().length === 0) {
        <div class="mensaje vacio"><h2>Aun no hay sucursales</h2><p>Registra la primera.</p>
          <button class="btn rosa" (click)="nuevaSucursal()">+ Nueva sucursal</button>
        </div>
      } @else {
        <table>
          <thead><tr><th class="col-indice">#</th><th>Codigo</th><th>Nombre</th><th>Ciudad</th><th>Direccion</th><th>Horario</th><th>Estado</th></tr></thead>
          <tbody>
            @for (s of sucursales(); track s.id; let i = $index) {
              <tr [class.inactiva]="!s.activo">
                <td class="col-indice">{{ i + 1 }}</td>
                <td class="mono">{{ s.codigo }}</td>
                <td><b>{{ s.nombre }}</b></td>
                <td>{{ s.ciudad }}</td>
                <td>{{ s.direccion }}</td>
                <td>{{ s.horario || '—' }}</td>
                <td><span class="estado" [class.ok]="s.activo" [class.bajo]="!s.activo">{{ s.estado }}</span></td>
              </tr>
            }
          </tbody>
        </table>
      }
    </div>

    @if (mensaje()) { <p class="mensaje">{{ mensaje() }}</p> }

    @if (formAbierto()) {
      <app-sucursal-form (cerrar)="formAbierto.set(false)" (creado)="listar()"></app-sucursal-form>
    }
  `,
  styles: [`
    .cabecera{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;}
    h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:18px;font-weight:800;}
  `],
})
export class SucursalesList {
  private api = inject(SucursalesService);
  private avisos = inject(Notificaciones);
  readonly sucursales = signal<any[]>([]);
  readonly cargando = signal(true);
  readonly formAbierto = signal(false);
  readonly mensaje = signal('');

  constructor() { this.listar(); }

  async listar() {
    this.cargando.set(true);
    try { this.sucursales.set(await firstValueFrom(this.api.listar())); }
    finally { this.cargando.set(false); }
  }

  nuevaSucursal(codigo?: string, nombre?: string, ciudad?: string, direccion?: string, horario?: string) {
    this.formAbierto.set(true);
    return { codigo, nombre, ciudad, direccion, horario };
  }

  async crearSucursal(datos: any) {
    try {
      await firstValueFrom(this.api.crear(datos));
      this.mostrarConfirmacion();
      await this.listar();
    } catch (e: any) { this.mensaje.set(mensajeDeError(e, 'No se pudo crear la sucursal')); }
  }

  mostrarConfirmacion() {
    this.mensaje.set('Sucursal creada');
    this.avisos.ok('Sucursal creada');
  }
}
