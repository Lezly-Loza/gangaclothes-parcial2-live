import { Injectable, inject } from '@angular/core';
import { SwUpdate, VersionReadyEvent } from '@angular/service-worker';
import { filter } from 'rxjs';

export class CacheRecursos {
  guardarRecursos(): Promise<void> { return caches.open('gangaclothes-recursos').then(() => undefined); }
}

@Injectable({providedIn: 'root'})
export class PwaService {
  private updates = inject(SwUpdate);
  private cache = new CacheRecursos();
  registrarServiceWorker() {
    if (this.updates.isEnabled) this.updates.versionUpdates.pipe(filter((e): e is VersionReadyEvent => e.type === 'VERSION_READY'))
      .subscribe(async () => { await this.updates.activateUpdate(); location.reload(); });
  }
  guardarRecursos() { return this.cache.guardarRecursos(); }
  mostrarAppInstalada() { return window.matchMedia('(display-mode: standalone)').matches; }
}
