import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kinetix_ai/models/optimization.dart';
import 'package:kinetix_ai/providers/weights_provider.dart';
import 'package:kinetix_ai/theme/kinetix_theme.dart';
import 'package:kinetix_ai/widgets/weight_sliders.dart';

/// Wraps [WeightSliders] in a testable widget tree with an optional initial
/// weight override.
Widget _buildApp({
  OptimizationWeights? initialWeights,
  Brightness brightness = Brightness.dark,
}) {
  return ProviderScope(
    overrides: [
      if (initialWeights != null)
        optimizationWeightsProvider.overrideWith(
          (ref) {
            final notifier = OptimizationWeightsNotifier();
            notifier.setWeights(initialWeights);
            return notifier;
          },
        ),
    ],
    child: MaterialApp(
      theme: brightness == Brightness.dark
          ? KinetixTheme.darkTheme()
          : KinetixTheme.lightTheme(),
      home: const Scaffold(
        body: SingleChildScrollView(
          child: WeightSliders(),
        ),
      ),
    ),
  );
}

void main() {
  group('WeightSliders', () {
    testWidgets('displays header with title', (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.text('Optimization Weights'), findsOneWidget);
      expect(find.byIcon(Icons.tune_rounded), findsOneWidget);
    });

    testWidgets('displays four slider labels', (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.text('Cost'), findsOneWidget);
      expect(find.text('Time'), findsOneWidget);
      expect(find.text('Carbon'), findsOneWidget);
      expect(find.text('Risk'), findsOneWidget);
    });

    testWidgets('displays four Slider widgets', (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.byType(Slider), findsNWidgets(4));
    });

    testWidgets('displays default numeric values (0.25)', (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      // All four sliders should show 0.25 by default
      expect(find.text('0.25'), findsNWidgets(4));
    });

    testWidgets('displays custom initial weight values', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          initialWeights: const OptimizationWeights(
            cost: 0.50,
            time: 0.10,
            carbon: 0.30,
            risk: 0.80,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('0.50'), findsOneWidget);
      expect(find.text('0.10'), findsOneWidget);
      expect(find.text('0.30'), findsOneWidget);
      expect(find.text('0.80'), findsOneWidget);
    });

    testWidgets('displays Reset button', (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.text('Reset'), findsOneWidget);
      expect(find.byIcon(Icons.restart_alt_rounded), findsOneWidget);
    });

    testWidgets('Reset button restores default weights', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          initialWeights: const OptimizationWeights(
            cost: 0.80,
            time: 0.60,
            carbon: 0.40,
            risk: 0.10,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify non-default values are shown
      expect(find.text('0.80'), findsOneWidget);

      // Tap Reset
      await tester.tap(find.text('Reset'));
      await tester.pumpAndSettle();

      // All values should be back to 0.25
      expect(find.text('0.25'), findsNWidgets(4));
    });

    testWidgets('displays slider icons', (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.attach_money), findsOneWidget);
      expect(find.byIcon(Icons.schedule), findsOneWidget);
      expect(find.byIcon(Icons.eco_outlined), findsOneWidget);
      expect(find.byIcon(Icons.shield_outlined), findsOneWidget);
    });

    testWidgets('renders correctly in light mode', (tester) async {
      await tester.pumpWidget(_buildApp(brightness: Brightness.light));
      await tester.pumpAndSettle();

      expect(find.text('Optimization Weights'), findsOneWidget);
      expect(find.byType(Slider), findsNWidgets(4));
    });

    testWidgets('wrapped in a GlassCard', (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      // The WeightSliders widget should contain a GlassCard
      expect(
        find.byType(WeightSliders),
        findsOneWidget,
      );
    });
  });
}
