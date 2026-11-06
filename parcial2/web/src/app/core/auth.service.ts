import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, map, tap } from 'rxjs';

import { API_URL } from './api';
import { rutaInicial } from './auth.guard';
import { SesionRespuesta, Usuario, permisosPorRoles, traducirRoles } from './modelos';
import { SesionStore } from './sesion';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  readonly sesion = inject(SesionStore);

  /**
   * Login del parcial 2.
   * - Con `codigo_tenant` → `/auth/login` (usuario de empresa).
   * - Sin `codigo_tenant` → `/auth/super/login` (superadministrador de plataforma).
   */
  login(email: string, password: string, codigo_tenant?: string): Observable<SesionRespuesta> {
    const url = codigo_tenant ? `${API_URL}/auth/login` : `${API_URL}/auth/super/login`;
    const payload = codigo_tenant
      ? { codigo_tenant, email, password }
      : { email, password };
    return this.http.post<any>(url, payload).pipe(
      map((r) => this.mapearRespuesta(r, email, codigo_tenant)),
      tap((respuesta) => this.sesion.guardar(respuesta)),
    );
  }

  /** Atajo sin `codigo_tenant` para el superadministrador. */
  superLogin(email: string, password: string): Observable<SesionRespuesta> {
    return this.login(email, password);
  }

  registrar(datos: { nombre: string; apellido?: string; email: string; password: string; telefono?: string }) {
    return this.http
      .post<any>(`${API_URL}/auth/register`, datos)
      .pipe(
        map((r) => this.mapearRespuesta(r, datos.email)),
        tap((respuesta) => this.sesion.guardar(respuesta)),
      );
  }

  recuperar(email: string): Observable<{ detail: string; minutos: number; reenvio_en: number }> {
    return this.http.post<{ detail: string; minutos: number; reenvio_en: number }>(
      `${API_URL}/auth/recuperar`,
      { email },
    );
  }

  restablecer(datos: { email: string; codigo: string; password: string }): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(`${API_URL}/auth/restablecer`, datos);
  }

  yo(): Observable<Usuario> {
    return this.http.get<any>(`${API_URL}/auth/me`).pipe(map((me) => this.meAUsuario(me)));
  }

  salir(): void {
    this.sesion.limpiar();
    this.router.navigate(['/login']);
  }

  logout(): void { this.salir(); }

  rutaInicial(): string {
    // Parcial 2: el superadministrador aterriza directo en la pantalla de empresas.
    if (this.sesion.usuario()?.kind === 'super') return '/admin/empresas';
    return rutaInicial(this.sesion.roles());
  }

  /**
   * Mapea la respuesta del backend parcial 2 (`TokenOut`) al modelo del
   * parcial 1 (`SesionRespuesta`), traduciendo roles y derivando permisos.
   */
  private mapearRespuesta(r: any, email: string, codigoTenantFallback?: string): SesionRespuesta {
    const nombreCompleto = String(r.nombre || '').trim();
    const partes = nombreCompleto.split(/\s+/);
    const nombre = partes[0] || nombreCompleto;
    const apellido = partes.length > 1 ? partes.slice(1).join(' ') : null;
    const rolesBackend = (r.roles || []) as string[];
    const usuario: Usuario = {
      id: r.user_id ?? 0,
      nombre: nombre,
      apellido,
      email,
      roles: traducirRoles(rolesBackend),
      permisos: permisosPorRoles(rolesBackend),
      sucursal_id: null,
      tenant_codigo: r.tenant_codigo ?? codigoTenantFallback ?? null,
      tenant_id: r.tenant_id ?? null,
      kind: r.kind ?? (codigoTenantFallback ? 'tenant' : 'super'),
    };
    return { access_token: r.access_token, token_type: r.token_type || 'bearer', usuario };
  }

  private meAUsuario(me: any): Usuario {
    const partes = String(me.nombre || '').trim().split(/\s+/);
    const rolesBackend = (me.roles || []) as string[];
    return {
      id: me.user_id ?? 0,
      nombre: partes[0] || '',
      apellido: partes.length > 1 ? partes.slice(1).join(' ') : null,
      email: me.email || '',
      roles: traducirRoles(rolesBackend),
      permisos: permisosPorRoles(rolesBackend),
      sucursal_id: null,
      tenant_codigo: me.tenant_codigo ?? null,
      tenant_id: me.tenant_id ?? null,
      kind: me.kind,
    };
  }
}
