import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

String _direccion() {
  const configurada = String.fromEnvironment('API_URL');
  if (configurada.isNotEmpty) return configurada;
  return kIsWeb || defaultTargetPlatform != TargetPlatform.android
      ? 'http://127.0.0.1:8000/api/v1' : 'http://10.0.2.2:8000/api/v1';
}
class ApiService {
  ApiService({String? baseUrl, HttpClientAdapter? adapter}) : _dio = Dio(BaseOptions(
    baseUrl: baseUrl ?? _direccion(), connectTimeout: const Duration(seconds: 12),
    receiveTimeout: const Duration(seconds: 20),
  )) {
    if (adapter != null) _dio.httpClientAdapter = adapter;
    _dio.interceptors.add(InterceptorsWrapper(onRequest: (options, handler) async {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('access_token');
      if (token != null && !options.headers.containsKey('Authorization')) options.headers['Authorization'] = 'Bearer $token';
      handler.next(options);
    }));
  }
  final Dio _dio;
  Future<Map<String, dynamic>> _saveSession(dynamic value) async {
    final result = Map<String, dynamic>.from(value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', result['access_token'] as String);
    await prefs.setString('last_session', jsonEncode(result));
    return result;
  }
  Future<Map<String, dynamic>> login(Map<String, dynamic> dto) async => _saveSession((await _dio.post('/auth/login', data: dto)).data);
  Future<Map<String, dynamic>> loginSuper(Map<String, dynamic> dto) async => _saveSession((await _dio.post('/auth/super/login', data: dto)).data);
  Future<Map<String, dynamic>> registrar(Map<String, dynamic> dto) async => _saveSession((await _dio.post('/auth/register', data: dto)).data);
  Future<Map<String, dynamic>?> sesionGuardada() async {
    final raw = (await SharedPreferences.getInstance()).getString('last_session');
    if (raw == null) return null;
    try { return Map<String, dynamic>.from(jsonDecode(raw)); } catch (_) { return null; }
  }
  Future<void> salir() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token'); await prefs.remove('last_session');
  }
  Future<dynamic> get(String path, [Map<String, dynamic>? params]) async => (await _dio.get(path, queryParameters: params)).data;
  Future<dynamic> post(String path, [Map<String, dynamic>? data]) async => (await _dio.post(path, data: data ?? {})).data;
  Future<dynamic> postConToken(String path, Map<String, dynamic> data, String token) async =>
      (await _dio.post(path, data: data, options: Options(headers: {'Authorization': 'Bearer $token'}))).data;
  Future<dynamic> put(String path, Map<String, dynamic> data) async => (await _dio.put(path, data: data)).data;
  Future<dynamic> patch(String path, Map<String, dynamic> data) async => (await _dio.patch(path, data: data)).data;
  Future<dynamic> delete(String path) async => (await _dio.delete(path)).data;
  Future<List<dynamic>> buscarClientes(String q) async => List.from(await get('/clientes', {'q': q}));
  Future<Map<String, dynamic>> crearCliente(Map<String, dynamic> dto) async => Map.from(await post('/clientes', dto));
  Future<Map<String, dynamic>> crearReserva(Map<String, dynamic> dto) async => Map.from(await post('/tienda/reservas', dto));
  Future<Map<String, dynamic>> registrarVenta(Map<String, dynamic> dto) async => Map.from(await post('/ventas', dto));
  Future<Map<String, dynamic>> anular(int id, String motivo) async => Map.from(await post('/ventas/$id/anular', {'motivo': motivo}));
  Future<Map<String, dynamic>> descargarCatalogo(Map<String, dynamic> filtros) async => Map.from(await get('/offline/catalogo', filtros));
}

String mensajeError(Object error) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) return data['detail'] as String;
    if (error.response?.statusCode == 401) return 'La sesión venció. Vuelve a iniciar sesión.';
    if (error.response?.statusCode == 403) return 'Tu cuenta no tiene permiso para esta acción.';
    if (error.response != null) return 'No se pudo completar la operación. Revisa los datos.';
    return 'No se pudo conectar. Comprueba la conexión y la dirección del servidor.';
  }
  return 'No se pudo completar la operación. Inténtalo de nuevo.';
}
