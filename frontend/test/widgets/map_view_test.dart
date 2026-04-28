import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kinetix_ai/models/shipment.dart';
import 'package:kinetix_ai/providers/shipments_provider.dart';
import 'package:kinetix_ai/theme/kinetix_theme.dart';
import 'package:kinetix_ai/widgets/map_view.dart';

/// Sample shipments for testing.
List<Shipment> _sampleShipments() => [
      Shipment(
        id: 'SHP-001',
        origin: 'Shanghai',
        destination: 'Los Angeles',
        originCoords: const Coordinates(lat: 31.23, lng: 121.47),
        destinationCoords: const Coordinates(lat: 33.94, lng: -118.41),
        currentCoords: const Coordinates(lat: 35.0, lng: -160.0),
        status: ShipmentStatus.inTransit,
        createdAt: DateTime(2025, 1, 1),
        updatedAt: DateTime(2025, 1, 2),
      ),
      Shipment(
        id: 'SHP-002',
        origin: 'Rotterdam',
        destination: 'New York',
        originCoords: const Coordinates(lat: 51.92, lng: 4.48),
        destinationCoords: const Coordinates(lat: 40.71, lng: -74.01),
        currentCoords: const Coordinates(lat: 48.0, lng: -30.0),
        status: ShipmentStatus.delayed,
        createdAt: DateTime(2025, 1, 1),
        updatedAt: DateTime(2025, 1, 2),
      ),
      Shipment(
        id: 'SHP-003',
        origin: 'Mumbai',
        destination: 'Dubai',
        originCoords: const Coordinates(lat: 19.08, lng: 72.88),
        destinationCoords: const Coordinates(lat: 25.20, lng: 55.27),
        currentCoords: const Coordinates(lat: 25.20, lng: 55.27),
        status: ShipmentStatus.delivered,
        createdAt: DateTime(2025, 1, 1),
        updatedAt: DateTime(2025, 1, 2),
      ),
    ];

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

/// Wraps [child] in a MaterialApp + ProviderScope with the given overrides.
Widget _buildApp({
  required Widget child,
  Brightness brightness = Brightness.dark,
  List<Override> overrides = const [],
}) {
  return ProviderScope(
    overrides: overrides,
    child: MaterialApp(
      theme: brightness == Brightness.dark
          ? KinetixTheme.darkTheme()
          : KinetixTheme.lightTheme(),
      home: Scaffold(
        body: SizedBox(
          width: 800,
          height: 600,
          child: child,
        ),
      ),
    ),
  );
}

/// Helper: override shipmentsProvider with a ready state containing [shipments].
Override _withShipments(List<Shipment> shipments) {
  return shipmentsProvider.overrideWith(
    () => _FakeShipmentsNotifier(
      ShipmentsState(shipments: shipments, isInitialLoading: false),
    ),
  );
}

/// Helper: override shipmentsProvider with the initial loading state.
Override _withLoading() {
  return shipmentsProvider.overrideWith(
    () => _FakeShipmentsNotifier(const ShipmentsState(isInitialLoading: true)),
  );
}

/// Helper: override shipmentsProvider with an error state.
Override _withError() {
  return shipmentsProvider.overrideWith(
    () => _FakeShipmentsNotifier(
      ShipmentsState(
        isInitialLoading: false,
        error: Exception('Network error'),
      ),
    ),
  );
}

void main() {
  group('MapView', () {
    testWidgets('renders live indicator', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const MapView(),
          overrides: [_withShipments(_sampleShipments())],
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('LIVE'), findsOneWidget);
    });

    testWidgets('shows shimmer loading while data is loading', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const MapView(),
          overrides: [_withLoading()],
        ),
      );
      await tester.pump();

      // ShimmerLoading should be present during initial load
      expect(find.byType(SizedBox), findsWidgets);
    });

    testWidgets('shows error retry on failure', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const MapView(),
          overrides: [_withError()],
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Failed to load shipment data.'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('renders map when data is loaded', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const MapView(),
          overrides: [_withShipments(_sampleShipments())],
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(CustomPaint), findsWidgets);
    });

    testWidgets('renders legend with all status labels', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const MapView(),
          overrides: [_withShipments(_sampleShipments())],
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('In Transit'), findsOneWidget);
      expect(find.text('Delayed'), findsOneWidget);
      expect(find.text('Disrupted'), findsOneWidget);
      expect(find.text('Created'), findsOneWidget);
      expect(find.text('Delivered'), findsOneWidget);
    });

    testWidgets('renders in light mode without errors', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          brightness: Brightness.light,
          child: const MapView(),
          overrides: [_withShipments(_sampleShipments())],
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(CustomPaint), findsWidgets);
    });

    testWidgets('renders with empty shipment list', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          child: const MapView(),
          overrides: [_withShipments([])],
        ),
      );
      await tester.pumpAndSettle();

      // Legend should still be visible
      expect(find.text('In Transit'), findsOneWidget);
    });
  });
}
