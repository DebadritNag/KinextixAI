import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kinetix_ai/widgets/opaque_data_text.dart';
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
  group('OpaqueDataText', () {
    testWidgets('renders the provided text', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const OpaqueDataText(text: '42.5%'),
        ),
      );

      expect(find.text('42.5%'), findsOneWidget);
    });

    testWidgets('dark mode uses colorPrimary (#0F172A) as background', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          brightness: Brightness.dark,
          child: const OpaqueDataText(text: 'metric'),
        ),
      );

      final containerFinder = find.byType(Container);
      // The first Container in the tree is the OpaqueDataText wrapper.
      final Container container = tester.widgetList<Container>(containerFinder)
          .firstWhere((c) => c.decoration != null);
      final decoration = container.decoration as BoxDecoration;

      expect(decoration.color, KinetixTheme.colorPrimary);
    });

    testWidgets('light mode uses lightSurface (#FFFFFF) as background', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          brightness: Brightness.light,
          child: const OpaqueDataText(text: 'metric'),
        ),
      );

      final Container container = tester.widgetList<Container>(
        find.byType(Container),
      ).firstWhere((c) => c.decoration != null);
      final decoration = container.decoration as BoxDecoration;

      expect(decoration.color, KinetixTheme.lightSurface);
    });

    testWidgets('accepts custom backgroundColor override', (tester) async {
      const customColor = Color(0xFF112233);

      await tester.pumpWidget(
        _buildApp(
          child: const OpaqueDataText(
            text: 'custom',
            backgroundColor: customColor,
          ),
        ),
      );

      final Container container = tester.widgetList<Container>(
        find.byType(Container),
      ).firstWhere((c) => c.decoration != null);
      final decoration = container.decoration as BoxDecoration;

      expect(decoration.color, customColor);
    });

    testWidgets('applies custom text style when provided', (tester) async {
      const customStyle = TextStyle(fontSize: 24, color: Colors.red);

      await tester.pumpWidget(
        _buildApp(
          child: const OpaqueDataText(text: 'styled', style: customStyle),
        ),
      );

      final Text textWidget = tester.widget(find.text('styled'));
      expect(textWidget.style?.fontSize, 24);
      expect(textWidget.style?.color, Colors.red);
    });

    testWidgets('has horizontal and vertical padding', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const OpaqueDataText(text: 'padded'),
        ),
      );

      final Container container = tester.widgetList<Container>(
        find.byType(Container),
      ).firstWhere((c) => c.decoration != null);

      expect(
        container.padding,
        const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      );
    });

    testWidgets('has rounded corners (borderRadius 6)', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const OpaqueDataText(text: 'rounded'),
        ),
      );

      final Container container = tester.widgetList<Container>(
        find.byType(Container),
      ).firstWhere((c) => c.decoration != null);
      final decoration = container.decoration as BoxDecoration;

      expect(decoration.borderRadius, BorderRadius.circular(6));
    });
  });
}
