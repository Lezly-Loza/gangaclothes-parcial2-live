export interface ItemMenu { etiqueta: string; ruta: string; roles: string[]; }
export interface GrupoMenu { titulo: string; items: ItemMenu[]; }

const SUPER = ['superadmin'];
const ADMIN = ['admin'];
const ADMIN_O_ENCARGADO = ['admin', 'encargado'];
const ADMIN_O_VENDEDOR = ['admin', 'vendedor'];
const OPERACION = ['admin', 'encargado', 'vendedor'];

export const MENU: GrupoMenu[] = [
  {
    titulo: 'Plataforma',
    items: [
      { etiqueta: 'Empresas',              ruta: '/admin/empresas',    roles: SUPER },
    ],
  },
  {
    titulo: 'General',
    items: [
      { etiqueta: 'Panel',                 ruta: '/admin',             roles: OPERACION },
    ],
  },
  {
    titulo: 'Suscripcion',
    items: [
      { etiqueta: 'Contratar plan',        ruta: '/admin/contratar',   roles: ADMIN },
      { etiqueta: 'Mi suscripcion',        ruta: '/admin/suscripcion', roles: ADMIN },
    ],
  },
  {
    titulo: 'Seguridad',
    items: [
      { etiqueta: 'Usuarios y roles',      ruta: '/admin/usuarios',    roles: ADMIN },
    ],
  },
  {
    titulo: 'Red de tiendas',
    items: [
      { etiqueta: 'Sucursales',            ruta: '/admin/sucursales',  roles: ADMIN },
    ],
  },
  {
    titulo: 'Catalogos base',
    items: [
      { etiqueta: 'Categorias',            ruta: '/admin/catalogos/categorias', roles: ADMIN },
      { etiqueta: 'Tallas',                ruta: '/admin/catalogos/tallas',     roles: ADMIN },
      { etiqueta: 'Colores',               ruta: '/admin/catalogos/colores',    roles: ADMIN },
      { etiqueta: 'Temporadas',            ruta: '/admin/catalogos/temporadas', roles: ADMIN },
    ],
  },
  {
    titulo: 'Productos',
    items: [
      { etiqueta: 'Prendas y variantes',   ruta: '/admin/productos',   roles: ADMIN },
      { etiqueta: 'Proveedores',           ruta: '/admin/proveedores', roles: ADMIN },
    ],
  },
  {
    titulo: 'Operacion',
    items: [
      { etiqueta: 'Inventario',            ruta: '/admin/inventario',  roles: ADMIN_O_ENCARGADO },
      { etiqueta: 'Caja',                  ruta: '/admin/caja',        roles: ADMIN_O_VENDEDOR },
      { etiqueta: 'Cambios de prendas',    ruta: '/admin/cambios',     roles: ADMIN_O_VENDEDOR },
      { etiqueta: 'Anular operacion',      ruta: '/admin/anular',      roles: ['admin', 'encargado'] },
      { etiqueta: 'Clientes',              ruta: '/admin/clientes',    roles: ADMIN_O_VENDEDOR },
      { etiqueta: 'Modo offline',          ruta: '/admin/offline',     roles: OPERACION },
    ],
  },
];

export function menuParaRoles(roles: string[]): GrupoMenu[] {
  return MENU.map((g) => ({
    ...g,
    items: g.items.filter((i) => i.roles.some((r) => roles.includes(r))),
  })).filter((g) => g.items.length > 0);
}
