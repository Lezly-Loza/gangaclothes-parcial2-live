import 'package:flutter/material.dart';
import 'api_service.dart';
import 'estilo.dart';
import 'main.dart' show api;
import 'tienda.dart' show titulo, campoTienda, imagenPrenda;

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

class AsistenteIaScreen extends StatefulWidget {
  const AsistenteIaScreen({super.key});
  @override State<AsistenteIaScreen> createState() => _AsistenteIaScreenState();
}
class _AsistenteIaScreenState extends State<AsistenteIaScreen> {
  final List<Map<String, dynamic>> mensajes = [
    {
      'remitente': 'asistente',
      'texto': '¡Hola! Soy tu asistente de compras con Inteligencia Artificial Gemini. ¿Buscas alguna prenda en especial, sugerencias para una ocasión o consultar tallas y precios?',
      'prendas': [],
    }
  ];
  final mensajeCtrl = TextEditingController();
  bool enviando = false;
  final ScrollController scroll = ScrollController();

  Future<void> enviar([String? textoDirecto]) async {
    final txt = textoDirecto ?? mensajeCtrl.text.trim();
    if (txt.isEmpty || enviando) return;
    mensajeCtrl.clear();
    setState(() {
      mensajes.add({'remitente': 'usuario', 'texto': txt});
      enviando = true;
    });
    _bajar();
    try {
      final r = mapa(await api.post('/ia/chat', {'mensaje': txt}));
      if (mounted) {
        setState(() {
          mensajes.add({
            'remitente': 'asistente',
            'texto': r['respuesta'] ?? 'Aquí tienes algunas recomendaciones.',
            'prendas': mapas(r['prendas']),
          });
        });
        _bajar();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          mensajes.add({
            'remitente': 'asistente',
            'texto': 'Disculpa, no pude procesar la consulta en este momento. Revisa tu conexión a internet.',
            'prendas': [],
          });
        });
      }
    } finally {
      if (mounted) setState(() => enviando = false);
    }
  }

  void _bajar() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (scroll.hasClients) {
        scroll.animateTo(scroll.position.maxScrollExtent, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      }
    });
  }

  @override void dispose() {
    mensajeCtrl.dispose();
    scroll.dispose();
    super.dispose();
  }

  @override Widget build(BuildContext context) => Scaffold(
    body: Column(
      children: [
        Expanded(
          child: ListView.builder(
            controller: scroll,
            padding: const EdgeInsets.all(16),
            itemCount: mensajes.length,
            itemBuilder: (ctx, i) {
              final m = mensajes[i];
              final esUsuario = m['remitente'] == 'usuario';
              final prendas = mapas(m['prendas']);
              return Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: Column(
                  crossAxisAlignment: esUsuario ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: esUsuario ? MainAxisAlignment.end : MainAxisAlignment.start,
                      children: [
                        if (!esUsuario) const CircleAvatar(radius: 13, backgroundColor: rosa, child: Icon(Icons.auto_awesome, size: 14, color: Colors.white)),
                        if (!esUsuario) const SizedBox(width: 8),
                        Flexible(
                          child: Container(
                            padding: const EdgeInsets.all(13),
                            decoration: BoxDecoration(
                              color: esUsuario ? rosa : Colors.white,
                              borderRadius: BorderRadius.circular(14),
                              border: esUsuario ? null : Border.all(color: borde),
                            ),
                            child: Text(
                              '${m['texto']}',
                              style: TextStyle(color: esUsuario ? Colors.white : Colors.black87, fontSize: 14),
                            ),
                          ),
                        ),
                      ],
                    ),
                    if (prendas.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      SizedBox(
                        height: 110,
                        child: ListView.builder(
                          scrollDirection: Axis.horizontal,
                          itemCount: prendas.length,
                          itemBuilder: (ctx, pi) {
                            final p = prendas[pi];
                            return Container(
                              width: 190,
                              margin: const EdgeInsets.only(right: 10),
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: borde),
                              ),
                              child: Row(
                                children: [
                                  Container(
                                    width: 50,
                                    height: 70,
                                    clipBehavior: Clip.antiAlias,
                                    decoration: BoxDecoration(borderRadius: BorderRadius.circular(6)),
                                    child: imagenPrenda(p['imagen_url']),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Text('${p['nombre']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                                        const SizedBox(height: 4),
                                        Text(bs(p['precio']), style: const TextStyle(color: rosa, fontWeight: FontWeight.bold, fontSize: 12)),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ],
                ),
              );
            },
          ),
        ),
        if (enviando) const Padding(padding: EdgeInsets.symmetric(horizontal: 16), child: LinearProgressIndicator(color: rosa)),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: Row(
            children: [
              ActionChip(avatar: const Icon(Icons.flash_on, size: 14, color: rosa), label: const Text('Ropa formal', style: TextStyle(fontSize: 11)), onPressed: () => enviar('Recomiéndame ropa formal de oficina')),
              const SizedBox(width: 6),
              ActionChip(avatar: const Icon(Icons.local_florist, size: 14, color: rosa), label: const Text('Prendas de verano', style: TextStyle(fontSize: 11)), onPressed: () => enviar('¿Qué prendas frescas de verano tienen?')),
              const SizedBox(width: 6),
              ActionChip(avatar: const Icon(Icons.celebration, size: 14, color: rosa), label: const Text('Vestidos de noche', style: TextStyle(fontSize: 11)), onPressed: () => enviar('Busco vestidos de noche elegantes')),
              const SizedBox(width: 6),
              ActionChip(avatar: const Icon(Icons.local_offer, size: 14, color: rosa), label: const Text('Promociones', style: TextStyle(fontSize: 11)), onPressed: () => enviar('¿Qué ofertas o promociones tienen activas?')),
            ],
          ),
        ),
        Container(
          color: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: mensajeCtrl,
                  decoration: const InputDecoration(hintText: 'Pregunta a Gemini AI sobre moda…', isDense: true),
                  onSubmitted: (_) => enviar(),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                style: IconButton.styleFrom(backgroundColor: rosa),
                icon: const Icon(Icons.send, color: Colors.white),
                onPressed: enviando ? null : () => enviar(),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class SucursalesScreen extends StatefulWidget {
  const SucursalesScreen({super.key});
  @override State<SucursalesScreen> createState() => _SucursalesScreenState();
}
class _SucursalesScreenState extends State<SucursalesScreen> {
  List<Map<String, dynamic>> sucursales = [];
  bool cargando = true;
  String error = '';
  @override void initState() { super.initState(); cargar(); }
  Future<void> cargar() async {
    setState(() { cargando = true; error = ''; });
    try {
      final r = mapas(await api.get('/sucursales'));
      if (mounted) setState(() => sucursales = r);
    } catch (e) {
      if (mounted) setState(() => error = mensajeError(e));
    } finally {
      if (mounted) setState(() => cargando = false);
    }
  }
  @override Widget build(BuildContext context) => Scaffold(
    body: RefreshIndicator(
      onRefresh: cargar,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          titulo('Red de Sucursales'),
          const Text('Tiendas físicas de la empresa habilitadas para inventario y retiros.'),
          const SizedBox(height: 14),
          if (cargando) const Center(child: CircularProgressIndicator())
          else if (error.isNotEmpty) Text(error, style: const TextStyle(color: Colors.deepOrange))
          else if (sucursales.isEmpty) vacio('No hay sucursales registradas.')
          else ...sucursales.map((s) => Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: ListTile(
              leading: const CircleAvatar(backgroundColor: Color(0xfffce7f3), child: Icon(Icons.storefront, color: rosa)),
              title: Text('${s['nombre']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (s['direccion'] != null) Text('📍 ${s['direccion']}', style: const TextStyle(fontSize: 12)),
                  if (s['telefono'] != null) Text('📞 ${s['telefono']}', style: const TextStyle(fontSize: 12)),
                ],
              ),
              trailing: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: (s['activo'] != false) ? const Color(0xffdcfce7) : const Color(0xfffee2e2),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  (s['activo'] != false) ? 'ABIERTA' : 'INACTIVA',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: (s['activo'] != false) ? const Color(0xff166534) : const Color(0xff991b1b),
                  ),
                ),
              ),
            ),
          )),
        ],
      ),
    ),
  );
}

class InventarioScreen extends StatefulWidget {
  const InventarioScreen({super.key});
  @override State<InventarioScreen> createState() => _InventarioScreenState();
}
class _InventarioScreenState extends State<InventarioScreen> {
  List<Map<String, dynamic>> sucursales = [];
  List<Map<String, dynamic>> items = [];
  int? sucursalId;
  bool soloAlertas = false;
  bool cargando = true;
  String error = '';

  @override void initState() { super.initState(); cargarSucursales(); }

  Future<void> cargarSucursales() async {
    try {
      final sucs = mapas(await api.get('/sucursales'));
      if (mounted) {
        setState(() {
          sucursales = sucs;
          sucursalId = sucs.firstOrNull?['id'] as int?;
        });
        if (sucursalId != null) cargarStock();
      }
    } catch (e) {
      if (mounted) setState(() { error = mensajeError(e); cargando = false; });
    }
  }

  Future<void> cargarStock() async {
    if (sucursalId == null) return;
    setState(() { cargando = true; error = ''; });
    try {
      final path = soloAlertas ? '/inventario/alertas' : '/inventario';
      final r = mapas(await api.get(path, {'sucursal_id': sucursalId}));
      if (mounted) setState(() => items = r);
    } catch (e) {
      if (mounted) setState(() => error = mensajeError(e));
    } finally {
      if (mounted) setState(() => cargando = false);
    }
  }

  @override Widget build(BuildContext context) => Scaffold(
    body: RefreshIndicator(
      onRefresh: cargarStock,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          titulo('Inventario por Sucursal'),
          const Text('Control de existencias y alertas de stock mínimo.'),
          const SizedBox(height: 12),
          if (sucursales.isNotEmpty) ...[
            DropdownButtonFormField<int>(
              initialValue: sucursalId,
              decoration: const InputDecoration(labelText: 'Sucursal'),
              items: sucursales.map((s) => DropdownMenuItem(value: s['id'] as int, child: Text('${s['nombre']}'))).toList(),
              onChanged: (v) { setState(() => sucursalId = v); cargarStock(); },
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                FilterChip(
                  label: const Text('Todas las existencias'),
                  selected: !soloAlertas,
                  onSelected: (val) { setState(() => soloAlertas = !val); cargarStock(); },
                ),
                const SizedBox(width: 8),
                FilterChip(
                  avatar: const Icon(Icons.warning_amber, size: 16, color: Colors.deepOrange),
                  label: const Text('Alertas Stock Bajo'),
                  selected: soloAlertas,
                  selectedColor: const Color(0xffffedd5),
                  onSelected: (val) { setState(() => soloAlertas = val); cargarStock(); },
                ),
              ],
            ),
          ],
          const SizedBox(height: 14),
          if (cargando) const Center(child: CircularProgressIndicator())
          else if (error.isNotEmpty) Text(error, style: const TextStyle(color: Colors.deepOrange))
          else if (items.isEmpty) vacio(soloAlertas ? 'No hay alertas de stock bajo en esta sucursal.' : 'No hay inventario cargado.')
          else ...items.map((it) {
            final bajo = it['bajo_minimo'] == true;
            return Card(
              margin: const EdgeInsets.only(bottom: 10),
              shape: RoundedRectangleBorder(
                side: BorderSide(color: bajo ? Colors.deepOrange : borde, width: bajo ? 1.5 : 1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${it['prenda_nombre'] ?? it['producto_nombre'] ?? 'Prenda'}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                          const SizedBox(height: 2),
                          Text('SKU: ${it['sku']} · ${it['talla'] ?? ''} / ${it['color'] ?? ''}', style: const TextStyle(fontSize: 12, color: Colors.black54)),
                          if (bajo)
                            Container(
                              margin: const EdgeInsets.only(top: 6),
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(color: const Color(0xfffee2e2), borderRadius: BorderRadius.circular(4)),
                              child: Text('⚠️ BAJO MÍNIMO (Mín: ${it['stock_min'] ?? 4})', style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold, fontSize: 10)),
                            ),
                        ],
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text('${it['stock']} disp.', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: bajo ? Colors.red : rosa)),
                        Text('${it['reservado'] ?? 0} res.', style: const TextStyle(fontSize: 11, color: Colors.black45)),
                      ],
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    ),
  );
}

class ReservasGestionScreen extends StatefulWidget {
  const ReservasGestionScreen({super.key});
  @override State<ReservasGestionScreen> createState() => _ReservasGestionScreenState();
}
class _ReservasGestionScreenState extends State<ReservasGestionScreen> {
  List<Map<String, dynamic>> sucursales = [];
  List<Map<String, dynamic>> reservas = [];
  int? sucursalId;
  String estadoFiltro = 'PENDIENTE';
  bool cargando = true;
  String error = '';

  @override void initState() { super.initState(); cargarSucursales(); }

  Future<void> cargarSucursales() async {
    try {
      final sucs = mapas(await api.get('/sucursales'));
      if (mounted) {
        setState(() {
          sucursales = sucs;
          sucursalId = sucs.firstOrNull?['id'] as int?;
        });
        if (sucursalId != null) cargarReservas();
      }
    } catch (e) {
      if (mounted) setState(() { error = mensajeError(e); cargando = false; });
    }
  }

  Future<void> cargarReservas() async {
    if (sucursalId == null) return;
    setState(() { cargando = true; error = ''; });
    try {
      final r = mapas(await api.get('/reservas', {
        'sucursal_id': sucursalId,
        if (estadoFiltro.isNotEmpty) 'estado': estadoFiltro,
      }));
      if (mounted) setState(() => reservas = r);
    } catch (e) {
      if (mounted) setState(() => error = mensajeError(e));
    } finally {
      if (mounted) setState(() => cargando = false);
    }
  }

  Future<void> cambiarAccion(int reservaId, String accion) async {
    try {
      await api.post('/reservas/$reservaId/$accion');
      if (mounted) aviso(context, 'Reserva actualizada a $accion.');
      cargarReservas();
    } catch (e) {
      if (mounted) aviso(context, mensajeError(e));
    }
  }

  @override Widget build(BuildContext context) => Scaffold(
    body: RefreshIndicator(
      onRefresh: cargarReservas,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          titulo('Reservas de Sucursal'),
          const Text('Atención de reservas en tienda física.'),
          const SizedBox(height: 12),
          if (sucursales.isNotEmpty) ...[
            DropdownButtonFormField<int>(
              initialValue: sucursalId,
              decoration: const InputDecoration(labelText: 'Sucursal'),
              items: sucursales.map((s) => DropdownMenuItem(value: s['id'] as int, child: Text('${s['nombre']}'))).toList(),
              onChanged: (v) { setState(() => sucursalId = v); cargarReservas(); },
            ),
            const SizedBox(height: 10),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final est in ['', 'PENDIENTE', 'PREPARADA', 'RETIRADA']) ...[
                    FilterChip(
                      label: Text(est.isEmpty ? 'Todas' : est),
                      selected: estadoFiltro == est,
                      onSelected: (val) { setState(() => estadoFiltro = est); cargarReservas(); },
                    ),
                    const SizedBox(width: 6),
                  ],
                ],
              ),
            ),
          ],
          const SizedBox(height: 14),
          if (cargando) const Center(child: CircularProgressIndicator())
          else if (error.isNotEmpty) Text(error, style: const TextStyle(color: Colors.deepOrange))
          else if (reservas.isEmpty) vacio('No hay reservas con este filtro.')
          else ...reservas.map((r) => Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('${r['codigo']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: r['estado'] == 'RETIRADA' ? const Color(0xffdcfce7) : r['estado'] == 'PREPARADA' ? const Color(0xffdbeafe) : const Color(0xfffef3c7),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text('${r['estado']}', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text('Cliente: ${r['cliente_nombre'] ?? 'Cliente'} · Tel: ${r['cliente_telefono'] ?? 'Sin tel'}', style: const TextStyle(fontSize: 13)),
                  Text('Cita: ${fecha(r['fecha_hora_prueba'])}', style: const TextStyle(fontSize: 12, color: Colors.black54)),
                  const Divider(height: 18),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      if (r['estado'] == 'PENDIENTE')
                        FilledButton.tonalIcon(
                          icon: const Icon(Icons.check, size: 16),
                          label: const Text('Marcar Preparada'),
                          onPressed: () => cambiarAccion(r['id'] as int, 'preparar'),
                        ),
                      if (r['estado'] == 'PREPARADA')
                        FilledButton.icon(
                          icon: const Icon(Icons.shopping_bag_outlined, size: 16),
                          label: const Text('Entregar Prenda'),
                          onPressed: () => cambiarAccion(r['id'] as int, 'retirar'),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          )),
        ],
      ),
    ),
  );
}

class BitacoraSuperScreen extends StatefulWidget {
  const BitacoraSuperScreen({super.key});
  @override State<BitacoraSuperScreen> createState() => _BitacoraSuperScreenState();
}
class _BitacoraSuperScreenState extends State<BitacoraSuperScreen> {
  List<Map<String, dynamic>> eventos = [];
  bool cargando = true;
  String error = '';
  @override void initState() { super.initState(); cargar(); }
  Future<void> cargar() async {
    setState(() { cargando = true; error = ''; });
    try {
      final r = mapas(await api.get('/seguridad/bitacora', {'limite': 50}));
      if (mounted) setState(() => eventos = r);
    } catch (e) {
      if (mounted) setState(() => error = mensajeError(e));
    } finally {
      if (mounted) setState(() => cargando = false);
    }
  }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Bitácora de Auditoría')),
    body: RefreshIndicator(
      onRefresh: cargar,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          titulo('Auditoría y Seguridad'),
          const Text('Registro de eventos, modificaciones y accesos en la plataforma.'),
          const SizedBox(height: 14),
          if (cargando) const Center(child: CircularProgressIndicator())
          else if (error.isNotEmpty) Text(error, style: const TextStyle(color: Colors.deepOrange))
          else if (eventos.isEmpty) vacio('No hay eventos de auditoría registrados.')
          else ...eventos.map((ev) => Card(
            margin: const EdgeInsets.only(bottom: 10),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(color: const Color(0xfff1f5f9), borderRadius: BorderRadius.circular(4)),
                        child: Text('${ev['modulo'] ?? 'SISTEMA'}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.blueGrey)),
                      ),
                      Text(fecha(ev['fecha']), style: const TextStyle(fontSize: 11, color: Colors.black45)),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text('${ev['detalle'] ?? ev['accion']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                  const SizedBox(height: 4),
                  Text('Actor: ${ev['actor'] ?? 'Sistema'} · IP: ${ev['ip'] ?? 'Local'}', style: const TextStyle(fontSize: 12, color: Colors.black54)),
                ],
              ),
            ),
          )),
        ],
      ),
    ),
  );
}

class CajaCobroScreen extends StatefulWidget {
  const CajaCobroScreen({super.key});
  @override State<CajaCobroScreen> createState() => _CajaCobroScreenState();
}
class _CajaCobroScreenState extends State<CajaCobroScreen> {
  List<Map<String, dynamic>> sucursales = [];
  List<Map<String, dynamic>> prendas = [];
  int? sucursalId, varianteId;
  final cantidadCtrl = TextEditingController(text: '1');
  final montoCtrl = TextEditingController();
  String formaPago = 'efectivo';
  bool ocupado = false;

  @override void initState() { super.initState(); cargarDatos(); }
  @override void dispose() { cantidadCtrl.dispose(); montoCtrl.dispose(); super.dispose(); }

  Future<void> cargarDatos() async {
    try {
      final sucs = mapas(await api.get('/sucursales'));
      final cat = mapas(await api.get('/catalogo'));
      if (mounted) {
        setState(() {
          sucursales = sucs;
          sucursalId = sucs.firstOrNull?['id'] as int?;
          prendas = cat;
        });
      }
    } catch (_) {}
  }

  List<Map<String, dynamic>> get variantesDisponibles {
    final List<Map<String, dynamic>> vars = [];
    for (final p in prendas) {
      for (final v in mapas(p['variantes'])) {
        vars.add({
          'id': v['id'],
          'sku': v['sku'],
          'nombre': '${p['nombre']} · ${v['talla'] ?? ''} ${v['color'] ?? ''}',
          'precio': p['precio_final'],
        });
      }
    }
    return vars;
  }

  Future<void> cobrar() async {
    if (sucursalId == null || varianteId == null) {
      aviso(context, 'Elige sucursal y prenda.');
      return;
    }
    final qty = int.tryParse(cantidadCtrl.text) ?? 1;
    final v = variantesDisponibles.firstWhere((e) => e['id'] == varianteId);
    final total = (v['precio'] as num) * qty;

    setState(() => ocupado = true);
    try {
      final r = mapa(await api.post('/ventas', {
        'sucursal_id': sucursalId,
        'forma_pago': formaPago,
        'items': [{'variante_id': varianteId, 'cantidad': qty}],
        'monto_recibido': double.tryParse(montoCtrl.text) ?? total.toDouble(),
      }));
      if (mounted) {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('¡Venta Exitosa!'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Comprobante: ${r['codigo']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 6),
                Text('Total cobrado: ${bs(r['total'])}'),
                Text('Método: ${formaPago.toUpperCase()}'),
              ],
            ),
            actions: [FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('Aceptar'))],
          ),
        );
        cantidadCtrl.text = '1';
        montoCtrl.clear();
      }
    } catch (e) {
      if (mounted) aviso(context, mensajeError(e));
    } finally {
      if (mounted) setState(() => ocupado = false);
    }
  }

  @override Widget build(BuildContext context) => Scaffold(
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        titulo('Caja y Cobros'),
        const Text('Emisión de comprobante de venta en mostrador.'),
        const SizedBox(height: 14),
        if (sucursales.isNotEmpty)
          DropdownButtonFormField<int>(
            initialValue: sucursalId,
            decoration: const InputDecoration(labelText: 'Sucursal'),
            items: sucursales.map((s) => DropdownMenuItem(value: s['id'] as int, child: Text('${s['nombre']}'))).toList(),
            onChanged: (v) => setState(() => sucursalId = v),
          ),
        const SizedBox(height: 12),
        DropdownButtonFormField<int>(
          initialValue: varianteId,
          decoration: const InputDecoration(labelText: 'Prenda y variante a vender'),
          items: variantesDisponibles.map((v) => DropdownMenuItem(
            value: v['id'] as int,
            child: Text('${v['nombre']} (${bs(v['precio'])})', overflow: TextOverflow.ellipsis),
          )).toList(),
          onChanged: (v) => setState(() => varianteId = v),
        ),
        const SizedBox(height: 12),
        campoTienda('Cantidad de unidades', cantidadCtrl, numero: true),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: formaPago,
          decoration: const InputDecoration(labelText: 'Forma de Pago'),
          items: const [
            DropdownMenuItem(value: 'efectivo', child: Text('Efectivo')),
            DropdownMenuItem(value: 'qr', child: Text('Pago QR Simple')),
            DropdownMenuItem(value: 'tarjeta', child: Text('Tarjeta Débito/Crédito')),
          ],
          onChanged: (v) { if (v != null) setState(() => formaPago = v); },
        ),
        const SizedBox(height: 12),
        campoTienda('Monto recibido (opcional)', montoCtrl, numero: true),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: ocupado ? null : cobrar,
          icon: const Icon(Icons.point_of_sale),
          label: Text(ocupado ? 'Procesando…' : 'Emitir Venta y Cobrar'),
        ),
      ],
    ),
  );
}

class CambiosScreen extends StatefulWidget {
  const CambiosScreen({super.key});
  @override State<CambiosScreen> createState() => _CambiosScreenState();
}
class _CambiosScreenState extends State<CambiosScreen> {
  final codigoCtrl = TextEditingController(text: 'VEN-2611-SOF1');
  final motivoCtrl = TextEditingController(text: 'Cambio de prenda por talla o preferencia');
  Map<String, dynamic>? venta;
  bool buscando = false, confirmando = false;
  String error = '';

  @override void dispose() { codigoCtrl.dispose(); motivoCtrl.dispose(); super.dispose(); }

  Future<void> buscarVenta() async {
    final cod = codigoCtrl.text.trim();
    if (cod.isEmpty) return;
    setState(() { buscando = true; error = ''; venta = null; });
    try {
      final r = mapa(await api.get('/ventas/$cod'));
      if (mounted) setState(() => venta = r);
    } catch (e) {
      if (mounted) setState(() => error = mensajeError(e));
    } finally {
      if (mounted) setState(() => buscando = false);
    }
  }

  Future<void> procesarCambio() async {
    if (venta == null) return;
    final detalles = mapas(venta?['detalles']);
    if (detalles.isEmpty) return;
    final det = detalles.first;
    setState(() => confirmando = true);
    try {
      await api.post('/cambios', {
        'venta_id': venta!['id'],
        'variante_entregada_id': det['variante_id'],
        'variante_recibida_id': det['variante_id'],
        'cantidad': 1,
        'motivo': motivoCtrl.text.trim(),
        'diferencia_monto': 0.0,
      });
      if (mounted) {
        aviso(context, '¡Cambio de prenda procesado con éxito!');
        setState(() => venta = null);
        codigoCtrl.clear();
      }
    } catch (e) {
      if (mounted) aviso(context, mensajeError(e));
    } finally {
      if (mounted) setState(() => confirmando = false);
    }
  }

  @override Widget build(BuildContext context) => Scaffold(
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        titulo('Cambios de Prenda'),
        const Text('Gestión de garantía de cambio en ventana de 7 días.'),
        const SizedBox(height: 14),
        campoTienda('Código de Venta (ej: VEN-2611-SOF1)', codigoCtrl),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: buscando ? null : buscarVenta,
          icon: const Icon(Icons.search),
          label: Text(buscando ? 'Buscando…' : 'Validar Ticket de Venta'),
        ),
        if (error.isNotEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Text(error, style: const TextStyle(color: Colors.deepOrange))),
        if (venta != null) ...[
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Venta: ${venta!['codigo']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  Text('Total original: ${bs(venta!['total'])}'),
                  Text('Estado: ${venta!['estado']}'),
                  const Divider(height: 20),
                  campoTienda('Motivo de cambio', motivoCtrl),
                  const SizedBox(height: 10),
                  FilledButton.icon(
                    onPressed: confirmando ? null : procesarCambio,
                    icon: const Icon(Icons.swap_horizontal_circle_outlined),
                    label: Text(confirmando ? 'Procesando…' : 'Confirmar Cambio de Prenda'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    ),
  );
}

class ReportesScreen extends StatefulWidget {
  const ReportesScreen({super.key});
  @override State<ReportesScreen> createState() => _ReportesScreenState();
}

class _ReportesScreenState extends State<ReportesScreen> with SingleTickerProviderStateMixin {
  late TabController tabCtrl;
  Map<String, dynamic>? dashboard;
  bool cargando = true;
  String error = '';

  @override
  void initState() {
    super.initState();
    tabCtrl = TabController(length: 3, vsync: this);
    cargarReporte();
  }

  @override
  void dispose() {
    tabCtrl.dispose();
    super.dispose();
  }

  Future<void> cargarReporte() async {
    setState(() { cargando = true; error = ''; });
    try {
      final res = mapa(await api.get('/reportes/dashboard'));
      if (mounted) setState(() => dashboard = res);
    } catch (e) {
      if (mounted) setState(() => error = mensajeError(e));
    } finally {
      if (mounted) setState(() => cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Reportes y Métricas Oficiales', style: TextStyle(fontSize: 16)),
        bottom: TabBar(
          controller: tabCtrl,
          indicatorColor: rosa,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white60,
          tabs: const [
            Tab(icon: Icon(Icons.insights, size: 20), text: 'KPIs'),
            Tab(icon: Icon(Icons.leaderboard, size: 20), text: 'Top Prendas'),
            Tab(icon: Icon(Icons.pie_chart, size: 20), text: 'Canales y Pagos'),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Actualizar',
            icon: const Icon(Icons.refresh),
            onPressed: cargarReporte,
          ),
        ],
      ),
      body: cargando
          ? const Center(child: CircularProgressIndicator())
          : error.isNotEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error_outline, size: 48, color: Colors.deepOrange),
                        const SizedBox(height: 12),
                        Text(error, textAlign: TextAlign.center),
                        const SizedBox(height: 12),
                        FilledButton(onPressed: cargarReporte, child: const Text('Reintentar')),
                      ],
                    ),
                  ),
                )
              : TabBarView(
                  controller: tabCtrl,
                  children: [
                    _tabKPIs(),
                    _tabTopPrendas(),
                    _tabCanalesYPagos(),
                  ],
                ),
    );
  }

  Widget _tabKPIs() {
    final ind = mapa(dashboard?['indicadores'] ?? {});
    return RefreshIndicator(
      onRefresh: cargarReporte,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              Expanded(
                child: _tarjetaKpi(
                  'Ventas Totales',
                  bs(ind['total']),
                  Icons.monetization_on,
                  Colors.green,
                  '${ind['ventas'] ?? 0} ventas',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _tarjetaKpi(
                  'Ganancia Estimada',
                  bs(ind['ganancia']),
                  Icons.trending_up,
                  rosa,
                  'Margen: ${(ind['margen_porcentaje'] as num?)?.toStringAsFixed(1) ?? '0'}%',
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _tarjetaKpi(
                  'Unidades Vendidas',
                  '${ind['unidades'] ?? 0} uds.',
                  Icons.checkroom,
                  Colors.blue,
                  'Ticket prom: ${bs(ind['ticket_promedio'])}',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _tarjetaKpi(
                  'Alertas de Stock',
                  '${ind['alertas_stock'] ?? 0} bajas',
                  Icons.warning_amber,
                  Colors.orange,
                  'Stock total: ${ind['unidades_en_stock'] ?? 0}',
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Estado de Operaciones', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                  const SizedBox(height: 10),
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.event_note, color: rosa),
                    title: const Text('Reservas activas en tienda'),
                    trailing: Text('${ind['reservas_activas'] ?? 0}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  ),
                  const Divider(height: 8),
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.local_offer_outlined, color: Colors.blue),
                    title: const Text('Promociones vigentes'),
                    trailing: Text('${ind['promociones_vigentes'] ?? 0}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  ),
                  const Divider(height: 8),
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.account_balance_wallet_outlined, color: Colors.purple),
                    title: const Text('Valor de inventario (venta)'),
                    trailing: Text(bs(ind['valor_inventario_venta']), style: const TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _tarjetaKpi(String titulo, String valor, IconData icono, Color color, String pie) {
    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icono, color: color, size: 20),
                const SizedBox(width: 6),
                Expanded(child: Text(titulo, style: const TextStyle(fontSize: 12, color: Colors.black54, fontWeight: FontWeight.bold), overflow: TextOverflow.ellipsis)),
              ],
            ),
            const SizedBox(height: 8),
            Text(valor, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
            const SizedBox(height: 4),
            Text(pie, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }

  Widget _tabTopPrendas() {
    final top = mapas(dashboard?['top_prendas']);
    if (top.isEmpty) return vacio('No hay prendas vendidas en el periodo.');
    return RefreshIndicator(
      onRefresh: cargarReporte,
      child: ListView.builder(
        padding: const EdgeInsets.all(14),
        itemCount: top.length,
        itemBuilder: (ctx, i) {
          final p = top[i];
          return Card(
            margin: const EdgeInsets.only(bottom: 10),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: i == 0 ? Colors.amber : (i == 1 ? Colors.grey.shade400 : (i == 2 ? Colors.brown.shade300 : rosa)),
                foregroundColor: Colors.white,
                child: Text('#${i + 1}', style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
              title: Text('${p['etiqueta']}', style: const TextStyle(fontWeight: FontWeight.bold)),
              subtitle: Text('${p['unidades']} uds vendidas · Ganancia: ${bs(p['ganancia'])}'),
              trailing: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(bs(p['total']), style: const TextStyle(fontWeight: FontWeight.w900, color: rosa)),
                  Text('${(p['participacion'] as num?)?.toStringAsFixed(1) ?? '0'}%', style: const TextStyle(fontSize: 11, color: Colors.black54)),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _tabCanalesYPagos() {
    final canales = mapas(dashboard?['por_canal']);
    final metodos = mapas(dashboard?['metodos_pago']);

    return RefreshIndicator(
      onRefresh: cargarReporte,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          titulo('Ventas por Canal'),
          const Text('Desglose de ingresos por origen de la venta.'),
          const SizedBox(height: 12),
          for (final c in canales)
            Card(
              margin: const EdgeInsets.only(bottom: 10),
              child: ListTile(
                leading: Icon(
                  c['etiqueta'] == 'movil'
                      ? Icons.smartphone
                      : (c['etiqueta'] == 'caja' ? Icons.point_of_sale : Icons.laptop_chromebook),
                  color: rosa,
                ),
                title: Text('Canal ${c['etiqueta'].toString().toUpperCase()}', style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text('${c['ventas']} operaciones · ${c['unidades']} prendas'),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(bs(c['total']), style: const TextStyle(fontWeight: FontWeight.w900)),
                    Text('${(c['participacion'] as num?)?.toStringAsFixed(1) ?? '0'}%', style: const TextStyle(fontSize: 12, color: rosa, fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 20),
          titulo('Métodos de Pago'),
          const Text('Total recaudado por modalidad de cobro.'),
          const SizedBox(height: 12),
          for (final m in metodos)
            Card(
              margin: const EdgeInsets.only(bottom: 10),
              child: ListTile(
                leading: Icon(
                  m['metodo'] == 'QR'
                      ? Icons.qr_code_2
                      : (m['metodo'] == 'EFECTIVO' ? Icons.payments_outlined : Icons.credit_card),
                  color: Colors.teal,
                ),
                title: Text('Pago ${m['metodo']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text('${m['pagos']} transacciones procesadas'),
                trailing: Text(bs(m['total']), style: const TextStyle(fontWeight: FontWeight.w900, color: Colors.teal, fontSize: 15)),
              ),
            ),
        ],
      ),
    );
  }
}
