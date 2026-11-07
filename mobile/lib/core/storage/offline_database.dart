// ============================================================================
// CU-19 & CU-20: Almacenamiento Local Offline con SQLite (Flutter / Mobile)
//
// Patrón Arquitectónico ICONIX:
//   Boundary: ReservasScreen / CatalogoScreen (UI con badge y banner offline)
//   Controller: OfflineSyncController (Manejo de estado LOCAL -> CONFIRMADA)
//   Entity: OfflineDatabase & Tablas Locales (SQLite)
// ============================================================================

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// Estados de una operación local offline (regla arquitectónica crítica)
enum EstadoOperacionLocal {
  local,
  enviada,
  confirmada,
  rechazada,
  enConflicto,
}

extension EstadoOperacionExtension on EstadoOperacionLocal {
  String get valor {
    switch (this) {
      case EstadoOperacionLocal.local:
        return 'LOCAL';
      case EstadoOperacionLocal.enviada:
        return 'ENVIADA';
      case EstadoOperacionLocal.confirmada:
        return 'CONFIRMADA';
      case EstadoOperacionLocal.rechazada:
        return 'RECHAZADA';
      case EstadoOperacionLocal.enConflicto:
        return 'EN_CONFLICTO';
    }
  }

  static EstadoOperacionLocal desdeString(String str) {
    switch (str.toUpperCase()) {
      case 'ENVIADA':
        return EstadoOperacionLocal.enviada;
      case 'CONFIRMADA':
        return EstadoOperacionLocal.confirmada;
      case 'RECHAZADA':
        return EstadoOperacionLocal.rechazada;
      case 'EN_CONFLICTO':
        return EstadoOperacionLocal.enConflicto;
      case 'LOCAL':
      default:
        return EstadoOperacionLocal.local;
    }
  }
}

/// Registro en la bitácora local de operaciones pendientes
class OperacionPendienteLocal {
  final String uuidOperacion;
  final String tipo; // 'RESERVA'
  final Map<String, dynamic> payload;
  final String fechaCreacion;
  EstadoOperacionLocal estado;
  int reintentos;
  String? errorDetalle;

  OperacionPendienteLocal({
    required this.uuidOperacion,
    required this.tipo,
    required this.payload,
    required this.fechaCreacion,
    this.estado = EstadoOperacionLocal.local,
    this.reintentos = 0,
    this.errorDetalle,
  });

  Map<String, dynamic> toMap() => {
        'uuid_operacion': uuidOperacion,
        'tipo': tipo,
        'payload': jsonEncode(payload),
        'fecha_creacion': fechaCreacion,
        'estado': estado.valor,
        'reintentos': reintentos,
        'error_detalle': errorDetalle,
      };

  factory OperacionPendienteLocal.fromMap(Map<String, dynamic> map) =>
      OperacionPendienteLocal(
        uuidOperacion: map['uuid_operacion'] as String,
        tipo: map['tipo'] as String,
        payload: jsonDecode(map['payload'] as String) as Map<String, dynamic>,
        fechaCreacion: map['fecha_creacion'] as String,
        estado: EstadoOperacionExtension.desdeString(map['estado'] as String),
        reintentos: (map['reintentos'] as int?) ?? 0,
        errorDetalle: map['error_detalle'] as String?,
      );
}

/// Manejador de persistencia local offline para Flutter.
/// Compatible con SQLite / sqflite o SharedPreferences en ausencia de plugin nativo.
class OfflineStorageService {
  static const String _keyProductos = 'offline_productos_local';
  static const String _keyVariantes = 'offline_variantes_local';
  static const String _keyReservas = 'offline_reservas_local';
  static const String _keyOperaciones = 'offline_operaciones_pendientes';
  static const String _keyUltimaDescarga = 'offline_ultima_descarga';

  // ------------------------------------------------------------- CU-19: Catálogo
  /// Guarda el catálogo en almacenamiento local junto con la fecha de descarga.
  Future<void> guardarCatalogoLocal(
      List<Map<String, dynamic>> productos,
      List<Map<String, dynamic>> variantes) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyProductos, jsonEncode(productos));
    await prefs.setString(_keyVariantes, jsonEncode(variantes));
    await prefs.setString(_keyUltimaDescarga, DateTime.now().toIso8601String());
  }

  /// Lee productos del catálogo local offline.
  Future<List<Map<String, dynamic>>> obtenerProductosLocales() async {
    final prefs = await SharedPreferences.getInstance();
    final data = prefs.getString(_keyProductos);
    if (data == null) return [];
    final list = jsonDecode(data) as List;
    return list.cast<Map<String, dynamic>>();
  }

  /// Retorna la fecha de la última sincronización del catálogo.
  Future<String?> obtenerFechaUltimaDescarga() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyUltimaDescarga);
  }

  // ------------------------------------------------------------- CU-20: Reserva
  /// Registra una reserva localmente sin conexión con UUIDv4.
  /// Estado inicial: LOCAL. Jamás se borra al enviarse.
  Future<void> registrarReservaLocal({
    required String uuidOperacion,
    required int varianteId,
    required int sucursalId,
    required int clienteId,
    required int cantidad,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final ahora = DateTime.now().toIso8601String();

    // 1. Guardar en reservas_local
    final reservas = await _leerLista(prefs, _keyReservas);
    reservas.add({
      'uuid_operacion': uuidOperacion,
      'variante_id': varianteId,
      'sucursal_id': sucursalId,
      'cliente_id': clienteId,
      'cantidad': cantidad,
      'codigo': 'OFF-${uuidOperacion.substring(0, 6).toUpperCase()}',
      'estado': 'PENDIENTE_SYNC',
      'fecha_creacion': ahora,
    });
    await prefs.setString(_keyReservas, jsonEncode(reservas));

    // 2. Registrar en cola de operaciones_pendientes con estado LOCAL
    final op = OperacionPendienteLocal(
      uuidOperacion: uuidOperacion,
      tipo: 'RESERVA',
      payload: {
        'uuid_operacion': uuidOperacion,
        'variante_id': varianteId,
        'sucursal_id': sucursalId,
        'cliente_id': clienteId,
        'cantidad': cantidad,
      },
      fechaCreacion: ahora,
      estado: EstadoOperacionLocal.local,
    );

    final ops = await _leerOperaciones(prefs);
    ops.add(op);
    await _guardarOperaciones(prefs, ops);
  }

  /// Transiciona el estado de una operación local (p.ej. de LOCAL a ENVIADA o CONFIRMADA)
  Future<void> actualizarEstadoOperacion(
    String uuidOperacion,
    EstadoOperacionLocal nuevoEstado, {
    String? errorDetalle,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final ops = await _leerOperaciones(prefs);
    for (final op in ops) {
      if (op.uuidOperacion == uuidOperacion) {
        op.estado = nuevoEstado;
        if (errorDetalle != null) {
          op.errorDetalle = errorDetalle;
        }
        break;
      }
    }
    await _guardarOperaciones(prefs, ops);
  }

  /// Retorna las operaciones que aún no están confirmadas
  Future<List<OperacionPendienteLocal>> obtenerOperacionesPendientes() async {
    final prefs = await SharedPreferences.getInstance();
    final ops = await _leerOperaciones(prefs);
    return ops
        .where((o) =>
            o.estado == EstadoOperacionLocal.local ||
            o.estado == EstadoOperacionLocal.enviada)
        .toList();
  }

  // ------------------------------------------------------------- helpers
  Future<List<Map<String, dynamic>>> _leerLista(
      SharedPreferences prefs, String key) async {
    final raw = prefs.getString(key);
    if (raw == null) return [];
    return (jsonDecode(raw) as List).cast<Map<String, dynamic>>();
  }

  Future<List<OperacionPendienteLocal>> _leerOperaciones(
      SharedPreferences prefs) async {
    final raw = prefs.getString(_keyOperaciones);
    if (raw == null) return [];
    final list = jsonDecode(raw) as List;
    return list
        .map((item) => OperacionPendienteLocal.fromMap(
            Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  Future<void> _guardarOperaciones(
      SharedPreferences prefs, List<OperacionPendienteLocal> ops) async {
    final list = ops.map((o) => o.toMap()).toList();
    await prefs.setString(_keyOperaciones, jsonEncode(list));
  }
}

