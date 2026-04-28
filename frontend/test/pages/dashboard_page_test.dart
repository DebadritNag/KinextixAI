import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:kinetix_ai/models/alert.dart';
import 'package:kinetix_ai/models/shipment.dart';
import 'package:kinetix_ai/pages/dashboard_page.dart';
import 'package:kinetix_ai/providers/alerts_provider.dart';
import 'package:kinetix_ai/providers/auth_provider.dart';
import 'package:kinetix_ai/providers/shipments_provider.dart';
import 'package:kinetix_ai/theme/kinetix_theme.dart';

/// A pre-authenticated AuthNotifier for testing.
class _PreAuthNotifier extends AuthNotifier {
  _PreAuthNotifier() : super() {
    state = const AuthState(
      isAuthenticated: true,
      token: 'test-token',
      user: {'username': 'testuser'},
    );
  }
}

/// A fake [ShipmentsNotifier] that immediately emits a fixed state.
class _FakeShipmentsNotifier extends ShipmentsNotifier {
  _FakeShipmentsNotifier(ShipmentsState initialState) {
    state = initialState;
  }

  // Override to prevent the real timer/fetch from running.
  @override
  void dispose() {
    super.dispose();
  }
}

/// Builds a testable app wrapping [DashboardPage] with Riverpod and GoRouter.
///
/// Overrides [shipmentsProvider] and [alertsProvider] with mock data so the
/// widgets don't attempt real HTTP calls during tests.
Widget _buildApp({
  Brightness brightness = Brightness.dark,
}) {
  final router = GoRouter(
    initialLocation: '/dashboard',
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const Scaffold(
          body: Center(child: Text('Login Page')),
        ),
      ),
      GoRoute(
        path: '/dashboard',
        builder: (context, state) => const DashboardPage(),
        routes: [
          GoRoute(
            path: 'shipment/:id',
            builder: (context, state) => const Scaffold(
              body: Center(child: Text('Shipment Detail')),
            ),
          ),
        ],
      ),
      GoRoute(
        path: '/analytics',
        builder: (context, state) => const Scaffold(
          body: Center(child: Text('Analytics Page')),
        ),
      ),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const Scaffold(
          body: Center(child: Text('Settings Page')),
        ),
      ),
    ],
  );

  return ProviderScope(
    overrides: [
      authProvider.overrideWith((ref) => _PreAuthNotifier()),
      // Override with empty shipments in ready state
      shipmentsProvider.overrideWith(
        () => _FakeShipmentsNotifier(
          const ShipmentsState(shipments: [], isInitialLoading: false),
        ),
      ),
      alertsProvider.overrideWith((ref) async => <RiskAlert>[]),
    ],
    child: MaterialApp.router(
      routerConfig: router,
      theme: brightness == Brightness.dark
          ? KinetixTheme.darkTheme()
          : KinetixTheme.lightTheme(),
    ),
  );
}

void main() {
  group('DashboardPage - Desktop layout', () {
    testWidgets('renders sidebar with nav items and top bar', (tester) async {
      // Set desktop size with enough height for the full dashboard body
      // (MapView ~400px + IntrinsicHeight row with RiskAlertsPanel ~460px + WeightSliders + padding)
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      // Sidebar nav items
      expect(find.text('Dashboard'), findsOneWidget);
      expect(find.text('Analytics'), findsOneWidget);
      expect(find.text('Settings'), findsOneWidget);

      // Sidebar icons
      expect(find.byIcon(Icons.dashboard_outlined), findsOneWidget);
      expect(find.byIcon(Icons.analytics_outlined), findsOneWidget);
      expect(find.byIcon(Icons.settings_outlined), findsOneWidget);

      // Top bar search icon
      expect(find.byIcon(Icons.search), findsOneWidget);

      // Dashboard body content (MapView, RiskAlertsPanel, WeightSliders)
      expect(find.text('Shipment Map'), findsOneWidget);
    });

    testWidgets('renders brand logo in sidebar', (tester) async {
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.text('Kinetix AI'), findsOneWidget);
      expect(find.byIcon(Icons.hub_outlined), findsOneWidget);
    });

    testWidgets('renders theme toggle button', (tester) async {
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      // In dark mode, should show light_mode icon to switch
      expect(find.byIcon(Icons.light_mode), findsOneWidget);
    });

    testWidgets('renders user avatar', (tester) async {
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.person_outline), findsOneWidget);
    });

    testWidgets('renders version footer', (tester) async {
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.text('v1.0.0'), findsOneWidget);
    });

    testWidgets('renders correctly in light mode', (tester) async {
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(_buildApp(brightness: Brightness.light));
      await tester.pumpAndSettle();

      expect(find.text('Dashboard'), findsOneWidget);
      expect(find.text('Shipment Map'), findsOneWidget);
    });

    testWidgets('search field is present', (tester) async {
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      expect(find.byType(TextField), findsOneWidget);
    });
  });

  group('DashboardPage - Tablet layout', () {
    testWidgets('renders compact sidebar with icons only', (tester) async {
      tester.view.physicalSize = const Size(900, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      // Icons should be present
      expect(find.byIcon(Icons.dashboard_outlined), findsOneWidget);
      expect(find.byIcon(Icons.analytics_outlined), findsOneWidget);
      expect(find.byIcon(Icons.settings_outlined), findsOneWidget);

      // Dashboard body content
      expect(find.text('Shipment Map'), findsOneWidget);
    });
  });

  group('DashboardPage - Mobile layout', () {
    testWidgets('renders with app bar and menu button', (tester) async {
      tester.view.physicalSize = const Size(400, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      // Mobile app bar shows brand name
      expect(find.text('Kinetix AI'), findsOneWidget);

      // Menu button should be present
      expect(find.byIcon(Icons.menu), findsOneWidget);

      // Dashboard body content
      expect(find.text('Shipment Map'), findsOneWidget);
    });

    testWidgets('opens drawer when menu button is tapped', (tester) async {
      tester.view.physicalSize = const Size(400, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(_buildApp());
      await tester.pumpAndSettle();

      // Tap menu button
      await tester.tap(find.byIcon(Icons.menu));
      await tester.pumpAndSettle();

      // Drawer should show nav items with labels
      expect(find.text('Dashboard'), findsWidgets);
      expect(find.text('Analytics'), findsOneWidget);
      expect(find.text('Settings'), findsOneWidget);
    });
  });
}
