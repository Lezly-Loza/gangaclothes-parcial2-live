import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, forkJoin, of } from 'rxjs';

import { API_URL } from '../../../core/api';
import { AuthService } from '../../../core/auth.service';

interface Ficha {
  etiqueta: string;
  total: number | null;
}

interface Indicadores {
  ventas: number;
  unidades: number;
  total: number;
  ticket_promedio: number;
  variacion_porcentaje: number | null;
  reservas_activas: number;
  alertas_stock: number;
  unidades_en_stock: number;
  valor_inventario_venta: number;
}

interface TopPrenda {
  clave: number;
  etiqueta: string;
  unidades: number;
  total: number;
  participacion: number;
}

@Component({
  selector: 'app-admin-inicio',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './inicio.html',
  styleUrl: './inicio.css',
})
export class AdminInicio {
  private http = inject(HttpClient);
  private router = inject(Router);
  readonly sesion = inject(AuthService).sesion;
  readonly esSuper = this.sesion.esSuper;

  readonly fichas = signal<Ficha[]>([]);
  readonly indicadores = signal<Indicadores | null>(null);
  readonly topPrendas = signal<TopPrenda[]>([]);
  readonly cargando = signal(true);

  readonly tenantNombre = computed(() => {
    const cod = this.sesion.tenantCodigo();
    if (!cod) return 'Plataforma Global';
    if (cod === 'luna') return 'Boutique Luna SRL';
    if (cod === 'andina') return 'Moda Andina SA';
    return cod.toUpperCase();
  });

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
    this.cargarDatos();
  }

  cargarDatos(): void {
    this.cargando.set(true);

    if (this.esSuper()) {
      const recursos = this.recursosSuper();
      forkJoin(
        recursos.map(([, ruta]) =>
          this.http.get<unknown>(`${API_URL}/${ruta}`).pipe(catchError(() => of(null)))
        )
      ).subscribe((respuestas) => {
        this.fichas.set(
          recursos.map(([etiqueta], i) => ({
            etiqueta,
            total: Array.isArray(respuestas[i]) ? (respuestas[i] as unknown[]).length : null,
          }))
        );
        this.cargando.set(false);
      });
      return;
    }

    // Tenant regular: Cargar conteos y dashboard analítico
    const recursos = this.recursosTenant();
    const reqConteos = forkJoin(
      recursos.map(([, ruta]) =>
        this.http
          .get<unknown>(`${API_URL}/${ruta}${ruta === 'clientes' ? '?q=' : ''}`)
          .pipe(catchError(() => of(null)))
      )
    );

    const reqDashboard = this.http
      .get<{ indicadores: Indicadores; top_prendas: TopPrenda[] }>(`${API_URL}/reportes/dashboard`)
      .pipe(catchError(() => of(null)));

    forkJoin({ conteos: reqConteos, dash: reqDashboard }).subscribe(({ conteos, dash }) => {
      this.fichas.set(
        recursos.map(([etiqueta], i) => ({
          etiqueta,
          total: Array.isArray(conteos[i]) ? (conteos[i] as unknown[]).length : null,
        }))
      );

      if (dash && dash.indicadores) {
        this.indicadores.set(dash.indicadores);
        this.topPrendas.set(dash.top_prendas?.slice(0, 5) || []);
      }
      this.cargando.set(false);
    });
  }

  irA(ruta: string): void {
    this.router.navigateByUrl(ruta);
  }
}
