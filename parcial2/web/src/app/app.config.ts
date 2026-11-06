import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { provideServiceWorker } from '@angular/service-worker';

import { routes } from './app.routes';
import { erroresInterceptor } from './core/errores.interceptor';
import { jwtInterceptor } from './core/jwt.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes, withComponentInputBinding()),
    // El orden importa: jwt agrega el token, errores traduce la respuesta.
    provideHttpClient(withInterceptors([jwtInterceptor, erroresInterceptor])),
    provideServiceWorker('ngsw-worker.js', {
      enabled: false, // En dev lo dejamos apagado para evitar cache de SW.
      registrationStrategy: 'registerWhenStable:30000',
    }),
  ],
};
