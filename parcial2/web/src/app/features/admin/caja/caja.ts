import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { VentasService } from '../../../services/ventas.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { moneda } from '../../../shared/formato';

@Component({
  selector: 'app-caja',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-15 Punto de venta</div><h1>Caja · Sucursal {{ sucursal_id }}</h1></div>
    </div>

    <div class="caja">
      <section class="panel-venta">
        <div class="buscador">
          <label class="etiqueta">Agregar por variante (SKU o ID)</label>
          <div class="ctl">
            <input type="number" class="campo" [(ngModel)]="variante" placeholder="ID variante">
            <input type="number" class="campo cantidad" [(ngModel)]="cantidad" min="1">
            <button class="btn linea" (click)="agregarItem(variante, cantidad)">Agregar</button>
          </div>
        </div>

        <div class="marco-tabla">
          @if (items.length === 0) {
            <div class="mensaje vacio"><h2>Sin items todavia</h2><p>Agrega una variante para empezar.</p></div>
          } @else {
            <table>
              <thead><tr><th>Variante</th><th>Cantidad</th><th></th></tr></thead>
              <tbody>
                @for (i of items; track i.variante_id; let idx = $index) {
                  <tr>
                    <td class="mono">#{{ i.variante_id }}</td>
                    <td class="mono">{{ i.cantidad }}</td>
                    <td class="col-acciones"><button class="enlace peligro" (click)="quitar(idx)">Quitar</button></td>
                  </tr>
                }
              </tbody>
            </table>
          }
        </div>
      </section>

      <aside class="panel-cobro">
        <div class="ticket">
          <div class="fila"><span>Items</span><span class="mono">{{ items.length }}</span></div>
          <div class="fila"><span>Unidades</span><span class="mono">{{ calcularTotal() }}</span></div>
          <div class="fila tot"><span>Total</span><span class="mono">Bs {{ dinero(calcularTotal()) }}</span></div>
        </div>

        <label class="etiqueta">Cliente</label>
        <input type="number" class="campo" [(ngModel)]="cliente_id" placeholder="ID cliente">

        <label class="etiqueta" style="margin-top:12px">Forma de pago</label>
        <div class="metodos">
          @for (m of metodos; track m) {
            <button class="chip" [class.on]="forma_pago === m" (click)="forma_pago = m">{{ m }}</button>
          }
        </div>

        <button class="btn rosa bloque cobrar" (click)="confirmarVenta(cliente_id, forma_pago)" [disabled]="items.length === 0 || cobrando()">
          {{ cobrando() ? 'Procesando…' : 'Cobrar Bs ' + dinero(calcularTotal()) }}
        </button>

        @if (comprobante) {
          <div class="exito">
            <h3>Venta registrada</h3>
            <p class="mono">{{ comprobante }}</p>
            <button class="btn linea bloque" (click)="nuevaVenta()">Nueva venta</button>
          </div>
        }
      </aside>
    </div>
  `,
  styles: [`
    .cabecera{margin-bottom:14px;} h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;} h2{font-size:18px;font-weight:800;}
    .caja{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(320px,1fr);gap:16px;}
    .panel-venta{display:flex;flex-direction:column;gap:12px;}
    .buscador{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:14px;}
    .ctl{display:flex;gap:8px;margin-top:6px;} .ctl .campo{flex:1;} .ctl .cantidad{width:90px;flex:0;}
    .panel-cobro{background:var(--suave);border:1.5px solid var(--linea);border-radius:13px;padding:16px;display:flex;flex-direction:column;gap:6px;}
    .ticket{font-family:var(--mono);border:1.5px dashed var(--tinta);background:#fffdf6;border-radius:12px;padding:12px;margin-bottom:10px;}
    .ticket .fila{display:flex;justify-content:space-between;padding:3px 0;font-size:12px;}
    .ticket .tot{border-top:1px dashed var(--linea);margin-top:6px;padding-top:8px;font-weight:700;}
    .metodos{display:flex;gap:6px;margin-top:4px;}
    .cobrar{margin-top:14px;}
    .exito{background:#e4f2ec;color:var(--ok);border-radius:10px;padding:12px 14px;margin-top:12px;}
    .exito h3{font-size:14px;font-weight:800;margin-bottom:4px;}
    @media (max-width:900px){.caja{grid-template-columns:1fr;}}
  `],
})
export class CarritoPage {
  private api = inject(VentasService);
  private avisos = inject(Notificaciones);

  items: any[] = [];
  variante = 1;
  cantidad = 1;
  cliente_id = 1;
  forma_pago: string = 'EFECTIVO';
  sucursal_id = 1;
  comprobante = '';
  readonly cobrando = signal(false);
  readonly metodos = ['EFECTIVO', 'EN_LINEA'];

  agregarItem(variante: number, cantidad: number) {
    if (!variante || !cantidad) return;
    this.items = [...this.items, { variante_id: variante, cantidad }];
  }

  quitar(idx: number) { this.items = this.items.filter((_, i) => i !== idx); }

  calcularTotal(): number { return this.items.reduce((n, i) => n + i.cantidad, 0); }

  async confirmarVenta(cliente_id: number, forma_pago: string) {
    this.cobrando.set(true);
    try {
      const r = await firstValueFrom(this.api.registrarVenta({ cliente_id, forma_pago, sucursal_id: this.sucursal_id, items: this.items }));
      this.comprobante = r.comprobante || `Venta #${r.id} registrada`;
      this.avisos.ok('Venta registrada');
      this.mostrarComprobante();
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo cobrar')); }
    finally { this.cobrando.set(false); }
  }

  mostrarComprobante() { return this.comprobante; }

  nuevaVenta() { this.items = []; this.comprobante = ''; }
  dinero(v: unknown) { return moneda(v); }
}

@Component({
  selector: 'app-punto-venta',
  standalone: true,
  imports: [CarritoPage],
  template: `<app-caja />`,
})
export class PuntoVentaPage extends CarritoPage {}
