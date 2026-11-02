import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Injectable({providedIn: 'root'})
export class AuthService {
  private http = inject(HttpClient);
  login(dto: any) { return this.http.post<any>(`${environment.apiUrl}/auth/login`, dto); } superLogin(dto: any) { return this.http.post<any>(`${environment.apiUrl}/auth/super/login`, dto); } logout() { localStorage.removeItem('token'); localStorage.removeItem('session'); }
}
