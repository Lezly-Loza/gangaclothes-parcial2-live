import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';

class ProductoLocalDao {
  Future<Database> _db() async {
    final path = join(await getDatabasesPath(), 'gangaclothes.db');
    return openDatabase(path, version: 1, onCreate: (db, version) async {
      await db.execute('CREATE TABLE producto_local(id INTEGER PRIMARY KEY, nombre TEXT, precio_base REAL)');
      await db.execute('CREATE TABLE variante_local(id INTEGER PRIMARY KEY, producto_id INTEGER, sku TEXT, precio REAL, stock INTEGER)');
      await db.execute('CREATE TABLE estado_sincronizacion(clave TEXT PRIMARY KEY, valor TEXT)');
    });
  }

  Future<void> guardarCatalogoLocal(Map<String, dynamic> catalogo) async {
    if (kIsWeb) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('catalogo_local', jsonEncode(catalogo));
      return;
    }
    final db = await _db();
    await db.transaction((txn) async {
      for (final row in catalogo['productos'] as List<dynamic>) {
        final p = Map<String, dynamic>.from(row);
        await txn.insert('producto_local', {'id': p['id'], 'nombre': p['nombre'], 'precio_base': p['precio_base']},
            conflictAlgorithm: ConflictAlgorithm.replace);
      }
      for (final row in catalogo['variantes'] as List<dynamic>) {
        final v = Map<String, dynamic>.from(row);
        await txn.insert('variante_local', {'id': v['id'], 'producto_id': v['producto_id'],
          'sku': v['sku'], 'precio': v['precio'], 'stock': v['stock']}, conflictAlgorithm: ConflictAlgorithm.replace);
      }
      await txn.insert('estado_sincronizacion', {'clave':'fecha_descarga','valor':catalogo['fecha_descarga']},
          conflictAlgorithm: ConflictAlgorithm.replace);
    });
  }

  Future<int> contarProductos() async {
    if (kIsWeb) {
      final prefs = await SharedPreferences.getInstance();
      final data = prefs.getString('catalogo_local');
      return data == null ? 0 : (jsonDecode(data)['productos'] as List).length;
    }
    return Sqflite.firstIntValue(await (await _db()).rawQuery('SELECT COUNT(*) FROM producto_local')) ?? 0;
  }

  Future<String> fechaDescarga() async {
    if (kIsWeb) {
      final prefs = await SharedPreferences.getInstance();
      final data = prefs.getString('catalogo_local');
      return data == null ? '' : jsonDecode(data)['fecha_descarga'] as String;
    }
    final rows = await (await _db()).query('estado_sincronizacion', where:'clave=?', whereArgs:['fecha_descarga']);
    return rows.isEmpty ? '' : rows.first['valor'] as String;
  }
}
