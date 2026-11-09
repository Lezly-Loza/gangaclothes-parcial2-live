import { Component, inject, isDevMode, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth.service';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { CUENTAS_DEMO, CuentaDemo } from '../../../../environments/cuentas-demo';

/**
 * Los atajos de cuentas solo tienen sentido corriendo en local. Hay dos
 * barreras: esta condicion oculta el bloque, y el `fileReplacements` de
 * angular.json deja la lista vacia en la compilacion de produccion, para que
 * las credenciales ni siquiera existan dentro del bundle publicado.
 */
function enLocal(): boolean {
  return isDevMode() || ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
}

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private ruta = inject(ActivatedRoute);

  /** Se pasa al registro para que el cliente nuevo vuelva a donde estaba. */
  readonly volverA = this.ruta.snapshot.queryParamMap.get('volverA');

  readonly mostrarCuentasDemo = CUENTAS_DEMO.length > 0;
  readonly cuentasDemo = CUENTAS_DEMO;
  readonly enviando = signal(false);
  readonly esperandoServidor = signal(false);
  readonly error = signal<string | null>(null);
  private temporizadorEspera: any = null;

  /** Parcial 2: el superadmin entra sin codigo de empresa. */
  readonly modoSuper = signal(false);

  readonly formulario = this.fb.nonNullable.group({
    codigo_tenant: [this.ruta.snapshot.queryParamMap.get('tenant') ?? 'luna', []],
    // Viene rellenado al volver de "recuperar contrasena".
    email: [this.ruta.snapshot.queryParamMap.get('email') ?? '', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  cambiarModoSuper(activo: boolean): void {
    this.modoSuper.set(activo);
    const codigoCtrl = this.formulario.controls.codigo_tenant;
    if (activo) {
      codigoCtrl.setValue('');
      codigoCtrl.clearValidators();
    } else {
      codigoCtrl.setValidators([Validators.required]);
    }
    codigoCtrl.updateValueAndValidity();
  }

  usar(cuenta: CuentaDemo): void {
    const esSuper = !cuenta.codigo_tenant;
    this.cambiarModoSuper(esSuper);
    this.formulario.setValue({
      codigo_tenant: cuenta.codigo_tenant || '',
      email: cuenta.email,
      password: cuenta.password,
    });
    this.enviar();
  }

  /** Lleva el correo ya escrito a la pantalla de recuperacion. */
  correoEscrito(): Record<string, string> {
    const email = this.formulario.controls.email;
    return email.valid ? { email: email.value.trim() } : {};
  }

  invalido(campo: 'email' | 'password' | 'codigo_tenant'): boolean {
    const control = this.formulario.controls[campo];
    return control.invalid && (control.dirty || control.touched);
  }

  enviar(): void {
    this.error.set(null);
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const { email, password, codigo_tenant } = this.formulario.getRawValue();
    this.enviando.set(true);
    this.esperandoServidor.set(false);
    clearTimeout(this.temporizadorEspera);
    this.temporizadorEspera = setTimeout(() => {
      if (this.enviando()) {
        this.esperandoServidor.set(true);
      }
    }, 3500);

    const codigo = this.modoSuper() ? undefined : (codigo_tenant || undefined);
    this.auth.login(email, password, codigo).subscribe({
      next: () => {
        clearTimeout(this.temporizadorEspera);
        this.enviando.set(false);
        this.esperandoServidor.set(false);
        const volverA = this.ruta.snapshot.queryParamMap.get('volverA');
        this.router.navigateByUrl(volverA || this.auth.rutaInicial());
      },
      error: (err) => {
        clearTimeout(this.temporizadorEspera);
        this.enviando.set(false);
        this.esperandoServidor.set(false);
        this.error.set(
          err.status === 401
            ? 'Correo o contrasena incorrectos.'
            : mensajeDeError(err, 'No se pudo iniciar sesion. Intenta de nuevo.'),
        );
      },
    });
  }
}
