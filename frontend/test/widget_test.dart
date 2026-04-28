import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:kinetix_ai/main.dart';

void main() {
  testWidgets('App renders smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: KinetixApp(),
      ),
    );

    // The app now uses go_router; the initial route '/' shows the Landing Page.
    // The landing page displays the hero tagline instead of a placeholder title.
    expect(find.text('Predict. Optimize. Deliver.'), findsOneWidget);
  });
}
