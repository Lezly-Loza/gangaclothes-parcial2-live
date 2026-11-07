/** Permiso de lectura requerido para abrir cada sección del panel. */
export const PERMISO_POR_RUTA: Record<string, string> = {
  '/admin/empresas': 'tenants:gestionar', '/admin/planes': 'planes:gestionar',
  '/admin/usuarios': 'usuarios:ver', '/admin/roles': 'roles:ver', '/admin/bitacora': 'bitacora:ver',
  '/admin/categorias': 'catalogos:ver', '/admin/tallas': 'catalogos:ver',
  '/admin/colores': 'catalogos:ver', '/admin/temporadas': 'catalogos:ver',
  '/admin/colecciones': 'catalogos:ver', '/admin/ciudades': 'sucursales:ver',
  '/admin/sucursales': 'sucursales:ver', '/admin/prendas': 'prendas:ver',
  '/admin/proveedores': 'proveedores:ver', '/admin/clientes': 'clientes:ver',
  '/admin/inventario': 'inventario:ver', '/admin/movimientos': 'inventario:ver',
  '/admin/compras': 'inventario:ver', '/admin/reservas': 'reservas:ver',
  '/admin/caja': 'ventas:crear', '/admin/cambios': 'cambios:crear',
  '/admin/anular': 'ventas:anular', '/admin/offline': 'prendas:ver',
  '/admin/mi-suscripcion': 'suscripcion:gestionar', '/admin/contratar-plan': 'suscripcion:gestionar',
  '/admin/dashboard': 'reportes:ver', '/admin/reportes': 'reportes:ver',
  '/admin/promociones': 'promociones:ver', '/admin/envios': 'envios:ver',
  '/admin/oferta-proveedores': 'inventario:crear', '/proveedor': 'oferta:ver',
};

export function tieneAccesoPanel(roles: string[], permisos: string[]): boolean {
  const personal = roles.some((r) => !['cliente', 'proveedor'].includes(r));
  return personal && (permisos.length > 0 || roles.includes('administrador'));
}
