import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OfflineService } from '../../../services/offline.service';
import { Notificaciones } from '../../../core/notificaciones';
import { fechaLocal } from '../../../shared/formato';

@Component({
  selector: 'app-offline',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-18 Operacion sin conexion</div><h1>Modo offline</h1></div>
    </div>

    <div class="fichas">
      <div class="ficha">
        <div class="ceja">Productos disponibles offline</div>
        <div class="numero">{{ productos() }}</div>
        <div class="apoyo">cargados en IndexedDB</div>
      </div>
      <div class="ficha">
        <div class="ceja">Ultima descarga</div>
        <div class="numero">{{ fechaLegible() }}</div>
        <div class="apoyo">modo PWA habilitado</div>
      </div>
    </div>

    <section class="preparar">
      <h2>Preparar nueva descarga</h2>
      <p class="sub">Elige el filtro y presiona "Preparar modo offline". Si no hay conexion, se conserva la copia anterior.</p>
      <div class="controles">
        <label class="etiqueta">Sucursal</label>
        <input type="number" class="campo" [(ngModel)]="sucursal_id">
        <label class="etiqueta">Temporada (opcional)</label>
        <input type="number" class="campo" [(ngModel)]="temporada">
      </div>
      <button class="btn rosa" style="margin-top:14px" (click)="prepararOffline(categorias, temporada)" [disabled]="cargando()">
        {{ cargando() ? 'Descargando…' : 'Preparar modo offline' }}
      </button>
    </section>
  `,
  styles: [`
    .cabecera{margin-bottom:14px;} h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:14px;font-weight:800;}
    .fichas{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-bottom:14px;}
    .ficha{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:14px 16px;}
    .ficha .numero{font-family:var(--mono);font-size:23px;font-weight:700;margin:6px 0 5px;letter-spacing:-0.02em;}
    .ficha .apoyo{font-size:11.5px;color:var(--gris);}
    .preparar{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:16px 18px;}
    .sub{color:var(--gris);font-size:12.5px;margin:4px 0 12px;}
    .controles{display:grid;grid-template-columns:120px 1fr 120px 1fr;gap:8px;align-items:center;}
    @media(max-width:620px){.controles{grid-template-columns:1fr;}}
  `],
})
export class ModoOfflinePage {
  private api = inject(OfflineService);
  private avisos = inject(Notificaciones);

  readonly productos = signal(0);
  readonly fecha = signal('');
  readonly cargando = signal(false);
  categorias: number[] = [];
  temporada: number | null = null;
  sucursal_id = 1;

  constructor() { this.abrirModoOffline(); }

  abrirModoOffline() { return true; }

  async prepararOffline(categorias: any, temporada?: number | null) {
    this.cargando.set(true);
    try {
      const filtros = Array.isArray(categorias)
        ? { sucursal_id: this.sucursal_id, categorias, ...(temporada ? { temporada } : {}) }
        : { sucursal_id: this.sucursal_id, ...(categorias || {}) };
      const r = await this.api.descargarCatalogo(filtros);
      this.productos.set(r.productos.length);
      this.fecha.set(r.fecha_descarga || '');
      this.avisos.ok(`${r.productos.length} productos listos sin conexion`);
      this.mostrarDisponibles();
    } catch { this.avisos.error('No se pudo preparar el modo offline'); }
    finally { this.cargando.set(false); }
  }

  mostrarDisponibles() { return this.productos(); }

  fechaLegible() { return this.fecha() ? fechaLocal(this.fecha()) : '—'; }
}
