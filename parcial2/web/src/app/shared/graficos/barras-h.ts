import { Component, computed, input } from '@angular/core';

export interface FilaBarra {
  etiqueta: string;
  valor: number;
  texto: string;
  detalle?: string;
  color?: string;
}

@Component({
  selector: 'app-barras-h',
  standalone: true,
  template: `
    <div class="barras" role="list">
      @for (f of medidas(); track f.etiqueta) {
        <div class="fila-barra" role="listitem"
             [attr.aria-label]="f.etiqueta + ': ' + f.texto"
             [title]="f.etiqueta + ' · ' + f.texto + (f.detalle ? ' · ' + f.detalle : '')">
          <div class="rotulo">
            <span class="nombre">{{ f.etiqueta }}</span>
            <span class="mono valor">{{ f.texto }}</span>
          </div>
          <div class="pista"><div class="barra" [style.width.%]="f.ancho" [style.background]="f.color || null"></div></div>
          @if (f.detalle) { <div class="detalle">{{ f.detalle }}</div> }
        </div>
      } @empty {
        <p class="sin-datos">Sin datos.</p>
      }
    </div>
  `,
  styles: [`
    .barras{display:flex;flex-direction:column;gap:10px;}
    .fila-barra{display:flex;flex-direction:column;gap:3px;}
    .rotulo{display:flex;justify-content:space-between;align-items:baseline;font-size:12px;}
    .rotulo .nombre{font-weight:600;}
    .pista{background:#ecece5;border-radius:99px;height:8px;overflow:hidden;}
    .barra{height:100%;background:var(--tinta);border-radius:99px;transition:width .35s ease;}
    .detalle{font-size:11px;color:var(--gris);}
    .sin-datos{color:var(--gris);font-size:12.5px;padding:10px 0;}
  `],
})
export class BarrasH {
  readonly filas = input.required<FilaBarra[]>();
  readonly medidas = computed(() => {
    const max = Math.max(0, ...this.filas().map((f) => f.valor));
    return this.filas().map((f) => ({ ...f, ancho: max > 0 ? Math.max(0, (f.valor / max) * 100) : 0 }));
  });
}
