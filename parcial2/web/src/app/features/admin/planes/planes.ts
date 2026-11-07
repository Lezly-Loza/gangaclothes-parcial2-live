import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { Plan, PlanesService } from '../../../core/planes.service';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

const MODULOS_SUGERIDOS = [
  'ventas', 'inventario', 'compras', 'proveedores', 'clientes', 'reservas', 'cambios',
  'envios', 'reportes', 'promociones', 'red_de_tiendas', 'ia', 'sincronizacion_offline',
];

@Component({
  selector: 'app-planes',
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './planes.html',
  styleUrl: './planes.css',
})
export class Planes {
  private api = inject(PlanesService);
  private avisos = inject(Notificaciones);
  private fb = inject(FormBuilder);

  readonly planes = signal<Plan[]>([]);
  readonly cargando = signal(true);
  readonly errorCarga = signal<string | null>(null);

  readonly modalAbierto = signal(false);
  readonly editando = signal<Plan | null>(null);
  readonly guardando = signal(false);
  readonly errorFormulario = signal<string | null>(null);

  readonly modulosDisponibles = MODULOS_SUGERIDOS;

  readonly formulario = this.fb.nonNullable.group({
    codigo: ['', [Validators.required, Validators.pattern(/^[a-zA-Z0-9_-]+$/)]],
    nombre: ['', Validators.required],
    descripcion: [''],
    max_sucursales: [1, [Validators.required, Validators.min(1)]],
    max_usuarios: [3, [Validators.required, Validators.min(1)]],
    max_productos: [100, [Validators.required, Validators.min(1)]],
    precio_mensual: [19, [Validators.required, Validators.min(0)]],
    modulos: [[] as string[]],
  });

  constructor() { this.cargar(); }

  async cargar() {
    this.cargando.set(true);
    this.errorCarga.set(null);
    try { this.planes.set(await firstValueFrom(this.api.listar())); }
    catch (e: any) { this.errorCarga.set(mensajeDeError(e, 'No se pudieron cargar los planes.')); }
    finally { this.cargando.set(false); }
  }

  abrirNuevo() {
    this.editando.set(null);
    this.formulario.reset({
      codigo: '', nombre: '', descripcion: '',
      max_sucursales: 1, max_usuarios: 3, max_productos: 100,
      precio_mensual: 19, modulos: [],
    });
    this.errorFormulario.set(null);
    this.modalAbierto.set(true);
  }

  abrirEdicion(p: Plan) {
    this.editando.set(p);
    this.formulario.reset({
      codigo: p.codigo, nombre: p.nombre, descripcion: p.descripcion ?? '',
      max_sucursales: p.max_sucursales, max_usuarios: p.max_usuarios, max_productos: p.max_productos,
      precio_mensual: p.precio_mensual, modulos: [...(p.modulos || [])],
    });
    this.errorFormulario.set(null);
    this.modalAbierto.set(true);
  }

  cerrarModal() { this.modalAbierto.set(false); }

  toggleModulo(m: string) {
    const actuales = this.formulario.controls.modulos.value;
    const next = actuales.includes(m) ? actuales.filter((x) => x !== m) : [...actuales, m];
    this.formulario.controls.modulos.setValue(next);
  }

  tieneModulo(m: string): boolean { return this.formulario.controls.modulos.value.includes(m); }

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
      const editando = this.editando();
      if (editando) {
        await firstValueFrom(this.api.actualizar(editando.id, {
          nombre: v.nombre, descripcion: v.descripcion,
          max_sucursales: v.max_sucursales, max_usuarios: v.max_usuarios, max_productos: v.max_productos,
          precio_mensual: v.precio_mensual, modulos: v.modulos,
        }));
        this.avisos.ok(`Plan "${v.nombre}" actualizado.`);
      } else {
        await firstValueFrom(this.api.crear({
          codigo: v.codigo, nombre: v.nombre, descripcion: v.descripcion || null,
          max_sucursales: v.max_sucursales, max_usuarios: v.max_usuarios, max_productos: v.max_productos,
          precio_mensual: v.precio_mensual, modulos: v.modulos,
        }));
        this.avisos.ok(`Plan "${v.nombre}" creado.`);
      }
      this.modalAbierto.set(false);
      await this.cargar();
    } catch (e: any) { this.errorFormulario.set(mensajeDeError(e, 'No se pudo guardar el plan.')); }
    finally { this.guardando.set(false); }
  }

  async desactivar(p: Plan) {
    if (!confirm(`¿Desactivar el plan "${p.nombre}"? No se podra contratar hasta reactivarlo.`)) return;
    try {
      await firstValueFrom(this.api.desactivar(p.id));
      this.avisos.ok(`Plan "${p.nombre}" desactivado.`);
      await this.cargar();
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo desactivar.')); }
  }

  async reactivar(p: Plan) {
    try {
      await firstValueFrom(this.api.actualizar(p.id, { activo: true }));
      this.avisos.ok(`Plan "${p.nombre}" reactivado.`);
      await this.cargar();
    } catch (e: any) { this.avisos.error(mensajeDeError(e, 'No se pudo reactivar.')); }
  }
}
