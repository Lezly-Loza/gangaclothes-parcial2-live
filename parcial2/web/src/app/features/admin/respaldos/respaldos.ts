import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { API_URL } from '../../../core/api';

interface Programa {
  diario: boolean; hora: string; fecha_unica: string | null; siguiente_diario: string | null;
  ultimo: string | null; error: string | null; copias: {nombre: string; bytes: number}[];
}
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
    <h2>Respaldos automáticos</h2>
    <p>Por defecto se crea una copia cada día a las 02:00, hora de Bolivia. El servidor debe estar encendido y disponer de almacenamiento persistente; si estuvo apagado, se intentará al reiniciarlo.</p>
    <label><input type="checkbox" [checked]="diario()" (change)="diario.set($any($event.target).checked)" /> Crear una copia diaria</label>
    <label>Hora diaria <input class="campo" type="time" [value]="hora()" (input)="hora.set($any($event.target).value)" /></label>
    <label>Una copia adicional en fecha y hora (opcional)
      <input class="campo" type="datetime-local" [value]="fechaUnica()" (input)="fechaUnica.set($any($event.target).value)" />
    </label>
    <p>Deja la fecha vacía para cancelar la copia adicional. Hora de Bolivia.</p>
    <button class="btn rosa" type="button" [disabled]="ocupado()" (click)="guardar()">Guardar programación</button>
    @if (programa(); as p) {
      <p>Próxima diaria: {{ p.siguiente_diario ? mostrarFecha(p.siguiente_diario) : 'desactivada' }} · Última copia: {{ p.ultimo ? mostrarFecha(p.ultimo) : 'todavía no hay' }}</p>
      @if (p.error) { <p role="alert">{{ p.error }}</p> }
      <h3>Copias automáticas disponibles</h3>
      @for (c of p.copias; track c.nombre) { <p><button class="btn linea" type="button" (click)="descargarProgramado(c.nombre)">Descargar</button> {{ c.nombre }} · {{ c.bytes }} bytes</p> }
      @empty { <p>Aún no hay copias automáticas.</p> }
    }
  </section>
  <section class="tarjeta">
    <h2>Verificar copia</h2>
    <p>Comprueba que el archivo corresponde a esta empresa y no tiene daños accidentales.</p>
    <input type="file" accept="application/json,.json" (change)="verificar($event)" />
    @if (resultado()) { <p role="status">{{ resultado() }}</p> }
  </section>
`, styles: [`h1{font-size:24px;font-weight:800}.tarjeta{background:white;border:1px solid var(--linea);border-radius:12px;padding:18px;margin:16px 0;max-width:760px}h2{font-size:17px;font-weight:800}h3{font-size:15px;font-weight:800;margin-top:16px}p{color:var(--gris)}label{display:block;margin:12px 0}label .campo{display:block;max-width:250px;margin-top:5px}`]})
export class Respaldos {
  private http = inject(HttpClient);
  readonly ocupado = signal(false); readonly resultado = signal('');
  readonly programa = signal<Programa | null>(null); readonly diario = signal(true);
  readonly hora = signal('02:00'); readonly fechaUnica = signal('');
  constructor() { this.cargar(); }
  mostrarFecha(valor: string) { return new Intl.DateTimeFormat('es-BO', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/La_Paz' }).format(new Date(valor)); }
  async cargar() {
    try {
      const p = await firstValueFrom(this.http.get<Programa>(`${API_URL}/respaldos/programacion`));
      this.programa.set(p); this.diario.set(p.diario); this.hora.set(p.hora); this.fechaUnica.set(p.fecha_unica?.slice(0, 16) ?? '');
    } catch { this.resultado.set('No se pudo cargar la programación.'); }
  }
  async guardar() {
    this.ocupado.set(true);
    try {
      await firstValueFrom(this.http.put(`${API_URL}/respaldos/programacion`, {diario: this.diario(), hora: this.hora(), fecha_unica: this.fechaUnica() || null}));
      await this.cargar(); this.resultado.set('Programación guardada.');
    } catch { this.resultado.set('No se pudo guardar. Comprueba que la fecha adicional sea futura.'); }
    finally { this.ocupado.set(false); }
  }
  async descargarProgramado(nombre: string) {
    try {
      const blob = await firstValueFrom(this.http.get(`${API_URL}/respaldos/programados/${encodeURIComponent(nombre)}`, {responseType: 'blob'}));
      const url = URL.createObjectURL(blob); const enlace = document.createElement('a'); enlace.href = url; enlace.download = nombre; enlace.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch { this.resultado.set('No se pudo descargar la copia programada.'); }
  }
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
