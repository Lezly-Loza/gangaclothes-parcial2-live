import 'package:flutter/material.dart';
import 'api_service.dart';
import 'estilo.dart';
import 'main.dart' show api;
import 'tienda.dart' show titulo, campoTienda;

class ClientesScreen extends StatefulWidget {
  const ClientesScreen({super.key, required this.permisos});
  final List<String> permisos;
  @override State<ClientesScreen> createState() => _ClientesScreenState();
}
class _ClientesScreenState extends State<ClientesScreen> {
  final q = TextEditingController(); List<Map<String, dynamic>> clientes = []; String error = ''; bool cargando = true; int version = 0;
  @override void initState() { super.initState(); buscarClientes(''); }
  @override void dispose() { q.dispose(); super.dispose(); }
  Future<void> buscarClientes(String termino) async { final actual = ++version;
    try { final rows = mapas(await api.buscarClientes(termino)); if (mounted && actual == version) setState(() { clientes = rows; error = ''; }); }
    catch (e) { if (mounted && actual == version) setState(() => error = mensajeError(e)); }
    finally { if (mounted && actual == version) setState(() => cargando = false); }
  }
  Future<void> crearCliente(Map<String, dynamic> datos) async { await api.crearCliente(datos); await buscarClientes(q.text); }
  Future<void> formulario([Map<String, dynamic>? cliente]) async {
    final nombre = TextEditingController(text: cliente?['nombre']?.toString() ?? '');
    final documento = TextEditingController(text: cliente?['documento']?.toString() ?? '');
    final correo = TextEditingController(text: cliente?['correo']?.toString() ?? '');
    final telefono = TextEditingController(text: cliente?['telefono']?.toString() ?? '');
    final datos = await showDialog<Map<String, dynamic>>(context: context, builder: (c) => AlertDialog(
      title: Text(cliente == null ? 'Nuevo cliente' : 'Editar cliente'), content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
        campoTienda('Nombre', nombre), campoTienda('Documento', documento), campoTienda('Correo (opcional)', correo), campoTienda('Teléfono (opcional)', telefono)])),
      actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('Cancelar')),
        FilledButton(onPressed: () { if (nombre.text.trim().isEmpty || documento.text.trim().isEmpty) { aviso(c, 'Nombre y documento son obligatorios.'); return; }
          Navigator.pop(c, {'nombre': nombre.text.trim(), 'documento': documento.text.trim(), 'correo': correo.text.trim().isEmpty ? null : correo.text.trim(),
            'telefono': telefono.text.trim().isEmpty ? null : telefono.text.trim()}); }, child: const Text('Guardar'))]));
    if (datos == null) return;
    try { if (cliente == null) { await crearCliente(datos); } else { await api.patch('/clientes/${cliente['id']}', datos); await buscarClientes(q.text); }
      if (mounted) aviso(context, 'Cliente guardado.'); }
    catch (e) { if (mounted) aviso(context, mensajeError(e)); }
  }
  @override Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(18), children: [
    Row(children: [Expanded(child: titulo('Clientes')), if (widget.permisos.contains('clientes:crear'))
      FilledButton.icon(onPressed: formulario, icon: const Icon(Icons.add), label: const Text('Nuevo'))]),
    TextField(controller: q, onChanged: buscarClientes, decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Nombre o documento')),
    const SizedBox(height: 15), if (cargando) const Center(child: CircularProgressIndicator()) else if (error.isNotEmpty)
      Column(children: [Text(error), TextButton(onPressed: () => buscarClientes(q.text), child: const Text('Reintentar'))])
    else if (clientes.isEmpty) vacio('No se encontraron clientes.') else ...clientes.map((c) => Card(child: ListTile(
      title: Text('${c['nombre']}', style: const TextStyle(fontWeight: FontWeight.bold)), subtitle: Text('${c['documento']} · ${c['correo'] ?? 'Sin correo'}'),
      trailing: widget.permisos.contains('clientes:editar') ? IconButton(tooltip: 'Editar', icon: const Icon(Icons.edit_outlined), onPressed: () => formulario(c)) : null)))]);
}

class AnularOperacionScreen extends StatefulWidget {
  const AnularOperacionScreen({super.key, required this.permisos});
  final List<String> permisos;
  @override State<AnularOperacionScreen> createState() => _AnularOperacionScreenState();
}
class _AnularOperacionScreenState extends State<AnularOperacionScreen> {
  String tipo = 'ventas', error = ''; List<Map<String, dynamic>> recientes = []; Map<String, dynamic>? operacion; bool ocupado = false;
  final codigo = TextEditingController(); final motivo = TextEditingController();
  @override void initState() { super.initState(); if (!widget.permisos.contains('ventas:anular')) tipo = 'reservas'; cargar(); }
  @override void dispose() { codigo.dispose(); motivo.dispose(); super.dispose(); }
  Future<void> cargar() async { setState(() { error = ''; operacion = null; });
    try { final r = mapas(await api.get('/operaciones/recientes', {'tipo': tipo})); if (mounted) setState(() => recientes = r); }
    catch (e) { if (mounted) setState(() => error = mensajeError(e)); }
  }
  Future<void> buscarOperacion() async {
    if (codigo.text.trim().isEmpty) { aviso(context, 'Selecciona o escribe un código.'); return; }
    setState(() => ocupado = true); try { final path = tipo == 'ventas' ? '/ventas/${Uri.encodeComponent(codigo.text.trim())}' : '/reservas/buscar/${Uri.encodeComponent(codigo.text.trim())}';
      final r = mapa(await api.get(path)); if (mounted) setState(() => operacion = r); }
    catch (e) { if (mounted) { setState(() => operacion = null); aviso(context, mensajeError(e)); } }
    finally { if (mounted) setState(() => ocupado = false); }
  }
  Future<void> anular() async {
    if (operacion == null || motivo.text.trim().isEmpty) { aviso(context, 'Escribe el motivo de anulación.'); return; }
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(title: const Text('Confirmar anulación'),
      content: Text('¿Anular ${operacion!['codigo']}?'), actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Volver')),
      FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Anular'))]));
    if (ok != true) return;
    setState(() => ocupado = true); try { final id = operacion!['id'];
      final r = tipo == 'ventas' ? await api.anular(id as int, motivo.text.trim()) : mapa(await api.post('/reservas/$id/anular', {'motivo': motivo.text.trim()}));
      if (mounted) { mostrarAnulada(r); await cargar(); }
    } catch (e) { if (mounted) aviso(context, mensajeError(e)); } finally { if (mounted) setState(() => ocupado = false); }
  }
  void mostrarAnulada(Map<String, dynamic> r) => aviso(context, 'Operación ${r['codigo']} anulada.');
  @override Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(18), children: [titulo('Anular venta o reserva'),
    DropdownButtonFormField<String>(initialValue: tipo, decoration: const InputDecoration(labelText: 'Tipo de operación'), items: [
      if (widget.permisos.contains('ventas:anular')) const DropdownMenuItem(value: 'ventas', child: Text('Venta')),
      if (widget.permisos.contains('reservas:anular')) const DropdownMenuItem(value: 'reservas', child: Text('Reserva'))],
      onChanged: (v) { if (v != null) { setState(() { tipo = v; codigo.clear(); }); cargar(); } }), const SizedBox(height: 12),
    if (error.isNotEmpty) Text(error, style: const TextStyle(color: Colors.deepOrange)),
    if (recientes.isNotEmpty) DropdownButtonFormField<String>(key: ValueKey(tipo), decoration: const InputDecoration(labelText: 'Operaciones recientes'),
      items: recientes.map((r) => DropdownMenuItem<String>(value: r['codigo'].toString(), child: Text('${r['codigo']} · ${r['estado']}', overflow: TextOverflow.ellipsis))).toList(),
      onChanged: (v) { if (v != null) { codigo.text = v; buscarOperacion(); } }),
    const SizedBox(height: 12), campoTienda('Código de operación', codigo), OutlinedButton(onPressed: ocupado ? null : buscarOperacion, child: const Text('Buscar')),
    if (operacion != null) ...[Card(child: ListTile(title: Text('${operacion!['codigo']}'), subtitle: Text('Estado: ${operacion!['estado']}'))),
      campoTienda('Motivo', motivo), FilledButton(onPressed: ocupado ? null : anular, child: const Text('Anular operación'))],
  ]);
}
