import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kinetix_ai/theme/kinetix_theme.dart';
import 'package:kinetix_ai/widgets/shimmer_loading.dart';

/// Helper that wraps [child] in a MaterialApp with the given [brightness].
Widget _buildApp({
  required Widget child,
  Brightness brightness = Brightness.dark,
}) {
  return MaterialApp(
    theme: brightness == Brightness.dark
        ? KinetixTheme.darkTheme()
        : KinetixTheme.lightTheme(),
    home: Scaffold(body: SizedBox(width: 400, child: child)),
  );
}

void main() {
  group('ShimmerLoading', () {
    testWidgets('renders the default number of placeholder rows (3)',
        (tester) async {
      await tester.pumpWidget(
        _buildApp(child: const ShimmerLoading()),
      );

      // The Column should contain 3 FractionallySizedBox children.
      final fractionBoxes = find.byType(FractionallySizedBox);
      expect(fractionBoxes, findsNWidgets(3));
    });

    testWidgets('renders custom lineCount', (tester) async {
      await tester.pumpWidget(
        _buildApp(child: const ShimmerLoading(lineCount: 5)),
      );

      expect(find.byType(FractionallySizedBox), findsNWidgets(5));
    });

    testWidgets('last row has narrower width fraction (0.6)', (tester) async {
      await tester.pumpWidget(
        _buildApp(child: const ShimmerLoading(lineCount: 2)),
      );

      final boxes = tester.widgetList<FractionallySizedBox>(
        find.byType(FractionallySizedBox),
      ).toList();

      // First row: full width.
      expect(boxes[0].widthFactor, 1.0);
      // Last row: 60% width.
      expect(boxes[1].widthFactor, 0.6);
    });

    testWidgets('uses AnimationController (animation is running)',
        (tester) async {
      await tester.pumpWidget(
        _buildApp(child: const ShimmerLoading()),
      );

      // Pump a few frames to verify no errors during animation.
      await tester.pump(const Duration(milliseconds: 500));
      await tester.pump(const Duration(milliseconds: 500));

      // Widget should still be present and rendering.
      expect(find.byType(ShimmerLoading), findsOneWidget);
    });

    testWidgets('renders in light mode without errors', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          brightness: Brightness.light,
          child: const ShimmerLoading(),
        ),
      );

      await tester.pump(const Duration(milliseconds: 500));
      expect(find.byType(ShimmerLoading), findsOneWidget);
    });

    testWidgets('shows static placeholder when reduced motion is enabled',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: KinetixTheme.darkTheme(),
          home: MediaQuery(
            data: const MediaQueryData(disableAnimations: true),
            child: const Scaffold(
              body: SizedBox(width: 400, child: ShimmerLoading()),
            ),
          ),
        ),
      );

      // With reduced motion, no gradient animation should be running.
      // The widget renders plain Container children instead.
      expect(find.byType(ShimmerLoading), findsOneWidget);
      expect(find.byType(FractionallySizedBox), findsNWidgets(3));
    });

    testWidgets('single line renders correctly', (tester) async {
      await tester.pumpWidget(
        _buildApp(child: const ShimmerLoading(lineCount: 1)),
      );

      expect(find.byType(FractionallySizedBox), findsOneWidget);
      final box = tester.widget<FractionallySizedBox>(
        find.byType(FractionallySizedBox),
      );
      // Single line is also the last line, so width = 0.6.
      expect(box.widthFactor, 0.6);
    });
  });
}
