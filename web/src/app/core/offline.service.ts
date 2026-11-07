import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { API_URL } from './api';
import { Notificaciones } from './notificaciones';

export interface OperacionLocal {
  uuid_operacion: string;
  tipo: 'RESERVA' | 'VENTA';
  estado: 'LOCAL' | 'ENVIADA' | 'CONFIRMADA' | 'RECHAZADA' | 'EN_CONFLICTO';
  fecha_creacion: string;
  sucursal_id: number;
  usuario_id?: number;
  datos: any;
  mensaje_servidor?: string;
}

/**
 * CU-19 y CU-20: Servicio de persistencia y sincronización Offline (IndexedDB).
 *
 * Tablas locales en IndexedDB:
 *  - productos_local
 *  - variantes_local
 *  - reservas_local
 *  - operaciones_pendientes
 *
 * Máquina de estados de operación local:
 *  LOCAL -> ENVIADA -> CONFIRMADA | RECHAZADA | EN_CONFLICTO
 */
@Injectable({ providedIn: 'root' })
export class OfflineService {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);

  // Señales reactivas
  readonly enLinea = signal(navigator.onLine);
  readonly fechaUltimaDescarga = signal<Date | null>(this.leerUltimaDescarga());
  readonly operacionesPendientes = signal<number>(0);

  // Banner superior para CU-19
  readonly bannerOffline = computed(() => {
    if (this.enLinea()) return null;
    const f = this.fechaUltimaDescarga();
    const fechaStr = f
      ? f.toLocaleDateString('es-BO', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
      : 'sin datos previos';
    return `Modo sin conexión - Catálogo al: ${fechaStr}. Los datos pueden variar`;
  });

  private dbPromise: Promise<IDBDatabase> | null = null;
  private readonly DB_NAME = 'gangaclothes_pwa_db';
  private readonly DB_VERSION = 1;

  constructor() {
    window.addEventListener('online', () => {
      this.enLinea.set(true);
      this.avisos.ok('✓ Conexión a internet restablecida. Sincronizando operaciones...');
      this.sincronizarOperaciones();
    });

    window.addEventListener('offline', () => {
      this.enLinea.set(false);
      this.avisos.ok('Modo sin conexión activado. Las operaciones se guardarán localmente.');
    });

    this.initDB().then(() => {
      this.actualizarContadorPendientes();
      if (this.enLinea()) {
        this.sincronizarCatalogoLocal();
      }
    });
  }

  // ----------------------------------------------------------------- IndexedDB setup
  private initDB(): Promise<IDBDatabase> {
    if (this.dbPromise) return this.dbPromise;

    this.dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(this.DB_NAME, this.DB_VERSION);

      req.onupgradeneeded = (e) => {
        const db = (e.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains('productos_local')) {
          db.createObjectStore('productos_local', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('variantes_local')) {
          db.createObjectStore('variantes_local', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('reservas_local')) {
          db.createObjectStore('reservas_local', { keyPath: 'uuid_operacion' });
        }
        if (!db.objectStoreNames.contains('operaciones_pendientes')) {
          const store = db.createObjectStore('operaciones_pendientes', { keyPath: 'uuid_operacion' });
          store.createIndex('estado', 'estado', { unique: false });
        }
      };

      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });

    return this.dbPromise;
  }

  // ------------------------------------------------- CU-19: Sincronizar catálogo local
  async sincronizarCatalogoLocal(): Promise<void> {
    if (!this.enLinea()) return;
    try {
      const db = await this.initDB();
      this.http.get<any[]>(`${API_URL}/catalogo`).subscribe({
        next: (prendas) => {
          const tx = db.transaction(['productos_local', 'variantes_local'], 'readwrite');
          const pStore = tx.objectStore('productos_local');
          const vStore = tx.objectStore('variantes_local');
          pStore.clear();
          vStore.clear();

          prendas.forEach((p) => {
            pStore.put(p);
            (p.variantes || []).forEach((v: any) => vStore.put(v));
          });

          const ahora = new Date();
          localStorage.setItem('gangaclothes_catalogo_descarga', ahora.toISOString());
          this.fechaUltimaDescarga.set(ahora);
        },
        error: (err) => console.warn('Error al sincronizar catálogo local:', err),
      });
    } catch (e) {
      console.warn('Error accediendo a IndexedDB:', e);
    }
  }

  async obtenerCatalogoLocal(): Promise<any[]> {
    const db = await this.initDB();
    return new Promise((resolve) => {
      const tx = db.transaction('productos_local', 'readonly');
      const store = tx.objectStore('productos_local');
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  // ------------------------------------------------- CU-20: Registrar reserva offline
  /**
   * Genera UUIDv4, guarda en reservas_local y operaciones_pendientes con estado 'LOCAL'.
   */
  async registrarReservaOffline(datos: {
    sucursal_id: number;
    variante_id: number;
    cantidad: number;
    cliente_id?: number;
    notas?: string;
  }): Promise<string> {
    const uuid = this.generarUUID();
    const op: OperacionLocal = {
      uuid_operacion: uuid,
      tipo: 'RESERVA',
      estado: 'LOCAL',
      fecha_creacion: new Date().toISOString(),
      sucursal_id: datos.sucursal_id,
      datos,
    };

    const db = await this.initDB();
    const tx = db.transaction(['reservas_local', 'operaciones_pendientes'], 'readwrite');
    tx.objectStore('reservas_local').put(op);
    tx.objectStore('operaciones_pendientes').put(op);

    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });

    await this.actualizarContadorPendientes();

    // Notificación requerida en CU-20
    this.avisos.ok('Reserva guardada en el dispositivo. Se sincronizará automáticamente al recuperar conexión');
    return uuid;
  }

  // ------------------------------------------------- CU-20: Sincronización automática
  async sincronizarOperaciones(): Promise<void> {
    if (!this.enLinea()) return;
    const db = await this.initDB();

    const pendientes: OperacionLocal[] = await new Promise((resolve) => {
      const tx = db.transaction('operaciones_pendientes', 'readonly');
      const store = tx.objectStore('operaciones_pendientes');
      const index = store.index('estado');
      const req = index.getAll('LOCAL');
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });

    for (const op of pendientes) {
      await this.enviarOperacion(op);
    }

    await this.actualizarContadorPendientes();
  }

  private async enviarOperacion(op: OperacionLocal): Promise<void> {
    const db = await this.initDB();

    // Paso a ENVIADA
    await this.actualizarEstado(op.uuid_operacion, 'ENVIADA');

    return new Promise((resolve) => {
      this.http.post(`${API_URL}/reservas`, op.datos).subscribe({
        next: () => {
          this.actualizarEstado(op.uuid_operacion, 'CONFIRMADA');
          resolve();
        },
        error: (err) => {
          const nuevoEstado = err.status === 409 ? 'EN_CONFLICTO' : 'RECHAZADA';
          this.actualizarEstado(op.uuid_operacion, nuevoEstado, err.message);
          resolve();
        },
      });
    });
  }

  private async actualizarEstado(uuid: string, nuevoEstado: OperacionLocal['estado'], errorMsg?: string): Promise<void> {
    const db = await this.initDB();
    const tx = db.transaction(['reservas_local', 'operaciones_pendientes'], 'readwrite');
    const resStore = tx.objectStore('reservas_local');
    const opStore = tx.objectStore('operaciones_pendientes');

    const req = opStore.get(uuid);
    req.onsuccess = () => {
      if (req.result) {
        const item: OperacionLocal = { ...req.result, estado: nuevoEstado, mensaje_servidor: errorMsg };
        opStore.put(item);
        resStore.put(item);
      }
    };
  }

  async actualizarContadorPendientes(): Promise<void> {
    try {
      const db = await this.initDB();
      const count = await new Promise<number>((resolve) => {
        const tx = db.transaction('operaciones_pendientes', 'readonly');
        const store = tx.objectStore('operaciones_pendientes');
        const index = store.index('estado');
        const req = index.count('LOCAL');
        req.onsuccess = () => resolve(req.result || 0);
        req.onerror = () => resolve(0);
      });
      this.operacionesPendientes.set(count);
    } catch {
      this.operacionesPendientes.set(0);
    }
  }

  // ------------------------------------------------- Helpers
  private generarUUID(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  private leerUltimaDescarga(): Date | null {
    const raw = localStorage.getItem('gangaclothes_catalogo_descarga');
    return raw ? new Date(raw) : null;
  }
}

