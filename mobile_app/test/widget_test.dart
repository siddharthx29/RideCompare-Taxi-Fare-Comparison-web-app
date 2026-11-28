import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ridecompare_app/main.dart';
import 'package:ridecompare_app/screens/onboarding_screen.dart';
import 'package:ridecompare_app/screens/splash_screen.dart';

void main() {
  testWidgets('RideCompareApp transitions from splash to onboarding and skips to MainShell', (WidgetTester tester) async {
    await tester.pumpWidget(const RideCompareApp());
    expect(find.byType(SplashScreen), findsOneWidget);
    expect(find.byType(Image), findsAtLeastNWidgets(1));

    await tester.pump(const Duration(seconds: 3));
    await tester.pumpAndSettle();

    expect(find.byType(OnboardingScreen), findsOneWidget);
    await tester.tap(find.text('Skip'));
    await tester.pumpAndSettle();

    expect(find.byType(MainShell), findsOneWidget);
  });

  testWidgets('OnboardingScreen renders CTA and slides', (WidgetTester tester) async {
    var completed = false;
    await tester.pumpWidget(MaterialApp(home: OnboardingScreen(onComplete: () => completed = true)));
    expect(find.text('RideCompare'), findsOneWidget);
    expect(find.text('Continue'), findsOneWidget);
    await tester.tap(find.text('Skip'));
    expect(completed, isTrue);
  });
}
