# GangaClothes móvil · parcial 2

Aplicación Flutter conectada al mismo backend y a las mismas empresas que la web
de `parcial2`. La interfaz usa la identidad negra, blanca y rosa de la versión
actual. El menú depende de los roles y permisos de la cuenta.

- **CU-02:** inicio de sesión con código de empresa y registro de clientes.
  También se puede ingresar como superadministrador sin código para consultar
  empresas y planes; su administración y edición se realizan desde la web.
- **CU-11:** búsqueda, creación y edición de clientes, según permisos.
- **CU-14:** catálogo por sucursal, selección de variante y reserva con cita;
  consulta y cancelación de reservas propias.
- **CU-15:** carrito compartido con la web y compra de prueba, con retiro o
  envío a domicilio. La compra descuenta stock y aparece en los reportes.
- **CU-17:** clientes cancelan sus reservas; el personal con permisos puede
  buscar ventas o reservas por código o entre las recientes y anularlas.
- **CU-18 y CU-19:** descarga y consulta de catálogo por sucursal, categoría y
  temporada. La copia queda separada por empresa y cuenta y refleja el momento
  de descarga.
- **CU-20 a CU-23:** reserva local para clientes y venta de contado local para
  personal autorizado, una variante por operación. En «Operaciones locales» se
  consultan los pendientes y se sincronizan al recuperar conexión, al volver a
  abrir la aplicación o manualmente. Un conflicto requiere
  revisar stock, precio y efectivo; se puede descartar y crear otra operación.
  No se pueden descartar pendientes cuyo resultado pueda ser incierto.

El pago del carrito es **simulado** y no mueve dinero real. La tarifa y distancia
del envío no se calculan; el seguimiento se actualiza cuando la sucursal procesa
el pedido. En dispositivo se guarda la sesión localmente para poder volver a
abrir la copia offline; no utilices esta implementación como almacenamiento
seguro de credenciales para una aplicación de producción.
No borres los datos de la app antes de sincronizar: las operaciones pendientes
existen solo en ese dispositivo. El stock descargado no garantiza disponibilidad
en el servidor y un token vencido requiere volver a iniciar sesión.

En Android, «Activar avisos en Android» solicita permiso para mostrar el resultado
de cada operación cuando la aplicación sincroniza. Son notificaciones **locales**:
no son push remoto y no ejecutan la sincronización mientras la app está cerrada.
Al abrirla, vuelve a intentar las operaciones pendientes. Si una reserva tiene
conflicto por falta de stock o cambio de precio, no está confirmada; consulta
«Operaciones locales» para ver el motivo. Si el permiso está desactivado, los
resultados siguen guardados en la aplicación.

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

### Probar el servidor publicado en el emulador

La carpeta `mobile` de la raíz corresponde al primer parcial y no envía el
código de empresa. Ejecuta la aplicación desde `parcial2/mobile` para usar el
segundo parcial. Es una aplicación Android distinta y no borra los datos de la
anterior. En PowerShell:

```powershell
cd parcial2/mobile
flutter run -d emulator-5554 --dart-define=API_URL=https://gangaclothes-parcial2.onrender.com/api/v1 --dart-define=WEB_URL=https://ganga-clothes.vercel.app
```

En «Mi empresa», las cuentas demo de Ana y del cliente usan código `luna` y
contraseña `Luna12345`. En «Superadministrador», la cuenta demo usa
`root@plataforma.bo` y `SuperSegura123`, sin código de empresa. Los datos de
prueba se consultan en el servidor publicado, no en SQLite de la computadora.

## Verificación

```powershell
flutter analyze
flutter test
```
