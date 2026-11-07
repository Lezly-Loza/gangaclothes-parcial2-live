# GangaClothes móvil · parcial 2

Aplicación Flutter conectada al mismo backend y a las mismas empresas que la web
de `parcial2`. La interfaz usa la identidad negra, blanca y rosa de la versión
actual. El menú depende de los roles y permisos de la cuenta.

- **CU-02:** inicio de sesión con código de empresa y registro de clientes.
- **CU-11:** búsqueda, creación y edición de clientes, según permisos.
- **CU-14:** catálogo por sucursal, selección de variante y reserva con cita;
  consulta y cancelación de reservas propias.
- **CU-15:** carrito compartido con la web y compra de prueba, con retiro o
  envío a domicilio. La compra descuenta stock y aparece en los reportes.
- **CU-17:** clientes cancelan sus reservas; el personal con permisos puede
  buscar ventas o reservas por código o entre las recientes y anularlas.
- **CU-18:** descarga de catálogo por sucursal, categoría y temporada para
  consultar sin conexión. La copia queda separada por empresa y cuenta y se
  conserva si falla una descarga posterior. Los datos reflejan el momento de la
  descarga; comprar y reservar requieren conexión.

El pago del carrito es **simulado** y no mueve dinero real. La tarifa y distancia
del envío no se calculan; el seguimiento se actualiza cuando la sucursal procesa
el pedido. En dispositivo se guarda la sesión localmente para poder volver a
abrir la copia offline; no utilices esta implementación como almacenamiento
seguro de credenciales para una aplicación de producción.

## Ejecutar con Android

Inicia el backend de `parcial2` en la computadora. Si usas el emulador Android,
la app usa por defecto `http://10.0.2.2:8000/api/v1`, que apunta al puerto 8000
de la computadora. Después, en otra terminal:

```powershell
cd parcial2/mobile
flutter pub get
flutter devices
flutter run -d <id-del-emulador>
```

Si PowerShell indica que falta `JAVA_HOME` y tienes Android Studio instalado,
puedes configurarlo para esa terminal antes de ejecutar Flutter:

```powershell
$env:JAVA_HOME = 'C:\Program Files\Android\Android Studio\jbr'
```

Para un teléfono físico, conecta teléfono y computadora a la misma red, inicia
el backend escuchando en la red local y reemplaza la dirección por la IPv4 de la
computadora (se puede consultar con `ipconfig`):

```powershell
cd parcial2/backend
.\.venv-run\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```powershell
cd parcial2/mobile
flutter run -d <id-del-telefono> --dart-define=API_URL=http://IP-DE-TU-PC:8000/api/v1
```

Android permite HTTP local en la compilación **debug**. Para una distribución
real usa una URL HTTPS y configura la firma de la aplicación. En iOS se requiere
Xcode en macOS y un servidor HTTPS para cumplir la política de transporte del
sistema. En la web de Flutter el servidor debe permitir el origen mediante CORS.
Si las imágenes devueltas por el catálogo son rutas relativas de la web, pasa
también `--dart-define=WEB_URL=http://IP-DE-TU-PC:4200` para mostrarlas.

Cuenta de demostración: empresa `luna`, correo `cliente@boutique-luna.bo`,
contraseña `Luna12345`. Cierra sesión y vuelve a entrar después de cambiar los
permisos de una cuenta. No vuelvas a sembrar la base existente si contiene datos
que quieras conservar.

## Verificación

```powershell
flutter analyze
flutter test
```
