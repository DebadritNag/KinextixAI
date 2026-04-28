import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:kinetix_ai/pages/login_page.dart';
import 'package:kinetix_ai/theme/kinetix_theme.dart';
import 'package:kinetix_ai/widgets/glass_card.dart';

/// Builds a testable app wrapping [LoginPage] with Riverpod and GoRouter.
Widget _buildApp({
  Brightness brightness = Brightness.dark,
  List<Override>? overrides,
}) {
  final router = GoRouter(
    initialLocation: '/login',
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginPage(),
      ),
      GoRoute(
        path: '/dashboard',
        builder: (context, state) => const Scaffold(
          body: Center(child: Text('Dashboard')),
        ),
      ),
    ],
  );

  return ProviderScope(
    overrides: overrides ?? [],
    child: MaterialApp.router(
      routerConfig: router,
      theme: brightness == Brightness.dark
          ? KinetixTheme.darkTheme()
          : KinetixTheme.lightTheme(),
    ),
  );
}

void main() {
  group('LoginPage', () {
    testWidgets('renders branding, form fields, and sign-in button',
        (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      // Branding
      expect(find.text('Kinetix AI'), findsOneWidget);
      expect(find.text('Supply Chain Intelligence'), findsOneWidget);

      // Form heading
      expect(find.text('Sign In'), findsWidgets);
      expect(
          find.text('Enter any credentials to continue'), findsOneWidget);

      // Input fields
      expect(find.widgetWithText(TextFormField, 'Username'), findsOneWidget);
      expect(find.widgetWithText(TextFormField, 'Password'), findsOneWidget);

      // Submit button
      expect(find.widgetWithText(ElevatedButton, 'Sign In'), findsOneWidget);
    });

    testWidgets('password field obscures text', (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      // Find the password TextFormField by its label
      final passwordFields = tester.widgetList<EditableText>(
        find.byType(EditableText),
      );
      // The second EditableText is the password field
      final passwordField = passwordFields.elementAt(1);
      expect(passwordField.obscureText, isTrue);
    });

    testWidgets('shows validation errors when fields are empty',
        (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      // Tap sign in without entering anything
      await tester.tap(find.widgetWithText(ElevatedButton, 'Sign In'));
      await tester.pumpAndSettle();

      expect(find.text('Please enter a username'), findsOneWidget);
      expect(find.text('Please enter a password'), findsOneWidget);
    });

    testWidgets('shows validation error for empty username only',
        (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      // Enter password but not username
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Password'),
        'secret',
      );
      await tester.tap(find.widgetWithText(ElevatedButton, 'Sign In'));
      await tester.pumpAndSettle();

      expect(find.text('Please enter a username'), findsOneWidget);
      expect(find.text('Please enter a password'), findsNothing);
    });

    testWidgets('renders correctly in light mode', (tester) async {
      await tester.pumpWidget(_buildApp(brightness: Brightness.light));
      await tester.pumpAndSettle();

      // Core elements still present
      expect(find.text('Kinetix AI'), findsOneWidget);
      expect(find.widgetWithText(ElevatedButton, 'Sign In'), findsOneWidget);
    });

    testWidgets('renders correctly in dark mode', (tester) async {
      await tester.pumpWidget(_buildApp(brightness: Brightness.dark));
      await tester.pumpAndSettle();

      expect(find.text('Kinetix AI'), findsOneWidget);
      expect(find.widgetWithText(ElevatedButton, 'Sign In'), findsOneWidget);
    });

    testWidgets('contains GlassCard wrapping the form', (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.byType(GlassCard), findsOneWidget);
    });

    testWidgets('form has icon prefixes on input fields', (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.person_outline), findsOneWidget);
      expect(find.byIcon(Icons.lock_outline), findsOneWidget);
    });

    testWidgets('hub icon is displayed in the logo area', (tester) async {
      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.hub_outlined), findsOneWidget);
    });
  });
}
