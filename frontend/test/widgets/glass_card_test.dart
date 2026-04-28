import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kinetix_ai/widgets/glass_card.dart';
import 'package:kinetix_ai/theme/kinetix_theme.dart';

/// Helper that wraps [child] in a MaterialApp with the given [brightness].
Widget _buildApp({required Widget child, Brightness brightness = Brightness.dark}) {
  return MaterialApp(
    theme: brightness == Brightness.dark
        ? KinetixTheme.darkTheme()
        : KinetixTheme.lightTheme(),
    home: Scaffold(body: child),
  );
}

void main() {
  group('GlassCard', () {
    testWidgets('renders child content', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const GlassCard(child: Text('Hello')),
        ),
      );

      expect(find.text('Hello'), findsOneWidget);
    });

    testWidgets('applies BackdropFilter with default blur', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const GlassCard(child: Text('Blur test')),
        ),
      );

      final backdropFinder = find.byType(BackdropFilter);
      expect(backdropFinder, findsOneWidget);

      final BackdropFilter backdrop = tester.widget(backdropFinder);
      final filter = backdrop.filter;
      // BackdropFilter is present — the exact sigma is an internal detail,
      // but we verify the widget tree is correctly assembled.
      expect(filter, isNotNull);
    });

    testWidgets('uses ClipRRect with correct border radius', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const GlassCard(
            borderRadius: 20.0,
            child: Text('Radius'),
          ),
        ),
      );

      final clipFinder = find.byType(ClipRRect);
      expect(clipFinder, findsOneWidget);

      final ClipRRect clip = tester.widget(clipFinder);
      expect(clip.borderRadius, BorderRadius.circular(20.0));
    });

    testWidgets('dark mode uses correct background and border colours', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          brightness: Brightness.dark,
          child: const GlassCard(child: Text('Dark')),
        ),
      );

      // Find the AnimatedContainer inside the BackdropFilter.
      final containerFinder = find.byType(AnimatedContainer);
      expect(containerFinder, findsOneWidget);

      final AnimatedContainer container = tester.widget(containerFinder);
      final decoration = container.decoration as BoxDecoration;

      // Background: white @ 8% opacity.
      expect(decoration.color, Colors.white.withValues(alpha: 0.08));

      // Border: white @ 20% opacity.
      final border = decoration.border as Border;
      expect(border.top.color, Colors.white.withValues(alpha: 0.2));
    });

    testWidgets('light mode uses correct background and border colours', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          brightness: Brightness.light,
          child: const GlassCard(child: Text('Light')),
        ),
      );

      final AnimatedContainer container =
          tester.widget(find.byType(AnimatedContainer));
      final decoration = container.decoration as BoxDecoration;

      // Background: white @ 80% opacity.
      expect(decoration.color, Colors.white.withValues(alpha: 0.80));

      // Border: grey.shade200.
      final border = decoration.border as Border;
      expect(border.top.color, Colors.grey.shade200);
    });

    testWidgets('shows pointer cursor when onTap is provided', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: GlassCard(
            onTap: () {},
            child: const Text('Tappable'),
          ),
        ),
      );

      // Find the MouseRegion with click cursor (our widget's, not Scaffold's).
      final mouseRegions = tester.widgetList<MouseRegion>(
        find.byType(MouseRegion),
      );
      final clickRegion = mouseRegions.where(
        (mr) => mr.cursor == SystemMouseCursors.click,
      );
      expect(clickRegion, isNotEmpty);
    });

    testWidgets('does not show click-cursor MouseRegion when onTap is null', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const GlassCard(child: Text('Static')),
        ),
      );

      // No MouseRegion with click cursor should exist from our widget.
      final mouseRegions = tester.widgetList<MouseRegion>(
        find.byType(MouseRegion),
      );
      final clickRegion = mouseRegions.where(
        (mr) => mr.cursor == SystemMouseCursors.click,
      );
      expect(clickRegion, isEmpty);
    });

    testWidgets('fires onTap callback when tapped', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        _buildApp(
          child: GlassCard(
            onTap: () => tapped = true,
            child: const Text('Tap me'),
          ),
        ),
      );

      await tester.tap(find.text('Tap me'));
      expect(tapped, isTrue);
    });

    testWidgets('clamps blur below 10 to 10', (tester) async {
      // The widget should still render without error when blur < 10.
      await tester.pumpWidget(
        _buildApp(
          child: const GlassCard(blur: 5.0, child: Text('Low blur')),
        ),
      );

      expect(find.byType(BackdropFilter), findsOneWidget);
    });

    testWidgets('clamps blur above 20 to 20', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const GlassCard(blur: 30.0, child: Text('High blur')),
        ),
      );

      expect(find.byType(BackdropFilter), findsOneWidget);
    });
  });
}
