import 'package:flutter_test/flutter_test.dart';
import 'package:ridecompare_app/main.dart';

void main() {
  testWidgets('RideCompareApp renders splash screen', (WidgetTester tester) async {
    await tester.pumpWidget(const RideCompareApp());
    expect(find.text('RideCompare'), findsOneWidget);
    await tester.pump(const Duration(seconds: 2));
  });
}
