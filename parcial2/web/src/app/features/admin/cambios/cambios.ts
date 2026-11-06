import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { CambiosService } from '../../../services/cambios.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { moneda } from '../../../shared/formato';

@Component({
  selector: 'app-cambios',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-16 Cambios de prendas</div><h1>Cambio de prenda</h1></div>
    </div>

    <section class="buscar">
      <label class="etiqueta">Codigo de venta</label>
      <div class="ctl">
        <input class="campo" [(ngModel)]="codigo" placeholder="VEN-000123" (keydown.enter)="buscarVenta(codigo)">
        <button class="btn linea" (click)="buscarVenta(codigo)">Buscar</button>
      </div>
    </section>

    @if (venta) {
      <section class="venta">
        <div class="cabecera-panel">
          <h2>Venta {{ venta.codigo }}</h2>
          <div class="mono">Bs {{ dinero(venta.total) }}</div>
        </div>
        <div class="marco-tabla">
          <table>
            <thead><tr><th>Variante</th><th>Cantidad</th></tr></thead>
            <tbody>
              @for (d of venta.detalles; track $index) {
                <tr><td class="mono">#{{ d.variante_id }}</td><td class="mono">{{ d.cantidad }}</td></tr>
              }
            </tbody>
          </table>
        </div>
      </section>

      <section class="nueva">
        <label class="etiqueta">Variante nueva</label>
        <input type="number" class="campo" [(ngModel)]="variante_nueva">
        <label class="etiqueta" style="margin-top:10px">Motivo</label>
        <input class="campo" [(ngModel)]="motivo">
        <button class="btn rosa bloque" style="margin-top:14px"
                (click)="cambiar(venta, variante_nueva, motivo)" [disabled]="guardando()">
          {{ guardando() ? 'Procesando…' : 'Confirmar cambio' }}
        </button>
      </section>
    }

    @if (comprobante()) { <p class="exito mono">{{ comprobante() }}</p> }
  `,
  styles: [`
    .cabecera{margin-bottom:14px;} h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:14px;font-weight:800;}
    .buscar{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:14px;margin-bottom:14px;}
    .ctl{display:flex;gap:8px;margin-top:6px;} .ctl .campo{flex:1;}
    .venta{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:14px;margin-bottom:14px;}
    .cabecera-panel{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px;}
    .nueva{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:14px;}
    .exito{background:#e4f2ec;color:var(--ok);border-radius:10px;padding:12px 14px;margin-top:14px;}
  `],
})
export class CambioPrendaPage {
  private api = inject(CambiosService);
  private avisos = inject(Notificaciones);
  codigo = 'VEN-DEMO';
  venta: any = null;
  variante_nueva = 4;
  motivo = 'Cambio de talla';
  readonly comprobante = signal('');
  readonly guardando = signal(false);

  async buscarVenta(codigo: string) {
    try {
      this.venta = await firstValueFrom(this.api.obtenerVenta(codigo));
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'Venta no encontrada')); }
  }

  async cambiar(item: any, variante_nueva: number, motivo = 'Cambio') {
    if (!item) return;
    this.guardando.set(true);
    try {
      const r = await firstValueFrom(this.api.registrarCambio({
        venta_id: item.id,
        variante_devuelta_id: item.detalles?.[0]?.variante_id,
        variante_nueva_id: variante_nueva,
        motivo,
      }));
      this.comprobante.set(`Cambio ${r.id} · diferencia Bs ${moneda(r.diferencia)}`);
      this.avisos.ok('Cambio registrado');
      this.mostrarComprobante();
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo registrar el cambio')); }
    finally { this.guardando.set(false); }
  }

  mostrarComprobante() { return this.comprobante(); }
  dinero(v: unknown) { return moneda(v); }
}
