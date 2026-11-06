import { Injectable, computed, signal } from '@angular/core';

export type Rol = 'superadmin' | 'admin' | 'encargado' | 'vendedor' | 'cliente';

export interface Sesion {
  access_token: string;
  kind: 'tenant' | 'super';
  tenant_id: number | null;
  tenant_codigo: string | null;
  user_id: number;
  nombre: string;
  roles: string[];
}

const CLAVE_TOKEN = 'token';
const CLAVE_SESION = 'session';

@Injectable({ providedIn: 'root' })
export class SesionStore {
  private readonly _sesion = signal<Sesion | null>(this.leer());
  readonly sesion = this._sesion.asReadonly();
  readonly autenticado = computed(() => this._sesion() !== null);
  readonly roles = computed<string[]>(() => this._sesion()?.roles ?? []);
  readonly nombre = computed(() => this._sesion()?.nombre ?? '');
  readonly tenantCodigo = computed(() => this._sesion()?.tenant_codigo ?? null);
  readonly tenantId = computed(() => this._sesion()?.tenant_id ?? null);
  readonly esSuper = computed(() => this._sesion()?.kind === 'super');
  readonly rolPrincipal = computed<Rol | null>(() => {
    const jerarquia: Rol[] = ['superadmin', 'admin', 'encargado', 'vendedor', 'cliente'];
    return jerarquia.find((r) => this.roles().includes(r)) ?? null;
  });

  get token(): string | null { return localStorage.getItem(CLAVE_TOKEN); }

  guardar(sesion: Sesion): void {
    localStorage.setItem(CLAVE_TOKEN, sesion.access_token);
    localStorage.setItem(CLAVE_SESION, JSON.stringify(sesion));
    this._sesion.set(sesion);
  }
  limpiar(): void {
    localStorage.removeItem(CLAVE_TOKEN);
    localStorage.removeItem(CLAVE_SESION);
    this._sesion.set(null);
  }

  tieneAlgunRol(...roles: string[]): boolean {
    return roles.some((r) => this.roles().includes(r));
  }

  private leer(): Sesion | null {
    const crudo = localStorage.getItem(CLAVE_SESION);
    if (!crudo || !localStorage.getItem(CLAVE_TOKEN)) return null;
    try { return JSON.parse(crudo) as Sesion; }
    catch { localStorage.removeItem(CLAVE_SESION); return null; }
  }
}

export function rutaInicial(roles: string[]): string {
  if (roles.includes('superadmin')) return '/admin/empresas';
  if (roles.includes('cliente')) return '/tienda';
  if (roles.length > 0) return '/admin';
  return '/login';
}
