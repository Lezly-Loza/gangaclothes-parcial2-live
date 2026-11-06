import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { SesionStore, rutaInicial } from './sesion';
import { Notificaciones } from './notificaciones';

export const authGuard: CanActivateFn = (_route, state) => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  if (sesion.autenticado()) return true;
  router.navigate(['/login'], { queryParams: { volverA: state.url } });
  return false;
};

export const rolGuard: CanActivateFn = (route) => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  const avisos = inject(Notificaciones);
  const roles = (route.data?.['roles'] as string[] | undefined) ?? [];
  if (roles.length === 0) return true;
  if (sesion.tieneAlgunRol(...roles)) return true;
  avisos.error('No tienes permisos para acceder a esa seccion.');
  router.navigateByUrl(rutaInicial(sesion.roles()));
  return false;
};

export const invitadoGuard: CanActivateFn = () => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  if (!sesion.autenticado()) return true;
  router.navigateByUrl(rutaInicial(sesion.roles()));
  return false;
};
