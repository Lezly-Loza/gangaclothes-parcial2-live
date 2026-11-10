import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gangaclothes_mobile/main.dart';
import 'package:gangaclothes_mobile/main.dart' as app;
import 'package:gangaclothes_mobile/api_service.dart';
import 'package:gangaclothes_mobile/producto_local_dao.dart';
import 'package:gangaclothes_mobile/operaciones_offline.dart';
import 'package:gangaclothes_mobile/tienda.dart';
import 'package:gangaclothes_mobile/gestion.dart';
import 'package:dio/dio.dart';
import 'dart:convert';
import 'dart:typed_data';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));
  testWidgets('el acceso solicita empresa, correo y contraseña y valida los campos', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
    expect(find.text('Código de empresa'), findsOneWidget);
    expect(find.text('Correo electrónico'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Contraseña'), 100, scrollable: find.byType(Scrollable).first);
    expect(find.text('Contraseña'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Iniciar sesión'), 100, scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pump();
    expect(find.text('Completa los campos obligatorios.'), findsOneWidget);
  });
  testWidgets('cliente puede abrir el formulario de registro', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
    await tester.scrollUntilVisible(find.text('¿Cliente nuevo? Crear cuenta'), 200, scrollable: find.byType(Scrollable).first);
    await tester.tap(find.text('¿Cliente nuevo? Crear cuenta'));
    await tester.pumpAndSettle();
    expect(find.text('Nombre completo'), findsOneWidget);
    expect(find.text('Documento'), findsOneWidget);
  });
  test('el formulario de tarjeta valida Luhn antes de enviar', () {
    expect(tarjetaPruebaValida('4242 4242 4242 4242'), isTrue);
    expect(tarjetaPruebaValida('4000 0000 0000 0002'), isTrue);
    expect(tarjetaPruebaValida('4242 4242 4242 4241'), isFalse);
  });
  testWidgets('el asistente administrativo muestra dictado y lectura', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: AsistenteIaScreen(admin: true)));
    expect(find.textContaining('asistente administrativo'), findsOneWidget);
    expect(find.byTooltip('Dictar pregunta'), findsOneWidget);
    expect(find.byTooltip('Escuchar respuesta'), findsOneWidget);
  });
  testWidgets('superadministrador entra sin código de empresa y consulta plataforma', (tester) async {
    final adapter = ApiAcceso();
    app.api = ApiService(baseUrl: 'http://localhost/api/v1', adapter: adapter);
    await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
    await tester.tap(find.text('Superadministrador'));
    await tester.pump();
    expect(find.text('Código de empresa'), findsNothing);
    await tester.enterText(find.widgetWithText(TextField, 'Correo electrónico'), 'root@plataforma.bo');
    await tester.enterText(find.widgetWithText(TextField, 'Contraseña'), 'clave-prueba');
    tester.testTextInput.hide();
    await tester.scrollUntilVisible(find.text('Iniciar sesión'), 100, scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pumpAndSettle();
    expect(adapter.rutas, contains('/auth/super/login'));
    expect(adapter.enviado, isNot(contains('codigo_tenant')));
    expect(find.text('Superadministrador'), findsOneWidget);
    expect(find.text('1 Empresas Registradas'), findsOneWidget);
    await tester.tap(find.text('Planes'));
    await tester.pumpAndSettle();
    expect(find.text('Plan de prueba'), findsWidgets);
    app.api = ApiService();
  });
  test('acceso de empresa envía código de tenant y conserva sesión', () async {
    final adapter = ApiAcceso();
    final servicio = ApiService(baseUrl: 'http://localhost/api/v1', adapter: adapter);
    final sesion = await servicio.login({'codigo_tenant': 'luna', 'email': 'cliente@boutique-luna.bo', 'password': 'clave-prueba'});
    expect(adapter.rutas, contains('/auth/login'));
    expect(adapter.enviado['codigo_tenant'], 'luna');
    expect(sesion['tenant_codigo'], 'luna');
    expect((await servicio.sesionGuardada())?['kind'], 'tenant');
  });
  test('una sesión de otro backend no se reutiliza en el servidor local', () async {
    final anterior = ApiService(baseUrl: 'https://servidor-anterior/api/v1', adapter: ApiAcceso());
    await anterior.login({'codigo_tenant': 'luna', 'email': 'cliente@boutique-luna.bo', 'password': 'clave-prueba'});
    final local = ApiService(baseUrl: 'http://10.0.2.2:8001/api/v1', adapter: ApiAcceso());
    expect(await local.sesionGuardada(), isNull);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('access_token'), isNull);
  });
  test('las copias offline se separan por empresa y usuario y reemplazan la selección', () async {
    final a = ProductoLocalDao(tenantId: 1, userId: 1);
    final b = ProductoLocalDao(tenantId: 1, userId: 2);
    final c = ProductoLocalDao(tenantId: 2, userId: 1);
    await a.guardarCatalogoLocal({'fecha_descarga': 'hoy', 'productos': [{'nombre': 'Polera'}], 'variantes': []});
    expect(await a.contarProductos(), 1);
    expect(await b.contarProductos(), 0);
    expect(await c.contarProductos(), 0);
    await a.guardarCatalogoLocal({'fecha_descarga': 'mañana', 'productos': [], 'variantes': []});
    expect(await a.contarProductos(), 0);
    expect(await a.fechaDescarga(), 'mañana');
  });
  testWidgets('desde una prenda se reserva y se agrega al carrito con sucursal y variante', (tester) async {
    final adapter = ApiDePrueba();
    app.api = ApiService(baseUrl: 'http://localhost/api/v1', adapter: adapter);
    final prenda = {'id': 2, 'nombre': 'Polera', 'precio_final': 80, 'variantes': [
      {'id': 11, 'talla': 'M', 'color': 'Negro', 'disponible_total': 4,
       'disponibilidad': [{'sucursal_id': 3, 'sucursal': 'Luna Centro', 'disponible': 4}]}]};
    await tester.pumpWidget(MaterialApp(home: ReservarPrendaScreen(prenda: prenda)));
    await tester.scrollUntilVisible(find.text('Agregar al carrito'), 200, scrollable: find.byType(Scrollable).first);
    await tester.tap(find.text('Agregar al carrito'));
    await tester.pumpAndSettle();
    expect(adapter.rutas, contains('/tienda/carrito/items'));
    expect(adapter.item['variante_id'], 11);
    expect(adapter.item['cantidad'], 1);
    await tester.tap(find.text('Reservar para probar en tienda'));
    await tester.pumpAndSettle();
    expect(find.text('Reserva confirmada'), findsOneWidget);
    expect(adapter.reserva['sucursal_id'], 3);
    expect((adapter.reserva['detalle'] as List).first['variante_id'], 11);
    expect(find.textContaining('RES-PRUEBA'), findsOneWidget);
    app.api = ApiService();
  });
  test('operaciones pendientes se aíslan por cuenta y conservan su identificador al sincronizar', () async {
    SharedPreferences.setMockInitialValues({'last_session': jsonEncode({'tenant_id': 1, 'user_id': 1, 'access_token': 'prueba'}),
      'access_token': 'prueba', 'session_api_url': 'http://localhost/api/v1'});
    final adapter = ApiDePrueba();
    final servicio = ApiService(baseUrl: 'http://localhost/api/v1', adapter: adapter);
    final cola = OperacionesOffline(tenantId: 1, userId: 1, api: servicio);
    final otra = OperacionesOffline(tenantId: 1, userId: 2, api: servicio);
    final datos = {'tipo': 'venta', 'sucursal_id': 3, 'variante_id': 11, 'cantidad': 2,
      'precio_unitario': 80, 'monto_recibido': 160, 'fecha_hora_prueba': null,
      'fecha_local': '2026-11-07T10:00:00Z', 'nombre': 'Polera', 'sku': 'SKU', 'sucursal': 'Luna'};
    await cola.crear(datos, 2);
    final id = (await cola.listar()).single['uuid_operacion'];
    expect(await otra.listar(), isEmpty);
    await otra.crear(datos, 2);
    await expectLater(otra.sincronizar(), throwsStateError);
    expect((await otra.listar()).single['estado'], 'pendiente');
    await expectLater(cola.crear(datos, 2), throwsStateError);
    await expectLater(cola.quitar((await cola.listar()).single), throwsStateError);
    await cola.sincronizar();
    final op = (await cola.listar()).single;
    expect(op['uuid_operacion'], id);
    expect(op['estado'], 'confirmada');
    expect(op['codigo'], 'V-PRUEBA');
    await expectLater(cola.crear(datos, 2), throwsStateError);
    await expectLater(cola.quitar(op, sucursalCopia: 3), throwsStateError);
    await cola.registrarCopiaActualizada(3, {id as String});
    await cola.crear(datos, 2);
    await cola.sincronizar();
    expect(adapter.rutas.where((r) => r == '/offline/sincronizar').length, 2);
  });
  test('un conflicto queda visible y una falla de red conserva el pendiente', () async {
    SharedPreferences.setMockInitialValues({'last_session': jsonEncode({'tenant_id': 7, 'user_id': 9, 'access_token': 'prueba'}),
      'access_token': 'prueba', 'session_api_url': 'http://localhost/api/v1'});
    final adapter = ApiDePrueba()..codigoHttp = 409;
    final servicio = ApiService(baseUrl: 'http://localhost/api/v1', adapter: adapter);
    final cola = OperacionesOffline(tenantId: 7, userId: 9, api: servicio);
    final datos = {'tipo': 'venta', 'sucursal_id': 3, 'variante_id': 11, 'cantidad': 1,
      'precio_unitario': 80, 'monto_recibido': 80, 'fecha_hora_prueba': null,
      'fecha_local': '2026-11-07T10:00:00Z', 'nombre': 'Polera', 'sku': 'SKU', 'sucursal': 'Luna'};
    await cola.crear(datos, 3);
    await cola.sincronizar();
    expect((await cola.listar()).single['estado'], 'conflicto');
    expect((await cola.listar()).single['error'], 'Stock insuficiente');
    await cola.crear(datos, 3);
    adapter.codigoHttp = 503;
    await expectLater(cola.sincronizar(), throwsA(isA<DioException>()));
    expect((await cola.listar()).last['estado'], 'pendiente');
  });
  test('sincronizar y guardar simultáneamente no pierde operaciones de la misma cuenta', () async {
    SharedPreferences.setMockInitialValues({'last_session': jsonEncode({'tenant_id': 7, 'user_id': 9, 'access_token': 'prueba'}),
      'access_token': 'prueba', 'session_api_url': 'http://localhost/api/v1'});
    final adapter = ApiDePrueba();
    final servicio = ApiService(baseUrl: 'http://localhost/api/v1', adapter: adapter);
    final primera = OperacionesOffline(tenantId: 7, userId: 9, api: servicio);
    final segunda = OperacionesOffline(tenantId: 7, userId: 9, api: servicio);
    final datos = {'tipo': 'venta', 'sucursal_id': 3, 'variante_id': 11, 'cantidad': 1,
      'precio_unitario': 80, 'monto_recibido': 80, 'fecha_hora_prueba': null,
      'fecha_local': '2026-11-07T10:00:00Z', 'nombre': 'Polera', 'sku': 'SKU', 'sucursal': 'Luna'};
    await primera.crear(datos, 3);
    await Future.wait([primera.sincronizar(), segunda.crear(datos, 3)]);
    final guardadas = await primera.listar();
    expect(guardadas.length, 2);
    expect(guardadas.where((o) => o['estado'] == 'confirmada').length, 1);
    expect(guardadas.where((o) => o['estado'] == 'pendiente').length, 1);
  });
}

class ApiAcceso implements HttpClientAdapter {
  final rutas = <String>[];
  Map<String, dynamic> enviado = {};
  @override Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async {
    rutas.add(options.path);
    dynamic result;
    if (options.path == '/auth/super/login') {
      enviado = Map.from(options.data);
      result = {'access_token': 'prueba', 'kind': 'super', 'nombre': 'Super', 'user_id': 1, 'roles': ['superadmin']};
    } else if (options.path == '/auth/login') {
      enviado = Map.from(options.data);
      result = {'access_token': 'prueba', 'kind': 'tenant', 'tenant_id': 1, 'tenant_codigo': 'luna', 'user_id': 1, 'roles': ['cliente']};
    } else if (options.path == '/tenants') {
      result = [{'razon_social': 'Luna', 'codigo': 'luna', 'plan_actual': 'Plan de prueba'}];
    } else if (options.path == '/planes') {
      result = [{'nombre': 'Plan de prueba', 'max_sucursales': 2, 'max_usuarios': 10, 'precio_mensual': 99}];
    } else { result = []; }
    return ResponseBody.fromString(jsonEncode(result), 200, headers: {Headers.contentTypeHeader: ['application/json']});
  }
  @override void close({bool force = false}) {}
}

class ApiDePrueba implements HttpClientAdapter {
  final rutas = <String>[];
  int codigoHttp = 200;
  Map<String, dynamic> item = {}, reserva = {};
  @override Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async {
    rutas.add(options.path);
    dynamic result;
    if (options.path.endsWith('/tienda/carrito') && options.method == 'GET') { result = null; }
    else if (options.path.endsWith('/tienda/carrito/items')) { item = Map.from(options.data); result = {'unidades': 1}; }
    else if (options.path.endsWith('/tienda/reservas')) { reserva = Map.from(options.data); result = {'codigo': 'RES-PRUEBA'}; }
    else if (options.path.endsWith('/offline/sincronizar')) {
      if (codigoHttp != 200) return ResponseBody.fromString(jsonEncode({'detail': 'Stock insuficiente'}), codigoHttp,
        headers: {Headers.contentTypeHeader: ['application/json']});
      result = {'codigo': 'V-PRUEBA', 'confirmada_en': '2026-11-07T11:00:00Z'};
    }
    else { result = {}; }
    return ResponseBody.fromString(jsonEncode(result), 200, headers: {Headers.contentTypeHeader: ['application/json']});
  }
  @override void close({bool force = false}) {}
}
