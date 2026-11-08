import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class PushService {
  readonly soportado = typeof window !== 'undefined' && 'Notification' in window;
  readonly habilitado = signal<boolean>(false);

  constructor() {
    if (this.soportado) {
      this.habilitado.set(Notification.permission === 'granted');
    }
  }

  async solicitarPermiso(): Promise<boolean> {
    if (!this.soportado) return false;
    try {
      const permiso = await Notification.requestPermission();
      const concedido = permiso === 'granted';
      this.habilitado.set(concedido);
      if (concedido) {
        this.notificar('Notificaciones Push activadas', {
          body: 'GangaClothes te avisará sobre tus pedidos, reservas y novedades en tiempo real.',
          icon: '/favicon.ico',
        });
      }
      return concedido;
    } catch {
      return false;
    }
  }

  notificar(titulo: string, opciones?: { body?: string; icon?: string; tag?: string }): void {
    if (!this.soportado || Notification.permission !== 'granted') {
      return;
    }

    try {
      new Notification(titulo, {
        body: opciones?.body ?? 'Actualización en tu cuenta de GangaClothes.',
        icon: opciones?.icon ?? '/favicon.ico',
        tag: opciones?.tag ?? 'gangaclothes-notif',
      });
    } catch (e) {
      console.warn('No se pudo enviar notificación push:', e);
    }
  }
}
