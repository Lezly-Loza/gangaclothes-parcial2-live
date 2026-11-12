import { DecimalPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, input, signal } from '@angular/core';
import { API_URL } from '../../core/api';
import { mensajeDeError } from '../../core/errores.interceptor';
import { SerieDias } from '../../shared/graficos/serie-dias';

interface PrendaRanking { prenda: string; unidades: number; ingreso_bs: number; }
interface SucursalRanking { sucursal_id: number; sucursal: string; top: PrendaRanking[]; }
interface Resultado {
  modo: 'gemini' | 'sin_modelo'; respuesta: string; aviso?: string;
  datos: {
    por_dia: {clave: string; total: number; ventas: number}[];
    top_prendas_por_sucursal?: SucursalRanking[];
  };
}
interface Reconocimiento {
  lang: string; interimResults: boolean; start(): void;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null; onend: (() => void) | null;
}

@Component({ selector: 'app-reporte-generativo', imports: [SerieDias, DecimalPipe], template: `
  <section class="generativo sin-imprimir">
    <h2>Reporte por lenguaje natural</h2>
    <p>Escribe o dicta tu pregunta. Al generar con Gemini se envían la pregunta y cifras agregadas; no se incluyen datos personales de clientes.</p>
    <label for="pregunta-reporte">Tu pregunta</label>
    <textarea id="pregunta-reporte" class="campo" rows="3" [value]="pregunta()" (input)="pregunta.set($any($event.target).value)" placeholder="Ej.: Resume las ventas e inventario del período"></textarea>
    <div class="acciones"><button type="button" class="btn rosa" (click)="generar()" [disabled]="cargando() || pregunta().trim().length < 3">{{ cargando() ? 'Generando…' : 'Generar reporte' }}</button>
      <button type="button" class="btn linea" (click)="dictar()" [disabled]="escuchando()">{{ escuchando() ? 'Escuchando…' : 'Dictar pregunta' }}</button></div>
    <p class="nota">La voz se procesa con el servicio de reconocimiento del navegador cuando está disponible.</p>
    @if (error()) { <p class="error" role="alert">{{ error() }}</p> }
    @if (resultado(); as r) { <div class="respuesta"><b>{{ r.modo === 'gemini' ? 'Reporte generado con Gemini' : 'Resumen de datos sin modelo' }}</b>
      @if (r.aviso) { <p>{{ r.aviso }}</p> }<p class="texto">{{ r.respuesta }}</p>
      <button class="btn linea" type="button" (click)="leer(r.respuesta)">Escuchar respuesta</button>
      <h3>Ventas reales por día del período seleccionado</h3>
      @if (puntos().length) { <app-serie-dias [puntos]="puntos()" titulo="Ventas reales por día" /> }
      @else { <p>No hay ventas pagadas en este período.</p> }
      @if (ranking().length) {
        <h3>Top 10 prendas más vendidas por sucursal</h3>
        <p class="nota">Ranking real calculado del período, por unidades vendidas. Es el dato que se envía al modelo para redactar la respuesta.</p>
        <div class="rankings">
          @for (s of ranking(); track s.sucursal_id) {
            <div class="ranking-suc">
              <h4>{{ s.sucursal }}</h4>
              @if (s.top.length) {
                <table class="tabla-top">
                  <thead><tr><th>#</th><th>Prenda</th><th>Unidades</th><th>Ingreso (Bs)</th></tr></thead>
                  <tbody>
                    @for (p of s.top; track p.prenda; let i = $index) {
                      <tr><td>{{ i + 1 }}</td><td>{{ p.prenda }}</td><td>{{ p.unidades }}</td><td>{{ p.ingreso_bs | number:'1.2-2' }}</td></tr>
                    }
                  </tbody>
                </table>
              } @else { <p class="vacio">Sin ventas en esta sucursal durante el período.</p> }
            </div>
          }
        </div>
      }
    </div> }
  </section>
`, styles: [`.generativo{background:#fff;border:1px solid var(--linea);border-radius:14px;padding:18px;margin:16px 0}.generativo h2{font-size:18px;font-weight:800}.generativo p{font-size:13px;line-height:1.5;color:var(--gris)}.generativo h3{font-size:15px;font-weight:800;margin-top:18px}.generativo h4{font-size:14px;font-weight:800;margin:10px 0 6px;color:var(--tinta)}label{display:block;font-size:12px;margin:12px 0 5px}.campo{width:100%;resize:vertical}.acciones{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.respuesta{border-top:1px solid var(--linea);margin-top:16px;padding-top:14px}.respuesta .texto{white-space:pre-wrap;color:var(--tinta)}.error{color:#b32d13!important}.rankings{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:10px}.ranking-suc{background:#fafafa;border:1px solid var(--linea);border-radius:10px;padding:12px}.tabla-top{width:100%;border-collapse:collapse;font-size:13px}.tabla-top th,.tabla-top td{padding:6px 8px;text-align:left;border-bottom:1px solid #eee}.tabla-top th{background:#f1f5f9;font-weight:700}.tabla-top tbody tr:hover{background:#fff}.tabla-top td:nth-child(3),.tabla-top td:nth-child(4){text-align:right}.vacio{color:var(--gris);font-size:12px;margin:4px 0}`] })
export class ReporteGenerativo {
  private http = inject(HttpClient);
  readonly desde = input<string | null>(null); readonly hasta = input<string | null>(null); readonly sucursalId = input<number | null>(null);
  readonly pregunta = signal(''); readonly cargando = signal(false); readonly escuchando = signal(false);
  readonly resultado = signal<Resultado | null>(null); readonly error = signal('');
  readonly puntos = computed(() => (this.resultado()?.datos.por_dia ?? []).map(p => ({clave: p.clave, etiqueta: p.clave.slice(5), valor: p.total, detalle: `${p.ventas} ventas`})));
  readonly ranking = computed(() => this.resultado()?.datos.top_prendas_por_sucursal ?? []);
  leer(texto: string): void {
    if (!('speechSynthesis' in window)) { this.error.set('La lectura en voz no está disponible en este navegador.'); return; }
    window.speechSynthesis.cancel(); const mensaje = new SpeechSynthesisUtterance(texto); mensaje.lang = 'es-BO'; window.speechSynthesis.speak(mensaje);
  }
  generar(): void {
    const pregunta = this.pregunta().trim(); if (pregunta.length < 3 || this.cargando()) return;
    this.cargando.set(true); this.error.set(''); this.resultado.set(null);
    this.http.post<Resultado>(`${API_URL}/reportes/generativo`, { pregunta, desde: this.desde(), hasta: this.hasta(), sucursal_id: this.sucursalId() }).subscribe({
      next: r => { this.resultado.set(r); this.cargando.set(false); },
      error: e => { this.error.set(mensajeDeError(e, 'No se pudo generar el reporte.')); this.cargando.set(false); },
    });
  }
  dictar(): void {
    const navegador = window as unknown as { SpeechRecognition?: new () => Reconocimiento; webkitSpeechRecognition?: new () => Reconocimiento };
    const Constructor = navegador.SpeechRecognition ?? navegador.webkitSpeechRecognition;
    if (!Constructor) { this.error.set('El reconocimiento de voz no está disponible en este navegador. Puedes escribir la pregunta.'); return; }
    const voz = new Constructor(); voz.lang = 'es-BO'; voz.interimResults = false; this.error.set(''); this.escuchando.set(true);
    voz.onresult = e => { const texto = Array.from(e.results).map(r => r[0]?.transcript ?? '').join(' '); this.pregunta.set(texto); };
    voz.onerror = () => { this.error.set('No se pudo reconocer la voz. Comprueba el micrófono o escribe la pregunta.'); this.escuchando.set(false); };
    voz.onend = () => this.escuchando.set(false);
    try { voz.start(); } catch { this.error.set('No se pudo iniciar el micrófono.'); this.escuchando.set(false); }
  }
}
