import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { SesionStore } from '../../core/sesion';
import { AuthService } from '../../services/auth.service';
import { menuParaRoles } from './menu';

@Component({
  selector: 'app-admin-shell',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './shell.html',
  styleUrl: './shell.css',
})
export class AdminShell {
  private auth = inject(AuthService);
  private router = inject(Router);
  readonly sesion = inject(SesionStore);

  readonly menu = computed(() => menuParaRoles(this.sesion.roles()));
  readonly subtitulo = computed(() =>
    this.sesion.esSuper() ? 'plataforma' : 'panel interno',
  );

  readonly enLinea = signal(navigator.onLine);

  constructor() {
    window.addEventListener('online',  () => this.enLinea.set(true));
    window.addEventListener('offline', () => this.enLinea.set(false));
  }

  salir(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
