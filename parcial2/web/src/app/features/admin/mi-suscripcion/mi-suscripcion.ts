import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { EstadoSuscripcion, SuscripcionesService } from '../../../core/suscripciones.service';
import { Plan, PlanesService } from '../../../core/planes.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { fechaCortaLocal } from '../../../shared/formato';
import { BarrasH, FilaBarra } from '../../../shared/graficos/barras-h';

@Component({
  selector: 'app-mi-suscripcion',
  imports: [CommonModule, FormsModule, RouterLink, BarrasH],
  templateUrl: './mi-suscripcion.html',
  styleUrl: './mi-suscripcion.css',
})
export class MiSuscripcion {
  private api = inject(SuscripcionesService);
  private planesApi = inject(PlanesService);
  private avisos = inject(Notificaciones);

  readonly estado = signal<EstadoSuscripcion | null>(null);
  readonly planes = signal<Plan[]>([]);
  readonly cargando = signal(true);
  readonly errorCarga = signal<string | null>(null);

  readonly dialogoCambiar = signal(false);
  readonly planNuevo = signal<string>('');
  readonly guardandoCambio = signal(false);
  readonly renovando = signal(false);
  readonly diasRenovacion = signal(30);

  readonly filas = computed<FilaBarra[]>(() => {
    const e = this.estado();
    if (!e?.tiene_suscripcion) return [];
    return e.consumos.map((c) => ({
      etiqueta: c.recurso.charAt(0).toUpperCase() + c.recurso.slice(1),
      valor: c.actual,
      texto: `${c.actual} / ${c.limite}`,
      detalle: `disponible ${c.disponible}`,
      color: c.actual >= c.limite ? 'var(--alerta)' : undefined,
    }));
  });

  constructor() { this.verMiSuscripcion(); }

  async verMiSuscripcion() {
    this.cargando.set(true); this.errorCarga.set(null);
    try {
      const [est, pl] = await Promise.all([
        firstValueFrom(this.api.estado()),
        firstValueFrom(this.planesApi.listar()),
      ]);
      this.estado.set(est);
      this.planes.set(pl);
    } catch (e: any) { this.errorCarga.set(mensajeDeError(e, 'No se pudo cargar la suscripcion.')); }
    finally { this.cargando.set(false); }
  }

  abrirCambio() {
    const actual = this.estado()?.plan?.codigo || '';
    const alternativo = this.planes().find((p) => p.codigo !== actual)?.codigo || '';
    this.planNuevo.set(alternativo);
    this.dialogoCambiar.set(true);
  }

  async cambiarPlan(plan_codigo: string) {
    this.guardandoCambio.set(true);
    try {
      await firstValueFrom(this.api.cambiar({ plan_codigo, duracion_dias: 30 }));
      this.avisos.ok(`Plan cambiado a "${plan_codigo}".`);
      this.dialogoCambiar.set(false);
      await this.verMiSuscripcion();
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo cambiar el plan.')); }
    finally { this.guardandoCambio.set(false); }
  }

  async renovar() {
    this.renovando.set(true);
    try {
      await firstValueFrom(this.api.renovar({ duracion_dias: this.diasRenovacion() }));
      this.avisos.ok(`Suscripcion renovada ${this.diasRenovacion()} dias.`);
      await this.verMiSuscripcion();
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo renovar.')); }
    finally { this.renovando.set(false); }
  }

  fecha(iso: string | null | undefined) { return fechaCortaLocal(iso, true); }
}
