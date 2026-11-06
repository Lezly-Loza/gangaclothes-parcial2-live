import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Avisos } from './shared/avisos/avisos';
import { PwaService } from './services/pwa.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, Avisos],
  template: `
    <router-outlet />
    <app-avisos />
  `,
})
export class App {
  private pwa = inject(PwaService);
  constructor() {
    this.pwa.registrarServiceWorker();
  }
}
