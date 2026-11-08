import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, effect, inject, input, signal } from '@angular/core';
import { API_URL } from '../../core/api';
import { moneda } from '../../shared/formato';

interface Analitica {
  prediccion: { disponible: boolean; motivo?: string; metodo?: string; aviso?: string; dias_con_ventas: number;
    error_absoluto_medio_7_dias?: number | null; valores: { fecha: string; monto_estimado: number }[] };
  segmentos: { disponible: boolean; motivo?: string; metodo?: string; clientes_con_compras: number;
    grupos: { segmento: string; clientes: number; recencia_dias_promedio: number; compras_promedio: number; monto_promedio: number }[] };
}
@Component({ selector: 'app-analitica-dashboard', template: `
  <section class="analitica"><h2>Predicciones y segmentos</h2>
    <p>Modelos exploratorios basados en las ventas del período y la sucursal elegidos.</p>
    @if (error()) { <p class="error">{{ error() }}</p> }
    @else if (!datos()) { <p>Calculando análisis…</p> }
    @else { @if (datos(); as d) {
      <div class="columnas"><div><h3>Estimación de ventas · próximos 7 días</h3>
        @if (d.prediccion.disponible) {
          <p>{{ d.prediccion.metodo }} · {{ d.prediccion.dias_con_ventas }} días con ventas.</p>
          <ul>@for (p of d.prediccion.valores; track p.fecha) { <li><span>{{ p.fecha }}</span><b>Bs {{ moneda(p.monto_estimado) }}</b></li> }</ul>
          @if (d.prediccion.error_absoluto_medio_7_dias != null) { <p>Error medio en los últimos 7 días de prueba: Bs {{ moneda(d.prediccion.error_absoluto_medio_7_dias) }}.</p> }
          <p>{{ d.prediccion.aviso }}</p>
        } @else { <p>{{ d.prediccion.motivo }}</p> }
      </div><div><h3>Segmentos de clientes</h3>
        @if (d.segmentos.disponible) {
          <p>{{ d.segmentos.metodo }}. Solo compras asociadas a cliente; no se muestran datos personales.</p>
          @for (g of d.segmentos.grupos; track g.segmento) { <article><b>{{ g.segmento }} · {{ g.clientes }} clientes</b><p>Última compra: {{ g.recencia_dias_promedio }} días en promedio · {{ g.compras_promedio }} compras · Bs {{ moneda(g.monto_promedio) }} por cliente</p></article> }
        } @else { <p>{{ d.segmentos.motivo }}</p> }
      </div></div>
    } }
  </section>
`, styles: [`.analitica{background:#fff;border:1px solid var(--linea);border-radius:14px;margin:16px 0;padding:18px}.analitica h2{font-size:19px;font-weight:800}.analitica h3{font-size:15px;font-weight:800;margin:12px 0}.analitica p{font-size:12px;line-height:1.5;color:var(--gris)}.columnas{display:grid;grid-template-columns:1fr 1fr;gap:25px}.columnas ul{padding:0;list-style:none}.columnas li{display:flex;justify-content:space-between;border-bottom:1px solid var(--linea);padding:6px 0}article{border-bottom:1px solid var(--linea);padding:5px 0}.error{color:#bd320e!important}@media(max-width:700px){.columnas{grid-template-columns:1fr}}`] })
export class AnaliticaDashboard {
  private http = inject(HttpClient); readonly moneda = moneda;
  readonly desde = input.required<string>(); readonly hasta = input.required<string>(); readonly sucursalId = input<number | null>(null);
  readonly datos = signal<Analitica | null>(null); readonly error = signal(''); private version = 0;
  constructor() { effect(() => {
    const desde = this.desde(), hasta = this.hasta(), sucursal = this.sucursalId(); const version = ++this.version;
    let params = new HttpParams().set('desde', desde).set('hasta', hasta); if (sucursal !== null) params = params.set('sucursal_id', sucursal);
    this.datos.set(null); this.error.set('');
    this.http.get<Analitica>(`${API_URL}/reportes/analitica`, { params }).subscribe({
      next: r => { if (version === this.version) this.datos.set(r); },
      error: () => { if (version === this.version) this.error.set('No se pudo cargar la analítica.'); },
    });
  }); }
}
