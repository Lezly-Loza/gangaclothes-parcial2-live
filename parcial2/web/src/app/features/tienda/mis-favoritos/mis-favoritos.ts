import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { API_URL } from '../../../core/api';
import { Notificaciones } from '../../../core/notificaciones';
import { BarraTienda } from '../../../shared/tienda/barra-tienda';

export interface PrendaFavoritaItem {
  favorito_id: number;
  producto_id: number;
  nombre: string;
  descripcion: string | null;
  marca: string | null;
  imagen_url: string | null;
  precio_base: number;
  precio_final: number;
  en_promocion: boolean;
  promocion_etiqueta: string | null;
  stock_disponible: number;
  fecha_guardado: string;
}

@Component({
  selector: 'app-mis-favoritos',
  standalone: true,
  imports: [RouterLink, BarraTienda],
  templateUrl: './mis-favoritos.html',
  styleUrl: './mis-favoritos.css',
})
export class MisFavoritos implements OnInit {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);
  private router = inject(Router);

  readonly favoritos = signal<PrendaFavoritaItem[]>([]);
  readonly cargando = signal<boolean>(true);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.cargarFavoritos();
  }

  cargarFavoritos(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.http.get<PrendaFavoritaItem[]>(`${API_URL}/tienda/favoritos`).subscribe({
      next: (items) => {
        this.favoritos.set(items);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudieron cargar tus prendas favoritas.');
        this.cargando.set(false);
      },
    });
  }

  quitar(item: PrendaFavoritaItem, event: Event): void {
    event.stopPropagation();
    this.http.delete(`${API_URL}/tienda/favoritos/${item.producto_id}`).subscribe({
      next: () => {
        this.favoritos.update((lista) => lista.filter((f) => f.producto_id !== item.producto_id));
        this.avisos.ok(`«${item.nombre}» fue retirada de tus favoritos.`);
      },
      error: () => {
        this.avisos.error('No se pudo quitar la prenda de favoritos.');
      },
    });
  }

  verEnCatalogo(item: PrendaFavoritaItem): void {
    this.router.navigate(['/catalogo'], { queryParams: { q: item.nombre } });
  }
}

