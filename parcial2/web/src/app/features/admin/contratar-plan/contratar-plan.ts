import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { Plan, PlanesService } from '../../../core/planes.service';
import { EstadoSuscripcion, SuscripcionesService } from '../../../core/suscripciones.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

@Component({
  selector: 'app-contratar-plan',
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './contratar-plan.html',
  styleUrl: './contratar-plan.css',
})
export class ContratarPlan {
  private planesApi = inject(PlanesService);
  private suscripcionesApi = inject(SuscripcionesService);
  private avisos = inject(Notificaciones);
  private router = inject(Router);

  readonly planes = signal<Plan[]>([]);
  readonly estado = signal<EstadoSuscripcion | null>(null);
  readonly cargando = signal(true);
  readonly errorCarga = signal<string | null>(null);

  readonly planSeleccionado = signal<string>('');
  duracionDias = 30;
  readonly guardando = signal(false);

  constructor() { this.cargar(); }

  async cargar() {
    this.cargando.set(true); this.errorCarga.set(null);
    try {
      const [pl, est] = await Promise.all([
        firstValueFrom(this.planesApi.listar()),
        firstValueFrom(this.suscripcionesApi.estado()).catch(() => null),
      ]);
      this.planes.set(pl.filter((p) => p.activo));
      this.estado.set(est);
      const activos = pl.filter((p) => p.activo);
      if (activos.length) this.planSeleccionado.set(activos[1]?.codigo || activos[0].codigo);
    } catch (e: any) { this.errorCarga.set(mensajeDeError(e, 'No se pudieron cargar los planes.')); }
    finally { this.cargando.set(false); }
  }

  elegirPlan(codigo: string) { this.planSeleccionado.set(codigo); }

  planActual(): Plan | undefined {
    return this.planes().find((p) => p.codigo === this.planSeleccionado());
  }

  async contratarPlan() {
    const codigo = this.planSeleccionado();
    if (!codigo) { this.avisos.error('Elegi un plan primero.'); return; }
    this.guardando.set(true);
    try {
      await firstValueFrom(this.suscripcionesApi.contratar({
        plan_codigo: codigo, duracion_dias: this.duracionDias,
      }));
      this.avisos.ok(`Plan "${codigo}" contratado por ${this.duracionDias} dias.`);
      this.router.navigateByUrl('/admin/mi-suscripcion');
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo contratar el plan.')); }
    finally { this.guardando.set(false); }
  }
}
