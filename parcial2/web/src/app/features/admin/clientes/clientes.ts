import { Component, inject, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ClientesService } from '../../../services/clientes.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

@Component({
  selector: 'app-cliente-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="fondo" (click)="cerrar.emit()">
      <div class="modal angosto" (click)="$event.stopPropagation()">
        <h2>Nuevo cliente</h2>
        <label class="etiqueta">Nombre</label><input class="campo" [(ngModel)]="datos.nombre">
        <label class="etiqueta" style="margin-top:12px">Documento</label><input class="campo" [(ngModel)]="datos.documento">
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
export class ClienteForm {
  private api = inject(ClientesService);
  private avisos = inject(Notificaciones);
  readonly cerrar = output<void>();
  readonly creado = output<void>();
  readonly error = signal('');
  readonly guardando = signal(false);
  datos: any = { nombre: 'Cliente nuevo', documento: '' };

  async crear() {
    this.error.set(''); this.guardando.set(true);
    try { await firstValueFrom(this.api.crear(this.datos)); this.avisos.ok('Cliente creado'); this.creado.emit(); this.cerrar.emit(); }
    catch (e: any) { this.error.set(mensajeDeError(e, 'No se pudo crear')); }
    finally { this.guardando.set(false); }
  }
}

@Component({
  selector: 'app-clientes',
  standalone: true,
  imports: [CommonModule, FormsModule, ClienteForm],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-11 Clientes</div><h1>Clientes</h1></div>
      <button class="btn rosa" (click)="form.set(true)">+ Nuevo cliente</button>
    </div>

    <section class="buscador">
      <label class="etiqueta">Buscar por nombre o documento</label>
      <div class="controles">
        <input class="campo" [(ngModel)]="q" (keydown.enter)="buscar()" placeholder="Escribi y presiona Enter">
        <button class="btn linea" (click)="buscar()">Buscar</button>
      </div>
    </section>

    <div class="marco-tabla">
      @if (cargando()) { <p class="mensaje">Buscando…</p> }
      @else if (clientes().length === 0) {
        <div class="mensaje vacio"><h2>Sin resultados</h2><p>Probá otra busqueda o crea un cliente.</p></div>
      } @else {
        <table>
          <thead><tr><th class="col-indice">#</th><th>Nombre</th><th>Documento</th><th>Correo</th></tr></thead>
          <tbody>
            @for (c of clientes(); track c.id; let i = $index) {
              <tr><td class="col-indice">{{ i + 1 }}</td><td><b>{{ c.nombre }}</b></td><td class="mono">{{ c.documento || '—' }}</td><td>{{ c.correo || '—' }}</td></tr>
            }
          </tbody>
        </table>
      }
    </div>

    @if (form()) { <app-cliente-form (cerrar)="form.set(false)" (creado)="buscar()"></app-cliente-form> }
  `,
  styles: [`
    .cabecera{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;}
    h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:18px;font-weight:800;}
    .buscador{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:14px;margin-bottom:12px;}
    .controles{display:flex;gap:8px;margin-top:6px;} .controles .campo{flex:1;}
  `],
})
export class ClientesList {
  private api = inject(ClientesService);
  readonly clientes = signal<any[]>([]);
  readonly cargando = signal(true);
  readonly form = signal(false);
  q = '';

  constructor() { this.buscar(); }
  async buscar() {
    this.cargando.set(true);
    try { this.clientes.set(await firstValueFrom(this.api.buscar(this.q))); }
    finally { this.cargando.set(false); }
  }
}
