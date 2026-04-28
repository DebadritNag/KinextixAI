import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:kinetix_ai/widgets/responsive_layout.dart';
import 'package:kinetix_ai/theme/kinetix_theme.dart';

/// Helper that wraps [child] in a MaterialApp and sets the test view to
/// [surfaceWidth] so that [LayoutBuilder] receives the correct constraints.
Future<void> _pumpAtWidth(
  WidgetTester tester, {
  required double surfaceWidth,
  required Widget child,
  Brightness brightness = Brightness.dark,
}) async {
  tester.view.physicalSize = Size(surfaceWidth, 800);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() => tester.view.resetPhysicalSize());
  addTearDown(() => tester.view.resetDevicePixelRatio());

  await tester.pumpWidget(
    MaterialApp(
      theme: brightness == Brightness.dark
          ? KinetixTheme.darkTheme()
          : KinetixTheme.lightTheme(),
      home: Scaffold(body: child),
    ),
  );
}

void main() {
  // ---------------------------------------------------------------------------
  // ResponsiveBreakpoints
  // ---------------------------------------------------------------------------
  group('ResponsiveBreakpoints', () {
    test('mobile threshold is 768', () {
      expect(ResponsiveBreakpoints.mobile, 768.0);
    });

    test('tablet threshold is 1024', () {
      expect(ResponsiveBreakpoints.tablet, 1024.0);
    });

    test('isMobile returns true below 768', () {
      expect(ResponsiveBreakpoints.isMobile(767), isTrue);
      expect(ResponsiveBreakpoints.isMobile(375), isTrue);
      expect(ResponsiveBreakpoints.isMobile(0), isTrue);
    });

    test('isMobile returns false at 768 and above', () {
      expect(ResponsiveBreakpoints.isMobile(768), isFalse);
      expect(ResponsiveBreakpoints.isMobile(1024), isFalse);
      expect(ResponsiveBreakpoints.isMobile(1440), isFalse);
    });

    test('isTablet returns true between 768 and 1024 inclusive', () {
      expect(ResponsiveBreakpoints.isTablet(768), isTrue);
      expect(ResponsiveBreakpoints.isTablet(900), isTrue);
      expect(ResponsiveBreakpoints.isTablet(1024), isTrue);
    });

    test('isTablet returns false outside range', () {
      expect(ResponsiveBreakpoints.isTablet(767), isFalse);
      expect(ResponsiveBreakpoints.isTablet(1025), isFalse);
    });

    test('isDesktop returns true above 1024', () {
      expect(ResponsiveBreakpoints.isDesktop(1025), isTrue);
      expect(ResponsiveBreakpoints.isDesktop(1440), isTrue);
    });

    test('isDesktop returns false at 1024 and below', () {
      expect(ResponsiveBreakpoints.isDesktop(1024), isFalse);
      expect(ResponsiveBreakpoints.isDesktop(768), isFalse);
    });
  });

  // ---------------------------------------------------------------------------
  // deviceTypeFromWidth
  // ---------------------------------------------------------------------------
  group('deviceTypeFromWidth', () {
    test('returns mobile for widths below 768', () {
      expect(deviceTypeFromWidth(375), DeviceType.mobile);
      expect(deviceTypeFromWidth(767), DeviceType.mobile);
    });

    test('returns tablet for widths 768–1024', () {
      expect(deviceTypeFromWidth(768), DeviceType.tablet);
      expect(deviceTypeFromWidth(1024), DeviceType.tablet);
    });

    test('returns desktop for widths above 1024', () {
      expect(deviceTypeFromWidth(1025), DeviceType.desktop);
      expect(deviceTypeFromWidth(1440), DeviceType.desktop);
    });
  });

  // ---------------------------------------------------------------------------
  // ResponsiveValue
  // ---------------------------------------------------------------------------
  group('ResponsiveValue', () {
    const rv = ResponsiveValue<int>(mobile: 1, tablet: 2, desktop: 3);

    test('resolves mobile value for narrow widths', () {
      expect(rv.resolve(375), 1);
      expect(rv.resolve(767), 1);
    });

    test('resolves tablet value for medium widths', () {
      expect(rv.resolve(768), 2);
      expect(rv.resolve(1024), 2);
    });

    test('resolves desktop value for wide widths', () {
      expect(rv.resolve(1025), 3);
      expect(rv.resolve(1440), 3);
    });
  });

  // ---------------------------------------------------------------------------
  // ResponsiveLayout widget
  // ---------------------------------------------------------------------------
  group('ResponsiveLayout', () {
    testWidgets('renders desktop builder above 1024px', (tester) async {
      await _pumpAtWidth(
        tester,
        surfaceWidth: 1200,
        child: ResponsiveLayout(
          mobile: (_, constraints) => const Text('mobile'),
          tablet: (_, constraints) => const Text('tablet'),
          desktop: (_, constraints) => const Text('desktop'),
        ),
      );

      expect(find.text('desktop'), findsOneWidget);
      expect(find.text('tablet'), findsNothing);
      expect(find.text('mobile'), findsNothing);
    });

    testWidgets('renders tablet builder between 768 and 1024px', (tester) async {
      await _pumpAtWidth(
        tester,
        surfaceWidth: 900,
        child: ResponsiveLayout(
          mobile: (_, constraints) => const Text('mobile'),
          tablet: (_, constraints) => const Text('tablet'),
          desktop: (_, constraints) => const Text('desktop'),
        ),
      );

      expect(find.text('tablet'), findsOneWidget);
      expect(find.text('desktop'), findsNothing);
      expect(find.text('mobile'), findsNothing);
    });

    testWidgets('renders mobile builder below 768px', (tester) async {
      await _pumpAtWidth(
        tester,
        surfaceWidth: 375,
        child: ResponsiveLayout(
          mobile: (_, constraints) => const Text('mobile'),
          tablet: (_, constraints) => const Text('tablet'),
          desktop: (_, constraints) => const Text('desktop'),
        ),
      );

      expect(find.text('mobile'), findsOneWidget);
      expect(find.text('desktop'), findsNothing);
      expect(find.text('tablet'), findsNothing);
    });

    testWidgets('renders tablet at exact 768px boundary', (tester) async {
      await _pumpAtWidth(
        tester,
        surfaceWidth: 768,
        child: ResponsiveLayout(
          mobile: (_, constraints) => const Text('mobile'),
          tablet: (_, constraints) => const Text('tablet'),
          desktop: (_, constraints) => const Text('desktop'),
        ),
      );

      expect(find.text('tablet'), findsOneWidget);
    });

    testWidgets('renders tablet at exact 1024px boundary', (tester) async {
      await _pumpAtWidth(
        tester,
        surfaceWidth: 1024,
        child: ResponsiveLayout(
          mobile: (_, constraints) => const Text('mobile'),
          tablet: (_, constraints) => const Text('tablet'),
          desktop: (_, constraints) => const Text('desktop'),
        ),
      );

      expect(find.text('tablet'), findsOneWidget);
    });

    testWidgets('passes constraints to builder', (tester) async {
      double? receivedWidth;

      await _pumpAtWidth(
        tester,
        surfaceWidth: 1200,
        child: ResponsiveLayout(
          mobile: (_, c) {
            receivedWidth = c.maxWidth;
            return const SizedBox();
          },
          tablet: (_, c) {
            receivedWidth = c.maxWidth;
            return const SizedBox();
          },
          desktop: (_, c) {
            receivedWidth = c.maxWidth;
            return const SizedBox();
          },
        ),
      );

      expect(receivedWidth, isNotNull);
      expect(receivedWidth!, greaterThan(1024));
    });
  });

  // ---------------------------------------------------------------------------
  // DesktopLayout
  // ---------------------------------------------------------------------------
  group('DesktopLayout', () {
    testWidgets('renders sidebar and body in a Row', (tester) async {
      await _pumpAtWidth(
        tester,
        surfaceWidth: 1200,
        child: const DesktopLayout(
          sidebar: Text('sidebar'),
          body: Text('body'),
        ),
      );

      expect(find.text('sidebar'), findsOneWidget);
      expect(find.text('body'), findsOneWidget);
      expect(find.byType(Row), findsOneWidget);
    });

    testWidgets('sidebar has default width of 260', (tester) async {
      await _pumpAtWidth(
        tester,
        surfaceWidth: 1200,
        child: const DesktopLayout(
          sidebar: Text('sidebar'),
          body: Text('body'),
        ),
      );

      final sizedBoxes = tester.widgetList<SizedBox>(find.byType(SizedBox));
      final sidebarBox = sizedBoxes.where((sb) => sb.width == 260.0);
      expect(sidebarBox, isNotEmpty);
    });

    testWidgets('accepts custom sidebar width', (tester) async {
      await _pumpAtWidth(
        tester,
        surfaceWidth: 1200,
        child: const DesktopLayout(
          sidebar: Text('sidebar'),
          body: Text('body'),
          sidebarWidth: 300,
        ),
      );

      final sizedBoxes = tester.widgetList<SizedBox>(find.byType(SizedBox));
      final sidebarBox = sizedBoxes.where((sb) => sb.width == 300.0);
      expect(sidebarBox, isNotEmpty);
    });
  });

  // ---------------------------------------------------------------------------
  // TabletLayout
  // ---------------------------------------------------------------------------
  group('TabletLayout', () {
    testWidgets('renders compact sidebar and body in a Row', (tester) async {
      await _pumpAtWidth(
        tester,
        surfaceWidth: 900,
        child: const TabletLayout(
          sidebar: Text('compact-sidebar'),
          body: Text('body'),
        ),
      );

      expect(find.text('compact-sidebar'), findsOneWidget);
      expect(find.text('body'), findsOneWidget);
      expect(find.byType(Row), findsOneWidget);
    });

    testWidgets('sidebar has default width of 72', (tester) async {
      await _pumpAtWidth(
        tester,
        surfaceWidth: 900,
        child: const TabletLayout(
          sidebar: Text('sidebar'),
          body: Text('body'),
        ),
      );

      final sizedBoxes = tester.widgetList<SizedBox>(find.byType(SizedBox));
      final sidebarBox = sizedBoxes.where((sb) => sb.width == 72.0);
      expect(sidebarBox, isNotEmpty);
    });
  });

  // ---------------------------------------------------------------------------
  // MobileLayout
  // ---------------------------------------------------------------------------
  group('MobileLayout', () {
    testWidgets('renders body content', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: KinetixTheme.darkTheme(),
          home: const MobileLayout(
            drawer: Text('drawer-content'),
            body: Text('main-content'),
          ),
        ),
      );

      expect(find.text('main-content'), findsOneWidget);
    });

    testWidgets('provides a Drawer with the drawer widget', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: KinetixTheme.darkTheme(),
          home: const MobileLayout(
            drawer: Text('drawer-content'),
            body: Text('main-content'),
          ),
        ),
      );

      final scaffoldState = tester.state<ScaffoldState>(
        find.byType(Scaffold).last,
      );
      expect(scaffoldState.hasDrawer, isTrue);
    });

    testWidgets('drawer shows content when opened', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: KinetixTheme.darkTheme(),
          home: const MobileLayout(
            drawer: Text('drawer-content'),
            body: Text('main-content'),
          ),
        ),
      );

      final scaffoldState = tester.state<ScaffoldState>(
        find.byType(Scaffold).last,
      );
      scaffoldState.openDrawer();
      await tester.pumpAndSettle();

      expect(find.text('drawer-content'), findsOneWidget);
    });

    testWidgets('accepts custom appBar', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: KinetixTheme.darkTheme(),
          home: MobileLayout(
            appBar: AppBar(title: const Text('Custom AppBar')),
            drawer: const Text('drawer'),
            body: const Text('body'),
          ),
        ),
      );

      expect(find.text('Custom AppBar'), findsOneWidget);
    });
  });
}
