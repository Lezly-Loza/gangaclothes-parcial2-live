import { Component, inject } from '@angular/core';
import { OfflineService } from '../../core/offline.service';

/**
 * CU-19 y CU-20: Banner superior que notifica modo sin conexión
 * y muestra el contador de operaciones pendientes de sincronización.
 */
@Component({
  selector: 'app-banner-offline',
  template: `
    @if (offline.bannerOffline(); as mensaje) {
      <div class="w-full bg-amber-500 text-slate-900 px-4 py-2.5 text-xs font-semibold flex items-center justify-between border-b border-amber-600 shadow-sm animate-in slide-in-from-top">
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-amber-200 animate-ping"></span>
          <span>📡 {{ mensaje }}</span>
        </div>
        @if (offline.operacionesPendientes() > 0) {
          <span class="bg-slate-900 text-amber-300 px-2 py-0.5 rounded-full font-mono text-3xs font-black uppercase tracking-wider">
            {{ offline.operacionesPendientes() }} pendiente(s) de sincronizar
          </span>
        }
      </div>
    }
  `,
})
export class BannerOffline {
  readonly offline = inject(OfflineService);
}

