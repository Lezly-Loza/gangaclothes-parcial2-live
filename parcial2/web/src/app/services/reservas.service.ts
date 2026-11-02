import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({providedIn: 'root'})
export class ReservasService {
  private http = inject(HttpClient);
  crearReserva(dto: any) { return this.http.post<any>(`${environment.apiUrl}/reservas`, dto); }
}
