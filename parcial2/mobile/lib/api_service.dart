import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  ApiService({String? baseUrl})
      : _dio = Dio(BaseOptions(baseUrl: baseUrl ??
          (kIsWeb ? 'http://127.0.0.1:8000/api/v1' : 'http://10.0.2.2:8000/api/v1'))) {
    _dio.interceptors.add(InterceptorsWrapper(onRequest: (options, handler) async {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('access_token');
      if (token != null) options.headers['Authorization'] = 'Bearer $token';
      handler.next(options);
    }));
  }

  final Dio _dio;

  Future<Map<String, dynamic>> login(Map<String, dynamic> dto) async {
    final response = await _dio.post('/auth/login', data: dto);
    final result = Map<String, dynamic>.from(response.data);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', result['access_token'] as String);
    await prefs.setString('last_session', jsonEncode(result));
    return result;
  }

  Future<List<dynamic>> buscarClientes(String q) async =>
      List<dynamic>.from((await _dio.get('/clientes', queryParameters: {'q': q})).data);

  Future<Map<String, dynamic>> crearCliente(Map<String, dynamic> dto) async =>
      Map<String, dynamic>.from((await _dio.post('/clientes', data: dto)).data);

  Future<Map<String, dynamic>> crearReserva(Map<String, dynamic> dto) async =>
      Map<String, dynamic>.from((await _dio.post('/reservas', data: dto)).data);

  Future<Map<String, dynamic>> registrarVenta(Map<String, dynamic> dto) async =>
      Map<String, dynamic>.from((await _dio.post('/ventas', data: dto)).data);

  Future<Map<String, dynamic>> anular(int id, String motivo) async =>
      Map<String, dynamic>.from((await _dio.post('/ventas/$id/anular', data: {'motivo': motivo})).data);

  Future<Map<String, dynamic>> descargarCatalogo(Map<String, dynamic> filtros) async =>
      Map<String, dynamic>.from((await _dio.get('/offline/catalogo', queryParameters: filtros)).data);
}
