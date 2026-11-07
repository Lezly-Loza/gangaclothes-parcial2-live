import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from './api';

export interface Tenant {
  id: number;
  razon_social: string;
  nit: string;
  correo: string;
  telefono?: string | null;
  codigo: string;
  estado: string;
  activo: boolean;
  plan_actual?: string | null;
  fecha_fin_suscripcion?: string | null;
}

export interface AdminInicialIn {
  nombre: string;
  email: string;
  password: string;
}

export interface TenantCreateIn {
  razon_social: string;
  nit: string;
  correo: string;
  telefono?: string | null;
  codigo: string;
  admin: AdminInicialIn;
  plan_codigo?: string | null;
}

@Injectable({ providedIn: 'root' })
export class TenantsService {
  private http = inject(HttpClient);
  listar(): Observable<Tenant[]> { return this.http.get<Tenant[]>(`${API_URL}/tenants`); }
  obtener(id: number): Observable<Tenant> { return this.http.get<Tenant>(`${API_URL}/tenants/${id}`); }
  crear(datos: TenantCreateIn): Observable<Tenant> { return this.http.post<Tenant>(`${API_URL}/tenants`, datos); }
  actualizar(id: number, parciales: Partial<Tenant>) { return this.http.patch<Tenant>(`${API_URL}/tenants/${id}`, parciales); }
}
