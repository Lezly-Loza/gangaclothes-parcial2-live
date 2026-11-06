import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PwaService } from '../../../services/pwa.service';
import { Notificaciones } from '../../../core/notificaciones';

@Component({
  selector: 'app-instalar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="cabecera">
      <div><div class="ceja">CU-13 Instalacion PWA</div><h1>Instalar GangaClothes</h1></div>
    </div>

    <section class="tarjeta">
      <div class="logo" style="font-size:36px;">Ganga<b>Clothes</b></div>
      <p class="sub">Instala la aplicacion en tu dispositivo para usarla sin abrir el navegador y aprovechar el modo offline.</p>
      <button class="btn rosa bloque" (click)="instalarApp()">Instalar GangaClothes</button>
      @if (mensaje()) { <p class="mensaje">{{ mensaje() }}</p> }
    </section>
  `,
  styles: [`
    .cabecera{margin-bottom:14px;} h1{font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-top:2px;}
    .tarjeta{background:#fff;border:1.5px solid var(--linea);border-radius:13px;padding:30px;max-width:520px;text-align:center;}
    .sub{color:var(--gris);font-size:13px;margin:12px 0 18px;}
  `],
})
export class AvisoInstalacionComponent {
  private pwa = inject(PwaService);
  private avisos = inject(Notificaciones);
  evento: any = null;
  readonly mensaje = signal('');

  constructor() {
    window.addEventListener('beforeinstallprompt', (e: any) => { e.preventDefault(); this.evento = e; });
    this.abrirAplicacion();
  }

  abrirAplicacion() {
    this.pwa.registrarServiceWorker();
    this.pwa.guardarRecursos();
  }

  async instalarApp() {
    if (this.evento) {
      await this.evento.prompt();
      const decision = await this.evento.userChoice;
      if (decision.outcome === 'accepted') {
        this.mensaje.set('Instalacion aceptada');
        this.avisos.ok('App instalada');
        this.mostrarAppInstalada();
      } else {
        this.mensaje.set('Instalacion cancelada');
      }
    } else {
      this.mensaje.set('Usa el menu del navegador para instalar la PWA (Chrome → "Instalar GangaClothes")');
    }
  }

  mostrarAppInstalada() {
    const instalada = this.pwa.mostrarAppInstalada();
    this.mensaje.set(instalada ? 'Aplicacion instalada' : 'Instalacion aceptada');
    return instalada;
  }
}
