import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({providedIn: 'root'})
export class VentasService {
  private http = inject(HttpClient);
  registrarVenta(dto: any) { return this.http.post<any>(`${environment.apiUrl}/ventas`, dto); } anular(id: number, motivo: string) { return this.http.post<any>(`${environment.apiUrl}/ventas/${id}/anular`, {motivo}); }
}
