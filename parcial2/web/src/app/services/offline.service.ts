import { HttpClient } from '@angular/common/http';
import { Injectable, effect, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { API_URL } from '../core/api';
import { SesionStore } from '../core/sesion';
import { Notificaciones } from '../core/notificaciones';

export interface OpcionOffline { id: number; nombre: string; }
export interface CatalogoOffline {
  fecha_descarga: string; categorias: OpcionOffline[]; temporadas: OpcionOffline[];
  productos: { id: number; nombre: string; precio_base: number; categoria_id: number | null; temporada_id: number | null }[];
  variantes: { id: number; producto_id: number; sku: string; precio: number; stock: number }[];
}
export interface CopiaOffline { catalogo: CatalogoOffline; sucursal: OpcionOffline; sucursales: OpcionOffline[]; categoria: string; temporada: string; }
export interface OperacionLocal {
  uuid_operacion: string; tipo: 'reserva' | 'venta'; sucursal_id: number; variante_id: number;
  cantidad: number; precio_unitario: number; monto_recibido: number | null;
  fecha_hora_prueba: string | null; fecha_local: string;
  estado: 'pendiente' | 'conflicto' | 'confirmada'; error: string | null; codigo: string | null;
  confirmada_en: string | null;
  incluida_en_copia?: boolean;
  nombre: string; sku: string; sucursal: string; cuenta: string;
}

@Injectable({ providedIn: 'root' })
export class OfflineService {
  private http = inject(HttpClient); private sesion = inject(SesionStore);
  private avisos = inject(Notificaciones);
  private enCurso: Promise<void> | null = null;
  readonly revision = signal(0);

  constructor() {
    if (typeof window === 'undefined') return;
    const intentar = () => {
      if (!navigator.onLine || !this.sesion.usuario()?.tenant_id) return;
      const habiaIntento = this.enCurso !== null;
      void this.sincronizarPendientes().catch(() => {}).then(() => {
        // Si la reconexión llegó durante un intento sin red, se intenta una vez
        // más al terminar ese intento; el evento no debe perderse.
        if (habiaIntento && navigator.onLine && this.sesion.usuario()?.tenant_id)
          void this.sincronizarPendientes().catch(() => {});
      });
    };
    window.addEventListener('online', intentar);
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') intentar(); });
    effect(() => { this.sesion.usuario(); intentar(); });
  }

  sincronizarPendientes(incluirConflictos = false): Promise<void> {
    if (this.enCurso) return this.enCurso;
    this.enCurso = (async () => {
      for (const op of await this.operaciones()) {
        if (op.estado !== 'pendiente' && !(incluirConflictos && op.estado === 'conflicto')) continue;
        await this.sincronizar(op);
        const resultado = (await this.operaciones()).find(x => x.uuid_operacion === op.uuid_operacion);
        this.revision.update(n => n + 1);
        if (resultado?.estado === 'confirmada') this.avisos.ok(`${op.tipo === 'reserva' ? 'Reserva confirmada' : 'Venta confirmada'}: ${resultado.codigo}`);
        if (resultado?.estado === 'conflicto' && op.estado !== 'conflicto') this.avisos.error(`${op.tipo === 'reserva' ? 'Reserva no confirmada' : 'Venta no confirmada'}: ${resultado.error}`);
      }
    })().finally(() => { this.enCurso = null; });
    return this.enCurso;
  }
  private clave(): string {
    const u = this.sesion.usuario();
    if (!u?.tenant_id || !u.id) throw new Error('Inicia sesión para usar el catálogo guardado.');
    return `${u.tenant_id}:${u.id}`;
  }
  private abrir(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('ganga-catalogos-offline', 2);
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains('catalogos')) request.result.createObjectStore('catalogos');
        if (!request.result.objectStoreNames.contains('operaciones')) request.result.createObjectStore('operaciones');
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  async guardarCatalogoLocal(copia: CopiaOffline, confirmadasAntes: string[] = []): Promise<void> {
    const db = await this.abrir(); const cuenta = this.clave();
    try { await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(['catalogos', 'operaciones'], 'readwrite');
      tx.objectStore('catalogos').put(copia, cuenta);
      const store = tx.objectStore('operaciones'); const req = store.getAll();
      req.onsuccess = () => { for (const o of req.result as OperacionLocal[]) {
        if (o.cuenta === cuenta && o.estado === 'confirmada' && o.sucursal_id === copia.sucursal.id && confirmadasAntes.includes(o.uuid_operacion)) {
          store.put({ ...o, incluida_en_copia: true }, `${cuenta}:${o.uuid_operacion}`);
        }
      } };
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
  async operaciones(): Promise<OperacionLocal[]> {
    const db = await this.abrir(); const clave = this.clave();
    try { return await new Promise((resolve, reject) => {
      const req = db.transaction('operaciones').objectStore('operaciones').getAll();
      req.onsuccess = () => resolve((req.result as OperacionLocal[]).filter(o => o.cuenta === clave).sort((a, b) => a.fecha_local.localeCompare(b.fecha_local)));
      req.onerror = () => reject(req.error);
    }); } finally { db.close(); }
  }
  async guardarOperacion(datos: Omit<OperacionLocal, 'uuid_operacion' | 'estado' | 'error' | 'codigo' | 'cuenta' | 'confirmada_en'>): Promise<void> {
    const db = await this.abrir(); const cuenta = this.clave();
    try { await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(['operaciones', 'catalogos'], 'readwrite');
      const op = tx.objectStore('operaciones'); const catalogos = tx.objectStore('catalogos');
      const solicitud = catalogos.get(cuenta); let problema = '';
      solicitud.onsuccess = () => {
        const copia = solicitud.result as CopiaOffline | undefined;
        const variante = copia?.catalogo.variantes.find(v => v.id === datos.variante_id);
        if (!copia || copia.sucursal.id !== datos.sucursal_id || !variante || variante.precio !== datos.precio_unitario) {
          problema = 'La copia cambió. Revisa la prenda antes de registrar.'; tx.abort(); return;
        }
        const pendientes = op.getAll();
        pendientes.onsuccess = () => {
          const usados = (pendientes.result as OperacionLocal[]).filter(o => o.cuenta === cuenta && o.sucursal_id === datos.sucursal_id &&
            o.variante_id === datos.variante_id && ocupaCopia(o)).reduce((s, o) => s + o.cantidad, 0);
          if (datos.cantidad < 1 || !Number.isInteger(datos.cantidad) || datos.cantidad > variante.stock - usados) {
            problema = 'La cantidad supera el stock de la copia, descontando las operaciones pendientes.'; tx.abort(); return;
          }
          const nueva: OperacionLocal = { ...datos, uuid_operacion: crypto.randomUUID(), cuenta, estado: 'pendiente', error: null, codigo: null, confirmada_en: null };
          op.add(nueva, `${cuenta}:${nueva.uuid_operacion}`);
        };
      };
      tx.oncomplete = () => resolve(); tx.onabort = () => reject(new Error(problema || 'No se pudo guardar la operación.'));
      tx.onerror = () => reject(tx.error);
    }); } finally { db.close(); }
  }
  private async actualizarOperacion(o: OperacionLocal): Promise<void> {
    const cuenta = this.clave();
    if (cuenta !== o.cuenta) throw new Error('La sesión cambió; vuelve a entrar con la cuenta original.');
    const db = await this.abrir();
    try { await new Promise<void>((resolve, reject) => { const tx = db.transaction('operaciones', 'readwrite');
      const store = tx.objectStore('operaciones'); const key = `${cuenta}:${o.uuid_operacion}`;
      const actual = store.get(key);
      actual.onsuccess = () => {
        const previa = actual.result as OperacionLocal | undefined;
        if (!previa || (previa.estado === 'confirmada' && o.estado !== 'confirmada')) return;
        store.put({ ...o, incluida_en_copia: previa.estado === 'confirmada' ? previa.incluida_en_copia : false }, key);
      };
      tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error);
    }); } finally { db.close(); }
  }
  async quitarOperacion(o: OperacionLocal): Promise<void> {
    if (o.cuenta !== this.clave()) throw new Error('La sesión cambió; usa la cuenta original.');
    if (o.estado === 'pendiente') throw new Error('Sincroniza primero: el resultado de una operación pendiente puede ser incierto.');
    const copia = await this.obtenerCatalogoLocal();
    if (o.estado === 'confirmada' && copia?.sucursal.id === o.sucursal_id && ocupaCopia(o)) {
      throw new Error('Descarga de nuevo el catálogo antes de quitar este resultado, para conservar el stock local correcto.');
    }
    const db = await this.abrir();
    try { await new Promise<void>((resolve, reject) => { const tx = db.transaction('operaciones', 'readwrite');
      tx.objectStore('operaciones').delete(`${this.clave()}:${o.uuid_operacion}`);
      tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error);
    }); } finally { db.close(); }
  }
  async sincronizar(o: OperacionLocal): Promise<void> {
    if (o.cuenta !== this.clave()) throw new Error('La sesión cambió; vuelve a entrar con la cuenta original.');
    if (o.estado === 'confirmada') return;
    const { uuid_operacion, tipo, sucursal_id, variante_id, cantidad, precio_unitario, monto_recibido, fecha_hora_prueba, fecha_local } = o;
    try {
      const resultado = await firstValueFrom(this.http.post<{ codigo: string; confirmada_en: string }>(`${API_URL}/offline/sincronizar`,
        { uuid_operacion, tipo, sucursal_id, variante_id, cantidad, precio_unitario, monto_recibido, fecha_hora_prueba, fecha_local }));
      await this.actualizarOperacion({ ...o, estado: 'confirmada', error: null, codigo: resultado.codigo, confirmada_en: resultado.confirmada_en });
    } catch (err: any) {
      if ([403, 409, 422].includes(err?.status)) {
        const detalle = typeof err?.error?.detail === 'string' ? err.error.detail : 'Operación rechazada. Revisa los datos.';
        await this.actualizarOperacion({ ...o, estado: 'conflicto', error: detalle });
      } else { throw err; }
    }
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

/** Una confirmación posterior a la descarga todavía no está reflejada en esa copia. */
export function ocupaCopia(o: OperacionLocal): boolean {
  return o.estado !== 'confirmada' || !o.incluida_en_copia;
}
