export type Rol = 'administrador' | 'encargado' | 'cajero' | 'cliente' | 'proveedor';

export interface Usuario {
  id: number;
  nombre: string;
  apellido: string | null;
  email: string;
  /** Los roles son administrables, asi que no se limitan a los del sistema. */
  roles: string[];
  /** Permisos que le llegan por sus roles, en formato "modulo:accion". */
  permisos: string[];
  /** Sucursal asignada al personal. */
  sucursal_id?: number | null;
  /** Parcial 2: codigo del tenant al que pertenece el usuario (null para superadmin). */
  tenant_codigo?: string | null;
  /** Parcial 2: id del tenant al que pertenece el usuario (null para superadmin). */
  tenant_id?: number | null;
  /** Parcial 2: tipo de sesion ('tenant' o 'super'). */
  kind?: 'tenant' | 'super';
}

export interface SesionRespuesta {
  access_token: string;
  token_type: string;
  usuario: Usuario;
}

/**
 * Parcial 2 — roles del backend usan vocabulario corto ('admin', 'vendedor').
 * Las vistas y guards del parcial 1 usan 'administrador', 'cajero', etc.
 * Esta funcion traduce para mantener compatibilidad.
 */
export function traducirRoles(rolesBackend: string[]): string[] {
  const mapa: Record<string, string> = {
    admin: 'administrador',
    vendedor: 'cajero',
    superadmin: 'administrador',
    encargado: 'encargado',
    cliente: 'cliente',
    proveedor: 'proveedor',
  };
  return Array.from(new Set(rolesBackend.map((r) => mapa[r] ?? r)));
}

/**
 * Deriva permisos "modulo:accion" a partir de los roles del parcial 2.
 * Admin / superadmin reciben todo; encargado y vendedor un subconjunto.
 */
export function permisosPorRoles(rolesBackend: string[]): string[] {
  const esSuper = rolesBackend.includes('superadmin');
  const esAdmin = rolesBackend.includes('admin');
  const esEncargado = rolesBackend.includes('encargado');
  const esVendedor = rolesBackend.includes('vendedor');
  const base: string[] = [];
  const TODOS = [
    'reportes:ver',
    'inventario:ver', 'inventario:crear', 'inventario:editar',
    'envios:ver', 'envios:crear',
    'promociones:ver', 'promociones:crear',
    'oferta:ver',
    'ventas:crear', 'ventas:anular',
    'reservas:crear', 'reservas:anular',
    'cambios:crear',
    'suscripcion:gestionar',
  ];
  if (esSuper) return ['tenants:gestionar', 'planes:gestionar'];
  if (esAdmin) return TODOS;
  if (esEncargado) base.push('reportes:ver', 'inventario:ver', 'inventario:editar', 'envios:ver', 'reservas:crear', 'reservas:anular');
  if (esVendedor) base.push('ventas:crear', 'cambios:crear', 'envios:ver');
  return base;
}
