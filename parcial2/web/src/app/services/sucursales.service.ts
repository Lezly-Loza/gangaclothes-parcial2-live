import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({providedIn: 'root'})
export class SucursalesService {
  private http = inject(HttpClient);
  listar() { return this.http.get<any[]>(`${environment.apiUrl}/sucursales`); } crear(dto: any) { return this.http.post<any>(`${environment.apiUrl}/sucursales`, dto); }
}
