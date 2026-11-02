import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterOutlet, Routes } from '@angular/router';
import { HttpInterceptorFn } from '@angular/common/http';
import { AuthService } from './services/auth.service';
import { PwaService } from './services/pwa.service';
import { LoginPage, RegistrarEmpresaForm, UsuariosList, SucursalesList, ContratarPlanForm,
         MiSuscripcion, ProductosList, CatalogosPage, ProveedoresList, ClientesList,
         InventarioPage, AvisoInstalacionComponent, ReservarPrendaPage, PuntoVentaPage,
         CambioPrendaPage, AnularOperacionDialog, ModoOfflinePage } from './screens';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem('token');
  return next(token ? req.clone({setHeaders:{Authorization:`Bearer ${token}`}}) : req);
};

export const routes: Routes = [
  {path:'',redirectTo:'login',pathMatch:'full'},
  {path:'login',component:LoginPage},
  {path:'empresas',component:RegistrarEmpresaForm},
  {path:'usuarios',component:UsuariosList},
  {path:'sucursales',component:SucursalesList},
  {path:'contratar',component:ContratarPlanForm},
  {path:'suscripcion',component:MiSuscripcion},
  {path:'productos',component:ProductosList},
  {path:'catalogos',component:CatalogosPage},
  {path:'proveedores',component:ProveedoresList},
  {path:'clientes',component:ClientesList},
  {path:'inventario',component:InventarioPage},
  {path:'instalar',component:AvisoInstalacionComponent},
  {path:'reservar',component:ReservarPrendaPage},
  {path:'ventas',component:PuntoVentaPage},
  {path:'cambios',component:CambioPrendaPage},
  {path:'anular',component:AnularOperacionDialog},
  {path:'offline',component:ModoOfflinePage}
];

@Component({selector:'app-root',standalone:true,imports:[CommonModule,RouterOutlet,RouterLink],template:`
  <nav><strong style="color:white;padding:9px">GangaClothes</strong>
    <a *ngFor="let n of menu" [routerLink]="n.path">{{n.label}}</a>
    <a routerLink="/instalar">Instalar</a>
    <a routerLink="/login" (click)="salir()">Salir</a>
    <span style="color:white;padding:9px">{{enLinea?'En línea':'Sin conexión'}}</span>
  </nav><main class="shell"><router-outlet></router-outlet></main>`})
export class AppComponent {
  private auth=inject(AuthService);private pwa=inject(PwaService);
  enLinea=navigator.onLine;menu:{path:string;label:string}[]=[];
  constructor(){window.addEventListener('online',()=>this.enLinea=true);window.addEventListener('offline',()=>this.enLinea=false);this.abrirAplicacion();}
  abrirAplicacion(){this.pwa.registrarServiceWorker();const session=JSON.parse(localStorage.getItem('session')||'{}');const role=session.roles?.[0]||'';
    const all=[['empresas','Empresas',['superadmin']],['usuarios','Usuarios',['admin']],['sucursales','Sucursales',['admin','encargado']],
      ['contratar','Contratar plan',['admin']],['suscripcion','Suscripción',['admin']],['productos','Productos',['admin','vendedor']],
      ['catalogos','Catálogos',['admin']],['proveedores','Proveedores',['admin']],['clientes','Clientes',['admin','vendedor']],
      ['inventario','Inventario',['admin','encargado']],['reservar','Reservas',['cliente']],['ventas','Ventas',['vendedor','cliente']],
      ['cambios','Cambios',['admin','vendedor']],['anular','Anular',['encargado']],['offline','Offline',['vendedor']]] as [string,string,string[]][];
    this.menu=all.filter(x=>x[2].includes(role)).map(x=>({path:x[0],label:x[1]}));
  }
  salir(){this.auth.logout();}
}
