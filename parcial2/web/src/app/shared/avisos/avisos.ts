import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Notificaciones } from '../../core/notificaciones';

@Component({
  selector: 'app-avisos',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="avisos" aria-live="polite">
      @for (a of n.avisos(); track a.id) {
        <div class="aviso" [class.ok]="a.tipo === 'ok'" [class.error]="a.tipo === 'error'" role="status">
          <span>{{ a.texto }}</span>
          <button class="cerrar" (click)="n.cerrar(a.id)" aria-label="Cerrar">×</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .aviso{display:flex;gap:12px;align-items:flex-start;padding:10px 12px;border-radius:10px;
           background:#fff;border:1.5px solid var(--linea);font-size:12.5px;box-shadow:0 8px 18px rgba(20,22,26,.12);}
    .aviso.ok{border-color:var(--ok);color:var(--ok);background:#e4f2ec;}
    .aviso.error{border-color:var(--alerta);color:var(--alerta);background:#fce9e2;}
    .cerrar{background:none;border:none;font-size:18px;line-height:1;cursor:pointer;color:inherit;margin-left:auto;}
  `],
})
export class Avisos {
  n = inject(Notificaciones);
}
