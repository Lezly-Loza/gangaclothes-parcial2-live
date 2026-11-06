import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { TenantsService } from '../../../services/tenants.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

@Component({
  selector: 'app-empresas',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="cabecera">
      <div>
        <div class="ceja">CU-01 Empresas contratantes</div>
        <h1>Empresas</h1>
      </div>
      <button class="btn rosa" (click)="abrirForm()">+ Nueva empresa</button>
    </div>

    <div class="marco-tabla">
      @if (cargando()) {
        <p class="mensaje">Cargando empresas…</p>
      } @else if (empresas().length === 0) {
        <div class="mensaje vacio">
          <h2>Todavia no hay empresas</h2>
          <p>Registra la primera empresa contratante.</p>
          <button class="btn rosa" (click)="abrirForm()">+ Nueva empresa</button>
        </div>
      } @else {
        <table>
          <thead><tr>
            <th class="col-indice">#</th>
            <th>Razon social</th><th>Codigo</th><th>NIT</th><th>Correo</th><th>Plan</th><th>Vence</th>
          </tr></thead>
          <tbody>
            @for (e of empresas(); track e.id; let i = $index) {
              <tr>
                <td class="col-indice">{{ i + 1 }}</td>
                <td><b>{{ e.razon_social }}</b></td>
                <td class="mono">{{ e.codigo }}</td>
                <td class="mono">{{ e.nit }}</td>
                <td>{{ e.correo }}</td>
                <td>@if (e.plan_actual) { <span class="estado rosa">{{ e.plan_actual }}</span> } @else { — }</td>
                <td class="mono">{{ e.fecha_fin_suscripcion || '—' }}</td>
              </tr>
            }
          </tbody>
        </table>
      }
    </div>

    @if (formAbierto()) {
      <div class="fondo" (click)="cerrarForm()">
        <div class="modal" (click)="$event.stopPropagation()">
          <h2>Registrar empresa</h2>
          <div class="rejilla">
            <div class="grupo completo">
              <label class="etiqueta">Razon social <span class="req">*</span></label>
              <input class="campo" [(ngModel)]="datos.razon_social" placeholder="Boutique Nueva SRL">
            </div>
            <div class="grupo"><label class="etiqueta">NIT</label><input class="campo" [(ngModel)]="datos.nit"></div>
            <div class="grupo"><label class="etiqueta">Codigo</label><input class="campo" [(ngModel)]="datos.codigo" placeholder="nueva"></div>
            <div class="grupo"><label class="etiqueta">Correo</label><input class="campo" type="email" [(ngModel)]="datos.correo"></div>
            <div class="grupo"><label class="etiqueta">Telefono</label><input class="campo" [(ngModel)]="datos.telefono"></div>
            <div class="grupo completo"><label class="etiqueta">Administrador inicial</label></div>
            <div class="grupo"><label class="etiqueta">Nombre</label><input class="campo" [(ngModel)]="datos.admin.nombre"></div>
            <div class="grupo"><label class="etiqueta">Correo admin</label><input class="campo" type="email" [(ngModel)]="datos.admin.email"></div>
            <div class="grupo"><label class="etiqueta">Contrasena</label><input class="campo" type="password" [(ngModel)]="datos.admin.password"></div>
            <div class="grupo">
              <label class="etiqueta">Plan</label>
              <select class="campo" [(ngModel)]="datos.plan_codigo">
                <option value="basico">Basico</option>
                <option value="profesional">Profesional</option>
                <option value="empresarial">Empresarial</option>
              </select>
            </div>
          </div>
          @if (error()) { <p class="error-servidor">{{ error() }}</p> }
          <div class="acciones">
            <button class="btn linea" (click)="cerrarForm()">Cancelar</button>
            <button class="btn rosa" (click)="registrarEmpresa(datos)" [disabled]="guardando()">
              {{ guardando() ? 'Guardando…' : 'Registrar' }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .cabecera{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;}
    h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:18px;font-weight:800;letter-spacing:-0.02em;margin:3px 0 16px;}
  `],
})
export class RegistrarEmpresaForm {
  private api = inject(TenantsService);
  private avisos = inject(Notificaciones);

  readonly empresas = signal<any[]>([]);
  readonly cargando = signal(true);
  readonly formAbierto = signal(false);
  readonly guardando = signal(false);
  readonly error = signal('');

  datos: any = {
    razon_social: 'Boutique Nueva SRL', nit: '', correo: '', telefono: '',
    codigo: 'nueva',
    admin: { nombre: 'Administradora', email: '', password: '' },
    plan_codigo: 'profesional',
  };

  constructor() { this.listar(); }

  async listar() {
    this.cargando.set(true);
    try { this.empresas.set(await firstValueFrom(this.api.listar())); }
    finally { this.cargando.set(false); }
  }
  abrirForm() { this.error.set(''); this.formAbierto.set(true); }
  cerrarForm() { this.formAbierto.set(false); }

  async registrarEmpresa(datos: any) {
    this.error.set(''); this.guardando.set(true);
    try {
      await firstValueFrom(this.api.crear(datos));
      this.avisos.ok('Empresa registrada');
      this.formAbierto.set(false);
      await this.listar();
    } catch (e: any) { this.error.set(mensajeDeError(e, 'No se pudo registrar')); }
    finally { this.guardando.set(false); }
  }
}

@Component({
  selector: 'app-empresas-list',
  standalone: true,
  imports: [CommonModule],
  template: `<p *ngFor="let e of empresas()">{{ e.razon_social }}</p>`,
})
export class EmpresasList {
  private api = inject(TenantsService);
  readonly empresas = signal<any[]>([]);
  constructor() { this.listar(); }
  async listar() { this.empresas.set(await firstValueFrom(this.api.listar())); }
  async registrarEmpresa(datos: any) { await firstValueFrom(this.api.crear(datos)); await this.listar(); }
}
