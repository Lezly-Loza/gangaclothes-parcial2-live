import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({providedIn: 'root'})
export class SuscripcionesService {
  private http = inject(HttpClient);
  estado() { return this.http.get<any>(`${environment.apiUrl}/suscripciones/estado`); } contratar(dto: any) { return this.http.post<any>(`${environment.apiUrl}/suscripciones/contratar`, dto); } cambiar(dto: any) { return this.http.post<any>(`${environment.apiUrl}/suscripciones/cambiar`, dto); } renovar(dto: any) { return this.http.post<any>(`${environment.apiUrl}/suscripciones/renovar`, dto); }
}
