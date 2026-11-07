import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { API_URL } from '../core/api';
import { SesionStore } from '../core/sesion';

export interface OpcionOffline { id: number; nombre: string; }
export interface CatalogoOffline {
  fecha_descarga: string; categorias: OpcionOffline[]; temporadas: OpcionOffline[];
  productos: { id: number; nombre: string; precio_base: number; categoria_id: number | null; temporada_id: number | null }[];
  variantes: { id: number; producto_id: number; sku: string; precio: number; stock: number }[];
}
export interface CopiaOffline { catalogo: CatalogoOffline; sucursal: OpcionOffline; sucursales: OpcionOffline[]; categoria: string; temporada: string; }

@Injectable({ providedIn: 'root' })
export class OfflineService {
  private http = inject(HttpClient); private sesion = inject(SesionStore);
  private clave(): string {
    const u = this.sesion.usuario();
    if (!u?.tenant_id || !u.id) throw new Error('Inicia sesión para usar el catálogo guardado.');
    return `${u.tenant_id}:${u.id}`;
  }
  private abrir(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('ganga-catalogos-offline', 1);
      request.onupgradeneeded = () => request.result.createObjectStore('catalogos');
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  async guardarCatalogoLocal(copia: CopiaOffline): Promise<void> {
    const db = await this.abrir();
    try { await new Promise<void>((resolve, reject) => {
      const tx = db.transaction('catalogos', 'readwrite');
      tx.objectStore('catalogos').put(copia, this.clave());
      tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error);
    }); } finally { db.close(); }
  }
  async obtenerCatalogoLocal(): Promise<CopiaOffline | null> {
    const db = await this.abrir();
    try { return await new Promise<CopiaOffline | null>((resolve, reject) => {
      const request = db.transaction('catalogos').objectStore('catalogos').get(this.clave());
      request.onsuccess = () => resolve(request.result ?? null); request.onerror = () => reject(request.error);
    }); } finally { db.close(); }
  }
  async descargarCatalogo(sucursalId: number, categoria: string, temporada: string): Promise<CatalogoOffline> {
    const params: Record<string, string> = { sucursal_id: String(sucursalId) };
    if (categoria) params['categoria_id'] = categoria;
    if (temporada) params['temporada_id'] = temporada;
    return firstValueFrom(this.http.get<CatalogoOffline>(`${API_URL}/offline/catalogo`, { params }));
  }
  opciones() { return firstValueFrom(this.http.get<{ categorias: OpcionOffline[]; temporadas: OpcionOffline[] }>(`${API_URL}/offline/opciones`)); }
  sucursales() { return firstValueFrom(this.http.get<OpcionOffline[]>(`${API_URL}/sucursales`)); }
}
