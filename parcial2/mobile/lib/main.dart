import 'package:flutter/material.dart';
import 'api_service.dart';
import 'estilo.dart';
import 'tienda.dart';
import 'gestion.dart';
import 'offline.dart';
import 'operaciones_offline.dart';
import 'sincronizador.dart';

ApiService api = ApiService();
void main() => runApp(const GangaApp());

class GangaApp extends StatelessWidget {
  const GangaApp({super.key});
  @override Widget build(BuildContext context) => MaterialApp(title: 'GangaClothes',
    debugShowCheckedModeBanner: false, theme: tema, home: const Inicio());
}
class Inicio extends StatelessWidget {
  const Inicio({super.key});
  @override Widget build(BuildContext context) => FutureBuilder<Map<String, dynamic>?>(
    future: api.sesionGuardada(), builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) return const Scaffold(body: Center(child: CircularProgressIndicator()));
      return snapshot.data == null ? const LoginScreen() : HomeScreen(sesion: snapshot.data!);
    });
}
void entrar(BuildContext context, Map<String, dynamic> sesion) => Navigator.pushAndRemoveUntil(context,
    MaterialPageRoute(builder: (_) => HomeScreen(sesion: sesion)), (_) => false);

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override State<LoginScreen> createState() => _LoginScreenState();
}
class _LoginScreenState extends State<LoginScreen> {
  final empresa = TextEditingController(); final correo = TextEditingController(); final clave = TextEditingController();
  bool registro = false, ocupado = false; String? error;
  final nombre = TextEditingController(); final documento = TextEditingController(); final telefono = TextEditingController();
  @override void dispose() { for (final c in [empresa, correo, clave, nombre, documento, telefono]) { c.dispose(); } super.dispose(); }
  Future<void> login() async {
    if (empresa.text.trim().isEmpty || correo.text.trim().isEmpty || clave.text.isEmpty ||
        (registro && (nombre.text.trim().isEmpty || documento.text.trim().isEmpty))) {
      setState(() => error = 'Completa los campos obligatorios.'); return;
    }
    setState(() { ocupado = true; error = null; });
    try {
      final datos = {'codigo_tenant': empresa.text.trim(), 'email': correo.text.trim(), 'password': clave.text,
        if (registro) ...{'nombre': nombre.text.trim(), 'documento': documento.text.trim(), 'telefono': telefono.text.trim()}};
      final sesion = registro ? await api.registrar(datos) : await api.login(datos);
      if (mounted) entrar(context, sesion);
    } catch (e) { if (mounted) setState(() => error = mensajeError(e)); }
    finally { if (mounted) setState(() => ocupado = false); }
  }
  @override Widget build(BuildContext context) => Scaffold(body: SafeArea(child: Center(child: ConstrainedBox(
    constraints: const BoxConstraints(maxWidth: 480), child: ListView(padding: const EdgeInsets.all(24), children: [
      Container(padding: const EdgeInsets.all(24), decoration: BoxDecoration(color: negro, borderRadius: BorderRadius.circular(16)),
        child: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Icon(Icons.checkroom, color: rosa, size: 40),
          SizedBox(height: 16), Marca(clara: true), SizedBox(height: 10), Text('Tu tienda, en un solo lugar.', style: TextStyle(color: Colors.white70))])),
      const SizedBox(height: 28), Text(registro ? 'Crear cuenta de cliente' : 'Bienvenido de vuelta', style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w900)),
      const SizedBox(height: 8), const Text('Ingresa el código de tu empresa para continuar.', style: TextStyle(color: Colors.black54)),
      const SizedBox(height: 20), campo('Código de empresa', empresa),
      if (registro) ...[campo('Nombre completo', nombre), campo('Documento', documento), campo('Teléfono (opcional)', telefono)],
      campo('Correo electrónico', correo, tipo: TextInputType.emailAddress), campo('Contraseña', clave, secreto: true),
      if (error != null) Padding(padding: const EdgeInsets.only(bottom: 12), child: Text(error!, style: const TextStyle(color: Colors.red))),
      SizedBox(height: 48, child: FilledButton(onPressed: ocupado ? null : login, child: Text(ocupado ? 'Espera…' : registro ? 'Crear cuenta' : 'Iniciar sesión'))),
      TextButton(onPressed: ocupado ? null : () => setState(() { registro = !registro; error = null; }),
        child: Text(registro ? 'Ya tengo una cuenta' : '¿Cliente nuevo? Crear cuenta')),
    ])))));
}
Widget campo(String nombre, TextEditingController c, {bool secreto = false, TextInputType? tipo}) => Padding(
  padding: const EdgeInsets.only(bottom: 12), child: TextField(controller: c, obscureText: secreto,
    keyboardType: tipo, decoration: InputDecoration(labelText: nombre)));

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.sesion});
  final Map<String, dynamic> sesion;
  @override State<HomeScreen> createState() => _HomeScreenState();
}
class _HomeScreenState extends State<HomeScreen> {
  int indice = 0;
  late final Sincronizador sincronizador;
  @override void initState() {
    super.initState();
    sincronizador = Sincronizador(OperacionesOffline(tenantId: widget.sesion['tenant_id'] as int,
      userId: widget.sesion['user_id'] as int, api: api), (op) {
      if (!mounted) return;
      final tipo = op['tipo'] == 'reserva' ? 'Reserva' : 'Venta';
      final texto = op['estado'] == 'confirmada' ? '$tipo confirmada: ${op['codigo']}' : '$tipo no confirmada: ${op['error']}';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(texto)));
    });
  }
  @override void dispose() { sincronizador.dispose(); super.dispose(); }
  @override Widget build(BuildContext context) {
    final roles = List<String>.from(widget.sesion['roles'] ?? []);
    final permisos = List<String>.from(widget.sesion['permisos'] ?? []);
    final cliente = roles.contains('cliente');
    final opciones = <({String nombre, IconData icono, Widget pagina})>[
      if (cliente) (nombre: 'Catálogo', icono: Icons.checkroom, pagina: const CatalogoScreen()),
      if (cliente) (nombre: 'Mis reservas', icono: Icons.event_available_outlined, pagina: const MisReservasScreen()),
      if (cliente) (nombre: 'Carrito', icono: Icons.shopping_bag_outlined, pagina: const CarritoScreen()),
      if (cliente) (nombre: 'Mis compras', icono: Icons.receipt_long_outlined, pagina: const MisComprasScreen()),
      if (cliente) (nombre: 'Mis pedidos', icono: Icons.local_shipping_outlined, pagina: const MisPedidosScreen()),
      if (permisos.any((p) => ['prendas:ver', 'inventario:ver', 'ventas:crear', 'reservas:crear'].contains(p)))
        (nombre: 'Catálogo sin conexión', icono: Icons.offline_pin_outlined, pagina: ModoOfflineScreen(sesion: widget.sesion, sincronizador: sincronizador)),
      if (permisos.contains('clientes:ver')) (nombre: 'Clientes', icono: Icons.people_outline, pagina: ClientesScreen(permisos: permisos)),
      if (permisos.contains('ventas:anular') || permisos.contains('reservas:anular'))
        (nombre: 'Anular operación', icono: Icons.cancel_outlined, pagina: AnularOperacionScreen(permisos: permisos)),
    ];
    if (indice >= opciones.length) indice = 0;
    return Scaffold(appBar: AppBar(title: const Marca(clara: true), actions: [IconButton(tooltip: 'Cerrar sesión',
      onPressed: () async { await api.salir(); if (context.mounted) Navigator.pushAndRemoveUntil(context, MaterialPageRoute(builder: (_) => const LoginScreen()), (_) => false); },
      icon: const Icon(Icons.logout))]),
      drawer: Drawer(backgroundColor: negro, child: SafeArea(child: Column(children: [
        ListTile(title: const Marca(clara: true), subtitle: Padding(padding: const EdgeInsets.only(top: 8), child: Text(
          '${widget.sesion['nombre']} · ${(widget.sesion['tenant_codigo'] ?? '')}', style: const TextStyle(color: Colors.white70)))),
        const Divider(color: Colors.white24), Expanded(child: ListView(children: [for (var i = 0; i < opciones.length; i++)
          ListTile(selected: indice == i, selectedTileColor: const Color(0xff351927), iconColor: Colors.white70,
            textColor: Colors.white, selectedColor: rosa, leading: Icon(opciones[i].icono), title: Text(opciones[i].nombre),
            onTap: () { setState(() => indice = i); Navigator.pop(context); })]))]))),
      body: opciones.isEmpty ? vacio('Tu cuenta no tiene funciones móviles asignadas.') : opciones[indice].pagina);
  }
}
