import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { SesionStore } from '../../core/sesion';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-tienda-shell',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, RouterOutlet],
  template: `
    <header class="tienda-head">
      <a routerLink="/tienda" class="logo">Ganga<b>Clothes</b></a>
      <nav>
        <a routerLink="/tienda" routerLinkActive="on" [routerLinkActiveOptions]="{exact:true}">Catalogo</a>
        <a routerLink="/tienda/reservar" routerLinkActive="on">Reservar</a>
        <a routerLink="/tienda/carrito" routerLinkActive="on">Carrito</a>
      </nav>
      <div class="acciones">
        @if (sesion.autenticado()) {
          <span class="yo mono">{{ sesion.nombre() }}</span>
          <button class="btn linea pequeno" (click)="salir()">Salir</button>
        } @else {
          <a routerLink="/login" class="btn linea pequeno">Iniciar sesion</a>
        }
      </div>
    </header>
    <main><router-outlet /></main>
  `,
  styles: [`
    .tienda-head{display:flex;gap:18px;align-items:center;padding:16px 26px;background:#fff;border-bottom:1.5px solid var(--linea);}
    .logo{font-size:18px;}
    nav{display:flex;gap:16px;margin-left:12px;}
    nav a{padding:8px 4px;font-size:13px;color:var(--gris);border-bottom:2px solid transparent;}
    nav a.on{color:var(--tinta);font-weight:700;border-bottom-color:var(--ganga);}
    .acciones{margin-left:auto;display:flex;gap:10px;align-items:center;}
    .yo{color:var(--tinta);}
    .btn.pequeno{padding:6px 12px;font-size:11.5px;}
    main{padding:22px 26px 40px;}
  `],
})
export class TiendaShell {
  private auth = inject(AuthService);
  private router = inject(Router);
  readonly sesion = inject(SesionStore);
  salir() { this.auth.logout(); this.router.navigate(['/login']); }
}
