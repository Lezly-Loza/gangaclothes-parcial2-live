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

interface TenantItem {
  id: number;
  codigo: string;
  razon_social: string;
  nit: string;
  plan_codigo?: string;
  estado?: string;
}

interface PlanItem {
  id: number;
  codigo: string;
  nombre: string;
  precio_mensual: number;
  max_sucursales: number;
  max_usuarios: number;
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
  readonly empresas = signal<TenantItem[]>([]);
  readonly planes = signal<PlanItem[]>([]);
  readonly cargando = signal(true);

  readonly tenantNombre = computed(() => {
    const cod = this.sesion.tenantCodigo();
    if (!cod) return 'Plataforma Global';
    if (cod === 'luna') return 'Boutique Luna SRL';
    if (cod === 'andina') return 'Moda Andina SA';
    return cod.toUpperCase();
  });

  private recursosTenant(): Array<[string, string, string]> {
    return [
      ['Categorias',  'catalogos/categorias', 'catalogos:ver'],
      ['Tallas',      'catalogos/tallas',     'catalogos:ver'],
      ['Colores',     'catalogos/colores',    'catalogos:ver'],
      ['Temporadas',  'catalogos/temporadas', 'catalogos:ver'],
      ['Sucursales',  'sucursales',           'sucursales:ver'],
      ['Proveedores', 'proveedores',          'proveedores:ver'],
      ['Clientes',    'clientes',             'clientes:ver'],
    ];
  }

  constructor() {
    this.cargarDatos();
  }

  cargarDatos(): void {
    this.cargando.set(true);

    if (this.esSuper()) {
      forkJoin({
        tenants: this.http.get<TenantItem[]>(`${API_URL}/tenants`).pipe(catchError(() => of([]))),
        planes: this.http.get<PlanItem[]>(`${API_URL}/planes`).pipe(catchError(() => of([]))),
      }).subscribe(({ tenants, planes }) => {
        this.empresas.set(tenants || []);
        this.planes.set(planes || []);
        this.fichas.set([
          { etiqueta: 'Empresas Registradas', total: tenants?.length ?? 0 },
          { etiqueta: 'Planes de Suscripción', total: planes?.length ?? 0 },
        ]);
        this.cargando.set(false);
      });
      return;
    }

    // Tenant regular: Cargar unicamente recursos a los que el rol del usuario tiene permiso
    const recursos = this.recursosTenant().filter(([, , perm]) => this.sesion.tienePermiso(perm));
    const reqConteos = recursos.length > 0
      ? forkJoin(
          recursos.map(([, ruta]) =>
            this.http
              .get<unknown>(`${API_URL}/${ruta}${ruta === 'clientes' ? '?q=' : ''}`)
              .pipe(catchError(() => of(null)))
          )
        )
      : of([]);

    const reqDashboard = this.sesion.tienePermiso('reportes:ver')
      ? this.http
          .get<{ indicadores: Indicadores; top_prendas: TopPrenda[] }>(`${API_URL}/reportes/dashboard`)
          .pipe(catchError(() => of(null)))
      : of(null);

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
