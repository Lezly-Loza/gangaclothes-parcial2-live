import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({providedIn: 'root'})
export class ClientesService {
  private http = inject(HttpClient);
  buscar(q: string) { return this.http.get<any[]>(`${environment.apiUrl}/clientes`, {params:{q}}); } crear(dto: any) { return this.http.post<any>(`${environment.apiUrl}/clientes`, dto); }
}
