import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { Asistente } from './shared/asistente/asistente';
import { Avisos } from './shared/avisos/avisos';
import { PwaService } from './core/pwa.service';
import { OfflineService } from './services/offline.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Avisos, Asistente],
  template: `
    <router-outlet />
    <app-avisos />
    <!-- CU28: flota sobre cualquier pantalla; el propio componente decide si
         se muestra (hay sesion) y en que modo (cliente o personal). -->
    <app-asistente />
  `,
})
export class App { readonly pwa = inject(PwaService); private readonly offline = inject(OfflineService); }
