import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { API_URL } from '../../../core/api';

@Component({selector: 'app-respaldos', template: `
  <h1>Respaldos de la empresa</h1>
  <p>Descarga una copia de los datos guardados en el servidor para esta empresa.</p>
  <section class="tarjeta">
    <h2>Descargar respaldo</h2>
    <p>El archivo contiene datos privados de clientes y usuarios. Guárdalo en un lugar seguro.</p>
    <p>Las operaciones pendientes guardadas solo en un dispositivo no están incluidas. Sincronízalas primero.</p>
    <button class="btn rosa" [disabled]="ocupado()" (click)="descargar()">Descargar respaldo</button>
  </section>
  <section class="tarjeta">
    <h2>Verificar copia</h2>
    <p>Comprueba que el archivo corresponde a esta empresa y no tiene daños accidentales.</p>
    <input type="file" accept="application/json,.json" (change)="verificar($event)" />
    @if (resultado()) { <p role="status">{{ resultado() }}</p> }
  </section>
`, styles: [`h1{font-size:24px;font-weight:800}.tarjeta{background:white;border:1px solid var(--linea);border-radius:12px;padding:18px;margin:16px 0;max-width:760px}h2{font-size:17px;font-weight:800}p{color:var(--gris)}`]})
export class Respaldos {
  private http = inject(HttpClient);
  readonly ocupado = signal(false); readonly resultado = signal('');
  async descargar() {
    this.ocupado.set(true); this.resultado.set('');
    try {
      const respuesta = await firstValueFrom(this.http.get(`${API_URL}/respaldos/empresa`, {observe: 'response', responseType: 'blob'}));
      const url = URL.createObjectURL(respuesta.body!);
      const enlace = document.createElement('a'); enlace.href = url; enlace.download = 'respaldo-empresa.json'; enlace.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      this.resultado.set('Respaldo descargado.');
    } catch { this.resultado.set('No se pudo descargar el respaldo.'); }
    finally { this.ocupado.set(false); }
  }
  async verificar(evento: Event) {
    const archivo = (evento.target as HTMLInputElement).files?.[0]; if (!archivo) return;
    try {
      if (archivo.size > 25 * 1024 * 1024) throw new Error('El archivo supera 25 MB.');
      const datos = JSON.parse(await archivo.text());
      const r = await firstValueFrom(this.http.post<{empresa: {codigo: string}; creado_en: string}>(`${API_URL}/respaldos/verificar`, datos));
      this.resultado.set(`Copia válida para ${r.empresa.codigo}, creada ${r.creado_en}.`);
    } catch { this.resultado.set('No se pudo verificar: archivo dañado, incompatible o de otra empresa.'); }
  }
}
