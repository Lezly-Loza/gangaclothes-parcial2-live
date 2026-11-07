import 'package:flutter/material.dart';

const rosa = Color(0xffed0b56);
const negro = Color(0xff111318);
const papel = Color(0xfff2f1ec);
const borde = Color(0xffdeddd5);
final tema = ThemeData(
  useMaterial3: true, scaffoldBackgroundColor: papel,
  colorScheme: ColorScheme.fromSeed(seedColor: rosa, primary: rosa, surface: Colors.white),
  appBarTheme: const AppBarTheme(backgroundColor: negro, foregroundColor: Colors.white, centerTitle: false),
  inputDecorationTheme: InputDecorationTheme(filled: true, fillColor: Colors.white,
    border: OutlineInputBorder(borderRadius: BorderRadius.circular(11), borderSide: const BorderSide(color: borde)),
    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(11), borderSide: const BorderSide(color: borde))),
  cardTheme: CardThemeData(color: Colors.white, elevation: 0, shape: RoundedRectangleBorder(
      side: const BorderSide(color: borde), borderRadius: BorderRadius.circular(14))),
  filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(backgroundColor: rosa,
      foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)))),
);

class Marca extends StatelessWidget {
  const Marca({super.key, this.clara = false});
  final bool clara;
  @override Widget build(BuildContext context) => RichText(text: TextSpan(
    style: TextStyle(color: clara ? Colors.white : negro, fontSize: 20, fontWeight: FontWeight.w900),
    children: const [TextSpan(text: 'GANGA'), TextSpan(text: 'CLOTHES', style: TextStyle(color: rosa))]));
}
void aviso(BuildContext context, String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
String bs(dynamic n) => 'Bs ${(num.tryParse('$n') ?? 0).toStringAsFixed(2)}';
String fecha(dynamic valor) {
  final d = DateTime.tryParse('$valor');
  if (d == null) return 'Sin fecha';
  String dos(int n) => n.toString().padLeft(2, '0');
  return '${dos(d.day)}/${dos(d.month)}/${d.year} ${dos(d.hour)}:${dos(d.minute)}';
}
Map<String, dynamic> mapa(dynamic value) => Map<String, dynamic>.from(value as Map);
List<Map<String, dynamic>> mapas(dynamic value) => (value as List? ?? []).map(mapa).toList();
Widget vacio(String texto) => Padding(padding: const EdgeInsets.symmetric(vertical: 36),
    child: Center(child: Text(texto, textAlign: TextAlign.center, style: const TextStyle(color: Colors.black54))));
