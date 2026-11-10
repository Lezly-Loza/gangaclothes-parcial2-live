import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'api_service.dart';
import 'estilo.dart';
import 'main.dart' show api;
import 'sincronizador.dart';

Widget imagenPrenda(dynamic url, {double icono = 34}) {
  final texto = url?.toString() ?? '';
  const web = String.fromEnvironment('WEB_URL', defaultValue: '');
  final direccion = texto.startsWith('http://') || texto.startsWith('https://')
      ? texto : web.isNotEmpty && texto.startsWith('/') ? '$web$texto' : '';
  Widget alternativa() => Icon(Icons.checkroom, size: icono, color: rosa);
  if (direccion.isEmpty) return alternativa();
  return Image.network(direccion, fit: BoxFit.cover, errorBuilder: (context, error, stack) => alternativa());
}

class CatalogoScreen extends StatefulWidget {
  const CatalogoScreen({super.key});
  @override State<CatalogoScreen> createState() => _CatalogoScreenState();
}
class _CatalogoScreenState extends State<CatalogoScreen> {
  List<Map<String, dynamic>> prendas = [], sucursales = []; int? sucursal; String texto = '', error = ''; bool cargando = true;
  int peticion = 0;
  @override void initState() { super.initState(); cargarOpciones(); buscar(); }
  Future<void> cargarOpciones() async { try { final r = mapa(await api.get('/catalogo/opciones')); if (mounted) setState(() => sucursales = mapas(r['sucursales'])); } catch (_) {} }
  Future<void> buscar() async {
    final actual = ++peticion; setState(() { cargando = true; error = ''; });
    try { final r = mapas(await api.get('/catalogo', {if (sucursal != null) 'sucursal_id': sucursal, if (texto.trim().isNotEmpty) 'q': texto.trim()}));
      if (mounted && actual == peticion) setState(() => prendas = r);
    } catch (e) { if (mounted && actual == peticion) setState(() => error = mensajeError(e)); }
    finally { if (mounted && actual == peticion) setState(() => cargando = false); }
  }
  @override Widget build(BuildContext context) => RefreshIndicator(onRefresh: buscar, child: ListView(padding: const EdgeInsets.all(18), children: [
    Text('Catálogo', style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w900)),
    const Text('PRENDAS PARA TI', style: TextStyle(letterSpacing: 2, fontSize: 10, color: Colors.black54)), const SizedBox(height: 18),
    TextField(decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Buscar prenda…'),
      onChanged: (v) { texto = v; buscar(); }), const SizedBox(height: 12),
    DropdownButtonFormField<int>(initialValue: sucursal, decoration: const InputDecoration(labelText: 'Sucursal'),
      items: [const DropdownMenuItem<int>(value: null, child: Text('Todas las sucursales')), ...sucursales.map((s) => DropdownMenuItem<int>(value: s['id'] as int, child: Text('${s['nombre']}')))],
      onChanged: (v) { setState(() => sucursal = v); buscar(); }), const SizedBox(height: 18),
    if (cargando) const Center(child: CircularProgressIndicator())
    else if (error.isNotEmpty) Column(children: [Text(error), TextButton(onPressed: buscar, child: const Text('Reintentar'))])
    else if (prendas.isEmpty) vacio('No hay prendas disponibles con estos filtros.')
    else ...prendas.map((p) => Card(child: InkWell(borderRadius: BorderRadius.circular(14),
      onTap: () async { await Navigator.push(context, MaterialPageRoute(builder: (_) => ReservarPrendaScreen(prenda: p, sucursalInicial: sucursal))); if (mounted) buscar(); },
      child: Padding(padding: const EdgeInsets.all(16), child: Row(children: [
        Container(width: 65, height: 75, clipBehavior: Clip.antiAlias, decoration: BoxDecoration(color: papel, borderRadius: BorderRadius.circular(10)), child: imagenPrenda(p['imagen_url'])),
        const SizedBox(width: 15), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${p['nombre']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)), const SizedBox(height: 4),
          Text(bs(p['precio_final']), style: const TextStyle(color: rosa, fontWeight: FontWeight.bold)),
          Text('${p['disponible_total']} disponibles', style: const TextStyle(color: Colors.black54, fontSize: 12))])),
        const Icon(Icons.chevron_right)]))))),
  ]));
}

class ReservarPrendaScreen extends StatefulWidget {
  const ReservarPrendaScreen({super.key, required this.prenda, this.sucursalInicial});
  final Map<String, dynamic> prenda; final int? sucursalInicial;
  @override State<ReservarPrendaScreen> createState() => _ReservarPrendaScreenState();
}
class _ReservarPrendaScreenState extends State<ReservarPrendaScreen> {
  int? varianteId, sucursalId; int cantidad = 1; bool ocupado = false;
  DateTime cita = DateTime.now().add(const Duration(days: 1));
  List<Map<String, dynamic>> get variantes => mapas(widget.prenda['variantes']);
  Map<String, dynamic>? get variante => variantes.where((v) => v['id'] == varianteId).firstOrNull;
  List<Map<String, dynamic>> get disponibles => mapas(variante?['disponibilidad']).where((s) => (s['disponible'] as num) > 0).toList();
  @override void initState() { super.initState(); elegirPrenda(); }
  void elegirPrenda() { final v = variantes.where((v) => (v['disponible_total'] as num) > 0).firstOrNull;
    varianteId = v?['id'] as int?; ajustarSucursal(); }
  void ajustarSucursal() { final opciones = disponibles; final elegida = widget.sucursalInicial ?? sucursalId;
    sucursalId = opciones.any((s) => s['sucursal_id'] == elegida) ? elegida : opciones.firstOrNull?['sucursal_id'] as int?; cantidad = 1; }
  Future<void> elegirFecha() async { final ahora = DateTime.now(); final dia = await showDatePicker(context: context,
      initialDate: cita.isBefore(ahora) ? ahora : cita, firstDate: ahora, lastDate: ahora.add(const Duration(days: 365)));
    if (dia == null || !mounted) return;
    final hora = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(cita));
    if (hora != null && mounted) setState(() => cita = DateTime(dia.year, dia.month, dia.day, hora.hour, hora.minute)); }
  Future<void> reservar() async {
    if (varianteId == null || sucursalId == null) return;
    if (!cita.isAfter(DateTime.now())) { aviso(context, 'Elige una fecha futura.'); return; }
    setState(() => ocupado = true);
    try { final r = await api.crearReserva({'sucursal_id': sucursalId, 'fecha_hora_prueba': cita.toIso8601String(),
      'detalle': [{'variante_id': varianteId, 'cantidad': cantidad}]});
      if (mounted) { await mostrarCodigo('${r['codigo']}'); if (mounted) Navigator.pop(context); }
    } catch (e) { if (mounted) aviso(context, mensajeError(e)); } finally { if (mounted) setState(() => ocupado = false); }
  }
  Future<void> mostrarCodigo(String codigo) => showDialog<void>(context: context, builder: (c) => AlertDialog(
    title: const Text('Reserva confirmada'), content: Text('Código: $codigo\nConsulta o cancela desde Mis reservas.'),
    actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('Aceptar'))]));
  Future<void> agregarAlCarrito() async {
    if (varianteId == null || sucursalId == null) return;
    setState(() => ocupado = true);
    try {
      final actual = await api.get('/tienda/carrito');
      if (actual != null && actual['sucursal_id'] != sucursalId && (actual['detalle'] as List).isNotEmpty) {
        if (!mounted) return;
        final aceptar = await showDialog<bool>(context: context, builder: (c) => AlertDialog(title: const Text('Cambiar sucursal'),
          content: const Text('Todo el carrito pasará a la sucursal seleccionada. Se volverá a comprobar el stock.'),
          actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancelar')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Continuar'))]));
        if (aceptar != true) return;
      }
      if (actual == null || actual['sucursal_id'] != sucursalId) await api.post('/tienda/carrito', {'sucursal_id': sucursalId});
      await api.post('/tienda/carrito/items', {'variante_id': varianteId, 'cantidad': cantidad});
      if (mounted) aviso(context, 'Prenda agregada al carrito.');
    } catch (e) { if (mounted) aviso(context, mensajeError(e)); } finally { if (mounted) setState(() => ocupado = false); }
  }
  @override Widget build(BuildContext context) {
    final stock = disponibles.where((d) => d['sucursal_id'] == sucursalId).firstOrNull?['disponible'] as int? ?? 0;
    return Scaffold(appBar: AppBar(title: const Text('Detalle de prenda')), body: ListView(padding: const EdgeInsets.all(20), children: [
      Container(height: 140, clipBehavior: Clip.antiAlias, decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)), child: imagenPrenda(widget.prenda['imagen_url'], icono: 70)),
      const SizedBox(height: 20), Text('${widget.prenda['nombre']}', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
      Text(bs(widget.prenda['precio_final']), style: const TextStyle(color: rosa, fontSize: 20, fontWeight: FontWeight.w800)),
      if (widget.prenda['descripcion'] != null) Text('${widget.prenda['descripcion']}'), const SizedBox(height: 20),
      DropdownButtonFormField<int>(initialValue: varianteId, decoration: const InputDecoration(labelText: 'Talla y color'),
        items: variantes.map((v) => DropdownMenuItem<int>(value: v['id'] as int, child: Text('${v['talla']} · ${v['color']}'))).toList(),
        onChanged: ocupado ? null : (v) => setState(() { varianteId = v; ajustarSucursal(); })), const SizedBox(height: 12),
      DropdownButtonFormField<int>(key: ValueKey('$varianteId-$sucursalId'), initialValue: sucursalId,
        decoration: const InputDecoration(labelText: 'Sucursal'), items: disponibles.map((s) => DropdownMenuItem<int>(value: s['sucursal_id'] as int,
          child: Text('${s['sucursal']} · ${s['disponible']} disponibles'))).toList(),
        onChanged: ocupado ? null : (v) => setState(() { sucursalId = v; cantidad = 1; })),
      const SizedBox(height: 15), Row(children: [const Text('Cantidad'), const Spacer(), IconButton(onPressed: cantidad > 1 && !ocupado ? () => setState(() => cantidad--) : null, icon: const Icon(Icons.remove_circle_outline)),
        Text('$cantidad'), IconButton(onPressed: cantidad < stock && !ocupado ? () => setState(() => cantidad++) : null, icon: const Icon(Icons.add_circle_outline))]),
      if (stock == 0) const Text('Esta variante no tiene stock disponible.'),
      const SizedBox(height: 12), OutlinedButton.icon(onPressed: ocupado || stock == 0 ? null : elegirFecha,
        icon: const Icon(Icons.calendar_month), label: Text('Visita: ${fecha(cita.toIso8601String())}')),
      OutlinedButton(onPressed: ocupado || stock == 0 ? null : reservar, child: const Text('Reservar para probar en tienda')),
      FilledButton(onPressed: ocupado || stock == 0 ? null : agregarAlCarrito, child: const Text('Agregar al carrito')),
    ]));
  }
}

class MisReservasScreen extends StatefulWidget {
  const MisReservasScreen({super.key});
  @override State<MisReservasScreen> createState() => _MisReservasScreenState();
}
class _MisReservasScreenState extends State<MisReservasScreen> {
  List<Map<String, dynamic>> reservas = []; bool cargando = true; String error = '';
  @override void initState() { super.initState(); cargar(); }
  Future<void> cargar() async {
    try { final r = mapas(await api.get('/tienda/reservas')); if (mounted) setState(() { reservas = r; error = ''; }); }
    catch (e) { if (mounted) setState(() => error = mensajeError(e)); }
    finally { if (mounted) setState(() => cargando = false); }
  }
  Future<void> cancelar(Map<String, dynamic> reserva) async {
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(title: const Text('Cancelar reserva'),
      content: Text('¿Cancelar ${reserva['codigo']} y liberar las prendas?'), actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Volver')),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Cancelar reserva'))]));
    if (ok != true) return;
    try { await api.post('/tienda/reservas/${reserva['id']}/cancelar'); await cargar(); }
    catch (e) { if (mounted) aviso(context, mensajeError(e)); }
  }
  @override Widget build(BuildContext context) => listado(context, 'Mis reservas', cargando, error, cargar,
    reservas.map((r) => Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [Expanded(child: Text('${r['codigo']}', style: const TextStyle(fontWeight: FontWeight.w900))), Chip(label: Text('${r['estado']}'))]),
      Text('${r['sucursal']} · ${fecha(r['fecha_hora_prueba'])}'),
      for (final d in mapas(r['detalle'])) Text('${d['prenda']} · ${d['talla']} · ${d['color']} × ${d['cantidad']}'),
      if (['pendiente', 'preparada'].contains(r['estado'])) TextButton(onPressed: () => cancelar(r), child: const Text('Cancelar reserva')),
    ])))).toList(), 'Aún no tienes reservas.');
}

class CarritoScreen extends StatefulWidget {
  const CarritoScreen({super.key});
  @override State<CarritoScreen> createState() => _CarritoScreenState();
}
class _CarritoScreenState extends State<CarritoScreen> {
  Map<String, dynamic>? carrito; bool cargando = true, ocupado = false; String error = ''; bool delivery = false;
  String metodo = 'tarjeta';
  Map<String, dynamic>? qr;
  Timer? consultaQr;
  bool consultandoQr = false;
  final numeroTarjeta = TextEditingController();
  final direccion = TextEditingController(), latitud = TextEditingController(), longitud = TextEditingController(), telefono = TextEditingController(), referencia = TextEditingController();
  @override void initState() { super.initState(); cargar(); }
  @override void dispose() { consultaQr?.cancel(); for (final c in [direccion, latitud, longitud, telefono, referencia, numeroTarjeta]) { c.dispose(); } super.dispose(); }
  Future<void> cargar() async { try { final r = await api.get('/tienda/carrito'); if (mounted) setState(() { carrito = r == null ? null : mapa(r); error = ''; }); }
    catch (e) { if (mounted) setState(() => error = mensajeError(e)); }
    finally { if (mounted) setState(() => cargando = false); } }
  Future<void> cambiar(Map<String, dynamic> linea, int cantidad) async {
    if (cantidad < 1 || ocupado) return; setState(() => ocupado = true);
    try { final r = await api.put('/tienda/carrito/items/${linea['id']}', {'cantidad': cantidad}); if (mounted) setState(() => carrito = mapa(r)); }
    catch (e) { if (mounted) aviso(context, mensajeError(e)); } finally { if (mounted) setState(() => ocupado = false); }
  }
  Future<void> quitar(Map<String, dynamic> linea) async {
    setState(() => ocupado = true); try { final r = await api.delete('/tienda/carrito/items/${linea['id']}'); if (mounted) setState(() => carrito = mapa(r)); }
    catch (e) { if (mounted) aviso(context, mensajeError(e)); } finally { if (mounted) setState(() => ocupado = false); }
  }
  Future<void> confirmarVenta() async {
    if (delivery && (direccion.text.trim().length < 3 || double.tryParse(latitud.text) == null || double.tryParse(longitud.text) == null)) {
      aviso(context, 'Indica la dirección y las coordenadas del envío.'); return;
    }
    if (metodo == 'tarjeta' && !tarjetaPruebaValida(numeroTarjeta.text)) {
      aviso(context, 'Usa una tarjeta de prueba válida. 4242 4242 4242 4242 aprueba y 4000 0000 0000 0002 rechaza.'); return;
    }
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(title: const Text('Confirmar pago de prueba'),
      content: Text(metodo == 'tarjeta' ? 'Stripe comprobará la tarjeta de prueba. No se cobrará dinero real.'
          : 'Se generará un QR y la compra quedará pendiente hasta confirmar el pago.'),
      actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Volver')),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Confirmar'))]));
    if (ok != true) return;
    setState(() => ocupado = true);
    try {
      final entrega = delivery ? {'direccion': direccion.text.trim(), 'latitud': double.parse(latitud.text),
        'longitud': double.parse(longitud.text), 'telefono': telefono.text.trim(), 'referencia': referencia.text.trim()} : <String, dynamic>{};
      if (metodo == 'tarjeta') {
        final r = mapa(await api.post('/pagos/tarjeta', {...entrega, 'numero_tarjeta': numeroTarjeta.text}));
        if (mounted) { setState(() => carrito = null); await mostrarComprobante(r); }
      } else {
        final r = mapa(await api.post('/pagos/qr', entrega));
        if (mounted) {
          setState(() { qr = r; error = ''; });
          consultaQr?.cancel();
          consultaQr = Timer.periodic(const Duration(seconds: 4), (_) => consultarQr());
        }
      }
    } catch (e) { if (mounted) aviso(context, mensajeError(e)); }
    finally { if (mounted) setState(() => ocupado = false); }
  }
  Future<void> consultarQr() async {
    final actual = qr;
    if (actual == null || consultandoQr) return;
    consultandoQr = true;
    try {
      final r = mapa(await api.get('/pagos/qr/${actual['qr_id']}'));
      if (!mounted) return;
      setState(() { qr = {...actual, ...r}; error = ''; });
      if (r['aprobado'] == true) {
        consultaQr?.cancel();
        setState(() { qr = null; carrito = null; });
        await mostrarComprobante(r);
      } else if (r['rechazado'] == true) {
        consultaQr?.cancel();
        setState(() { qr = null; error = 'El QR venció o fue anulado. Puedes intentar otra vez.'; });
      }
    } catch (e) { if (mounted) setState(() => error = mensajeError(e)); }
    finally { consultandoQr = false; }
  }
  Future<void> mostrarComprobante(Map<String, dynamic> r) async {
    await Sincronizador.notificar(
      'Compra confirmada: ${r['codigo']}',
      'Total: ${bs(r['total'])}. Tu compra se registró con éxito.',
    );
    if (!mounted) return;
    return showDialog<void>(context: context, builder: (c) => AlertDialog(
      title: const Text('Pago de prueba confirmado'), content: Text('Código: ${r['codigo']}\nTotal: ${bs(r['total'])}\nNo se cobró dinero real.'),
      actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('Aceptar'))]));
  }
  @override Widget build(BuildContext context) {
    final lineas = mapas(carrito?['detalle']);
    return ListView(padding: const EdgeInsets.all(18), children: [titulo('Carrito'),
      if (cargando) const Center(child: CircularProgressIndicator())
      else if (error.isNotEmpty) Column(children: [Text(error), TextButton(onPressed: cargar, child: const Text('Reintentar'))])
      else if (lineas.isEmpty && qr == null) vacio('Tu carrito está vacío. Agrega prendas desde el catálogo.')
      else ...[Text('Sucursal: ${carrito?['sucursal']}'), for (final l in lineas) Card(child: Padding(padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('${l['prenda']}', style: const TextStyle(fontWeight: FontWeight.bold)),
          Text('${l['talla']} · ${l['color']} · ${bs(l['subtotal'])}'),
          if (l['alcanza'] == false) const Text('Stock insuficiente o prenda no disponible', style: TextStyle(color: Colors.red)),
          Row(children: [IconButton(onPressed: ocupado ? null : () => cambiar(l, (l['cantidad'] as int) - 1), icon: const Icon(Icons.remove_circle_outline)),
            Text('${l['cantidad']}'), IconButton(onPressed: ocupado ? null : () => cambiar(l, (l['cantidad'] as int) + 1), icon: const Icon(Icons.add_circle_outline)),
            const Spacer(), TextButton(onPressed: ocupado ? null : () => quitar(l), child: const Text('Quitar'))])]))),
        SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('Envío a domicilio'), value: delivery, onChanged: ocupado ? null : (v) => setState(() => delivery = v)),
        if (delivery) ...[const Text('Envío de prueba. La tarifa y la distancia no se calculan.'), const SizedBox(height: 10),
          campoTienda('Dirección', direccion), campoTienda('Referencia (opcional)', referencia), campoTienda('Teléfono (opcional)', telefono),
          campoTienda('Latitud', latitud, numero: true), campoTienda('Longitud', longitud, numero: true)],
        const SizedBox(height: 15), Text('Total de prendas: ${bs(carrito?['total'])}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18)),
        const SizedBox(height: 10), DropdownButtonFormField<String>(initialValue: metodo,
          decoration: const InputDecoration(labelText: 'Método de pago'),
          items: const [DropdownMenuItem(value: 'tarjeta', child: Text('Tarjeta Stripe (prueba)')),
            DropdownMenuItem(value: 'qr', child: Text('QR BCP'))],
          onChanged: qr != null || ocupado ? null : (v) => setState(() => metodo = v ?? 'tarjeta')),
        if (metodo == 'tarjeta') ...[const SizedBox(height: 10), campoTienda('Número de tarjeta de prueba', numeroTarjeta, numero: true),
          const Text('4242 4242 4242 4242 aprueba · 4000 0000 0000 0002 rechaza. Solo tarjetas de prueba.', style: TextStyle(fontSize: 12))],
        if (qr != null) ...[const SizedBox(height: 12),
          if ((qr?['imagen_base64'] ?? '').toString().isNotEmpty) Center(child: Image.memory(base64Decode('${qr!['imagen_base64']}'), width: 220, height: 220)),
          Text('QR ${qr?['estado']} · vence ${qr?['expira']}'),
          TextButton(onPressed: consultarQr, child: const Text('Consultar estado'))],
        const SizedBox(height: 10), FilledButton(onPressed: ocupado || qr != null || lineas.any((l) => l['alcanza'] == false) ? null : confirmarVenta,
          child: Text(metodo == 'qr' ? 'Generar QR' : 'Pagar con tarjeta de prueba'))],
    ]);
  }
}
bool tarjetaPruebaValida(String numero) {
  final digitos = numero.replaceAll(RegExp(r'\s+'), '');
  if (!RegExp(r'^\d{13,19}$').hasMatch(digitos)) return false;
  var suma = 0; var doble = false;
  for (final caracter in digitos.split('').reversed) {
    var n = int.parse(caracter);
    if (doble) { n *= 2; if (n > 9) n -= 9; }
    suma += n; doble = !doble;
  }
  return suma % 10 == 0;
}
Widget campoTienda(String label, TextEditingController c, {bool numero = false}) => Padding(padding: const EdgeInsets.only(bottom: 10),
  child: TextField(controller: c, keyboardType: numero ? const TextInputType.numberWithOptions(decimal: true, signed: true) : null,
    decoration: InputDecoration(labelText: label)));

class MisComprasScreen extends StatelessWidget {
  const MisComprasScreen({super.key});
  @override Widget build(BuildContext context) => ListaRemota(titulo: 'Mis compras', ruta: '/tienda/compras', vacioTexto: 'Aún no tienes compras.',
    tarjeta: (v) => Card(child: ListTile(title: Text('${v['nro_comprobante']} · ${bs(v['total'])}'),
      subtitle: Text('${v['sucursal']} · ${v['estado']}\n${fecha(v['fecha'])}\n${mapas(v['pagos']).map((p) => p['metodo']).join(', ')}'), isThreeLine: true)));
}
class MisPedidosScreen extends StatelessWidget {
  const MisPedidosScreen({super.key});
  @override Widget build(BuildContext context) => ListaRemota(titulo: 'Mis pedidos', ruta: '/tienda/pedidos', vacioTexto: 'Aún no tienes pedidos a domicilio.',
    tarjeta: (v) => Card(child: ListTile(title: Text('${v['venta']?['nro_comprobante'] ?? 'Pedido'} · ${v['etiqueta_estado']}'),
      subtitle: Text('${v['direccion']}\n${v['repartidor'] ?? 'Sin repartidor asignado'}\nCosto de envío no calculado'), isThreeLine: true)));
}
Widget titulo(String valor) => Padding(padding: const EdgeInsets.only(bottom: 18), child: Text(valor, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)));
Widget listado(BuildContext context, String tituloTexto, bool cargando, String error, VoidCallback cargar, List<Widget> cards, String mensaje) =>
  ListView(padding: const EdgeInsets.all(18), children: [titulo(tituloTexto), if (cargando) const Center(child: CircularProgressIndicator())
    else if (error.isNotEmpty) Column(children: [Text(error), TextButton(onPressed: cargar, child: const Text('Reintentar'))])
    else if (cards.isEmpty) vacio(mensaje) else ...cards]);
class ListaRemota extends StatefulWidget {
  const ListaRemota({super.key, required this.titulo, required this.ruta, required this.vacioTexto, required this.tarjeta});
  final String titulo, ruta, vacioTexto; final Widget Function(Map<String, dynamic>) tarjeta;
  @override State<ListaRemota> createState() => _ListaRemotaState();
}
class _ListaRemotaState extends State<ListaRemota> {
  bool cargando = true; String error = ''; List<Map<String, dynamic>> filas = [];
  @override void initState() { super.initState(); cargar(); }
  Future<void> cargar() async { try { final r = mapas(await api.get(widget.ruta)); if (mounted) setState(() { filas = r; error = ''; }); }
    catch (e) { if (mounted) setState(() => error = mensajeError(e)); } finally { if (mounted) setState(() => cargando = false); } }
  @override Widget build(BuildContext context) => listado(context, widget.titulo, cargando, error, cargar, filas.map(widget.tarjeta).toList(), widget.vacioTexto);
}
