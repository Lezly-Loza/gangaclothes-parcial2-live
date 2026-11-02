import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({providedIn: 'root'})
export class UsuariosService {
  private http = inject(HttpClient);
  listar() { return this.http.get<any[]>(`${environment.apiUrl}/usuarios`); } crear(dto: any) { return this.http.post<any>(`${environment.apiUrl}/usuarios`, dto); }
}
