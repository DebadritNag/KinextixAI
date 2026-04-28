import 'package:flutter_test/flutter_test.dart';
import 'package:kinetix_ai/models/models.dart';

void main() {
  group('ShipmentStatus', () {
    test('fromJson parses all valid values', () {
      expect(ShipmentStatus.fromJson('created'), ShipmentStatus.created);
      expect(ShipmentStatus.fromJson('in_transit'), ShipmentStatus.inTransit);
      expect(ShipmentStatus.fromJson('delayed'), ShipmentStatus.delayed);
      expect(ShipmentStatus.fromJson('delivered'), ShipmentStatus.delivered);
      expect(ShipmentStatus.fromJson('disrupted'), ShipmentStatus.disrupted);
    });

    test('fromJson throws on unknown value', () {
      expect(
        () => ShipmentStatus.fromJson('unknown'),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('value property returns snake_case string', () {
      expect(ShipmentStatus.inTransit.value, 'in_transit');
    });
  });

  group('Severity', () {
    test('fromJson parses all valid values', () {
      expect(Severity.fromJson('low'), Severity.low);
      expect(Severity.fromJson('medium'), Severity.medium);
      expect(Severity.fromJson('high'), Severity.high);
    });

    test('fromJson throws on unknown value', () {
      expect(
        () => Severity.fromJson('critical'),
        throwsA(isA<ArgumentError>()),
      );
    });
  });

  group('Coordinates', () {
    test('fromJson/toJson round-trip', () {
      final json = {'lat': 31.23, 'lng': 121.47};
      final coords = Coordinates.fromJson(json);
      expect(coords.lat, 31.23);
      expect(coords.lng, 121.47);
      expect(coords.toJson(), json);
    });
  });

  group('TimelineEvent', () {
    test('fromJson/toJson round-trip with nullable fields', () {
      final json = {
        'timestamp': '2025-01-15T10:30:00.000',
        'event': 'Departed origin',
        'location': 'Shanghai Port',
        'details': null,
      };
      final event = TimelineEvent.fromJson(json);
      expect(event.event, 'Departed origin');
      expect(event.location, 'Shanghai Port');
      expect(event.details, isNull);

      final output = event.toJson();
      expect(output['event'], 'Departed origin');
      expect(output['location'], 'Shanghai Port');
      expect(output['details'], isNull);
    });
  });

  group('Shipment', () {
    late Map<String, dynamic> sampleJson;

    setUp(() {
      sampleJson = {
        'id': 'SHP-001',
        'origin': 'Shanghai',
        'destination': 'Los Angeles',
        'origin_coords': {'lat': 31.23, 'lng': 121.47},
        'destination_coords': {'lat': 33.94, 'lng': -118.41},
        'current_coords': {'lat': 32.5, 'lng': -110.0},
        'status': 'in_transit',
        'created_at': '2025-01-15T08:00:00.000',
        'updated_at': '2025-01-15T12:00:00.000',
        'eta_predicted': '2025-01-20T14:00:00.000',
        'eta_confidence_low': null,
        'eta_confidence_high': null,
        'delay_minutes': 45,
        'weather_condition': 'rain',
        'route_id': 'RT-01',
        'timeline': [
          {
            'timestamp': '2025-01-15T08:00:00.000',
            'event': 'Created',
            'location': 'Shanghai',
            'details': null,
          },
        ],
      };
    });

    test('fromJson parses all fields correctly', () {
      final shipment = Shipment.fromJson(sampleJson);
      expect(shipment.id, 'SHP-001');
      expect(shipment.status, ShipmentStatus.inTransit);
      expect(shipment.delayMinutes, 45);
      expect(shipment.weatherCondition, 'rain');
      expect(shipment.routeId, 'RT-01');
      expect(shipment.timeline, hasLength(1));
      expect(shipment.etaPredicted, isNotNull);
      expect(shipment.etaConfidenceLow, isNull);
    });

    test('fromJson uses defaults for missing optional fields', () {
      final minimalJson = {
        'id': 'SHP-002',
        'origin': 'A',
        'destination': 'B',
        'origin_coords': {'lat': 0.0, 'lng': 0.0},
        'destination_coords': {'lat': 1.0, 'lng': 1.0},
        'current_coords': {'lat': 0.5, 'lng': 0.5},
        'status': 'created',
        'created_at': '2025-01-15T08:00:00.000',
        'updated_at': '2025-01-15T08:00:00.000',
      };
      final shipment = Shipment.fromJson(minimalJson);
      expect(shipment.delayMinutes, 0);
      expect(shipment.weatherCondition, 'clear');
      expect(shipment.routeId, isNull);
      expect(shipment.timeline, isEmpty);
      expect(shipment.etaPredicted, isNull);
    });

    test('toJson produces snake_case keys', () {
      final shipment = Shipment.fromJson(sampleJson);
      final output = shipment.toJson();
      expect(output.containsKey('origin_coords'), isTrue);
      expect(output.containsKey('destination_coords'), isTrue);
      expect(output.containsKey('current_coords'), isTrue);
      expect(output.containsKey('delay_minutes'), isTrue);
      expect(output.containsKey('weather_condition'), isTrue);
      expect(output.containsKey('route_id'), isTrue);
      expect(output['status'], 'in_transit');
    });
  });

  group('RiskAlert', () {
    test('fromJson/toJson round-trip', () {
      final json = {
        'id': 'ALT-001',
        'shipment_id': 'SHP-001',
        'severity': 'high',
        'title': 'Severe weather detected',
        'description': 'Storm approaching route segment',
        'created_at': '2025-01-15T10:00:00.000',
        'is_active': true,
      };
      final alert = RiskAlert.fromJson(json);
      expect(alert.severity, Severity.high);
      expect(alert.isActive, isTrue);

      final output = alert.toJson();
      expect(output['severity'], 'high');
      expect(output['shipment_id'], 'SHP-001');
    });

    test('isActive defaults to true when missing', () {
      final json = {
        'id': 'ALT-002',
        'shipment_id': 'SHP-002',
        'severity': 'low',
        'title': 'Minor delay',
        'description': 'Slight delay expected',
        'created_at': '2025-01-15T10:00:00.000',
      };
      final alert = RiskAlert.fromJson(json);
      expect(alert.isActive, isTrue);
    });
  });

  group('OptimizationWeights', () {
    test('default values are 0.25', () {
      const weights = OptimizationWeights();
      expect(weights.cost, 0.25);
      expect(weights.time, 0.25);
      expect(weights.carbon, 0.25);
      expect(weights.risk, 0.25);
    });

    test('fromJson/toJson round-trip', () {
      final json = {
        'cost': 0.4,
        'time': 0.3,
        'carbon': 0.2,
        'risk': 0.1,
      };
      final weights = OptimizationWeights.fromJson(json);
      expect(weights.cost, 0.4);
      expect(weights.toJson(), json);
    });

    test('fromJson uses defaults for missing fields', () {
      final weights = OptimizationWeights.fromJson({});
      expect(weights.cost, 0.25);
      expect(weights.time, 0.25);
    });
  });

  group('RouteOption', () {
    test('fromJson/toJson round-trip', () {
      final json = {
        'route_id': 'RT-01',
        'waypoints': ['Shanghai', 'Tokyo', 'LA'],
        'label': 'fastest',
        'cost_usd': 5200.0,
        'eta_hours': 72.0,
        'carbon_kg': 450.0,
        'risk_score': 30.0,
        'score': 0.45,
        'is_recommended': true,
      };
      final route = RouteOption.fromJson(json);
      expect(route.routeId, 'RT-01');
      expect(route.waypoints, hasLength(3));
      expect(route.isRecommended, isTrue);

      final output = route.toJson();
      expect(output['route_id'], 'RT-01');
      expect(output['is_recommended'], isTrue);
    });

    test('isRecommended defaults to false', () {
      final json = {
        'route_id': 'RT-02',
        'waypoints': ['A', 'B'],
        'label': 'cheapest',
        'cost_usd': 1000.0,
        'eta_hours': 120.0,
        'carbon_kg': 200.0,
        'risk_score': 10.0,
        'score': 0.3,
      };
      final route = RouteOption.fromJson(json);
      expect(route.isRecommended, isFalse);
    });
  });

  group('ETAPrediction', () {
    test('fromJson/toJson round-trip', () {
      final json = {
        'shipment_id': 'SHP-001',
        'predicted_arrival': '2025-01-20T14:00:00.000',
        'confidence_low': '2025-01-20T10:00:00.000',
        'confidence_high': '2025-01-20T18:00:00.000',
        'model_version': 'v1.0.0',
      };
      final prediction = ETAPrediction.fromJson(json);
      expect(prediction.shipmentId, 'SHP-001');
      expect(prediction.modelVersion, 'v1.0.0');

      final output = prediction.toJson();
      expect(output['shipment_id'], 'SHP-001');
      expect(output['model_version'], 'v1.0.0');
    });
  });

  group('Settings', () {
    test('fromJson/toJson round-trip', () {
      final json = {
        'sla_thresholds': {'standard': 48.0, 'express': 24.0},
        'penalties': {'standard': 100.0, 'express': 250.0},
        'default_weights': {
          'cost': 0.3,
          'time': 0.3,
          'carbon': 0.2,
          'risk': 0.2,
        },
      };
      final settings = Settings.fromJson(json);
      expect(settings.slaThresholds['standard'], 48.0);
      expect(settings.penalties['express'], 250.0);
      expect(settings.defaultWeights.cost, 0.3);

      final output = settings.toJson();
      expect(output['sla_thresholds']['standard'], 48.0);
      expect(output['default_weights']['cost'], 0.3);
    });
  });

  group('AnalyticsData', () {
    test('fromJson/toJson round-trip', () {
      final json = {
        'delay_trends': [
          {'date': '2025-01-15', 'avg_delay_minutes': 30, 'count': 5},
        ],
        'cost_savings': [
          {
            'date': '2025-01-15',
            'baseline_cost': 10000,
            'optimized_cost': 8500,
          },
        ],
        'carbon_reduction': [
          {
            'date': '2025-01-15',
            'baseline_carbon': 500,
            'optimized_carbon': 350,
          },
        ],
        'sla_compliance_pct': 94.5,
        'sla_trend': [
          {'date': '2025-01-15', 'compliance_pct': 94.5},
        ],
      };
      final analytics = AnalyticsData.fromJson(json);
      expect(analytics.delayTrends, hasLength(1));
      expect(analytics.slaCompliancePct, 94.5);

      final output = analytics.toJson();
      expect(output['sla_compliance_pct'], 94.5);
      expect(output['delay_trends'], hasLength(1));
    });
  });
}
