import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { SesionStore } from './sesion';
import { Notificaciones } from './notificaciones';
import { API_URL } from './api';

export function mensajeDeError(error: unknown, porDefecto: string): string {
  if (!(error instanceof HttpErrorResponse)) return porDefecto;
  const detalle = (error.error as any)?.detail;
  if (typeof detalle === 'string') return detalle;
  if (Array.isArray(detalle))
    return detalle.map((d: any) => `${d.loc?.at(-1) ?? ''}: ${d.msg}`).join(' · ') || porDefecto;
  return porDefecto;
}

export const erroresInterceptor: HttpInterceptorFn = (req, next) => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  const avisos = inject(Notificaciones);
  const esAuth = req.url.startsWith(`${API_URL}/auth/`);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 0) {
        avisos.error(`No se pudo contactar al servidor. Verifica que la API este corriendo en ${API_URL}`);
      } else if (error.status === 401 && !esAuth) {
        sesion.limpiar();
        avisos.error('Tu sesion expiro. Inicia sesion de nuevo.');
        router.navigate(['/login'], { queryParams: { volverA: router.url } });
      } else if (error.status === 403) {
        avisos.error(mensajeDeError(error, 'No tienes permisos para esta operacion.'));
      } else if (error.status === 409) {
        avisos.error(mensajeDeError(error, 'No se puede completar la operacion.'));
      } else if (error.status >= 500) {
        avisos.error('Error interno del servidor. Intenta de nuevo en un momento.');
      }
      return throwError(() => error);
    }),
  );
};
