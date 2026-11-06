import { Component, inject, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { UsuariosService } from '../../../services/usuarios.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

@Component({
  selector: 'app-usuario-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="fondo" (click)="cerrar.emit()">
      <div class="modal angosto" (click)="$event.stopPropagation()">
        <h2>Nuevo usuario</h2>
        <label class="etiqueta">Nombre <span class="req">*</span></label>
        <input class="campo" [(ngModel)]="datos.nombre">
        <label class="etiqueta" style="margin-top:12px">Correo <span class="req">*</span></label>
        <input class="campo" type="email" [(ngModel)]="datos.email">
        <label class="etiqueta" style="margin-top:12px">Contrasena <span class="req">*</span></label>
        <input class="campo" type="password" [(ngModel)]="datos.password">
        <label class="etiqueta" style="margin-top:12px">Rol</label>
        <select class="campo" [(ngModel)]="datos.rol">
          <option value="admin">admin</option>
          <option value="encargado">encargado</option>
          <option value="vendedor">vendedor</option>
          <option value="cliente">cliente</option>
        </select>
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
export class UsuarioForm {
  private api = inject(UsuariosService);
  private avisos = inject(Notificaciones);

  readonly cerrar = output<void>();
  readonly creado = output<void>();

  datos: any = { nombre: 'Nuevo usuario', email: '', password: '', rol: 'vendedor' };
  readonly guardando = signal(false);
  readonly error = signal('');

  async crear() {
    this.error.set(''); this.guardando.set(true);
    try {
      await firstValueFrom(this.api.crear(this.datos));
      this.avisos.ok('Usuario creado');
      this.creado.emit();
      this.cerrar.emit();
    } catch (e: any) { this.error.set(mensajeDeError(e, 'No se pudo crear')); }
    finally { this.guardando.set(false); }
  }
}

@Component({
  selector: 'app-usuarios',
  standalone: true,
  imports: [CommonModule, FormsModule, UsuarioForm],
  template: `
    <div class="cabecera">
      <div>
        <div class="ceja">CU-03 Usuarios y roles</div>
        <h1>Usuarios</h1>
      </div>
      <button class="btn rosa" (click)="formAbierto.set(true)">+ Nuevo usuario</button>
    </div>

    <div class="marco-tabla">
      @if (cargando()) { <p class="mensaje">Cargando…</p> }
      @else if (usuarios().length === 0) {
        <div class="mensaje vacio"><h2>Aun no hay usuarios</h2><p>Crea el primero.</p></div>
      } @else {
        <table>
          <thead><tr><th class="col-indice">#</th><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th></tr></thead>
          <tbody>
            @for (u of usuarios(); track u.id; let i = $index) {
              <tr [class.inactiva]="!u.activo">
                <td class="col-indice">{{ i + 1 }}</td>
                <td><b>{{ u.nombre }}</b></td>
                <td>{{ u.email }}</td>
                <td><span class="estado rosa">{{ u.rol }}</span></td>
                <td><span class="estado" [class.ok]="u.activo" [class.bajo]="!u.activo">{{ u.activo ? 'activo' : 'inactivo' }}</span></td>
              </tr>
            }
          </tbody>
        </table>
      }
    </div>

    @if (formAbierto()) {
      <app-usuario-form (cerrar)="formAbierto.set(false)" (creado)="listar()"></app-usuario-form>
    }
  `,
  styles: [`
    .cabecera{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;}
    h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:18px;font-weight:800;}
  `],
})
export class UsuariosList {
  private api = inject(UsuariosService);
  readonly usuarios = signal<any[]>([]);
  readonly cargando = signal(true);
  readonly formAbierto = signal(false);

  constructor() { this.listar(); }
  async listar() {
    this.cargando.set(true);
    try { this.usuarios.set(await firstValueFrom(this.api.listar())); }
    finally { this.cargando.set(false); }
  }
}
