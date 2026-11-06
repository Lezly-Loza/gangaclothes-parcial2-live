import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { SuscripcionesService } from '../../../services/suscripciones.service';
import { SesionStore } from '../../../core/sesion';
import { BarrasH, FilaBarra } from '../../../shared/graficos/barras-h';
import { fechaCortaLocal } from '../../../shared/formato';

@Component({
  selector: 'app-admin-inicio',
  standalone: true,
  imports: [CommonModule, RouterLink, BarrasH],
  template: `
    <div class="cabecera">
      <div>
        <div class="ceja">Panel</div>
        <h1>Hola, {{ sesion.nombre() }}</h1>
        <p class="sub">{{ sesion.esSuper() ? 'Administras la plataforma GangaClothes.' : 'Resumen de tu suscripcion y consumo actual.' }}</p>
      </div>
    </div>

    @if (sesion.esSuper()) {
      <div class="super">
        <p>Como superadministrador, gestionas las empresas contratantes y sus planes.</p>
        <a routerLink="/admin/empresas" class="btn rosa">Ver empresas</a>
      </div>
    } @else if (cargando()) {
      <p class="mensaje">Cargando estado de la suscripcion…</p>
    } @else if (!estado()?.tiene_suscripcion) {
      <div class="mensaje vacio">
        <h2>Aun no tenes un plan contratado</h2>
        <p>Elegi un plan para desbloquear la operacion.</p>
        <a routerLink="/admin/contratar" class="btn rosa">Contratar plan</a>
      </div>
    } @else {
      <div class="fichas">
        <div class="ficha">
          <div class="ceja">Plan vigente</div>
          <div class="numero">{{ estado()!.plan!.nombre }}</div>
          <div class="apoyo">Bs {{ estado()!.plan!.precio_mensual }} / mes</div>
        </div>
        <div class="ficha">
          <div class="ceja">Vence</div>
          <div class="numero">{{ fechaCorta(estado()!.fecha_fin) }}</div>
          <div class="apoyo">Estado: {{ estado()!.estado }}</div>
        </div>
        <div class="ficha destacada">
          <div class="ceja">Modulos habilitados</div>
          <div class="apoyo lista">{{ estado()!.modulos_habilitados.join(' · ') }}</div>
        </div>
      </div>

      <section class="tarjeta-consumo">
        <div class="cabecera-panel">
          <h2>Consumo del plan</h2>
          <a routerLink="/admin/suscripcion" class="enlace">Ver detalle →</a>
        </div>
        <app-barras-h [filas]="filas()" />
      </section>
    }
  `,
  styles: [`
    .cabecera{margin-bottom:18px;}
    h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    .sub{color:var(--gris);font-size:13px;margin-top:4px;}
    .super{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:22px;display:flex;flex-direction:column;gap:12px;align-items:flex-start;}
    .fichas{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:12px;margin-bottom:14px;}
    .ficha{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:14px 16px;}
    .ficha .numero{font-family:var(--mono);font-size:23px;font-weight:700;line-height:1.15;margin:6px 0 5px;letter-spacing:-0.02em;}
    .ficha .apoyo{font-size:11.5px;color:var(--gris);line-height:1.4;}
    .ficha .apoyo.lista{font-size:12.5px;color:#fff;}
    .ficha.destacada{background:var(--tinta);border-color:var(--tinta);color:#fff;}
    .ficha.destacada .ceja{color:#c9cbd0;}
    .tarjeta-consumo{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:16px 18px 18px;}
    .cabecera-panel{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:14px;}
    h2{font-size:14px;font-weight:800;letter-spacing:-0.01em;}
  `],
})
export class AdminInicio {
  private api = inject(SuscripcionesService);
  readonly sesion = inject(SesionStore);
  readonly cargando = signal(true);
  readonly estado = signal<any | null>(null);
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

  constructor() {
    this.cargar();
  }
  async cargar() {
    if (this.sesion.esSuper()) { this.cargando.set(false); return; }
    try { this.estado.set(await firstValueFrom(this.api.estado())); }
    finally { this.cargando.set(false); }
  }
  fechaCorta(iso: string | null | undefined) { return fechaCortaLocal(iso, true); }
}
