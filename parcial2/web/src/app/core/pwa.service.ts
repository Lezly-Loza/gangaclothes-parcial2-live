import { Injectable, inject, signal } from '@angular/core';
import { SwUpdate } from '@angular/service-worker';

interface EventoInstalacion extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{outcome: 'accepted' | 'dismissed'}>;
}

export class CacheRecursos {
  async guardarRecursos(): Promise<void> {
    if ('caches' in window) await caches.open('gangaclothes-recursos');
  }
}

@Injectable({providedIn: 'root'})
export class PwaService {
  private updates = inject(SwUpdate);
  private evento: EventoInstalacion | null = null;
  readonly instalable = signal(false);
  readonly instalada = signal(false);

  constructor() {
    if (typeof window === 'undefined') return;
    this.instalada.set(window.matchMedia('(display-mode: standalone)').matches);
    window.addEventListener('beforeinstallprompt', (event) => {
      event.preventDefault();
      this.evento = event as EventoInstalacion;
      this.instalable.set(true);
    });
    window.addEventListener('appinstalled', () => this.mostrarAppInstalada());
    this.registrarServiceWorker();
  }

  registrarServiceWorker(): void {
    if (!this.updates.isEnabled) return;
    this.updates.versionUpdates.subscribe(async (event) => {
      if (event.type === 'VERSION_READY') {
        await this.updates.activateUpdate();
        document.location.reload();
      }
    });
  }

  guardarRecursos(): Promise<void> { return new CacheRecursos().guardarRecursos(); }
  mostrarAppInstalada(): void { this.instalada.set(true); this.instalable.set(false); this.evento = null; }

  async instalarApp(): Promise<boolean> {
    if (!this.evento) return false;
    await this.evento.prompt();
    const resultado = await this.evento.userChoice;
    this.evento = null;
    this.instalable.set(false);
    if (resultado.outcome === 'accepted') this.mostrarAppInstalada();
    return resultado.outcome === 'accepted';
  }
}
