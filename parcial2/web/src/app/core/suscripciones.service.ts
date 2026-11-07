import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from './api';
import { Plan } from './planes.service';

export interface Consumo {
  recurso: string;
  actual: number;
  limite: number;
  disponible: number;
}

export interface EstadoSuscripcion {
  tiene_suscripcion: boolean;
  plan: Plan | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  estado: string | null;
  consumos: Consumo[];
  modulos_habilitados: string[];
}

export interface Suscripcion {
  id: number;
  plan: Plan;
  fecha_inicio: string;
  fecha_fin: string | null;
  estado: string;
}

@Injectable({ providedIn: 'root' })
export class SuscripcionesService {
  private http = inject(HttpClient);
  estado(): Observable<EstadoSuscripcion> {
    return this.http.get<EstadoSuscripcion>(`${API_URL}/suscripciones/estado`);
  }
  contratar(dto: { plan_codigo: string; duracion_dias?: number }) {
    return this.http.post<Suscripcion>(`${API_URL}/suscripciones/contratar`, dto);
  }
  cambiar(dto: { plan_codigo: string; duracion_dias?: number }) {
    return this.http.post<Suscripcion>(`${API_URL}/suscripciones/cambiar`, dto);
  }
  renovar(dto: { duracion_dias?: number }) {
    return this.http.post<Suscripcion>(`${API_URL}/suscripciones/renovar`, dto);
  }
}
