import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { Notificaciones } from './notificaciones';
import { SesionStore } from './sesion';
import { PERMISO_POR_RUTA, tieneAccesoPanel } from './permisos-rutas';

/** Ruta inicial segun el rol: el personal va al panel, el proveedor a su portal y el cliente al catalogo. */
export function rutaInicial(roles: string[], permisos: string[] = []): string {
  const esPersonal = ['administrador', 'encargado', 'cajero'].some((r) => roles.includes(r));
  if (esPersonal || tieneAccesoPanel(roles, permisos)) return '/admin';
  return roles.includes('proveedor') ? '/proveedor' : roles.includes('cliente') ? '/modo-offline' : '/catalogo';
}

/** Exige sesion iniciada. Recuerda a donde queria ir para volver despues del login. */
export const authGuard: CanActivateFn = (_ruta, estado) => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  if (sesion.autenticado()) return true;
  return router.createUrlTree(['/login'], { queryParams: { volverA: estado.url } });
};

/**
 * Exige alguno de los roles declarados en `data.roles` de la ruta.
 * Uso: { path: 'usuarios', canActivate: [authGuard, rolGuard], data: { roles: ['administrador'] } }
 */
export const rolGuard: CanActivateFn = (ruta) => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  const avisos = inject(Notificaciones);
  const requeridos = (ruta.data['roles'] ?? []) as string[];
  const nombreRuta = ruta.routeConfig?.path ?? '';
  const permiso = (ruta.data['permiso'] as string | undefined) || PERMISO_POR_RUTA[`/admin/${nombreRuta}`];

  if (sesion.esSuper()) return true;
  if (nombreRuta === 'admin' && tieneAccesoPanel(sesion.roles(), sesion.permisos())) return true;
  if (nombreRuta === 'anular' && (sesion.tienePermiso('ventas:anular') || sesion.tienePermiso('reservas:anular'))) return true;
  if (permiso) {
    if (sesion.tienePermiso(permiso)) return true;
    avisos.error(`Tu rol no tiene el permiso necesario para esta sección (${permiso}).`);
    return router.createUrlTree([rutaInicial(sesion.roles(), sesion.permisos())]);
  }

  if (requeridos.length === 0 || sesion.tieneAlgunRol(...requeridos)) return true;

  avisos.error(
    `Esta seccion es solo para: ${requeridos.join(', ')}. Tu rol es: ${sesion.roles().join(', ') || 'ninguno'}.`,
  );
  return router.createUrlTree([rutaInicial(sesion.roles(), sesion.permisos())]);
};

/**
 * Exige el permiso declarado en `data.permiso`. Se usa en las secciones que el
 * administrador puede dar o quitar desde la pantalla de roles (reportes): asi el
 * menu, la ruta y la API responden a lo mismo.
 */
export const permisoGuard: CanActivateFn = (ruta) => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  const avisos = inject(Notificaciones);
  if (sesion.esSuper()) return true;
  const permiso = ruta.data['permiso'] as string | undefined;

  if (!permiso || sesion.tienePermiso(permiso)) return true;

  avisos.error(`Tu rol no tiene el permiso necesario para esta seccion (${permiso}).`);
  return router.createUrlTree([rutaInicial(sesion.roles(), sesion.permisos())]);
};

/** Impide volver al login con la sesion ya iniciada. */
export const invitadoGuard: CanActivateFn = () => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  if (!sesion.autenticado()) return true;
  return router.createUrlTree([rutaInicial(sesion.roles(), sesion.permisos())]);
};
