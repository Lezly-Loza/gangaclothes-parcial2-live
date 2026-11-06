import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ReservasService } from '../../services/reservas.service';
import { Notificaciones } from '../../core/notificaciones';
import { mensajeDeError } from '../../core/errores.interceptor';

@Component({
  selector: 'app-reservar',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-14 Reservar prenda</div><h1>Reservar para probar en sucursal</h1></div>
    </div>

    <section class="tarjeta">
      <div class="rejilla">
        <div class="grupo"><label class="etiqueta">Variante</label><input type="number" class="campo" [(ngModel)]="datos.variante_id"></div>
        <div class="grupo"><label class="etiqueta">Sucursal</label><input type="number" class="campo" [(ngModel)]="datos.sucursal_id"></div>
        <div class="grupo"><label class="etiqueta">Cliente</label><input type="number" class="campo" [(ngModel)]="datos.cliente_id"></div>
        <div class="grupo"><label class="etiqueta">Cantidad</label><input type="number" class="campo" min="1" [(ngModel)]="datos.cantidad"></div>
      </div>
      <div class="acciones">
        <button class="btn rosa" (click)="reservar(datos)" [disabled]="guardando()">
          {{ guardando() ? 'Reservando…' : 'Confirmar reserva' }}
        </button>
      </div>
      @if (codigo()) {
        <div class="codigo">
          <div class="ceja">Codigo de reserva</div>
          <h2 class="mono">{{ codigo() }}</h2>
          <p class="sub">Mostralo en sucursal para probar la prenda.</p>
        </div>
      }
    </section>
  `,
  styles: [`
    .cabecera{margin-bottom:14px;} h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:26px;font-weight:800;letter-spacing:-0.02em;margin:5px 0;}
    .tarjeta{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:18px;max-width:640px;}
    .sub{color:var(--gris);font-size:12.5px;}
    .codigo{margin-top:18px;background:#e4f2ec;border:1.5px solid var(--ok);border-radius:10px;padding:14px;}
  `],
})
export class ReservarPrendaPage {
  private api = inject(ReservasService);
  private avisos = inject(Notificaciones);
  private ruta = inject(ActivatedRoute);
  datos: any = { variante_id: 1, sucursal_id: 1, cliente_id: 1, cantidad: 1 };
  readonly codigo = signal('');
  readonly guardando = signal(false);

  constructor() {
    const v = Number(this.ruta.snapshot.queryParamMap.get('variante'));
    if (v) this.datos.variante_id = v;
  }

  elegirPrenda() { return this.datos.variante_id; }

  async reservar(datos: any) {
    this.guardando.set(true);
    try {
      const r = await firstValueFrom(this.api.crearReserva(datos));
      this.codigo.set(r.codigo || `RES-${r.id || '000'}`);
      this.avisos.ok('Reserva creada');
      this.mostrarCodigo();
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo reservar')); }
    finally { this.guardando.set(false); }
  }

  mostrarCodigo() { return this.codigo(); }
}
