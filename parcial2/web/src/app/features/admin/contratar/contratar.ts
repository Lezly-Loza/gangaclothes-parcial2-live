import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { Router } from '@angular/router';
import { SuscripcionesService } from '../../../services/suscripciones.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

interface PlanTarjeta { codigo: string; nombre: string; precio: number; max_sucursales: number; max_usuarios: number; max_productos: number; modulos: string[]; }

const PLANES: PlanTarjeta[] = [
  { codigo: 'basico', nombre: 'Basico', precio: 19, max_sucursales: 1, max_usuarios: 3, max_productos: 100, modulos: ['ventas', 'inventario'] },
  { codigo: 'profesional', nombre: 'Profesional', precio: 49, max_sucursales: 3, max_usuarios: 10, max_productos: 1000, modulos: ['ventas', 'inventario', 'reportes', 'promociones'] },
  { codigo: 'empresarial', nombre: 'Empresarial', precio: 129, max_sucursales: 10, max_usuarios: 50, max_productos: 100000, modulos: ['ventas', 'inventario', 'reportes', 'promociones', 'ia', 'sincronizacion_offline'] },
];

@Component({
  selector: 'app-contratar',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="cabecera">
      <div>
        <div class="ceja">CU-05 Suscripcion</div>
        <h1>Contratar plan</h1>
        <p class="sub">Elegi el plan que se ajusta a tu operacion.</p>
      </div>
    </div>

    <div class="tarjetas-plan">
      @for (p of planes; track p.codigo) {
        <div class="tarjeta-plan" [class.on]="plan() === p.codigo" (click)="elegirPlan(p.codigo)">
          <div class="ceja">{{ p.codigo }}</div>
          <div class="nombre">{{ p.nombre }}</div>
          <div class="precio"><span class="bs">Bs</span> {{ p.precio }}<small>/mes</small></div>
          <ul class="limites">
            <li>{{ p.max_sucursales }} sucursales</li>
            <li>{{ p.max_usuarios }} usuarios</li>
            <li>{{ p.max_productos | number }} productos</li>
          </ul>
          <div class="modulos">@for (m of p.modulos; track m) { <span class="chip on">{{ m }}</span> }</div>
        </div>
      }
    </div>

    <section class="confirmar">
      <div>
        <div class="ceja">Confirmacion</div>
        <h2>Plan {{ planElegido()?.nombre }}</h2>
        <div class="mono">Bs {{ planElegido()?.precio }} / mes · duracion {{ dias }} dias</div>
      </div>
      <div class="controles">
        <label class="etiqueta">Dias de duracion</label>
        <input type="number" class="campo" min="1" [(ngModel)]="dias">
        <button class="btn rosa" (click)="contratarPlan({plan_codigo: plan(), duracion_dias: dias})" [disabled]="guardando()">
          {{ guardando() ? 'Contratando…' : 'Contratar' }}
        </button>
      </div>
    </section>

    @if (resumen()) { <p class="exito">{{ resumen() }}</p> }
  `,
  styles: [`
    .cabecera{margin-bottom:14px;}
    h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:18px;font-weight:800;letter-spacing:-0.02em;}
    .sub{color:var(--gris);font-size:13px;}
    .tarjetas-plan{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin-bottom:14px;}
    .tarjeta-plan{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:18px;cursor:pointer;transition:border-color .15s ease,transform .15s ease;}
    .tarjeta-plan:hover{border-color:var(--tinta);}
    .tarjeta-plan.on{border-color:var(--ganga);box-shadow:0 0 0 3px rgba(232,23,93,.1);}
    .tarjeta-plan .nombre{font-size:20px;font-weight:800;letter-spacing:-0.02em;margin:5px 0;}
    .precio{font-family:var(--mono);font-size:26px;color:var(--tinta);margin-bottom:12px;}
    .precio .bs{font-size:14px;color:var(--gris);}
    .precio small{font-size:12px;color:var(--gris);}
    .limites{list-style:none;padding:0;margin:0 0 10px;font-size:12.5px;color:var(--gris);display:flex;flex-direction:column;gap:3px;}
    .modulos{display:flex;flex-wrap:wrap;}
    .modulos .chip{font-size:10px;padding:2px 8px;margin:0 4px 4px 0;}
    .confirmar{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:18px;display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap;}
    .controles{display:flex;gap:8px;align-items:flex-end;}
    .controles .campo{width:120px;}
    .exito{background:#e4f2ec;color:var(--ok);border-radius:10px;padding:10px 14px;margin-top:12px;font-weight:700;}
  `],
})
export class ContratarPlanForm {
  private api = inject(SuscripcionesService);
  private avisos = inject(Notificaciones);
  private router = inject(Router);

  readonly planes = PLANES;
  readonly plan = signal<string>('profesional');
  readonly planElegido = computed(() => this.planes.find((p) => p.codigo === this.plan()));
  dias = 30;
  readonly resumen = signal('');
  readonly guardando = signal(false);

  elegirPlan(codigo: string, duracion_dias = 30) {
    this.plan.set(codigo);
    if (duracion_dias) this.dias = duracion_dias;
  }

  async contratarPlan(dto: any) {
    this.resumen.set(''); this.guardando.set(true);
    try {
      await firstValueFrom(this.api.contratar(dto));
      this.mostrarResumen();
      this.avisos.ok(`Plan ${dto.plan_codigo} contratado`);
      setTimeout(() => this.router.navigateByUrl('/admin/suscripcion'), 800);
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo contratar')); }
    finally { this.guardando.set(false); }
  }

  mostrarResumen() { this.resumen.set(`Plan ${this.plan()} contratado por ${this.dias} dias.`); }
}
