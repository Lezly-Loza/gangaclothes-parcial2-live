import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { openDB } from 'idb';
import { environment } from '../../environments/environment';

export class ProductoLocal {
  async guardarCatalogoLocal(catalogo: any): Promise<void> {
    const db = await openDB('gangaclothes', 1, { upgrade(db) {
      db.createObjectStore('productos', { keyPath: 'id' });
      db.createObjectStore('variantes', { keyPath: 'id' });
      db.createObjectStore('estado');
    }});
    const tx = db.transaction(['productos', 'variantes', 'estado'], 'readwrite');
    for (const producto of catalogo.productos) await tx.objectStore('productos').put(producto);
    for (const variante of catalogo.variantes) await tx.objectStore('variantes').put(variante);
    await tx.objectStore('estado').put(catalogo.fecha_descarga, 'fecha_ultima_descarga');
    await tx.done;
  }
}

@Injectable({providedIn: 'root'})
export class OfflineService {
  private http = inject(HttpClient);
  private local = new ProductoLocal();
  async descargarCatalogo(filtros: {sucursal_id: number; categorias?: number[]; temporada?: number}) {
    const db = await openDB('gangaclothes', 1, { upgrade(db) {
      db.createObjectStore('productos', { keyPath: 'id' });
      db.createObjectStore('variantes', { keyPath: 'id' });
      db.createObjectStore('estado');
    }});
    const desde = await db.get('estado', 'fecha_ultima_descarga');
    try {
      const params: any = { sucursal_id: filtros.sucursal_id };
      if (desde) params.desde = desde;
      const catalogo = await firstValueFrom(this.http.get<any>(`${environment.apiUrl}/offline/catalogo`, {params}));
      await this.local.guardarCatalogoLocal(catalogo);
    } catch { /* Se conserva la última copia local. */ }
    return { productos: await db.getAll('productos'), fecha_descarga: await db.get('estado', 'fecha_ultima_descarga') };
  }
}
