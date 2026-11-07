import 'package:flutter_test/flutter_test.dart';
import 'package:gangaclothes_mobile/main.dart';

void main() {
  testWidgets('login presenta los tres campos del tenant', (tester) async {
    await tester.pumpWidget(const GangaApp());
    expect(find.text('Código de tenant'), findsOneWidget);
    expect(find.text('Correo'), findsOneWidget);
    expect(find.text('Contraseña'), findsOneWidget);
  });
}
