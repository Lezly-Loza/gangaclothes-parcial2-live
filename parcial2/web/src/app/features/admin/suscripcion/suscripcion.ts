import { Component, computed, inject, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { SuscripcionesService } from '../../../services/suscripciones.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { BarrasH, FilaBarra } from '../../../shared/graficos/barras-h';
import { fechaCortaLocal } from '../../../shared/formato';

@Component({
  selector: 'app-cambiar-plan',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="fondo" (click)="cerrar.emit()">
      <div class="modal angosto" (click)="$event.stopPropagation()">
        <h2>Cambiar plan</h2>
        <p class="sub">Selecciona el nuevo plan. Si el consumo actual supera los limites se rechaza.</p>
        <label class="etiqueta" style="margin-top:14px">Nuevo plan</label>
        <select class="campo" [(ngModel)]="plan">
          <option value="basico">Basico</option>
          <option value="profesional">Profesional</option>
          <option value="empresarial">Empresarial</option>
        </select>
        @if (mensaje()) { <p class="error-servidor">{{ mensaje() }}</p> }
        <div class="acciones">
          <button class="btn linea" (click)="cerrar.emit()">Cancelar</button>
          <button class="btn rosa" (click)="cambiarPlan(plan)" [disabled]="guardando()">
            {{ guardando() ? 'Cambiando…' : 'Confirmar cambio' }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`h2{font-size:18px;font-weight:800;margin:3px 0 10px;} .sub{color:var(--gris);font-size:12.5px;}`],
})
export class CambiarPlanDialog {
  private api = inject(SuscripcionesService);
  private avisos = inject(Notificaciones);
  readonly cerrar = output<void>();
  readonly cambiado = output<void>();
  readonly mensaje = signal('');
  readonly guardando = signal(false);
  plan = 'empresarial';

  async cambiarPlan(plan_codigo: string) {
    this.mensaje.set(''); this.guardando.set(true);
    try {
      await firstValueFrom(this.api.cambiar({ plan_codigo }));
      this.mostrarNuevoPlan();
      this.avisos.ok(`Plan cambiado a ${plan_codigo}`);
      this.cambiado.emit();
      this.cerrar.emit();
    } catch (e: any) { this.mensaje.set(mensajeDeError(e, 'No se pudo cambiar el plan')); }
    finally { this.guardando.set(false); }
  }

  mostrarNuevoPlan() { /* lo refleja la vista parent al escuchar cambiado */ }
}

@Component({
  selector: 'app-mi-suscripcion',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, BarrasH, CambiarPlanDialog],
  template: `
    <div class="cabecera">
      <div>
        <div class="ceja">CU-07 Suscripcion</div>
        <h1>Mi suscripcion</h1>
      </div>
      @if (estado()?.tiene_suscripcion) {
        <div class="botones">
          <button class="btn linea" (click)="dialogo.set(true)">Cambiar plan (CU-06)</button>
          <button class="btn rosa" (click)="renovar()" [disabled]="renovando()">{{ renovando() ? 'Renovando…' : 'Renovar 30 dias' }}</button>
        </div>
      }
    </div>

    @if (cargando()) { <p class="mensaje">Cargando…</p> }
    @else if (!estado()?.tiene_suscripcion) {
      <div class="mensaje vacio">
        <h2>Sin suscripcion activa</h2>
        <p>Contrata un plan para desbloquear la operacion.</p>
        <a routerLink="/admin/contratar" class="btn rosa">Contratar ahora</a>
      </div>
    } @else {
      <div class="fichas">
        <div class="ficha">
          <div class="ceja">Plan</div>
          <div class="numero">{{ estado()!.plan!.nombre }}</div>
          <div class="apoyo">Bs {{ estado()!.plan!.precio_mensual }} / mes</div>
        </div>
        <div class="ficha">
          <div class="ceja">Inicio</div>
          <div class="numero">{{ fechaCorta(estado()!.fecha_inicio) }}</div>
          <div class="apoyo">Estado: {{ estado()!.estado }}</div>
        </div>
        <div class="ficha">
          <div class="ceja">Vence</div>
          <div class="numero">{{ fechaCorta(estado()!.fecha_fin) }}</div>
          <div class="apoyo">dias restantes aprox.</div>
        </div>
        <div class="ficha destacada">
          <div class="ceja">Modulos</div>
          <div class="apoyo lista">{{ estado()!.modulos_habilitados.join(' · ') }}</div>
        </div>
      </div>

      <section class="tarjeta-consumo">
        <div class="cabecera-panel"><h2>Consumo por recurso</h2></div>
        <app-barras-h [filas]="filas()" />
      </section>
    }

    @if (dialogo()) {
      <app-cambiar-plan (cerrar)="dialogo.set(false)" (cambiado)="verMiSuscripcion()"></app-cambiar-plan>
    }
  `,
  styles: [`
    .cabecera{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;}
    .botones{display:flex;gap:8px;}
    h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:14px;font-weight:800;letter-spacing:-0.01em;}
    .fichas{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:12px;margin-bottom:14px;}
    .ficha{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:14px 16px;}
    .ficha .numero{font-family:var(--mono);font-size:23px;font-weight:700;margin:6px 0 5px;letter-spacing:-0.02em;}
    .ficha .apoyo{font-size:11.5px;color:var(--gris);line-height:1.4;}
    .ficha .apoyo.lista{font-size:12.5px;color:#fff;}
    .ficha.destacada{background:var(--tinta);border-color:var(--tinta);color:#fff;}
    .ficha.destacada .ceja{color:#c9cbd0;}
    .tarjeta-consumo{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:16px 18px 18px;}
    .cabecera-panel{margin-bottom:14px;}
  `],
})
export class MiSuscripcion {
  private api = inject(SuscripcionesService);
  private avisos = inject(Notificaciones);
  readonly estado = signal<any | null>(null);
  readonly cargando = signal(true);
  readonly dialogo = signal(false);
  readonly renovando = signal(false);

  readonly filas = computed<FilaBarra[]>(() => {
    const e = this.estado();
    if (!e?.tiene_suscripcion) return [];
    return (e.consumos as any[]).map((c) => ({
      etiqueta: c.recurso.charAt(0).toUpperCase() + c.recurso.slice(1),
      valor: c.actual,
      texto: `${c.actual} / ${c.limite}`,
      detalle: `disponible ${c.disponible}`,
      color: c.actual >= c.limite ? 'var(--alerta)' : undefined,
    }));
  });

  constructor() { this.verMiSuscripcion(); }

  async verMiSuscripcion() {
    this.cargando.set(true);
    try { this.estado.set(await firstValueFrom(this.api.estado())); }
    finally { this.cargando.set(false); }
  }

  async cambiarPlan(plan_codigo: string) {
    try {
      await firstValueFrom(this.api.cambiar({ plan_codigo }));
      this.mostrarNuevoPlan();
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo cambiar el plan')); }
  }

  mostrarNuevoPlan() { this.verMiSuscripcion(); }

  async renovar() {
    this.renovando.set(true);
    try {
      await firstValueFrom(this.api.renovar({ duracion_dias: 30 }));
      this.avisos.ok('Suscripcion renovada 30 dias');
      this.verMiSuscripcion();
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo renovar')); }
    finally { this.renovando.set(false); }
  }

  fechaCorta(iso: string | null | undefined) { return fechaCortaLocal(iso, true); }
}
