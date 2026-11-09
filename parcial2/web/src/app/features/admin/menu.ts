import { Rol } from '../../core/modelos';
import { PERMISO_POR_RUTA } from '../../core/permisos-rutas';

export interface ItemMenu {
  etiqueta: string;
  ruta: string;
  roles: Rol[];
  /** Si se indica, el item solo aparece cuando la sesion tiene ese permiso. */
  permiso?: string;
  /** Los casos de uso de iteraciones posteriores se listan, pero aun sin pantalla. */
  disponible: boolean;
}

export interface GrupoMenu {
  titulo: string;
  items: ItemMenu[];
}

const ADMIN: Rol[] = ['administrador'];

export const MENU: GrupoMenu[] = [
  {
    titulo: 'General',
    items: [
      { etiqueta: 'Panel de Control', ruta: '/admin', roles: ['administrador', 'encargado', 'cajero'], disponible: true },
    ],
  },
  {
    titulo: 'Plataforma SaaS',
    items: [
      { etiqueta: 'Empresas (Tenants)', ruta: '/admin/empresas', roles: ADMIN, permiso: 'tenants:gestionar', disponible: true },
      { etiqueta: 'Planes y Precios', ruta: '/admin/planes', roles: ADMIN, permiso: 'planes:gestionar', disponible: true },
      { etiqueta: 'Contratar Plan', ruta: '/admin/contratar-plan', roles: ADMIN, permiso: 'suscripcion:gestionar', disponible: true },
      { etiqueta: 'Mi Suscripción', ruta: '/admin/mi-suscripcion', roles: ADMIN, permiso: 'suscripcion:gestionar', disponible: true },
    ],
  },
  {
    titulo: 'Seguridad',
    items: [
      { etiqueta: 'Usuarios', ruta: '/admin/usuarios', roles: ADMIN, disponible: true },
      { etiqueta: 'Roles y Permisos', ruta: '/admin/roles', roles: ADMIN, disponible: true },
      { etiqueta: 'Bitácora de Auditoría', ruta: '/admin/bitacora', roles: ADMIN, disponible: true },
      { etiqueta: 'Respaldos', ruta: '/admin/respaldos', roles: ADMIN, disponible: true },
    ],
  },
  {
    titulo: 'Catálogo e Inventario',
    items: [
      { etiqueta: 'Categorías y Atributos', ruta: '/admin/categorias', roles: ADMIN, disponible: true },
      { etiqueta: 'Prendas y Variantes', ruta: '/admin/prendas', roles: ADMIN, disponible: true },
      { etiqueta: 'Sucursales', ruta: '/admin/sucursales', roles: ADMIN, disponible: true },
      { etiqueta: 'Proveedores', ruta: '/admin/proveedores', roles: ['administrador', 'encargado'], disponible: true },
      { etiqueta: 'Clientes', ruta: '/admin/clientes', roles: ['administrador', 'cajero'], disponible: true },
      { etiqueta: 'Inventario por Sucursal', ruta: '/admin/inventario', roles: ['administrador', 'encargado'], disponible: true },
    ],
  },
  {
    titulo: 'Ventas y Atención',
    items: [
      { etiqueta: 'Reservas de Prendas', ruta: '/admin/reservas', roles: ['administrador', 'encargado'], disponible: true },
      { etiqueta: 'Caja y Cobros', ruta: '/admin/caja', roles: ['administrador', 'cajero'], disponible: true },
      { etiqueta: 'Cambios de Prenda', ruta: '/admin/cambios', roles: ['administrador', 'encargado', 'cajero'], disponible: true },
      { etiqueta: 'Anulación de Operaciones', ruta: '/admin/anular', roles: ['administrador', 'encargado'], disponible: true },
    ],
  },
  {
    titulo: 'Operación y Logística',
    items: [
      { etiqueta: 'Movimientos de Stock', ruta: '/admin/movimientos', roles: ['administrador', 'encargado'], disponible: true },
      { etiqueta: 'Envíos a Domicilio', ruta: '/admin/envios', roles: ['administrador', 'encargado', 'cajero'], permiso: 'envios:ver', disponible: true },
      { etiqueta: 'Catálogo sin Conexión', ruta: '/modo-offline', roles: ['administrador', 'cajero'], disponible: true },
    ],
  },
  {
    titulo: 'Analítica y Reportes',
    items: [
      { etiqueta: 'Reportes Oficiales', ruta: '/admin/reportes', roles: ['administrador', 'encargado'], permiso: 'reportes:ver', disponible: true },
      { etiqueta: 'Promociones', ruta: '/admin/promociones', roles: ADMIN, permiso: 'promociones:ver', disponible: true },
      { etiqueta: 'Indicadores y Métricas', ruta: '/admin/dashboard', roles: ['administrador', 'encargado'], permiso: 'reportes:ver', disponible: true },
    ],
  },
  {
    titulo: 'Portal del Proveedor',
    items: [
      { etiqueta: 'Mi Oferta de Confección', ruta: '/proveedor', roles: ['proveedor'], permiso: 'oferta:ver', disponible: true },
    ],
  },
];

/** Deja solo los grupos e items que el rol (y, si el item lo pide, el permiso) del usuario puede ver. */
export function menuParaRoles(roles: string[], permisos: string[] = [], esSuper = false): GrupoMenu[] {
  return MENU.map((grupo) => ({
    ...grupo,
    items: grupo.items.filter(
      (item) => {
        // El superadmin tiene visibilidad total del sistema
        if (esSuper) {
          if (item.ruta === '/admin/contratar-plan' || item.ruta === '/admin/mi-suscripcion') {
            return false;
          }
          return true;
        }
        // Las tiendas clientes no gestionan empresas ni planes globales
        if (item.ruta === '/admin/empresas' || item.ruta === '/admin/planes') {
          return false;
        }
        if (item.ruta === '/admin/anular') {
          return permisos.includes('ventas:anular') || permisos.includes('reservas:anular');
        }
        const permiso = item.permiso || PERMISO_POR_RUTA[item.ruta];
        return permiso ? permisos.includes(permiso) : item.roles.some((r) => roles.includes(r));
      },
    ),
  })).filter((grupo) => grupo.items.length > 0);
}
