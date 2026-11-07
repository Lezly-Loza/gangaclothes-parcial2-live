import { Injectable, signal } from '@angular/core';

export type TipoAviso = 'error' | 'ok';

export interface Aviso {
  id: number;
  tipo: TipoAviso;
  texto: string;
}

@Injectable({ providedIn: 'root' })
export class Notificaciones {
  private siguienteId = 1;
  private readonly recientes = new Map<string, number>();
  readonly avisos = signal<Aviso[]>([]);

  error(texto: string): void {
    this.mostrar('error', texto);
  }

  ok(texto: string): void {
    this.mostrar('ok', texto);
  }

  cerrar(id: number): void {
    this.avisos.update((lista) => lista.filter((a) => a.id !== id));
  }

  private mostrar(tipo: TipoAviso, texto: string): void {
    // Dedupe: si el mismo mensaje se repitio hace menos de 3s, se ignora
    // para que un panel que dispara 7 endpoints en paralelo no muestre 7 toasts iguales.
    const clave = `${tipo}:${texto}`;
    const ahora = Date.now();
    const anterior = this.recientes.get(clave);
    if (anterior && ahora - anterior < 3000) return;
    this.recientes.set(clave, ahora);

    const aviso: Aviso = { id: this.siguienteId++, tipo, texto };
    this.avisos.update((lista) => [...lista, aviso]);
    setTimeout(() => this.cerrar(aviso.id), 5000);
  }
}
