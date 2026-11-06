/**
 * Atajos de login del parcial 2 (usuarios de `backend/app/seeds/demo.py`).
 * `codigo_tenant` vacio = superadministrador.
 * En produccion este archivo se reemplaza por `cuentas-demo.prod.ts`.
 */
export interface CuentaDemo {
  rol: string;
  codigo_tenant: string;
  email: string;
  password: string;
}

export const CUENTAS_DEMO: CuentaDemo[] = [
  { rol: 'Super',       codigo_tenant: '',       email: 'root@plataforma.bo',       password: 'SuperSegura123' },
  { rol: 'Admin Luna',  codigo_tenant: 'luna',   email: 'ana@boutique-luna.bo',     password: 'Luna12345' },
  { rol: 'Encargado',   codigo_tenant: 'luna',   email: 'encargado@boutique-luna.bo', password: 'Luna12345' },
  { rol: 'Admin Andina',codigo_tenant: 'andina', email: 'rodrigo@modaandina.bo',   password: 'Andina12345' },
];
