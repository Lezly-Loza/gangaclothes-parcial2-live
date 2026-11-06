import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { VentasService } from '../../../services/ventas.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

@Component({
  selector: 'app-anular',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-17 Anular operacion</div><h1>Anular venta o reserva</h1></div>
    </div>

    <section class="tarjeta">
      <label class="etiqueta">ID de la venta a anular</label>
      <input type="number" class="campo" [(ngModel)]="id" (change)="buscarOperacion()">

      <label class="etiqueta" style="margin-top:12px">Motivo <span class="req">*</span></label>
      <textarea class="campo" rows="3" [(ngModel)]="motivo" placeholder="Describe el motivo"></textarea>

      <div class="acciones">
        <button class="btn peligro" (click)="anular(id, motivo)" [disabled]="guardando()">
          {{ guardando() ? 'Anulando…' : 'Anular operacion' }}
        </button>
      </div>

      @if (mensaje()) {
        <div class="resultado"><span class="estado bajo">{{ mensaje() }}</span></div>
      }
    </section>
  `,
  styles: [`
    .cabecera{margin-bottom:14px;} h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    .tarjeta{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:18px;max-width:560px;}
    .resultado{margin-top:14px;}
  `],
})
export class AnularOperacionDialog {
  private api = inject(VentasService);
  private avisos = inject(Notificaciones);
  id = 1;
  motivo = 'Solicitud del cliente';
  readonly mensaje = signal('');
  readonly guardando = signal(false);

  buscarOperacion() { return this.id; }

  async anular(venta_id: number, motivo: string) {
    if (!motivo?.trim()) { this.avisos.error('Motivo requerido'); return; }
    this.guardando.set(true);
    try {
      const r = await firstValueFrom(this.api.anular(venta_id, motivo));
      this.mensaje.set(`Venta ${venta_id} · estado ${r.estado}`);
      this.mostrarAnulada();
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo anular')); }
    finally { this.guardando.set(false); }
  }

  mostrarAnulada() { this.avisos.ok('Operacion anulada'); return this.mensaje(); }
}
