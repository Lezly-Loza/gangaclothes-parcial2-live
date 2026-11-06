import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { menuParaRoles } from './menu';

@Component({
  selector: 'app-admin-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.html',
  styleUrl: './shell.css',
})
export class AdminShell {
  private auth = inject(AuthService);
  readonly sesion = this.auth.sesion;
  readonly menu = computed(() => menuParaRoles(this.sesion.roles(), this.sesion.permisos()));
  /** El proveedor usa el mismo marco, pero no es personal de la tienda. */
  readonly subtitulo = computed(() => {
    if (this.sesion.esSuper()) return 'plataforma';
    if (this.sesion.rolPrincipal() === 'proveedor') return 'portal de proveedores';
    return 'panel interno';
  });
  readonly tenantCodigo = this.sesion.tenantCodigo;
  readonly esSuper = this.sesion.esSuper;
  readonly enLinea = signal(typeof navigator !== 'undefined' ? navigator.onLine : true);

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online',  () => this.enLinea.set(true));
      window.addEventListener('offline', () => this.enLinea.set(false));
    }
  }

  salir(): void {
    this.auth.salir();
  }
}
