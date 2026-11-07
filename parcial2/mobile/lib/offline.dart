import 'package:flutter/material.dart';
import 'api_service.dart';
import 'estilo.dart';
import 'main.dart' show api;
import 'producto_local_dao.dart';
import 'tienda.dart' show titulo;

class ModoOfflineScreen extends StatefulWidget {
  const ModoOfflineScreen({super.key, required this.sesion});
  final Map<String, dynamic> sesion;
  @override State<ModoOfflineScreen> createState() => _ModoOfflineScreenState();
}
class _ModoOfflineScreenState extends State<ModoOfflineScreen> {
  late ProductoLocalDao dao; Map<String, dynamic>? copia; List<Map<String, dynamic>> sucursales = [], categorias = [], temporadas = [];
  int? sucursal, categoria, temporada; bool ocupado = false; String error = '';
  @override void initState() { super.initState(); dao = ProductoLocalDao(tenantId: widget.sesion['tenant_id'] as int, userId: widget.sesion['user_id'] as int); abrirModoOffline(); opciones(); }
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
    try { final data = await api.descargarCatalogo({'sucursal_id': sucursal, if (categoria != null) 'categoria_id': categoria,
      if (temporada != null) 'temporada_id': temporada});
      data['sucursal_nombre'] = sucursales.firstWhere((s) => s['id'] == sucursal)['nombre'];
      await dao.guardarCatalogoLocal(data); await abrirModoOffline();
      if (mounted) aviso(context, 'Selección guardada en este dispositivo.');
    } catch (e) { if (mounted) setState(() => error = '${mensajeError(e)} La copia anterior se conserva.'); }
    finally { if (mounted) setState(() => ocupado = false); }
  }
  int mostrarDisponibles() => mapas(copia?['productos']).length;
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
        const Text('Precios y stock corresponden al momento de la descarga. No permite reservar ni comprar sin conexión.', style: TextStyle(color: Colors.black54)),
        const SizedBox(height: 10), for (final p in productos) Card(child: ListTile(title: Text('${p['nombre']}'),
          subtitle: Text('${variantes.where((v) => v['producto_id'] == p['id']).fold<int>(0, (n, v) => n + ((v['stock'] as num?)?.toInt() ?? 0))} disponibles al descargar'),
          trailing: Text(bs(p['precio_base']), style: const TextStyle(color: rosa, fontWeight: FontWeight.bold)))),
      ] else vacio('Todavía no hay una copia descargada para esta cuenta.')]);
  }
}
