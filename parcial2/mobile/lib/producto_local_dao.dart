import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// Una copia completa por cuenta y empresa; reemplazarla no mezcla selecciones.
class ProductoLocalDao {
  ProductoLocalDao({required this.tenantId, required this.userId});
  final int tenantId;
  final int userId;
  String get _clave => 'catalogo_local_${tenantId}_$userId';
  Future<void> guardarCatalogoLocal(Map<String, dynamic> catalogo) async {
    final texto = jsonEncode(catalogo);
    if (!await (await SharedPreferences.getInstance()).setString(_clave, texto)) {
      throw StateError('No se pudo guardar el catálogo');
    }
  }
  Future<Map<String, dynamic>?> leerCatalogo() async {
    final valor = (await SharedPreferences.getInstance()).getString(_clave);
    if (valor == null) return null;
    try { return Map<String, dynamic>.from(jsonDecode(valor)); } catch (_) { return null; }
  }
  Future<int> contarProductos() async => ((await leerCatalogo())?['productos'] as List?)?.length ?? 0;
  Future<String> fechaDescarga() async => (await leerCatalogo())?['fecha_descarga']?.toString() ?? '';
}
