import { Component, computed, effect, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { CatalogosService } from '../../../services/catalogos.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

const TIPOS = [
  { codigo: 'categorias', etiqueta: 'Categorias' },
  { codigo: 'tallas',     etiqueta: 'Tallas' },
  { codigo: 'colores',    etiqueta: 'Colores' },
  { codigo: 'temporadas', etiqueta: 'Temporadas' },
];

@Component({
  selector: 'app-catalogos',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RouterLinkActive],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-09 Catalogos base</div><h1>{{ tituloActual() }}</h1></div>
    </div>

    <nav class="tabs">
      @for (t of tipos; track t.codigo) {
        <a [routerLink]="['/admin/catalogos', t.codigo]" routerLinkActive="on">{{ t.etiqueta }}</a>
      }
    </nav>

    <div class="marco-tabla">
      @if (cargando()) { <p class="mensaje">Cargando…</p> }
      @else if (registros().length === 0) {
        <div class="mensaje vacio"><h2>Sin registros</h2><p>Agrega el primero.</p></div>
      } @else {
        <table>
          <thead><tr><th class="col-indice">#</th><th>Nombre</th></tr></thead>
          <tbody>
            @for (r of registros(); track r.id; let i = $index) {
              <tr><td class="col-indice">{{ i + 1 }}</td><td><b>{{ r.nombre }}</b></td></tr>
            }
          </tbody>
        </table>
      }
    </div>

    <section class="nuevo">
      <label class="etiqueta">Nuevo registro</label>
      <div class="controles">
        <input class="campo" [(ngModel)]="nombre" placeholder="Nombre">
        <button class="btn rosa" (click)="guardar()" [disabled]="guardando()">
          {{ guardando() ? 'Guardando…' : 'Guardar' }}
        </button>
      </div>
    </section>
  `,
  styles: [`
    .cabecera{margin-bottom:12px;} h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:18px;font-weight:800;}
    .tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap;}
    .tabs a{padding:7px 14px;border-radius:99px;border:1.5px solid var(--linea);background:#fff;color:var(--gris);font-size:12.5px;}
    .tabs a.on{border-color:var(--tinta);background:var(--tinta);color:#fff;font-weight:700;}
    .nuevo{margin-top:14px;background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:16px;}
    .controles{display:flex;gap:8px;margin-top:6px;} .controles .campo{flex:1;}
  `],
})
export class CatalogosPage {
  private api = inject(CatalogosService);
  private avisos = inject(Notificaciones);
  private ruta = inject(ActivatedRoute);

  readonly tipos = TIPOS;
  readonly tipo = signal<string>('categorias');
  readonly registros = signal<any[]>([]);
  readonly cargando = signal(true);
  readonly guardando = signal(false);
  nombre = '';

  readonly tituloActual = computed(() =>
    this.tipos.find((t) => t.codigo === this.tipo())?.etiqueta ?? 'Catalogos');

  constructor() {
    effect(() => {
      const t = this.ruta.snapshot.paramMap.get('tipo');
      if (t) this.tipo.set(t);
      this.listar();
    });
    this.ruta.paramMap.subscribe((p) => {
      const t = p.get('tipo');
      if (t && t !== this.tipo()) { this.tipo.set(t); this.listar(); }
    });
  }

  async listar() {
    this.cargando.set(true);
    try { this.registros.set(await firstValueFrom(this.api.listar(this.tipo()))); }
    catch { this.registros.set([]); }
    finally { this.cargando.set(false); }
  }

  async guardar() {
    if (!this.nombre.trim()) { this.avisos.error('Nombre requerido'); return; }
    this.guardando.set(true);
    try {
      await firstValueFrom(this.api.guardar(this.tipo(), { nombre: this.nombre }));
      this.avisos.ok('Registro guardado');
      this.nombre = '';
      await this.listar();
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo guardar')); }
    finally { this.guardando.set(false); }
  }
}
