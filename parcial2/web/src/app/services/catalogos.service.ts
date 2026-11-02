import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({providedIn: 'root'})
export class CatalogosService {
  private http = inject(HttpClient);
  listar(tipo: string) { return this.http.get<any[]>(`${environment.apiUrl}/catalogos/${tipo}`); } guardar(tipo: string, dto: any) { return this.http.post<any>(`${environment.apiUrl}/catalogos/${tipo}`, dto); }
}
