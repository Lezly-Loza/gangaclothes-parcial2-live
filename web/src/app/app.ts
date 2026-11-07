import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { Asistente } from './shared/asistente/asistente';
import { Avisos } from './shared/avisos/avisos';
import { BannerOffline } from './shared/offline/banner-offline';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Avisos, Asistente, BannerOffline],
  template: `
    <!-- CU-19 / CU-20: Banner superior de conectividad y modo offline -->
    <app-banner-offline />
    <router-outlet />
    <app-avisos />
    <!-- CU28: flota sobre cualquier pantalla; el propio componente decide si
         se muestra (hay sesion) y en que modo (cliente o personal). -->
    <app-asistente />
  `,
})
export class App {}
