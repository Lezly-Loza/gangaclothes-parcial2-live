import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { provideServiceWorker } from '@angular/service-worker';
import { AppComponent, routes, jwtInterceptor } from './app/app.component';

bootstrapApplication(AppComponent, {
  providers: [provideHttpClient(withInterceptors([jwtInterceptor])), provideRouter(routes),
              provideServiceWorker('ngsw-worker.js', { enabled: true, registrationStrategy: 'registerWhenStable:30000' })]
});
