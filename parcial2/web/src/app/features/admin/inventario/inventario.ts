import { Component, inject, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { InventarioService } from '../../../services/inventario.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

@Component({
  selector: 'app-movimiento-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="fondo" (click)="cerrar.emit()">
      <div class="modal" (click)="$event.stopPropagation()">
        <h2>Registrar movimiento</h2>
        <div class="rejilla">
          <div class="grupo"><label class="etiqueta">Sucursal</label><input type="number" class="campo" [(ngModel)]="datos.sucursal_id"></div>
          <div class="grupo"><label class="etiqueta">Variante</label><input type="number" class="campo" [(ngModel)]="datos.variante_id"></div>
          <div class="grupo">
            <label class="etiqueta">Tipo</label>
            <select class="campo" [(ngModel)]="datos.tipo">
              <option>ENTRADA</option><option>SALIDA</option><option>AJUSTE</option>
            </select>
          </div>
          <div class="grupo"><label class="etiqueta">Cantidad</label><input type="number" class="campo" [(ngModel)]="datos.cantidad"></div>
          <div class="grupo completo"><label class="etiqueta">Motivo</label><input class="campo" [(ngModel)]="datos.motivo"></div>
        </div>
        @if (mensaje()) { <p class="error-servidor">{{ mensaje() }}</p> }
        <div class="acciones">
          <button class="btn linea" (click)="cerrar.emit()">Cancelar</button>
          <button class="btn rosa" (click)="registrarMovimiento(datos.variante_id, datos.tipo, datos.cantidad, datos.motivo)" [disabled]="guardando()">
            {{ guardando() ? 'Guardando…' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`h2{font-size:18px;font-weight:800;margin:3px 0 16px;}`],
})
export class MovimientoForm {
  private api = inject(InventarioService);
  private avisos = inject(Notificaciones);
  readonly cerrar = output<void>();
  readonly creado = output<void>();
  readonly mensaje = signal('');
  readonly guardando = signal(false);
  datos: any = { sucursal_id: 1, variante_id: 1, tipo: 'ENTRADA', cantidad: 1, motivo: 'Reposicion' };

  async registrarMovimiento(variante: number, tipo: string, cantidad: number, motivo: string) {
    this.mensaje.set(''); this.guardando.set(true);
    try {
      const r = await firstValueFrom(this.api.registrarMovimiento({ ...this.datos, variante_id: variante, tipo, cantidad, motivo }));
      this.mensaje.set(r.alerta_minimo ? 'Alerta: stock por debajo del minimo' : 'Movimiento guardado');
      this.avisos.ok('Movimiento registrado');
      this.creado.emit();
      if (!r.alerta_minimo) this.cerrar.emit();
    } catch (e: any) { this.mensaje.set(mensajeDeError(e, 'No se pudo registrar')); }
    finally { this.guardando.set(false); }
  }
}

@Component({
  selector: 'app-inventario',
  standalone: true,
  imports: [CommonModule, FormsModule, MovimientoForm],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-12 Inventario</div><h1>Inventario por sucursal</h1></div>
      <div class="acciones-sup">
        <label class="etiqueta">Sucursal</label>
        <input type="number" class="campo small" [(ngModel)]="sucursal" (change)="abrirInventario()">
        <button class="btn linea" (click)="abrirInventario()">Consultar</button>
        <button class="btn rosa" (click)="form.set(true)">+ Movimiento</button>
      </div>
    </div>

    <div class="marco-tabla">
      @if (cargando()) { <p class="mensaje">Cargando…</p> }
      @else if (filas().length === 0) {
        <div class="mensaje vacio"><h2>Sin stock en esta sucursal</h2></div>
      } @else {
        <table>
          <thead><tr><th>SKU</th><th>Variante</th><th>Stock</th><th>Min</th><th>Max</th><th>Estado</th></tr></thead>
          <tbody>
            @for (i of filas(); track i.variante_id) {
              <tr [class.bajo-minimo]="i.stock < (i.stock_minimo ?? 0)">
                <td class="mono">{{ i.sku || '—' }}</td>
                <td>Variante {{ i.variante_id }}</td>
                <td class="mono">{{ i.stock }}</td>
                <td class="mono">{{ i.stock_minimo ?? '—' }}</td>
                <td class="mono">{{ i.stock_maximo ?? '—' }}</td>
                <td>
                  @if (i.stock < (i.stock_minimo ?? 0)) { <span class="estado bajo">⚠ Bajo minimo</span> }
                  @else { <span class="estado ok">OK</span> }
                </td>
              </tr>
            }
          </tbody>
        </table>
      }
    </div>

    @if (mensaje()) { <p class="mensaje">{{ mensaje() }}</p> }
    @if (form()) { <app-movimiento-form (cerrar)="form.set(false)" (creado)="abrirInventario()"></app-movimiento-form> }
  `,
  styles: [`
    .cabecera{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;gap:12px;flex-wrap:wrap;}
    h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:18px;font-weight:800;}
    .acciones-sup{display:flex;gap:8px;align-items:flex-end;}
    .campo.small{width:90px;}
    tr.bajo-minimo{background:#fff6f2;}
  `],
})
export class InventarioPage {
  private api = inject(InventarioService);
  readonly filas = signal<any[]>([]);
  readonly cargando = signal(true);
  readonly mensaje = signal('');
  readonly form = signal(false);
  sucursal = 1;

  constructor() { this.abrirInventario(); }

  async abrirInventario() {
    this.cargando.set(true);
    try { this.filas.set(await firstValueFrom(this.api.consultarStock(this.sucursal))); this.mostrarStock(); }
    catch { this.filas.set([]); }
    finally { this.cargando.set(false); }
  }

  async registrarMovimiento(variante: any, tipo?: string, cantidad?: number, motivo?: string) {
    const datos = typeof variante === 'object'
      ? variante
      : { sucursal_id: this.sucursal, variante_id: variante, tipo, cantidad, motivo };
    try {
      const r = await firstValueFrom(this.api.registrarMovimiento(datos));
      this.mensaje.set(r.alerta_minimo ? 'Alerta de stock minimo' : 'Movimiento registrado');
      await this.abrirInventario();
    } catch (e: any) { this.mensaje.set(mensajeDeError(e, 'No se pudo registrar')); }
  }

  mostrarStock() { return this.filas().length; }
}
