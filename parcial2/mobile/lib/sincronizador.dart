import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'operaciones_offline.dart';

class Sincronizador extends ChangeNotifier with WidgetsBindingObserver {
  Sincronizador(this.cola, this.alResultado) {
    WidgetsBinding.instance.addObserver(this);
    _conexion = Connectivity().onConnectivityChanged.listen((estados) {
      if (estados.any((e) => e != ConnectivityResult.none)) sincronizar();
    });
    sincronizar();
  }
  final OperacionesOffline cola;
  final void Function(Map<String, dynamic>) alResultado;
  static const canal = MethodChannel('gangaclothes/notificaciones');
  late final StreamSubscription<List<ConnectivityResult>> _conexion;
  bool _trabajando = false, _cerrado = false, _reintentar = false;
  @override void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) sincronizar();
  }
  Future<void> sincronizar() async {
    if (_cerrado) return;
    if (_trabajando) { _reintentar = true; return; }
    _trabajando = true;
    try {
      final resultados = await cola.sincronizar(incluirConflictos: false);
      if (_cerrado) return;
      notifyListeners();
      for (final op in resultados) {
        alResultado(op);
        final tipo = op['tipo'] == 'reserva' ? 'Reserva' : 'Venta';
        final confirmada = op['estado'] == 'confirmada';
        try { await canal.invokeMethod('mostrar', {
          'titulo': '$tipo ${confirmada ? 'confirmada' : 'no confirmada'}',
          'texto': confirmada ? 'Código: ${op['codigo']}' : 'Revisa el conflicto en operaciones locales.',
        }); } on MissingPluginException { /* El resultado sigue en la app. */ }
          on PlatformException { /* Sin permiso, el resultado sigue en la app. */ }
      }
    } catch (_) { /* Conserva la cola para la próxima conexión o inicio. */ }
    finally {
      _trabajando = false;
      if (_reintentar && !_cerrado) { _reintentar = false; sincronizar(); }
    }
  }
  static Future<void> solicitarPermiso() async {
    try { await canal.invokeMethod('solicitarPermiso'); }
    on MissingPluginException { throw StateError('Los avisos del sistema están disponibles en Android.'); }
  }
  static Future<void> notificar(String titulo, String texto) async {
    try {
      await canal.invokeMethod('mostrar', {'titulo': titulo, 'texto': texto});
    } catch (_) {}
  }
  @override void dispose() {
    _cerrado = true; WidgetsBinding.instance.removeObserver(this); _conexion.cancel(); super.dispose();
  }
}
