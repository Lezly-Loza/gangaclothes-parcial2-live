import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({providedIn: 'root'})
export class CambiosService {
  private http = inject(HttpClient);
  obtenerVenta(codigo: string) { return this.http.get<any>(`${environment.apiUrl}/ventas/${codigo}`); } registrarCambio(dto: any) { return this.http.post<any>(`${environment.apiUrl}/cambios`, dto); }
}
