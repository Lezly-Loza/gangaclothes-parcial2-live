import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ProductosService } from '../../services/productos.service';
import { moneda } from '../../shared/formato';

@Component({
  selector: 'app-catalogo-cliente',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-14 Tienda</div><h1>Nueva temporada</h1>
        <p class="sub">Elegi tu prenda, reservala para probarla en sucursal o agregala al carrito.</p>
      </div>
    </div>

    @if (cargando()) { <p class="mensaje">Cargando catalogo…</p> }
    @else if (productos().length === 0) {
      <div class="mensaje vacio"><h2>Sin prendas por ahora</h2></div>
    } @else {
      <div class="grid">
        @for (p of productos(); track p.id) {
          <article class="prenda">
            <div class="imagen">👗</div>
            <div class="info">
              <div class="ceja">{{ p.temporada || 'disponible' }}</div>
              <h3>{{ p.nombre }}</h3>
              <p class="mono precio">Bs {{ dinero(p.precio_base) }}</p>
              <div class="acciones-prenda">
                <a routerLink="/tienda/reservar" [queryParams]="{variante: p.variantes?.[0]?.id || 1}" class="btn linea pequeno">Reservar</a>
                <a routerLink="/tienda/carrito" [queryParams]="{variante: p.variantes?.[0]?.id || 1}" class="btn rosa pequeno">Comprar</a>
              </div>
            </div>
          </article>
        }
      </div>
    }
  `,
  styles: [`
    .cabecera{margin-bottom:14px;} h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    h2{font-size:18px;font-weight:800;}
    h3{font-size:14px;font-weight:700;margin:4px 0;}
    .sub{color:var(--gris);font-size:13px;}
    .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;}
    .prenda{background:#fff;border:1.5px solid var(--linea);border-radius:13px;overflow:hidden;display:flex;flex-direction:column;}
    .imagen{aspect-ratio:1/1;background:var(--suave);display:grid;place-items:center;font-size:64px;}
    .info{padding:12px 14px;}
    .precio{font-size:18px;margin:4px 0 10px;}
    .acciones-prenda{display:flex;gap:6px;}
    .btn.pequeno{padding:6px 12px;font-size:11.5px;flex:1;}
  `],
})
export class CatalogoCliente {
  private api = inject(ProductosService);
  readonly productos = signal<any[]>([]);
  readonly cargando = signal(true);
  constructor() { this.cargar(); }
  async cargar() {
    try { this.productos.set(await firstValueFrom(this.api.listar())); }
    catch { this.productos.set([]); }
    finally { this.cargando.set(false); }
  }
  dinero(v: unknown) { return moneda(v); }
}
