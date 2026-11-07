/**
 * Atajos de login para todos los roles oficiales de GangaClothes.
 * `codigo_tenant` vacio = superadministrador.
 */
export interface CuentaDemo {
  rol: string;
  codigo_tenant: string;
  email: string;
  password: string;
}

export const CUENTAS_DEMO: CuentaDemo[] = [
  { rol: 'Admin',       codigo_tenant: 'luna', email: 'admin@gangaclothes.com',      password: 'Admin123' },
  { rol: 'Encargado',   codigo_tenant: 'luna', email: 'encargado@gangaclothes.com',  password: 'Encargado123' },
  { rol: 'Cajero',      codigo_tenant: 'luna', email: 'cajero@gangaclothes.com',     password: 'Cajero123' },
  { rol: 'Sofia (Cliente)', codigo_tenant: 'luna', email: 'sofia@gangaclothes.com',  password: 'Cliente#2026' },
  { rol: 'Diego (Cliente)', codigo_tenant: 'luna', email: 'diego@gangaclothes.com',  password: 'Cliente#2026' },
  { rol: 'Valeria (Cliente)', codigo_tenant: 'luna', email: 'valeria@gangaclothes.com', password: 'Cliente#2026' },
  { rol: 'Textiles Andinos', codigo_tenant: 'luna', email: 'proveedor@gangaclothes.com', password: 'Proveedor123' },
  { rol: 'Conf. Oriente', codigo_tenant: 'luna', email: 'oriente@gangaclothes.com',    password: 'Proveedor123' },
  { rol: 'Superadmin',  codigo_tenant: '',     email: 'root@plataforma.bo',          password: 'SuperSegura123' },
];
