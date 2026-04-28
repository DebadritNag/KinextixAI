import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kinetix_ai/theme/kinetix_theme.dart';
import 'package:kinetix_ai/widgets/error_retry.dart';

/// Helper that wraps [child] in a MaterialApp with the given [brightness].
Widget _buildApp({
  required Widget child,
  Brightness brightness = Brightness.dark,
}) {
  return MaterialApp(
    theme: brightness == Brightness.dark
        ? KinetixTheme.darkTheme()
        : KinetixTheme.lightTheme(),
    home: Scaffold(body: child),
  );
}

void main() {
  group('ErrorRetry', () {
    testWidgets('displays default error message', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: ErrorRetry(onRetry: () {}),
        ),
      );

      expect(
        find.text('Something went wrong. Please try again.'),
        findsOneWidget,
      );
    });

    testWidgets('displays custom error message', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: ErrorRetry(
            message: 'Network error occurred',
            onRetry: () {},
          ),
        ),
      );

      expect(find.text('Network error occurred'), findsOneWidget);
    });

    testWidgets('displays error icon', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: ErrorRetry(onRetry: () {}),
        ),
      );

      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });

    testWidgets('displays custom icon', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: ErrorRetry(
            icon: Icons.wifi_off,
            onRetry: () {},
          ),
        ),
      );

      expect(find.byIcon(Icons.wifi_off), findsOneWidget);
    });

    testWidgets('error icon uses danger color', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: ErrorRetry(onRetry: () {}),
        ),
      );

      final icon = tester.widget<Icon>(find.byIcon(Icons.error_outline));
      expect(icon.color, KinetixTheme.colorDanger);
    });

    testWidgets('displays Retry button text', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: ErrorRetry(onRetry: () {}),
        ),
      );

      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('displays refresh icon on button', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: ErrorRetry(onRetry: () {}),
        ),
      );

      expect(find.byIcon(Icons.refresh), findsOneWidget);
    });

    testWidgets('fires onRetry callback when Retry button is tapped',
        (tester) async {
      var retried = false;
      await tester.pumpWidget(
        _buildApp(
          child: ErrorRetry(onRetry: () => retried = true),
        ),
      );

      await tester.tap(find.text('Retry'));
      expect(retried, isTrue);
    });

    testWidgets('renders correctly in light mode', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          brightness: Brightness.light,
          child: ErrorRetry(onRetry: () {}),
        ),
      );

      expect(find.byType(ErrorRetry), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);

      // Icon should still use danger color in light mode.
      final icon = tester.widget<Icon>(find.byIcon(Icons.error_outline));
      expect(icon.color, KinetixTheme.colorDanger);
    });

    testWidgets('icon has semantic label for accessibility', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: ErrorRetry(onRetry: () {}),
        ),
      );

      final icon = tester.widget<Icon>(find.byIcon(Icons.error_outline));
      expect(icon.semanticLabel, 'Error');
    });
  });
}
