import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { catchError, forkJoin, of } from 'rxjs';

import { API_URL } from '../../../core/api';
import { AuthService } from '../../../core/auth.service';

interface Ficha {
  etiqueta: string;
  total: number | null;
}

@Component({
  selector: 'app-admin-inicio',
  templateUrl: './inicio.html',
  styleUrl: './inicio.css',
})
export class AdminInicio {
  private http = inject(HttpClient);
  readonly sesion = inject(AuthService).sesion;
  readonly esSuper = this.sesion.esSuper;

  readonly fichas = signal<Ficha[]>([]);
  readonly cargando = signal(true);

  /**
   * Fichas "registros en la base de datos" — parcial 2. El super ve totales
   * de la plataforma (empresas, planes), el tenant ve sus propios recursos.
   * Los endpoints son los reales del backend parcial 2 (no los /admin/* del parcial 1).
   */
  private recursosTenant(): Array<[string, string]> {
    return [
      ['Categorias',  'catalogos/categorias'],
      ['Tallas',      'catalogos/tallas'],
      ['Colores',     'catalogos/colores'],
      ['Temporadas',  'catalogos/temporadas'],
      ['Sucursales',  'sucursales'],
      ['Proveedores', 'proveedores'],
      ['Clientes',    'clientes'],
    ];
  }

  private recursosSuper(): Array<[string, string]> {
    return [
      ['Empresas', 'tenants'],
      ['Planes',   'planes'],
    ];
  }

  constructor() {
    const recursos = this.esSuper() ? this.recursosSuper() : this.recursosTenant();
    forkJoin(
      recursos.map(([, ruta]) =>
        this.http
          .get<unknown>(`${API_URL}/${ruta}${ruta === 'clientes' ? '?q=' : ''}`)
          .pipe(catchError(() => of(null))),
      ),
    ).subscribe((respuestas) => {
      this.fichas.set(
        recursos.map(([etiqueta], i) => ({
          etiqueta,
          total: Array.isArray(respuestas[i]) ? (respuestas[i] as unknown[]).length : null,
        })),
      );
      this.cargando.set(false);
    });
  }
}
