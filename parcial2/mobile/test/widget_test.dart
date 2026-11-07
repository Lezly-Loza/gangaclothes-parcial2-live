import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gangaclothes_mobile/main.dart';
import 'package:gangaclothes_mobile/main.dart' as app;
import 'package:gangaclothes_mobile/api_service.dart';
import 'package:gangaclothes_mobile/producto_local_dao.dart';
import 'package:gangaclothes_mobile/tienda.dart';
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
    expect(find.text('Contraseña'), findsOneWidget);
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
}

class ApiDePrueba implements HttpClientAdapter {
  final rutas = <String>[];
  Map<String, dynamic> item = {}, reserva = {};
  @override Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async {
    rutas.add(options.path);
    dynamic result;
    if (options.path.endsWith('/tienda/carrito') && options.method == 'GET') { result = null; }
    else if (options.path.endsWith('/tienda/carrito/items')) { item = Map.from(options.data); result = {'unidades': 1}; }
    else if (options.path.endsWith('/tienda/reservas')) { reserva = Map.from(options.data); result = {'codigo': 'RES-PRUEBA'}; }
    else { result = {}; }
    return ResponseBody.fromString(jsonEncode(result), 200, headers: {Headers.contentTypeHeader: ['application/json']});
  }
  @override void close({bool force = false}) {}
}
