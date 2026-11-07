import { HttpClient } from '@angular/common/http';
import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { API_URL } from '../../core/api';
import { mensajeDeError } from '../../core/errores.interceptor';
import { Notificaciones } from '../../core/notificaciones';

export interface OpcionAnulacion {
  tipo: 'VENTA' | 'RESERVA';
  id: number;
  descripcion: string;
}

/**
 * CU-17: Modal con confirmación explícita (dialog de seguridad)
 * advirtiendo la reversión automática de stock e input obligatorio de justificación.
 */
@Component({
  selector: 'app-modal-anulacion',
  imports: [ReactiveFormsModule],
  templateUrl: './modal-anulacion.html',
  styleUrl: './modal-anulacion.css',
  host: { '(document:keydown.escape)': 'cerrar()' },
})
export class ModalAnulacion {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private avisos = inject(Notificaciones);

  @Input({ required: true }) opcion!: OpcionAnulacion;
  @Output() anulado = new EventEmitter<void>();
  @Output() cerrado = new EventEmitter<void>();

  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    motivo: ['', [Validators.required, Validators.minLength(5), Validators.maxLength(300)]],
    confirmacion: [false, Validators.requiredTrue],
  });

  cerrar(): void {
    if (!this.cargando()) this.cerrado.emit();
  }

  confirmarAnulacion(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) return;

    this.error.set(null);
    this.cargando.set(true);

    const datos = {
      tipo_operacion: this.opcion.tipo,
      operacion_id: this.opcion.id,
      motivo: this.form.value.motivo?.trim(),
    };

    this.http.post<{ mensaje: string }>(`${API_URL}/operaciones/anular`, datos).subscribe({
      next: (r) => {
        this.cargando.set(false);
        this.avisos.ok(r.mensaje || `${this.opcion.tipo} #${this.opcion.id} anulada.`);
        this.anulado.emit();
      },
      error: (err) => {
        this.cargando.set(false);
        this.error.set(mensajeDeError(err, 'No se pudo anular la operación.'));
      },
    });
  }
}

