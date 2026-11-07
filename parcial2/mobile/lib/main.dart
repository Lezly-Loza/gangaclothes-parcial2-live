import 'package:flutter/material.dart';
import 'api_service.dart';
import 'producto_local_dao.dart';

final api = ApiService();
void main() => runApp(const GangaApp());

class GangaApp extends StatelessWidget {
  const GangaApp({super.key});
  @override Widget build(BuildContext context) => MaterialApp(
    title: 'GangaClothes', theme: ThemeData(colorSchemeSeed: const Color(0xff263469)),
    home: const LoginScreen());
}

Widget field(String label, TextEditingController ctrl, {bool secret=false}) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 6),
  child: TextField(controller: ctrl, obscureText: secret, decoration: InputDecoration(
    labelText: label, border: const OutlineInputBorder())));

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override State<LoginScreen> createState() => _LoginScreenState();
}
class _LoginScreenState extends State<LoginScreen> {
  final tenant=TextEditingController(text:'luna');
  final email=TextEditingController(text:'vendedor@boutique-luna.bo');
  final password=TextEditingController(text:'Luna12345');
  String error='';
  Future<void> login() async {
    try {
      final session=await api.login({'codigo_tenant':tenant.text,'email':email.text,'password':password.text});
      if (!mounted) return;
      Navigator.pushReplacement(context, MaterialPageRoute(builder:(_)=>HomeScreen(rol:(session['roles'] as List).first.toString())));
    } catch (e) {setState(()=>error='Credenciales incorrectas o sin conexión');}
  }
  @override Widget build(BuildContext context) => Scaffold(appBar:AppBar(title:const Text('GangaClothes')),
    body:ListView(padding:const EdgeInsets.all(20),children:[const Text('Iniciar sesión',style:TextStyle(fontSize:26)),
      field('Código de tenant',tenant),field('Correo',email),field('Contraseña',password,secret:true),
      FilledButton(onPressed:login,child:const Text('Ingresar')),Text(error)]));
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key,required this.rol});final String rol;
  @override Widget build(BuildContext context) {
    final pages=<String,Widget>{
      if(rol=='vendedor'||rol=='admin') 'Clientes':const ClientesScreen(),
      if(rol=='cliente') 'Reservar':const ReservarPrendaScreen(),
      if(rol=='vendedor'||rol=='cliente') 'Carrito':const CarritoScreen(),
      if(rol=='encargado') 'Anular':const AnularOperacionScreen(),
      if(rol=='vendedor') 'Modo offline':const ModoOfflineScreen(),
    };
    return Scaffold(appBar:AppBar(title:Text('GangaClothes · $rol')),
      body:ListView(children:pages.entries.map((e)=>ListTile(title:Text(e.key),trailing:const Icon(Icons.chevron_right),
        onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>e.value)))).toList()));
  }
}

class ClientesScreen extends StatefulWidget {
  const ClientesScreen({super.key});
  @override State<ClientesScreen> createState()=>_ClientesScreenState();
}
class _ClientesScreenState extends State<ClientesScreen> {
  final q=TextEditingController();List<dynamic> clientes=[];String mensaje='';
  @override void initState(){super.initState();buscarClientes('');}
  Future<void> buscarClientes(String termino) async {try{final rows=await api.buscarClientes(termino);setState(()=>clientes=rows);}catch(e){setState(()=>mensaje='Sin conexión');}}
  Future<void> crearCliente(Map<String,dynamic> datos) async {await api.crearCliente(datos);await buscarClientes(q.text);}
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Buscar clientes')),
    body:ListView(padding:const EdgeInsets.all(16),children:[field('Nombre o documento',q),
      FilledButton(onPressed:()=>buscarClientes(q.text),child:const Text('Buscar')),Text(mensaje),
      ...clientes.map((c)=>ListTile(title:Text('${c['nombre']}'),subtitle:Text('${c['documento']}')))]));
}

class ReservarPrendaScreen extends StatefulWidget {
  const ReservarPrendaScreen({super.key});
  @override State<ReservarPrendaScreen> createState()=>_ReservarPrendaScreenState();
}
class _ReservarPrendaScreenState extends State<ReservarPrendaScreen> {
  final variante=TextEditingController(text:'2'), sucursal=TextEditingController(text:'1');
  final cliente=TextEditingController(text:'1'), cantidad=TextEditingController(text:'1');String codigo='';
  void elegirPrenda(){variante.text='1';}
  Future<void> reservar([dynamic varianteArg, dynamic sucursalArg, dynamic cantidadArg]) async {
    try {final r=await api.crearReserva({'variante_id':varianteArg is int ? varianteArg : int.parse(variante.text),
      'sucursal_id':sucursalArg is int ? sucursalArg : int.parse(sucursal.text),'cliente_id':int.parse(cliente.text),
      'cantidad':cantidadArg is int ? cantidadArg : int.parse(cantidad.text)});setState(()=>codigo='Reserva confirmada: ${r['codigo']}');mostrarCodigo();}
    catch(e){setState(()=>codigo='No se pudo reservar: $e');}
  }
  String mostrarCodigo()=>codigo;
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Reservar prenda')),
    body:ListView(padding:const EdgeInsets.all(16),children:[field('Variante',variante),field('Sucursal',sucursal),
      field('Cliente',cliente),field('Cantidad',cantidad),FilledButton(onPressed:()=>reservar(),child:const Text('Reservar')),Text(codigo)]));
}

class CarritoScreen extends StatefulWidget {
  const CarritoScreen({super.key});
  @override State<CarritoScreen> createState()=>_CarritoScreenState();
}
class _CarritoScreenState extends State<CarritoScreen> {
  final variante=TextEditingController(text:'1'),cantidad=TextEditingController(text:'1');
  final sucursal=TextEditingController(text:'1'),cliente=TextEditingController(text:'1');
  final List<Map<String,int>> items=[];String comprobante='';
  void agregarItem(int variante,int cant){setState(()=>items.add({'variante_id':variante,'cantidad':cant}));}
  int calcularTotal()=>items.fold(0,(total,item)=>total+item['cantidad']!);
  Future<void> confirmarVenta([dynamic datos]) async {try{final r=await api.registrarVenta({
    'sucursal_id':int.parse(sucursal.text),'cliente_id':int.parse(cliente.text),
    'forma_pago':'EFECTIVO','items':items});setState(()=>comprobante='${r['comprobante']} · Bs ${r['total']}');mostrarComprobante();}
    catch(e){setState(()=>comprobante='No se pudo vender: $e');}}
  String mostrarComprobante()=>comprobante;
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Carrito')),
    body:ListView(padding:const EdgeInsets.all(16),children:[field('Variante',variante),field('Cantidad',cantidad),
      FilledButton(onPressed:()=>agregarItem(int.parse(variante.text),int.parse(cantidad.text)),child:const Text('Agregar')),
      ...items.map((i)=>ListTile(title:Text('Variante ${i['variante_id']} × ${i['cantidad']}'))),
      Text('Total de unidades: ${calcularTotal()}'),field('Sucursal',sucursal),field('Cliente',cliente),
      FilledButton(onPressed:()=>confirmarVenta(),child:const Text('Confirmar venta')),Text(comprobante)]));
}

class AnularOperacionScreen extends StatefulWidget {
  const AnularOperacionScreen({super.key});
  @override State<AnularOperacionScreen> createState()=>_AnularOperacionScreenState();
}
class _AnularOperacionScreenState extends State<AnularOperacionScreen> {
  final id=TextEditingController(text:'1'),motivo=TextEditingController(text:'Solicitud del cliente');String resultado='';
  int buscarOperacion()=>int.parse(id.text);
  Future<void> anular(int id,String motivo) async {try{final r=await api.anular(id,motivo);setState(()=>resultado='Operación ${r['estado']}');mostrarAnulada();}
    catch(e){setState(()=>resultado='No se pudo anular: $e');}}
  String mostrarAnulada()=>resultado;
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Anular operación')),
    body:ListView(padding:const EdgeInsets.all(16),children:[field('Venta ID',id),field('Motivo',motivo),
      FilledButton(onPressed:()=>anular(buscarOperacion(),motivo.text),child:const Text('Anular')),Text(resultado)]));
}

class ModoOfflineScreen extends StatefulWidget {
  const ModoOfflineScreen({super.key});
  @override State<ModoOfflineScreen> createState()=>_ModoOfflineScreenState();
}
class _ModoOfflineScreenState extends State<ModoOfflineScreen> {
  final dao=ProductoLocalDao();int disponibles=0;String fecha='';
  @override void initState(){super.initState();abrirModoOffline();}
  Future<void> abrirModoOffline() async {setState(()=>disponibles=0);final n=await dao.contarProductos();final f=await dao.fechaDescarga();setState((){disponibles=n;fecha=f;});}
  Future<void> prepararOffline([dynamic filtros]) async {try{final data=await api.descargarCatalogo({'sucursal_id':1});
    await dao.guardarCatalogoLocal(data);}catch(e){/* Conserva datos locales. */}await abrirModoOffline();mostrarDisponibles();}
  int mostrarDisponibles()=>disponibles;
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Modo offline')),
    body:ListView(padding:const EdgeInsets.all(16),children:[FilledButton(onPressed:()=>prepararOffline(),child:const Text('Preparar offline')),
      Text('$disponibles productos disponibles offline',style:const TextStyle(fontSize:22)),Text('Última descarga: $fecha')]));
}

