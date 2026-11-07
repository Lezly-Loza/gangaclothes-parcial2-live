import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from './api';

export interface Plan {
  id: number;
  codigo: string;
  nombre: string;
  descripcion?: string | null;
  max_sucursales: number;
  max_usuarios: number;
  max_productos: number;
  modulos: string[];
  precio_mensual: number;
  activo: boolean;
}

export interface PlanCreateIn {
  codigo: string;
  nombre: string;
  descripcion?: string | null;
  max_sucursales: number;
  max_usuarios: number;
  max_productos: number;
  modulos: string[];
  precio_mensual: number;
}

@Injectable({ providedIn: 'root' })
export class PlanesService {
  private http = inject(HttpClient);
  listar(): Observable<Plan[]> { return this.http.get<Plan[]>(`${API_URL}/planes`); }
  crear(datos: PlanCreateIn) { return this.http.post<Plan>(`${API_URL}/planes`, datos); }
  actualizar(id: number, parciales: Partial<Plan>) { return this.http.patch<Plan>(`${API_URL}/planes/${id}`, parciales); }
  desactivar(id: number) { return this.http.post<Plan>(`${API_URL}/planes/${id}/desactivar`, {}); }
}
