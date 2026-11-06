import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../../services/auth.service';
import { SesionStore, rutaInicial } from '../../../core/sesion';
import { Notificaciones } from '../../../core/notificaciones';
import { mensajeDeError } from '../../../core/errores.interceptor';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class LoginPage {
  private api = inject(AuthService);
  private sesion = inject(SesionStore);
  private router = inject(Router);
  private ruta = inject(ActivatedRoute);
  private avisos = inject(Notificaciones);

  readonly modo = signal<'tenant' | 'super'>('tenant');
  readonly datos: any = { codigo_tenant: 'luna', email: 'ana@boutique-luna.bo', password: 'Luna12345' };
  readonly superDatos: any = { email: 'root@plataforma.bo', password: 'SuperSegura123' };
  readonly error = signal('');
  readonly cargando = signal(false);

  cambiarModo(m: 'tenant' | 'super') { this.modo.set(m); this.error.set(''); }

  async entrar() {
    this.error.set('');
    this.cargando.set(true);
    try {
      const s = this.modo() === 'super'
        ? await firstValueFrom(this.api.superLogin(this.superDatos))
        : await firstValueFrom(this.api.login(this.datos));
      this.sesion.guardar(s);
      this.avisos.ok(`Bienvenido/a, ${s.nombre}`);
      const volverA = this.ruta.snapshot.queryParamMap.get('volverA');
      this.router.navigateByUrl(volverA || rutaInicial(s.roles || []));
    } catch (e: any) {
      this.error.set(mensajeDeError(e, 'No se pudo iniciar sesion'));
    } finally {
      this.cargando.set(false);
    }
  }
}
