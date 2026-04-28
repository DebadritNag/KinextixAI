import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kinetix_ai/models/alert.dart';
import 'package:kinetix_ai/providers/alerts_provider.dart';
import 'package:kinetix_ai/theme/kinetix_theme.dart';
import 'package:kinetix_ai/widgets/risk_alerts_panel.dart';

/// Sample alerts for testing.
final _sampleAlerts = [
  RiskAlert(
    id: 'a1',
    shipmentId: 'SHP-001',
    severity: Severity.low,
    title: 'Minor delay detected',
    description: 'Shipment SHP-001 is experiencing a minor delay due to traffic.',
    createdAt: DateTime.now().subtract(const Duration(minutes: 5)),
  ),
  RiskAlert(
    id: 'a2',
    shipmentId: 'SHP-002',
    severity: Severity.high,
    title: 'Severe weather disruption',
    description: 'Severe storm affecting route for SHP-002. Immediate rerouting recommended.',
    createdAt: DateTime.now().subtract(const Duration(hours: 1)),
  ),
  RiskAlert(
    id: 'a3',
    shipmentId: 'SHP-003',
    severity: Severity.medium,
    title: 'Customs clearance delay',
    description: 'SHP-003 is held at customs. Expected delay of 2-4 hours.',
    createdAt: DateTime.now().subtract(const Duration(minutes: 30)),
  ),
];

/// Wraps [child] in a [ProviderScope] with an overridden [alertsProvider]
/// and a [MaterialApp] with the given [brightness].
Widget _buildApp({
  required AsyncValue<List<RiskAlert>> alertsValue,
  Brightness brightness = Brightness.dark,
}) {
  return ProviderScope(
    overrides: [
      alertsProvider.overrideWith((ref) {
        // Return a future that completes with the value from the AsyncValue.
        return alertsValue.when(
          data: (data) => Future.value(data),
          loading: () => Future.delayed(const Duration(days: 1), () => <RiskAlert>[]),
          error: (e, _) => Future.error(e),
        );
      }),
    ],
    child: MaterialApp(
      theme: brightness == Brightness.dark
          ? KinetixTheme.darkTheme()
          : KinetixTheme.lightTheme(),
      home: const Scaffold(
        body: SingleChildScrollView(
          child: RiskAlertsPanel(),
        ),
      ),
    ),
  );
}

void main() {
  group('RiskAlertsPanel', () {
    testWidgets('displays panel header with title', (tester) async {
      await tester.pumpWidget(
        _buildApp(alertsValue: AsyncValue.data(_sampleAlerts)),
      );
      await tester.pumpAndSettle();

      expect(find.text('Risk Alerts'), findsOneWidget);
    });

    testWidgets('displays warning icon in header', (tester) async {
      await tester.pumpWidget(
        _buildApp(alertsValue: AsyncValue.data(_sampleAlerts)),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.warning_amber_rounded), findsOneWidget);
    });

    testWidgets('displays shimmer loading state', (tester) async {
      // Use a Completer that never completes to simulate a perpetual loading
      // state without creating timers that outlive the test.
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            alertsProvider.overrideWith((ref) async {
              // Never-completing future simulated via Completer.
              final completer = Completer<List<RiskAlert>>();
              ref.onDispose(() {
                if (!completer.isCompleted) {
                  completer.complete([]);
                }
              });
              return completer.future;
            }),
          ],
          child: MaterialApp(
            theme: KinetixTheme.darkTheme(),
            home: const Scaffold(
              body: SingleChildScrollView(child: RiskAlertsPanel()),
            ),
          ),
        ),
      );
      await tester.pump();

      // The panel should be rendered in its loading state.
      expect(find.byType(RiskAlertsPanel), findsOneWidget);
    });

    testWidgets('displays error state with retry', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          alertsValue: AsyncValue.error(
            Exception('Network error'),
            StackTrace.current,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Failed to load alerts. Please try again.'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('displays all alert titles', (tester) async {
      await tester.pumpWidget(
        _buildApp(alertsValue: AsyncValue.data(_sampleAlerts)),
      );
      await tester.pumpAndSettle();

      expect(find.text('Severe weather disruption'), findsOneWidget);
      expect(find.text('Customs clearance delay'), findsOneWidget);
      expect(find.text('Minor delay detected'), findsOneWidget);
    });

    testWidgets('sorts alerts by severity: HIGH first', (tester) async {
      await tester.pumpWidget(
        _buildApp(alertsValue: AsyncValue.data(_sampleAlerts)),
      );
      await tester.pumpAndSettle();

      // Find all severity badge texts to verify order.
      final badgeTexts = tester
          .widgetList<Text>(find.text('HIGH'))
          .toList();
      expect(badgeTexts, isNotEmpty, reason: 'HIGH badge should be present');

      // Verify the order by checking the vertical positions of alert titles.
      final highPos = tester.getTopLeft(find.text('Severe weather disruption'));
      final medPos = tester.getTopLeft(find.text('Customs clearance delay'));
      final lowPos = tester.getTopLeft(find.text('Minor delay detected'));

      expect(highPos.dy, lessThan(medPos.dy),
          reason: 'HIGH alert should appear above MEDIUM');
      expect(medPos.dy, lessThan(lowPos.dy),
          reason: 'MEDIUM alert should appear above LOW');
    });

    testWidgets('displays severity badges with correct labels', (tester) async {
      await tester.pumpWidget(
        _buildApp(alertsValue: AsyncValue.data(_sampleAlerts)),
      );
      await tester.pumpAndSettle();

      expect(find.text('HIGH'), findsOneWidget);
      expect(find.text('MEDIUM'), findsOneWidget);
      expect(find.text('LOW'), findsOneWidget);
    });

    testWidgets('displays shipment IDs', (tester) async {
      await tester.pumpWidget(
        _buildApp(alertsValue: AsyncValue.data(_sampleAlerts)),
      );
      await tester.pumpAndSettle();

      expect(find.text('SHP-001'), findsOneWidget);
      expect(find.text('SHP-002'), findsOneWidget);
      expect(find.text('SHP-003'), findsOneWidget);
    });

    testWidgets('displays empty state when no active alerts', (tester) async {
      await tester.pumpWidget(
        _buildApp(alertsValue: const AsyncValue.data([])),
      );
      await tester.pumpAndSettle();

      expect(find.text('No active alerts'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle_outline), findsOneWidget);
    });

    testWidgets('filters out inactive alerts', (tester) async {
      final alertsWithInactive = [
        RiskAlert(
          id: 'a1',
          shipmentId: 'SHP-001',
          severity: Severity.high,
          title: 'Active alert',
          description: 'This is active.',
          createdAt: DateTime.now(),
          isActive: true,
        ),
        RiskAlert(
          id: 'a2',
          shipmentId: 'SHP-002',
          severity: Severity.medium,
          title: 'Inactive alert',
          description: 'This is inactive.',
          createdAt: DateTime.now(),
          isActive: false,
        ),
      ];

      await tester.pumpWidget(
        _buildApp(alertsValue: AsyncValue.data(alertsWithInactive)),
      );
      await tester.pumpAndSettle();

      expect(find.text('Active alert'), findsOneWidget);
      expect(find.text('Inactive alert'), findsNothing);
    });

    testWidgets('renders correctly in light mode', (tester) async {
      await tester.pumpWidget(
        _buildApp(
          alertsValue: AsyncValue.data(_sampleAlerts),
          brightness: Brightness.light,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Risk Alerts'), findsOneWidget);
      expect(find.text('Severe weather disruption'), findsOneWidget);
    });

    testWidgets('displays chevron icons for navigation hint', (tester) async {
      await tester.pumpWidget(
        _buildApp(alertsValue: AsyncValue.data(_sampleAlerts)),
      );
      await tester.pumpAndSettle();

      // Each alert item should have a chevron_right icon.
      expect(
        find.byIcon(Icons.chevron_right),
        findsNWidgets(_sampleAlerts.length),
      );
    });
  });

  group('RiskAlertsPanel.severityColor', () {
    test('HIGH maps to colorDanger (red)', () {
      expect(
        RiskAlertsPanel.severityColor(Severity.high),
        KinetixTheme.colorDanger,
      );
    });

    test('MEDIUM maps to colorWarning (amber)', () {
      expect(
        RiskAlertsPanel.severityColor(Severity.medium),
        KinetixTheme.colorWarning,
      );
    });

    test('LOW maps to colorAccent (green)', () {
      expect(
        RiskAlertsPanel.severityColor(Severity.low),
        KinetixTheme.colorAccent,
      );
    });
  });
}
