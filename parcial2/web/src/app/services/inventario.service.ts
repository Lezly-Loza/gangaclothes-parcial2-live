import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({providedIn: 'root'})
export class InventarioService {
  private http = inject(HttpClient);
  consultarStock(sucursal_id: number) { return this.http.get<any[]>(`${environment.apiUrl}/inventario`, {params:{sucursal_id}}); } registrarMovimiento(dto: any) { return this.http.post<any>(`${environment.apiUrl}/inventario/movimientos`, dto); }
}
