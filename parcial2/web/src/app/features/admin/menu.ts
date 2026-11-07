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
    titulo: 'P1. Plataforma y suscripciones',
    items: [
      { etiqueta: 'CU-01 Empresas (Tenants)', ruta: '/admin/empresas', roles: ADMIN, permiso: 'tenants:gestionar', disponible: true },
      { etiqueta: 'CU-05 Planes y precios', ruta: '/admin/planes', roles: ADMIN, permiso: 'planes:gestionar', disponible: true },
      { etiqueta: 'CU-06 Contratar plan', ruta: '/admin/contratar-plan', roles: ADMIN, permiso: 'suscripcion:gestionar', disponible: true },
      { etiqueta: 'CU-07 Mi suscripción', ruta: '/admin/mi-suscripcion', roles: ADMIN, permiso: 'suscripcion:gestionar', disponible: true },
    ],
  },
  {
    titulo: 'P2. Seguridad y administración',
    items: [
      { etiqueta: 'CU-02 / CU-03 Usuarios', ruta: '/admin/usuarios', roles: ADMIN, disponible: true },
      { etiqueta: 'CU-03 Roles y permisos', ruta: '/admin/roles', roles: ADMIN, disponible: true },
      { etiqueta: 'CU-04 Bitácora de auditoría', ruta: '/admin/bitacora', roles: ADMIN, disponible: true },
    ],
  },
  {
    titulo: 'P3. Catálogo, clientes e inventario',
    items: [
      { etiqueta: 'CU-08 Catálogos base', ruta: '/admin/categorias', roles: ADMIN, disponible: true },
      { etiqueta: 'CU-08 Prendas y variantes', ruta: '/admin/prendas', roles: ADMIN, disponible: true },
      { etiqueta: 'CU-09 Sucursales y tiendas', ruta: '/admin/sucursales', roles: ADMIN, disponible: true },
      { etiqueta: 'CU-10 Proveedores', ruta: '/admin/proveedores', roles: ['administrador', 'encargado'], disponible: true },
      { etiqueta: 'CU-11 Clientes', ruta: '/admin/clientes', roles: ['administrador', 'cajero'], disponible: true },
      { etiqueta: 'CU-12 Inventario por sucursal', ruta: '/admin/inventario', roles: ['administrador', 'encargado'], disponible: true },
    ],
  },
  {
    titulo: 'P4. Ventas y reservas en línea',
    items: [
      { etiqueta: 'CU-14 Reservas en línea', ruta: '/admin/reservas', roles: ['administrador', 'encargado'], disponible: true },
      { etiqueta: 'CU-15 Caja y ventas', ruta: '/admin/caja', roles: ['administrador', 'cajero'], disponible: true },
      { etiqueta: 'CU-16 Cambios de prendas', ruta: '/admin/cambios', roles: ['administrador', 'cajero'], disponible: true },
      { etiqueta: 'CU-17 Anular venta o reserva', ruta: '/admin/anular', roles: ['administrador', 'encargado'], disponible: true },
    ],
  },
  {
    titulo: 'P5. Operación offline y sincronización',
    items: [
      { etiqueta: 'CU-13 Movimientos y ajustes', ruta: '/admin/movimientos', roles: ['administrador', 'encargado'], disponible: true },
      { etiqueta: 'CU-18 Envíos a domicilio', ruta: '/admin/envios', roles: ['administrador', 'encargado', 'cajero'], permiso: 'envios:ver', disponible: true },
      { etiqueta: 'CU-19 / CU-20 Catálogo offline', ruta: '/modo-offline', roles: ['administrador', 'cajero'], disponible: true },
    ],
  },
  {
    titulo: 'P6. Reportes e Inteligencia Artificial',
    items: [
      { etiqueta: 'CU-24 Reportes (Excel / PDF)', ruta: '/admin/reportes', roles: ['administrador', 'encargado'], permiso: 'reportes:ver', disponible: true },
      { etiqueta: 'CU-25 Promociones y descuentos', ruta: '/admin/promociones', roles: ADMIN, permiso: 'promociones:ver', disponible: true },
      { etiqueta: 'CU-26 Dashboard & IA (ML)', ruta: '/admin/dashboard', roles: ['administrador', 'encargado'], permiso: 'reportes:ver', disponible: true },
    ],
  },
  {
    titulo: 'Portal del proveedor',
    items: [
      { etiqueta: 'Mi oferta de telas y prendas', ruta: '/proveedor', roles: ['proveedor'], permiso: 'oferta:ver', disponible: true },
    ],
  },
];

/** Deja solo los grupos e items que el rol (y, si el item lo pide, el permiso) del usuario puede ver. */
export function menuParaRoles(roles: string[], permisos: string[] = [], esSuper = false): GrupoMenu[] {
  return MENU.map((grupo) => ({
    ...grupo,
    items: grupo.items.filter(
      (item) => {
        if (esSuper) {
          return item.ruta === '/admin/empresas' || item.ruta === '/admin/planes';
        }
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
