import 'package:flutter/material.dart';
import 'api_service.dart';
import 'estilo.dart';
import 'main.dart' show api;
import 'producto_local_dao.dart';
import 'operaciones_offline.dart';
import 'sincronizador.dart';
import 'tienda.dart' show titulo, campoTienda;

class ModoOfflineScreen extends StatefulWidget {
  const ModoOfflineScreen({super.key, required this.sesion, required this.sincronizador});
  final Map<String, dynamic> sesion;
  final Sincronizador sincronizador;
  @override State<ModoOfflineScreen> createState() => _ModoOfflineScreenState();
}
class _ModoOfflineScreenState extends State<ModoOfflineScreen> {
  late ProductoLocalDao dao; late OperacionesOffline cola; Map<String, dynamic>? copia; List<Map<String, dynamic>> sucursales = [], categorias = [], temporadas = [], operaciones = [];
  int? sucursal, categoria, temporada; bool ocupado = false; String error = '';
  int? varianteId; final cantidad = TextEditingController(text: '1'), recibido = TextEditingController();
  DateTime cita = DateTime.now().add(const Duration(days: 1)); String tipo = 'reserva';
  bool get esCliente => (widget.sesion['roles'] as List).contains('cliente') && (widget.sesion['permisos'] as List).contains('reservas:crear');
  bool get esPersonal => (widget.sesion['roles'] as List).any((r) => r != 'cliente' && r != 'proveedor') && (widget.sesion['permisos'] as List).contains('ventas:crear');
  @override void initState() { super.initState(); dao = ProductoLocalDao(tenantId: widget.sesion['tenant_id'] as int, userId: widget.sesion['user_id'] as int);
    cola = OperacionesOffline(tenantId: widget.sesion['tenant_id'] as int, userId: widget.sesion['user_id'] as int, api: api);
    widget.sincronizador.addListener(_actualizar); if (!esCliente) tipo = 'venta'; abrirModoOffline(); cargarOperaciones(); opciones(); }
  void _actualizar() { cargarOperaciones(); }
  @override void dispose() { widget.sincronizador.removeListener(_actualizar); cantidad.dispose(); recibido.dispose(); super.dispose(); }
  Future<void> abrirModoOffline() async { final r = await dao.leerCatalogo(); if (mounted) setState(() => copia = r); }
  Future<void> opciones() async {
    try { final r = await Future.wait([api.get('/sucursales'), api.get('/offline/opciones')]); final op = mapa(r[1]);
      if (mounted) setState(() { sucursales = mapas(r[0]).where((s) => s['activo'] != false).toList();
        categorias = mapas(op['categorias']); temporadas = mapas(op['temporadas']); sucursal = sucursales.firstOrNull?['id'] as int?; });
    } catch (e) { if (mounted) setState(() => error = 'Sin conexión: puedes consultar la última copia guardada.'); }
  }
  Future<void> prepararOffline() async {
    if (sucursal == null) { aviso(context, 'Selecciona una sucursal con conexión.'); return; }
    setState(() { ocupado = true; error = ''; });
    try { final confirmadasAntes = (await cola.listar()).where((o) => o['estado'] == 'confirmada').map((o) => o['uuid_operacion'] as String).toSet();
      final data = await api.descargarCatalogo({'sucursal_id': sucursal, if (categoria != null) 'categoria_id': categoria,
      if (temporada != null) 'temporada_id': temporada});
      data['sucursal_nombre'] = sucursales.firstWhere((s) => s['id'] == sucursal)['nombre']; data['sucursal_id'] = sucursal;
      await dao.guardarCatalogoLocal(data); await cola.registrarCopiaActualizada(sucursal!, confirmadasAntes); await cargarOperaciones(); varianteId = null; await abrirModoOffline();
      if (mounted) aviso(context, 'Selección guardada en este dispositivo.');
    } catch (e) { if (mounted) setState(() => error = '${mensajeError(e)} La copia anterior se conserva.'); }
    finally { if (mounted) setState(() => ocupado = false); }
  }
  int mostrarDisponibles() => mapas(copia?['productos']).length;
  Future<void> cargarOperaciones() async { final filas = await cola.listar(); if (mounted) setState(() => operaciones = filas); }
  int disponible(Map<String, dynamic> v) {
    final usados = operaciones.where((o) => o['sucursal_id'] == copia?['sucursal_id'] && o['variante_id'] == v['id'] && ocupaCopia(o))
        .fold<int>(0, (s, o) => s + (o['cantidad'] as int));
    return ((v['stock'] as int) - usados).clamp(0, 999999);
  }
  Future<void> elegirCita() async {
    final ahora = DateTime.now(); final d = await showDatePicker(context: context, initialDate: cita.isBefore(ahora) ? ahora : cita,
      firstDate: ahora, lastDate: ahora.add(const Duration(days: 365)));
    if (d == null || !mounted) return;
    final h = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(cita));
    if (h != null && mounted) setState(() => cita = DateTime(d.year, d.month, d.day, h.hour, h.minute));
  }
  Future<void> registrarLocal() async {
    if (ocupado) return;
    final v = mapas(copia?['variantes']).where((v) => v['id'] == varianteId).firstOrNull;
    final cantidadValor = int.tryParse(cantidad.text); final monto = double.tryParse(recibido.text);
    if (v == null || cantidadValor == null || cantidadValor < 1 || cantidadValor > 100 || copia?['sucursal_id'] == null) { aviso(context, 'Elige una variante y una cantidad entre 1 y 100.'); return; }
    if (tipo == 'reserva' && (!esCliente || !cita.isAfter(DateTime.now()))) { aviso(context, 'Elige una cita futura con una cuenta de cliente.'); return; }
    if (tipo == 'venta' && (!esPersonal || monto == null || !monto.isFinite || monto < (v['precio'] as num) * cantidadValor || (monto * 100 - (monto * 100).round()).abs() > 0.00001)) { aviso(context, 'El efectivo debe cubrir el total y tener hasta dos decimales.'); return; }
    setState(() { ocupado = true; error = ''; });
    try {
      final producto = mapas(copia?['productos']).where((p) => p['id'] == v['producto_id']).firstOrNull;
      await cola.crear({'tipo': tipo, 'sucursal_id': copia!['sucursal_id'], 'variante_id': v['id'], 'cantidad': cantidadValor,
        'precio_unitario': v['precio'], 'monto_recibido': tipo == 'venta' ? monto : null,
        'fecha_hora_prueba': tipo == 'reserva' ? cita.toIso8601String() : null, 'fecha_local': DateTime.now().toUtc().toIso8601String(),
        'nombre': producto?['nombre'] ?? 'Prenda', 'sku': v['sku'], 'sucursal': copia?['sucursal_nombre']}, v['stock'] as int);
      await cargarOperaciones(); if (mounted) aviso(context, 'Guardada localmente. Aún no está confirmada.');
    } on StateError catch (e) { if (mounted) aviso(context, e.message); }
    catch (e) { if (mounted) aviso(context, 'No se pudo guardar la operación.'); }
    finally { if (mounted) setState(() => ocupado = false); }
  }
  Future<void> sincronizar() async {
    if (ocupado) return; setState(() { ocupado = true; error = ''; });
    try { await cola.sincronizar(); await cargarOperaciones(); if (mounted) aviso(context, 'Revisa los estados y conflictos.'); }
    catch (e) { await cargarOperaciones(); if (mounted) setState(() => error = 'No se pudo conectar o la sesión venció. Las operaciones se conservan.'); }
    finally { if (mounted) setState(() => ocupado = false); }
  }
  Future<void> quitar(Map<String, dynamic> op) async {
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(title: const Text('Quitar operación'),
      content: Text(op['estado'] == 'conflicto' ? '¿Descartar? Si recibiste efectivo, resuélvelo con el cliente.' : '¿Quitar este resultado del historial local?'),
      actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Volver')),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Quitar'))]));
    if (ok == true) { try { await cola.quitar(op, sucursalCopia: copia?['sucursal_id'] as int?); await cargarOperaciones(); }
      on StateError catch (e) { if (mounted) aviso(context, e.message); } catch (_) { if (mounted) aviso(context, 'No se pudo quitar.'); } }
  }
  @override Widget build(BuildContext context) {
    final productos = mapas(copia?['productos']); final variantes = mapas(copia?['variantes']);
    return ListView(padding: const EdgeInsets.all(18), children: [titulo('Catálogo sin conexión'),
      const Text('Descarga una selección para consultar prendas y existencias sin internet.'), const SizedBox(height: 15),
      if (sucursales.isNotEmpty) ...[
        DropdownButtonFormField<int>(initialValue: sucursal, decoration: const InputDecoration(labelText: 'Sucursal'),
          items: sucursales.map((s) => DropdownMenuItem<int>(value: s['id'] as int, child: Text('${s['nombre']}'))).toList(), onChanged: (v) => setState(() => sucursal = v)),
        const SizedBox(height: 10), DropdownButtonFormField<int>(initialValue: categoria, decoration: const InputDecoration(labelText: 'Categoría'),
          items: [const DropdownMenuItem<int>(value: null, child: Text('Todas')), ...categorias.map((s) => DropdownMenuItem<int>(value: s['id'] as int, child: Text('${s['nombre']}')))],
          onChanged: (v) => setState(() => categoria = v)), const SizedBox(height: 10),
        DropdownButtonFormField<int>(initialValue: temporada, decoration: const InputDecoration(labelText: 'Temporada'),
          items: [const DropdownMenuItem<int>(value: null, child: Text('Todas')), ...temporadas.map((s) => DropdownMenuItem<int>(value: s['id'] as int, child: Text('${s['nombre']}')))],
          onChanged: (v) => setState(() => temporada = v)), const SizedBox(height: 10),
        FilledButton.icon(onPressed: ocupado ? null : prepararOffline, icon: const Icon(Icons.download), label: Text(ocupado ? 'Descargando…' : 'Descargar selección')),
      ] else TextButton(onPressed: opciones, child: const Text('Reintentar conexión')),
      if (error.isNotEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 10), child: Text(error, style: const TextStyle(color: Colors.deepOrange))),
      const SizedBox(height: 16), if (copia != null) ...[
        Text('${mostrarDisponibles()} prendas guardadas · ${copia?['sucursal_nombre'] ?? 'Sucursal'}', style: const TextStyle(fontWeight: FontWeight.w900)),
        Text('Descarga: ${fecha(copia?['fecha_descarga'])}'),
        const Text('Precios y stock corresponden al momento de la descarga. Las operaciones se confirman al sincronizar.', style: TextStyle(color: Colors.black54)),
        const SizedBox(height: 10), for (final p in productos) Card(child: ListTile(title: Text('${p['nombre']}'),
          subtitle: Text('${variantes.where((v) => v['producto_id'] == p['id']).fold<int>(0, (n, v) => n + ((v['stock'] as num?)?.toInt() ?? 0))} disponibles al descargar'),
          trailing: Text(bs(p['precio_base']), style: const TextStyle(color: rosa, fontWeight: FontWeight.bold)))),
        const SizedBox(height: 20), const Text('Registrar operación local', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),
        if (copia?['sucursal_id'] == null) const Text('Descarga otra vez la selección para registrar operaciones.') else ...[
          DropdownButtonFormField<String>(initialValue: tipo, decoration: const InputDecoration(labelText: 'Operación'), items: [
            if (esCliente) const DropdownMenuItem(value: 'reserva', child: Text('Reserva')),
            if (esPersonal) const DropdownMenuItem(value: 'venta', child: Text('Venta de contado'))],
            onChanged: (v) { if (v != null) setState(() => tipo = v); }), const SizedBox(height: 10),
          DropdownButtonFormField<int>(key: ValueKey('${copia?['fecha_descarga']}'), initialValue: varianteId,
            decoration: const InputDecoration(labelText: 'Variante'), items: variantes.map((v) => DropdownMenuItem<int>(value: v['id'] as int,
              child: Text('${v['sku']} · ${bs(v['precio'])} · ${disponible(v)} disponibles', overflow: TextOverflow.ellipsis))).toList(),
            onChanged: (v) => setState(() => varianteId = v)), const SizedBox(height: 10),
          campoTienda('Cantidad', cantidad, numero: true),
          if (tipo == 'reserva') OutlinedButton(onPressed: elegirCita, child: Text('Visita: ${fecha(cita.toIso8601String())}')),
          if (tipo == 'venta') ...[campoTienda('Efectivo recibido', recibido, numero: true),
            const Text('Registra solo efectivo realmente recibido. Si cambia el stock o precio, deberás revisar el conflicto.')],
          FilledButton(onPressed: ocupado || varianteId == null ? null : registrarLocal, child: const Text('Guardar operación pendiente')),
        ],
      ] else vacio('Todavía no hay una copia descargada para esta cuenta.'),
      const SizedBox(height: 20), const Text('Operaciones locales', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w900)),
      const Text('La app intenta sincronizar al recuperar internet o al abrirla de nuevo.'),
      TextButton.icon(onPressed: () async {
        try {
          await Sincronizador.solicitarPermiso();
          await Sincronizador.notificar(
            'GangaClothes: Avisos Activados',
            'Recibirás notificaciones al confirmar ventas y reservas.',
          );
          if (context.mounted) aviso(context, '¡Avisos activados y notificación de prueba enviada!');
        } catch (_) {
          if (context.mounted) aviso(context, 'Los avisos del sistema están disponibles en Android.');
        }
      },
      icon: const Icon(Icons.notifications_active_outlined), label: const Text('Activar y probar avisos en Android')),
      FilledButton(onPressed: ocupado || operaciones.isEmpty ? null : sincronizar, child: const Text('Sincronizar pendientes')),
      if (operaciones.isEmpty) vacio('No hay operaciones guardadas.'),
      for (final op in operaciones) Card(child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${op['tipo']} · ${op['nombre']} · ${op['sku']}', style: const TextStyle(fontWeight: FontWeight.bold)),
        Text('${op['cantidad']} × ${bs(op['precio_unitario'])} · ${op['estado'] == 'pendiente' ? 'Pendiente: aún no confirmada' : op['estado'] == 'conflicto' ? 'No confirmada' : 'Confirmada'}'),
        if (op['codigo'] != null) Text('Código: ${op['codigo']}'),
        if (op['error'] != null) Text('${op['error']}', style: const TextStyle(color: Colors.deepOrange)),
        if (op['estado'] == 'conflicto') const Text('Revisa el stock y precio. Puedes descartar y crear otra operación con datos actualizados.'),
        if (op['estado'] != 'pendiente') TextButton(onPressed: ocupado ? null : () => quitar(op), child: Text(op['estado'] == 'conflicto' ? 'Descartar conflicto' : 'Quitar del historial')),
      ])))]);
  }
}
