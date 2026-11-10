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
      return snapshot.data == null ? const LoginScreen() : pantallaSesion(snapshot.data!);
    });
}
Widget pantallaSesion(Map<String, dynamic> sesion) => sesion['kind'] == 'super'
    ? SuperHomeScreen(sesion: sesion) : HomeScreen(sesion: sesion);
void entrar(BuildContext context, Map<String, dynamic> sesion) => Navigator.pushAndRemoveUntil(context,
    MaterialPageRoute(builder: (_) => pantallaSesion(sesion)), (_) => false);

const _cuentasDemo = [
  (rol: 'Admin', tenant: 'luna', email: 'admin@gangaclothes.com', pass: 'Admin123'),
  (rol: 'Encargado', tenant: 'luna', email: 'encargado@gangaclothes.com', pass: 'Encargado123'),
  (rol: 'Cajero', tenant: 'luna', email: 'cajero@gangaclothes.com', pass: 'Cajero123'),
  (rol: 'Sofia (Cliente)', tenant: 'luna', email: 'sofia@gangaclothes.com', pass: 'Cliente#2026'),
  (rol: 'Diego (Cliente)', tenant: 'luna', email: 'diego@gangaclothes.com', pass: 'Cliente#2026'),
  (rol: 'Admin Andina', tenant: 'andina', email: 'admin@andina.bo', pass: 'Admin123'),
  (rol: 'Superadmin', tenant: '', email: 'root@plataforma.bo', pass: 'SuperSegura123'),
];

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override State<LoginScreen> createState() => _LoginScreenState();
}
class _LoginScreenState extends State<LoginScreen> {
  final empresa = TextEditingController(); final correo = TextEditingController(); final clave = TextEditingController();
  bool registro = false, ocupado = false, superadmin = false; String? error;
  final nombre = TextEditingController(); final documento = TextEditingController(); final telefono = TextEditingController();
  @override void dispose() { for (final c in [empresa, correo, clave, nombre, documento, telefono]) { c.dispose(); } super.dispose(); }
  void usarCuenta(String tenant, String mail, String pwd) {
    setState(() {
      superadmin = tenant.isEmpty;
      empresa.text = tenant;
      correo.text = mail;
      clave.text = pwd;
      error = null;
    });
    login();
  }
  Future<void> login() async {
    if ((!superadmin && empresa.text.trim().isEmpty) || correo.text.trim().isEmpty || clave.text.isEmpty ||
        (registro && (nombre.text.trim().isEmpty || documento.text.trim().isEmpty))) {
      setState(() => error = 'Completa los campos obligatorios.'); return;
    }
    setState(() { ocupado = true; error = null; });
    try {
      final datos = {if (!superadmin) 'codigo_tenant': empresa.text.trim(), 'email': correo.text.trim(), 'password': clave.text,
        if (registro) ...{'nombre': nombre.text.trim(), 'documento': documento.text.trim(), 'telefono': telefono.text.trim()}};
      final sesion = registro ? await api.registrar(datos) : superadmin ? await api.loginSuper(datos) : await api.login(datos);
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
      if (!registro) ...[const SizedBox(height: 12), Wrap(spacing: 8, children: [
        ChoiceChip(label: const Text('Mi empresa'), selected: !superadmin, onSelected: ocupado ? null : (_) => setState(() { superadmin = false; error = null; })),
        ChoiceChip(label: const Text('Superadministrador'), selected: superadmin, onSelected: ocupado ? null : (_) => setState(() { superadmin = true; error = null; })),
      ])],
      const SizedBox(height: 8), Text(superadmin ? 'Acceso a la plataforma.' : 'Ingresa el código de tu empresa para continuar.', style: const TextStyle(color: Colors.black54)),
      const SizedBox(height: 20), if (!superadmin) campo('Código de empresa', empresa),
      if (registro) ...[campo('Nombre completo', nombre), campo('Documento', documento), campo('Teléfono (opcional)', telefono)],
      campo('Correo electrónico', correo, tipo: TextInputType.emailAddress), campo('Contraseña', clave, secreto: true),
      if (ocupado) const Padding(
        padding: EdgeInsets.symmetric(vertical: 8),
        child: Center(
          child: Column(
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 8),
              Text('Conectando con el servidor en Render…', style: TextStyle(fontSize: 12, color: Colors.black54)),
            ],
          ),
        ),
      ),
      if (error != null) Padding(padding: const EdgeInsets.only(bottom: 12), child: Text(error!, style: const TextStyle(color: Colors.red))),
      SizedBox(height: 48, child: FilledButton(onPressed: ocupado ? null : login, child: Text(ocupado ? 'Espera…' : registro ? 'Crear cuenta' : 'Iniciar sesión'))),
      if (!superadmin) TextButton(onPressed: ocupado ? null : () => setState(() { registro = !registro; error = null; }),
        child: Text(registro ? 'Ya tengo una cuenta' : '¿Cliente nuevo? Crear cuenta')),
      if (!registro) ...[
        const SizedBox(height: 16),
        const Divider(),
        const SizedBox(height: 8),
        const Text('Cuentas de prueba (seed):', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black54)),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final c in _cuentasDemo)
              ActionChip(
                avatar: const Icon(Icons.person, size: 16, color: rosa),
                label: Text(c.rol, style: const TextStyle(fontSize: 12)),
                onPressed: ocupado ? null : () => usarCuenta(c.tenant, c.email, c.pass),
              ),
          ],
        ),
      ],
    ])))));
}
Widget campo(String nombre, TextEditingController c, {bool secreto = false, TextInputType? tipo}) => Padding(
  padding: const EdgeInsets.only(bottom: 12), child: TextField(controller: c, obscureText: secreto,
    keyboardType: tipo, decoration: InputDecoration(labelText: nombre)));

class SuperHomeScreen extends StatefulWidget {
  const SuperHomeScreen({super.key, required this.sesion});
  final Map<String, dynamic> sesion;
  @override State<SuperHomeScreen> createState() => _SuperHomeScreenState();
}
class _SuperHomeScreenState extends State<SuperHomeScreen> {
  int tabActual = 0;
  late Future<List<dynamic>> datos;
  @override void initState() { super.initState(); datos = cargar(); }
  Future<List<dynamic>> cargar() => Future.wait([api.get('/tenants'), api.get('/planes')]);
  void recargar() => setState(() => datos = cargar());

  Future<void> cambiarPlanEmpresa(Map<String, dynamic> emp, List<Map<String, dynamic>> planes) async {
    final elegido = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Controlar Plan: ${emp['razon_social']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
              const SizedBox(height: 6),
              Text('Plan actual: ${emp['plan_actual'] ?? 'Sin plan'}', style: const TextStyle(color: Colors.black54)),
              const Divider(height: 24),
              for (final p in planes)
                ListTile(
                  leading: const Icon(Icons.stars, color: rosa),
                  title: Text('${p['nombre']} · ${bs(p['precio_mensual'])}/mes', style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text('${p['max_sucursales']} sucursales · ${p['max_usuarios']} usuarios · ${p['max_productos']} prendas'),
                  trailing: (p['nombre'] == emp['plan_actual']) ? const Icon(Icons.check, color: Colors.green) : null,
                  onTap: () => Navigator.pop(ctx, p['codigo'] as String),
                ),
            ],
          ),
        ),
      ),
    );
    if (elegido != null && mounted) {
      try {
        await api.post('/tenants/${emp['id']}/plan', {'plan_codigo': elegido});
        if (mounted) aviso(context, 'Plan de ${emp['razon_social']} actualizado a ${elegido.toUpperCase()}');
        recargar();
      } catch (e) {
        if (mounted) aviso(context, 'No se pudo actualizar el plan.');
      }
    }
  }

  Future<void> alternarEstadoEmpresa(Map<String, dynamic> emp) async {
    final nuevoActivo = !(emp['activo'] == true);
    try {
      await api.patch('/tenants/${emp['id']}', {
        'activo': nuevoActivo,
        'estado': nuevoActivo ? 'activo' : 'suspendido',
      });
      if (mounted) aviso(context, 'Empresa ${nuevoActivo ? 'activada' : 'suspendida'}.');
      recargar();
    } catch (e) {
      if (mounted) aviso(context, 'No se pudo cambiar el estado de la empresa.');
    }
  }

  Future<void> crearEmpresa(List<Map<String, dynamic>> planes) async {
    final razon = TextEditingController();
    final codigo = TextEditingController();
    final nit = TextEditingController();
    final correo = TextEditingController();
    final adminNom = TextEditingController();
    final adminClave = TextEditingController(text: 'Admin123');
    String planCod = planes.isNotEmpty ? planes.first['codigo'] as String : 'profesional';

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDState) => AlertDialog(
          title: const Text('Nueva Empresa Contratante'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                campo('Razón Social', razon),
                campo('Código (ej: nueva)', codigo),
                campo('NIT', nit),
                campo('Correo de la empresa', correo, tipo: TextInputType.emailAddress),
                campo('Nombre del Administrador', adminNom),
                campo('Contraseña inicial', adminClave),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  initialValue: planCod,
                  decoration: const InputDecoration(labelText: 'Plan inicial'),
                  items: planes.map((p) => DropdownMenuItem(value: p['codigo'] as String, child: Text('${p['nombre']} (${bs(p['precio_mensual'])})'))).toList(),
                  onChanged: (v) { if (v != null) setDState(() => planCod = v); },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Crear Empresa')),
          ],
        ),
      ),
    );
    if (ok == true && mounted) {
      if (razon.text.trim().isEmpty || codigo.text.trim().isEmpty || nit.text.trim().isEmpty || adminNom.text.trim().isEmpty) {
        aviso(context, 'Completa los campos obligatorios');
        return;
      }
      try {
        await api.post('/tenants', {
          'razon_social': razon.text.trim(),
          'codigo': codigo.text.trim().toLowerCase(),
          'nit': nit.text.trim(),
          'correo': correo.text.trim().isEmpty ? 'contacto@${codigo.text.trim()}.bo' : correo.text.trim(),
          'admin': {
            'nombre': adminNom.text.trim(),
            'email': 'admin@${codigo.text.trim()}.bo',
            'password': adminClave.text,
          },
          'plan_codigo': planCod,
        });
        if (mounted) aviso(context, 'Empresa ${razon.text} registrada con éxito.');
        recargar();
      } catch (e) {
        if (mounted) aviso(context, 'Error al registrar empresa: $e');
      }
    }
  }

  Future<void> editarPlan(Map<String, dynamic> p) async {
    final precioCtrl = TextEditingController(text: '${p['precio_mensual']}');
    final sucsCtrl = TextEditingController(text: '${p['max_sucursales']}');
    final usersCtrl = TextEditingController(text: '${p['max_usuarios']}');
    final prodsCtrl = TextEditingController(text: '${p['max_productos']}');

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Editar Plan: ${p['nombre']}'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              campo('Precio mensual (Bs)', precioCtrl, tipo: TextInputType.number),
              campo('Máx. Sucursales', sucsCtrl, tipo: TextInputType.number),
              campo('Máx. Usuarios', usersCtrl, tipo: TextInputType.number),
              campo('Máx. Prendas / Productos', prodsCtrl, tipo: TextInputType.number),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Guardar Cambios')),
        ],
      ),
    );
    if (ok == true && mounted) {
      final precio = double.tryParse(precioCtrl.text);
      final sucs = int.tryParse(sucsCtrl.text);
      final users = int.tryParse(usersCtrl.text);
      final prods = int.tryParse(prodsCtrl.text);
      if (precio == null || sucs == null || users == null || prods == null) {
        aviso(context, 'Valores numéricos no válidos.');
        return;
      }
      try {
        await api.patch('/planes/${p['id']}', {
          'precio_mensual': precio,
          'max_sucursales': sucs,
          'max_usuarios': users,
          'max_productos': prods,
        });
        if (mounted) aviso(context, 'Plan ${p['nombre']} actualizado.');
        recargar();
      } catch (e) {
        if (mounted) aviso(context, 'Error al actualizar el plan.');
      }
    }
  }

  Future<void> crearPlan() async {
    final codCtrl = TextEditingController();
    final nomCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    final precioCtrl = TextEditingController(text: '49.0');
    final sucsCtrl = TextEditingController(text: '3');
    final usersCtrl = TextEditingController(text: '5');
    final prodsCtrl = TextEditingController(text: '300');

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Nuevo Plan de Suscripción'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              campo('Código (ej: premium)', codCtrl),
              campo('Nombre del Plan', nomCtrl),
              campo('Descripción', descCtrl),
              campo('Precio mensual (Bs)', precioCtrl, tipo: TextInputType.number),
              campo('Máx. Sucursales', sucsCtrl, tipo: TextInputType.number),
              campo('Máx. Usuarios', usersCtrl, tipo: TextInputType.number),
              campo('Máx. Productos', prodsCtrl, tipo: TextInputType.number),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Crear Plan')),
        ],
      ),
    );
    if (ok == true && mounted) {
      if (codCtrl.text.trim().isEmpty || nomCtrl.text.trim().isEmpty) {
        aviso(context, 'Código y nombre son obligatorios.');
        return;
      }
      try {
        await api.post('/planes', {
          'codigo': codCtrl.text.trim().toLowerCase(),
          'nombre': nomCtrl.text.trim(),
          'descripcion': descCtrl.text.trim(),
          'precio_mensual': double.tryParse(precioCtrl.text) ?? 49.0,
          'max_sucursales': int.tryParse(sucsCtrl.text) ?? 3,
          'max_usuarios': int.tryParse(usersCtrl.text) ?? 5,
          'max_productos': int.tryParse(prodsCtrl.text) ?? 300,
          'modulos': ['ventas', 'inventario', 'reportes'],
        });
        if (mounted) aviso(context, 'Plan ${nomCtrl.text} creado.');
        recargar();
      } catch (e) {
        if (mounted) aviso(context, 'Error al crear plan: $e');
      }
    }
  }

  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Superadministrador', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          Text('Consola Global SaaS', style: TextStyle(fontSize: 11, color: Colors.white70)),
        ],
      ),
      actions: [
        IconButton(tooltip: 'Recargar datos', icon: const Icon(Icons.refresh), onPressed: recargar),
        IconButton(tooltip: 'Cerrar sesión', icon: const Icon(Icons.logout),
          onPressed: () async { await api.salir(); if (context.mounted) Navigator.pushAndRemoveUntil(context, MaterialPageRoute(builder: (_) => const LoginScreen()), (_) => false); }),
      ],
    ),
    body: FutureBuilder<List<dynamic>>(future: datos, builder: (context, snapshot) {
      if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
      if (snapshot.hasError) return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Text('No se pudieron cargar empresas y planes.'),
        TextButton(onPressed: recargar, child: const Text('Reintentar'))]));
      final empresas = mapas(snapshot.data![0]), planes = mapas(snapshot.data![1]);

      if (tabActual == 0) {
        // Tab Empresas
        return RefreshIndicator(
          onRefresh: () async => recargar(),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('${empresas.length} Empresas Registradas', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
                  FilledButton.icon(
                    style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6)),
                    onPressed: () => crearEmpresa(planes),
                    icon: const Icon(Icons.add_business, size: 16),
                    label: const Text('Nueva'),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (empresas.isEmpty) vacio('No hay empresas registradas.'),
              for (final e in empresas) Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${e['razon_social']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                                const SizedBox(height: 2),
                                Text('Código: ${e['codigo']} · NIT: ${e['nit']}', style: const TextStyle(fontSize: 12, color: Colors.black54)),
                              ],
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: (e['activo'] == true) ? const Color(0xffdcfce7) : const Color(0xfffee2e2),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              (e['activo'] == true) ? 'ACTIVO' : 'PAUSADO',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: (e['activo'] == true) ? const Color(0xff166534) : const Color(0xff991b1b),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        children: [
                          Chip(
                            avatar: const Icon(Icons.stars, size: 14, color: rosa),
                            label: Text('Plan: ${e['plan_actual'] ?? 'Sin plan'}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                            padding: EdgeInsets.zero,
                            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                          Chip(
                            avatar: const Icon(Icons.storefront, size: 14),
                            label: Text('${e['sucursales_count'] ?? 1} sucursales', style: const TextStyle(fontSize: 11)),
                            padding: EdgeInsets.zero,
                            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                          Chip(
                            avatar: const Icon(Icons.people, size: 14),
                            label: Text('${e['usuarios_count'] ?? 0} usuarios', style: const TextStyle(fontSize: 11)),
                            padding: EdgeInsets.zero,
                            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          OutlinedButton.icon(
                            style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4)),
                            icon: Icon((e['activo'] == true) ? Icons.pause_circle_outline : Icons.play_circle_outline, size: 16),
                            label: Text((e['activo'] == true) ? 'Pausar' : 'Activar', style: const TextStyle(fontSize: 12)),
                            onPressed: () => alternarEstadoEmpresa(e),
                          ),
                          const SizedBox(width: 8),
                          FilledButton.icon(
                            style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4)),
                            icon: const Icon(Icons.swap_horiz, size: 16),
                            label: const Text('Cambiar Plan', style: const TextStyle(fontSize: 12)),
                            onPressed: () => cambiarPlanEmpresa(e, planes),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      } else if (tabActual == 1) {
        // Tab Planes
        return RefreshIndicator(
          onRefresh: () async => recargar(),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('${planes.length} Planes de Suscripción', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
                  FilledButton.icon(
                    style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6)),
                    onPressed: crearPlan,
                    icon: const Icon(Icons.add, size: 16),
                    label: const Text('Nuevo Plan'),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (planes.isEmpty) vacio('No hay planes registrados.'),
              for (final p in planes) Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('${p['nombre']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
                          Text(bs(p['precio_mensual']), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: rosa)),
                        ],
                      ),
                      Text('Código: ${p['codigo']}', style: const TextStyle(fontSize: 12, color: Colors.black54)),
                      if (p['descripcion'] != null && '${p['descripcion']}'.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text('${p['descripcion']}', style: const TextStyle(fontSize: 13)),
                      ],
                      const Divider(height: 18),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text('• Hasta ${p['max_sucursales']} sucursales', style: const TextStyle(fontSize: 12)),
                            Text('• Hasta ${p['max_usuarios']} usuarios', style: const TextStyle(fontSize: 12)),
                            Text('• Hasta ${p['max_productos']} prendas', style: const TextStyle(fontSize: 12)),
                          ]),
                          OutlinedButton.icon(
                            icon: const Icon(Icons.tune, size: 16),
                            label: const Text('Editar límites', style: TextStyle(fontSize: 12)),
                            onPressed: () => editarPlan(p),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      } else {
        // Tab Consola SaaS
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text('Consola Tecnológica SaaS', style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w900)),
            const SizedBox(height: 6),
            const Text('Supervisión y control global de infraestructura multitenant.'),
            const SizedBox(height: 20),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    ListTile(
                      leading: const Icon(Icons.verified, color: Colors.green),
                      title: const Text('Aislamiento Multitenant', style: TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: const Text('SQLAlchemy TenantMixin + Filtro estricto por tenant_id'),
                    ),
                    const Divider(),
                    ListTile(
                      leading: const Icon(Icons.cloud_done, color: Colors.blue),
                      title: const Text('Servicio Backend API', style: TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: const Text('Render Producción · Conexión segura HTTPS activa'),
                    ),
                    const Divider(),
                    ListTile(
                      leading: const Icon(Icons.apartment, color: rosa),
                      title: Text('${empresas.length} Empresas Inquilinas'),
                      subtitle: const Text('Boutique Luna SRL, Moda Andina SA'),
                    ),
                    const Divider(),
                    ListTile(
                      leading: const Icon(Icons.card_membership, color: Colors.purple),
                      title: Text('${planes.length} Planes Configurados'),
                      subtitle: const Text('Básico, Profesional, Empresarial'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            FilledButton.tonalIcon(
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const BitacoraSuperScreen())),
              icon: const Icon(Icons.shield_outlined),
              label: const Text('Consultar Bitácora de Auditoría Global'),
            ),
            const SizedBox(height: 10),
            FilledButton.icon(
              onPressed: recargar,
              icon: const Icon(Icons.refresh),
              label: const Text('Sincronizar Métricas'),
            ),
          ],
        );
      }
    }),
    bottomNavigationBar: NavigationBar(
      selectedIndex: tabActual,
      onDestinationSelected: (idx) => setState(() => tabActual = idx),
      destinations: const [
        NavigationDestination(icon: Icon(Icons.apartment), label: 'Empresas'),
        NavigationDestination(icon: Icon(Icons.stars), label: 'Planes'),
        NavigationDestination(icon: Icon(Icons.dashboard_customize), label: 'Consola SaaS'),
      ],
    ),
  );
}

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
    final esAdmin = roles.contains('administrador');
    final esEncargado = roles.contains('encargado');
    final esCajero = roles.contains('cajero');

    final opciones = <({String nombre, IconData icono, Widget pagina})>[
      // Opciones para cliente
      if (cliente) (nombre: 'Catálogo', icono: Icons.checkroom, pagina: const CatalogoScreen()),
      if (cliente) (nombre: 'Asistente IA (Gemini)', icono: Icons.auto_awesome, pagina: const AsistenteIaScreen()),
      if (cliente) (nombre: 'Mis reservas', icono: Icons.event_available_outlined, pagina: const MisReservasScreen()),
      if (cliente) (nombre: 'Carrito', icono: Icons.shopping_bag_outlined, pagina: const CarritoScreen()),
      if (cliente) (nombre: 'Mis compras', icono: Icons.receipt_long_outlined, pagina: const MisComprasScreen()),
      if (cliente) (nombre: 'Mis pedidos', icono: Icons.local_shipping_outlined, pagina: const MisPedidosScreen()),

      // Opciones para personal (Admin de tienda, Encargado de sucursal, Cajero)
      if (esAdmin || esEncargado || esCajero)
        (nombre: 'Asistente IA (Gemini)', icono: Icons.auto_awesome, pagina: const AsistenteIaScreen(admin: true)),
      if (esAdmin || permisos.contains('sucursales:ver'))
        (nombre: 'Red de Sucursales', icono: Icons.storefront, pagina: const SucursalesScreen()),
      if (esAdmin || esEncargado || permisos.contains('inventario:ver'))
        (nombre: 'Inventario y Stock', icono: Icons.inventory_2_outlined, pagina: const InventarioScreen()),
      if (esAdmin || esCajero || permisos.contains('ventas:crear'))
        (nombre: 'Caja y Cobros', icono: Icons.point_of_sale, pagina: const CajaCobroScreen()),
      if (esAdmin || esEncargado || esCajero || permisos.contains('reservas:ver'))
        (nombre: 'Reservas de Tienda', icono: Icons.event_note, pagina: const ReservasGestionScreen()),
      if (esAdmin || esEncargado || esCajero || permisos.contains('cambios:crear'))
        (nombre: 'Cambios de Prenda', icono: Icons.swap_horiz, pagina: const CambiosScreen()),
      if (permisos.contains('clientes:ver') || esAdmin || esCajero)
        (nombre: 'Clientes', icono: Icons.people_outline, pagina: ClientesScreen(permisos: permisos)),
      if (permisos.contains('ventas:anular') || permisos.contains('reservas:anular') || esAdmin)
        (nombre: 'Anular Operación', icono: Icons.cancel_outlined, pagina: AnularOperacionScreen(permisos: permisos)),
      if (esAdmin || esEncargado || permisos.contains('reportes:ver'))
        (nombre: 'Reportes y Métricas', icono: Icons.insights_outlined, pagina: const ReportesScreen()),

      // Catálogo offline disponible para todos
      (nombre: 'Catálogo sin conexión', icono: Icons.offline_pin_outlined, pagina: ModoOfflineScreen(sesion: widget.sesion, sincronizador: sincronizador)),
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
