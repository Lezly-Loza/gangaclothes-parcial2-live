import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({providedIn: 'root'})
export class TenantsService {
  private http = inject(HttpClient);
  crear(dto: any) { return this.http.post<any>(`${environment.apiUrl}/tenants`, dto); } listar() { return this.http.get<any[]>(`${environment.apiUrl}/tenants`); }
}
