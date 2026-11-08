import 'dart:convert';
import 'dart:async';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import 'api_service.dart';

bool ocupaCopia(Map<String, dynamic> op) => op['estado'] != 'confirmada' || op['incluida_en_copia'] != true;

class OperacionesOffline {
  OperacionesOffline({required this.tenantId, required this.userId, required this.api});
  final int tenantId, userId;
  final ApiService api;
  String get clave => 'operaciones_offline_${tenantId}_$userId';
  static final Map<String, Future<void>> _turnos = {};
  Future<T> _exclusivo<T>(Future<T> Function() accion) async {
    final anterior = _turnos[clave] ?? Future<void>.value();
    final fin = Completer<void>(); _turnos[clave] = fin.future;
    try { await anterior; return await accion(); }
    finally { fin.complete(); if (identical(_turnos[clave], fin.future)) _turnos.remove(clave); }
  }
  Future<List<Map<String, dynamic>>> listar() async {
    final texto = (await SharedPreferences.getInstance()).getString(clave);
    if (texto == null) return [];
    return (jsonDecode(texto) as List).map((v) => Map<String, dynamic>.from(v)).toList();
  }
  Future<void> _guardar(List<Map<String, dynamic>> filas) async {
    if (!await (await SharedPreferences.getInstance()).setString(clave, jsonEncode(filas))) throw StateError('No se pudo guardar');
  }
  Future<void> crear(Map<String, dynamic> datos, int stockCopia) => _exclusivo(() async {
    final filas = await listar();
    final usados = filas.where((o) => o['sucursal_id'] == datos['sucursal_id'] && o['variante_id'] == datos['variante_id'] && ocupaCopia(o))
        .fold<int>(0, (s, o) => s + (o['cantidad'] as int));
    final cantidad = datos['cantidad'] as int;
    if (cantidad < 1 || cantidad > stockCopia - usados) throw StateError('Cantidad mayor al stock de la copia, descontando pendientes.');
    filas.add({...datos, 'uuid_operacion': const Uuid().v4(), 'estado': 'pendiente', 'error': null, 'codigo': null});
    await _guardar(filas);
  });
  Future<void> registrarCopiaActualizada(int sucursalId, Set<String> confirmadasAntes) => _exclusivo(() async {
    final filas = await listar();
    for (var i = 0; i < filas.length; i++) {
      final op = filas[i];
      if (op['estado'] == 'confirmada' && op['sucursal_id'] == sucursalId && confirmadasAntes.contains(op['uuid_operacion'])) {
        filas[i] = {...op, 'incluida_en_copia': true};
      }
    }
    await _guardar(filas);
  });
  Future<List<Map<String, dynamic>>> sincronizar({bool incluirConflictos = true}) => _exclusivo(() async {
    final sesion = await api.sesionGuardada();
    if (sesion == null || sesion['tenant_id'] != tenantId || sesion['user_id'] != userId || sesion['access_token'] is! String) {
      throw StateError('Vuelve a iniciar sesión con la cuenta que registró estas operaciones.');
    }
    final token = sesion['access_token'] as String;
    final filas = await listar();
    final resultados = <Map<String, dynamic>>[];
    for (var i = 0; i < filas.length; i++) {
      final op = filas[i];
      if (op['estado'] == 'confirmada') continue;
      if (op['estado'] == 'conflicto' && !incluirConflictos) continue;
      final datos = <String, dynamic>{for (final k in ['uuid_operacion', 'tipo', 'sucursal_id', 'variante_id', 'cantidad',
        'precio_unitario', 'monto_recibido', 'fecha_hora_prueba', 'fecha_local']) k: op[k]};
      try {
        final r = Map<String, dynamic>.from(await api.postConToken('/offline/sincronizar', datos, token));
        filas[i] = {...op, 'estado': 'confirmada', 'error': null, 'codigo': r['codigo'], 'confirmada_en': r['confirmada_en']};
      } on DioException catch (e) {
        if ([403, 409, 422].contains(e.response?.statusCode)) {
          final detalle = e.response?.data;
          filas[i] = {...op, 'estado': 'conflicto', 'error': detalle is Map && detalle['detail'] is String ? detalle['detail'] : 'Revisa los datos.'};
        } else { await _guardar(filas); rethrow; }
      }
      await _guardar(filas);
      if (op['estado'] != filas[i]['estado']) resultados.add(filas[i]);
    }
    return resultados;
  });
  Future<void> quitar(Map<String, dynamic> op, {int? sucursalCopia}) => _exclusivo(() async {
    if (op['estado'] == 'pendiente') throw StateError('Sincroniza primero: el resultado podría ser incierto.');
    if (op['estado'] == 'confirmada' && op['sucursal_id'] == sucursalCopia && ocupaCopia(op)) {
      throw StateError('Descarga el catálogo de nuevo antes de quitar este resultado para conservar el stock local correcto.');
    }
    final filas = await listar(); filas.removeWhere((o) => o['uuid_operacion'] == op['uuid_operacion']); await _guardar(filas);
  });
}
