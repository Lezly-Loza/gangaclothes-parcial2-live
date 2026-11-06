import { Routes } from '@angular/router';
import { authGuard, rolGuard, invitadoGuard } from './core/auth.guard';

const SUPER = { roles: ['superadmin'] };
const ADMIN = { roles: ['admin'] };
const ADMIN_O_ENCARGADO = { roles: ['admin', 'encargado'] };
const ADMIN_O_VENDEDOR = { roles: ['admin', 'vendedor'] };
const CUALQUIER_PERSONAL = { roles: ['admin', 'encargado', 'vendedor'] };
const SUPER_O_ADMIN = { roles: ['superadmin', 'admin', 'encargado', 'vendedor'] };
const SOLO_CLIENTE = { roles: ['cliente'] };

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [invitadoGuard],
    loadComponent: () => import('./features/auth/login/login').then(m => m.LoginPage),
  },
  {
    path: 'tienda',
    loadComponent: () => import('./features/tienda/tienda-shell').then(m => m.TiendaShell),
    children: [
      { path: '', loadComponent: () => import('./features/tienda/catalogo-cliente').then(m => m.CatalogoCliente) },
      { path: 'reservar', loadComponent: () => import('./features/tienda/reservar').then(m => m.ReservarPrendaPage) },
      { path: 'carrito', loadComponent: () => import('./features/tienda/carrito').then(m => m.CarritoPage) },
    ],
  },
  {
    path: 'admin',
    canActivate: [authGuard, rolGuard],
    data: SUPER_O_ADMIN,
    loadComponent: () => import('./features/admin/shell').then(m => m.AdminShell),
    children: [
      { path: '', loadComponent: () => import('./features/admin/inicio/inicio').then(m => m.AdminInicio) },
      { path: 'empresas',    canActivate: [rolGuard], data: SUPER,              loadComponent: () => import('./features/admin/empresas/empresas').then(m => m.RegistrarEmpresaForm) },
      { path: 'usuarios',    canActivate: [rolGuard], data: ADMIN,              loadComponent: () => import('./features/admin/usuarios/usuarios').then(m => m.UsuariosList) },
      { path: 'sucursales',  canActivate: [rolGuard], data: ADMIN,              loadComponent: () => import('./features/admin/sucursales/sucursales').then(m => m.SucursalesList) },
      { path: 'contratar',   canActivate: [rolGuard], data: ADMIN,              loadComponent: () => import('./features/admin/contratar/contratar').then(m => m.ContratarPlanForm) },
      { path: 'suscripcion', canActivate: [rolGuard], data: ADMIN,              loadComponent: () => import('./features/admin/suscripcion/suscripcion').then(m => m.MiSuscripcion) },
      { path: 'catalogos',   canActivate: [rolGuard], data: ADMIN,              loadComponent: () => import('./features/admin/catalogos/catalogos').then(m => m.CatalogosPage) },
      { path: 'catalogos/:tipo', canActivate: [rolGuard], data: ADMIN,          loadComponent: () => import('./features/admin/catalogos/catalogos').then(m => m.CatalogosPage) },
      { path: 'productos',   canActivate: [rolGuard], data: ADMIN,              loadComponent: () => import('./features/admin/productos/productos').then(m => m.ProductosList) },
      { path: 'proveedores', canActivate: [rolGuard], data: ADMIN,              loadComponent: () => import('./features/admin/proveedores/proveedores').then(m => m.ProveedoresList) },
      { path: 'clientes',    canActivate: [rolGuard], data: ADMIN_O_VENDEDOR,   loadComponent: () => import('./features/admin/clientes/clientes').then(m => m.ClientesList) },
      { path: 'inventario',  canActivate: [rolGuard], data: ADMIN_O_ENCARGADO,  loadComponent: () => import('./features/admin/inventario/inventario').then(m => m.InventarioPage) },
      { path: 'caja',        canActivate: [rolGuard], data: ADMIN_O_VENDEDOR,   loadComponent: () => import('./features/admin/caja/caja').then(m => m.PuntoVentaPage) },
      { path: 'cambios',     canActivate: [rolGuard], data: ADMIN_O_VENDEDOR,   loadComponent: () => import('./features/admin/cambios/cambios').then(m => m.CambioPrendaPage) },
      { path: 'anular',      canActivate: [rolGuard], data: { roles: ['admin', 'encargado'] }, loadComponent: () => import('./features/admin/anular/anular').then(m => m.AnularOperacionDialog) },
      { path: 'offline',     canActivate: [rolGuard], data: { roles: ['admin', 'encargado', 'vendedor'] }, loadComponent: () => import('./features/admin/offline/offline').then(m => m.ModoOfflinePage) },
      { path: 'instalar',    loadComponent: () => import('./features/admin/instalar/instalar').then(m => m.AvisoInstalacionComponent) },
    ],
  },
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];
