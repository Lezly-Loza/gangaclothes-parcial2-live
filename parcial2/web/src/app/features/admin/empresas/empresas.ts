import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { Tenant, TenantsService } from '../../../core/tenants.service';
import { PlanesService, Plan } from '../../../core/planes.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { fechaCortaLocal } from '../../../shared/formato';

@Component({
  selector: 'app-empresas',
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './empresas.html',
  styleUrl: './empresas.css',
})
export class Empresas {
  private api = inject(TenantsService);
  private planesApi = inject(PlanesService);
  private avisos = inject(Notificaciones);
  private fb = inject(FormBuilder);

  readonly empresas = signal<Tenant[]>([]);
  readonly planes = signal<Plan[]>([]);
  readonly cargando = signal(true);
  readonly errorCarga = signal<string | null>(null);

  readonly modalAbierto = signal(false);
  readonly guardando = signal(false);
  readonly errorFormulario = signal<string | null>(null);

  readonly formulario = this.fb.nonNullable.group({
    razon_social: ['', [Validators.required, Validators.minLength(2)]],
    nit: ['', Validators.required],
    correo: ['', [Validators.required, Validators.email]],
    telefono: [''],
    codigo: ['', [Validators.required, Validators.pattern(/^[a-zA-Z0-9_-]+$/)]],
    admin_nombre: ['', [Validators.required, Validators.minLength(2)]],
    admin_email: ['', [Validators.required, Validators.email]],
    admin_password: ['', [Validators.required, Validators.minLength(6)]],
    plan_codigo: ['profesional'],
  });

  constructor() { this.cargar(); }

  async cargar() {
    this.cargando.set(true);
    this.errorCarga.set(null);
    try {
      const [emp, pl] = await Promise.all([
        firstValueFrom(this.api.listar()),
        firstValueFrom(this.planesApi.listar()),
      ]);
      this.empresas.set(emp);
      this.planes.set(pl);
    } catch (e: any) {
      this.errorCarga.set(mensajeDeError(e, 'No se pudieron cargar las empresas.'));
    } finally {
      this.cargando.set(false);
    }
  }

  abrirNuevo() {
    this.formulario.reset({ plan_codigo: 'profesional' } as any);
    this.errorFormulario.set(null);
    this.modalAbierto.set(true);
  }

  cerrarModal() { this.modalAbierto.set(false); }

  invalido(campo: string): boolean {
    const c = this.formulario.get(campo);
    return !!(c && c.invalid && (c.dirty || c.touched));
  }

  async guardar() {
    this.errorFormulario.set(null);
    if (this.formulario.invalid) { this.formulario.markAllAsTouched(); return; }
    const v = this.formulario.getRawValue();
    this.guardando.set(true);
    try {
      await firstValueFrom(this.api.crear({
        razon_social: v.razon_social, nit: v.nit, correo: v.correo,
        telefono: v.telefono || null, codigo: v.codigo,
        admin: { nombre: v.admin_nombre, email: v.admin_email, password: v.admin_password },
        plan_codigo: v.plan_codigo || null,
      }));
      this.avisos.ok(`Empresa "${v.razon_social}" registrada.`);
      this.modalAbierto.set(false);
      await this.cargar();
    } catch (e: any) {
      this.errorFormulario.set(mensajeDeError(e, 'No se pudo registrar la empresa.'));
    } finally {
      this.guardando.set(false);
    }
  }

  fecha(iso: string | null | undefined) { return fechaCortaLocal(iso, true); }
}
