import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kinetix_ai/models/optimization.dart';
import 'package:kinetix_ai/providers/routes_provider.dart';
import 'package:kinetix_ai/theme/kinetix_theme.dart';
import 'package:kinetix_ai/widgets/route_optimization_cards.dart';

const _testShipmentId = 'SHP-TEST-001';

/// Sample route options for testing.
final _sampleRoutes = [
  const RouteOption(
    routeId: 'r1',
    waypoints: ['Shanghai', 'Singapore', 'Rotterdam'],
    label: 'cheapest',
    costUsd: 1200,
    etaHours: 72.5,
    carbonKg: 450,
    riskScore: 35,
    score: 0.42,
    isRecommended: true,
  ),
  const RouteOption(
    routeId: 'r2',
    waypoints: ['Shanghai', 'Dubai', 'Rotterdam'],
    label: 'fastest',
    costUsd: 2800,
    etaHours: 36.0,
    carbonKg: 680,
    riskScore: 50,
    score: 0.55,
  ),
  const RouteOption(
    routeId: 'r3',
    waypoints: ['Shanghai', 'Mumbai', 'Suez', 'Rotterdam'],
    label: 'greenest',
    costUsd: 1800,
    etaHours: 96.0,
    carbonKg: 280,
    riskScore: 20,
    score: 0.61,
  ),
];

/// Wraps [RouteOptimizationCards] in a testable widget tree with overridden
/// [routeOptionsProvider].
Widget _buildApp({
  required AsyncValue<List<RouteOption>> routesValue,
  Brightness brightness = Brightness.dark,
}) {
  return ProviderScope(
    overrides: [
      routeOptionsProvider(_testShipmentId).overrideWith((ref) {
        return routesValue.when(
          data: (data) => Future.value(data),
          loading: () {
            final completer = Completer<List<RouteOption>>();
            ref.onDispose(() {
              if (!completer.isCompleted) completer.complete([]);
            });
            return completer.future;
          },
          error: (e, _) => Future.error(e),
        );
      }),
    ],
    child: MaterialApp(
      theme: brightness == Brightness.dark
          ? KinetixTheme.darkTheme()
          : KinetixTheme.lightTheme(),
      home: Scaffold(
        body: SingleChildScrollView(
          child: RouteOptimizationCards(shipmentId: _testShipmentId),
        ),
      ),
    ),
  );
}

void main() {
  group('RouteOptimizationCards', () {
    testWidgets('displays section header with title', (tester) async {
      await tester.pumpWidget(
        _buildApp(routesValue: AsyncValue.data(_sampleRoutes)),
      );
      await tester.pumpAndSettle();

      expect(find.text('Route Options'), findsOneWidget);
      expect(find.byIcon(Icons.alt_route_rounded), findsOneWidget);
    });

    testWidgets('displays shimmer loading state', (tester) async {
      await tester.pumpWidget(
        _buildApp(routesValue: const AsyncValue.loading()),
      );
      await tester.pump();

      expect(find.byType(RouteOptimizationCards), findsOneWidget);
    });

    testWidgets('displays error state with retry button', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          routesValue: AsyncValue.error(
            Exception('Network error'),
            StackTrace.current,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.text('Failed to load route options. Please try again.'),
        findsOneWidget,
      );
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('displays empty state when no routes', (tester) async {
      await tester.pumpWidget(
        _buildApp(routesValue: const AsyncValue.data([])),
      );
      await tester.pumpAndSettle();

      expect(find.text('No routes available'), findsOneWidget);
    });

    testWidgets('displays label badges for each route', (tester) async {
      await tester.pumpWidget(
        _buildApp(routesValue: AsyncValue.data(_sampleRoutes)),
      );
      await tester.pumpAndSettle();

      expect(find.text('CHEAPEST'), findsOneWidget);
      expect(find.text('FASTEST'), findsOneWidget);
      expect(find.text('GREENEST'), findsOneWidget);
    });

    testWidgets('displays RECOMMENDED badge on recommended route',
        (tester) async {
      await tester.pumpWidget(
        _buildApp(routesValue: AsyncValue.data(_sampleRoutes)),
      );
      await tester.pumpAndSettle();

      expect(find.text('RECOMMENDED'), findsOneWidget);
    });

    testWidgets('displays cost metric for each route', (tester) async {
      await tester.pumpWidget(
        _buildApp(routesValue: AsyncValue.data(_sampleRoutes)),
      );
      await tester.pumpAndSettle();

      expect(find.text('\$1,200'), findsOneWidget);
      expect(find.text('\$2,800'), findsOneWidget);
      expect(find.text('\$1,800'), findsOneWidget);
    });

    testWidgets('displays ETA metric for each route', (tester) async {
      await tester.pumpWidget(
        _buildApp(routesValue: AsyncValue.data(_sampleRoutes)),
      );
      await tester.pumpAndSettle();

      expect(find.text('72.5h'), findsOneWidget);
      expect(find.text('36.0h'), findsOneWidget);
      expect(find.text('96.0h'), findsOneWidget);
    });

    testWidgets('displays carbon metric for each route', (tester) async {
      await tester.pumpWidget(
        _buildApp(routesValue: AsyncValue.data(_sampleRoutes)),
      );
      await tester.pumpAndSettle();

      expect(find.text('450kg CO\u2082'), findsOneWidget);
      expect(find.text('680kg CO\u2082'), findsOneWidget);
      expect(find.text('280kg CO\u2082'), findsOneWidget);
    });

    testWidgets('displays risk metric for each route', (tester) async {
      await tester.pumpWidget(
        _buildApp(routesValue: AsyncValue.data(_sampleRoutes)),
      );
      await tester.pumpAndSettle();

      expect(find.text('35/100'), findsOneWidget);
      expect(find.text('50/100'), findsOneWidget);
      expect(find.text('20/100'), findsOneWidget);
    });

    testWidgets('displays waypoints for each route', (tester) async {
      await tester.pumpWidget(
        _buildApp(routesValue: AsyncValue.data(_sampleRoutes)),
      );
      await tester.pumpAndSettle();

      expect(
        find.text('Shanghai → Singapore → Rotterdam'),
        findsOneWidget,
      );
      expect(
        find.text('Shanghai → Dubai → Rotterdam'),
        findsOneWidget,
      );
      expect(
        find.text('Shanghai → Mumbai → Suez → Rotterdam'),
        findsOneWidget,
      );
    });

    testWidgets('renders correctly in light mode', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          routesValue: AsyncValue.data(_sampleRoutes),
          brightness: Brightness.light,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Route Options'), findsOneWidget);
      expect(find.text('CHEAPEST'), findsOneWidget);
    });

    testWidgets('limits display to 3 routes', (tester) async {
      final fourRoutes = [
        ..._sampleRoutes,
        const RouteOption(
          routeId: 'r4',
          waypoints: ['Shanghai', 'Tokyo', 'Rotterdam'],
          label: 'safest',
          costUsd: 3200,
          etaHours: 48.0,
          carbonKg: 520,
          riskScore: 10,
          score: 0.70,
        ),
      ];

      await tester.pumpWidget(
        _buildApp(routesValue: AsyncValue.data(fourRoutes)),
      );
      await tester.pumpAndSettle();

      // Only 3 label badges should appear (the 4th route is excluded)
      expect(find.text('CHEAPEST'), findsOneWidget);
      expect(find.text('FASTEST'), findsOneWidget);
      expect(find.text('GREENEST'), findsOneWidget);
      expect(find.text('SAFEST'), findsNothing);
    });
  });
}
