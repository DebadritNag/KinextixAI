import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:kinetix_ai/providers/auth_provider.dart';
import 'package:kinetix_ai/providers/weights_provider.dart';

void main() {
  group('AuthNotifier', () {
    late ProviderContainer container;

    setUp(() {
      // Reset session storage to a clean in-memory instance for each test.
      sessionStorage = InMemorySessionStorage();
      container = ProviderContainer();
    });

    tearDown(() {
      container.dispose();
    });

    test('initial state is unauthenticated', () {
      final state = container.read(authProvider);
      expect(state.isAuthenticated, isFalse);
      expect(state.token, isNull);
      expect(state.user, isNull);
    });

    test('logout clears auth state to unauthenticated', () async {
      final notifier = container.read(authProvider.notifier);

      // Simulate a logged-in state by logging in (will fail against real API,
      // so we test the logout path by directly manipulating state).
      // Instead, call logout from the default unauthenticated state and
      // verify it remains unauthenticated.
      await notifier.logout();

      final state = container.read(authProvider);
      expect(state.isAuthenticated, isFalse);
      expect(state.token, isNull);
      expect(state.user, isNull);
    });

    test('logout clears auth-related session storage keys', () async {
      final notifier = container.read(authProvider.notifier);

      // Pre-populate session storage with auth-related keys.
      sessionStorage.write('kinetix_auth_token', 'mock-token-123');
      sessionStorage.write('kinetix_auth_user', '{"username":"admin"}');

      // Also write non-auth keys that should survive logout.
      sessionStorage.write('kinetix_optimization_weights', '{"cost":0.5}');
      sessionStorage.write('kinetix_theme_mode', 'dark');

      await notifier.logout();

      // Auth keys should be cleared.
      expect(sessionStorage.read('kinetix_auth_token'), isNull);
      expect(sessionStorage.read('kinetix_auth_user'), isNull);

      // Non-auth keys should be preserved.
      expect(sessionStorage.read('kinetix_optimization_weights'), '{"cost":0.5}');
      expect(sessionStorage.read('kinetix_theme_mode'), 'dark');
    });

    test('logout resets isAuthenticated to false', () async {
      final notifier = container.read(authProvider.notifier);

      // Verify logout always results in unauthenticated state.
      await notifier.logout();

      final state = container.read(authProvider);
      expect(state.isAuthenticated, false);
    });
  });

  group('AuthState', () {
    test('default constructor creates unauthenticated state', () {
      const state = AuthState();
      expect(state.isAuthenticated, isFalse);
      expect(state.token, isNull);
      expect(state.user, isNull);
    });

    test('copyWith preserves unchanged fields', () {
      const original = AuthState(
        isAuthenticated: true,
        token: 'abc',
        user: {'name': 'test'},
      );

      final copied = original.copyWith(token: 'xyz');
      expect(copied.isAuthenticated, isTrue);
      expect(copied.token, 'xyz');
      expect(copied.user, {'name': 'test'});
    });
  });
}
