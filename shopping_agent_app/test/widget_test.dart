import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:shopping_agent_app/main.dart';
import 'package:shopping_agent_app/services/api_service.dart';

const _searchResult = {
  'session_id': '11111111-1111-1111-1111-111111111111',
  'query': 'running shoes men size 9 under 5000',
  'source_status': {'amazon': 'ok', 'flipkart': 'timeout', 'web': 'ok'},
  'results': {
    'amazon': [
      {
        'title': 'ASICS Gel-Contend 8',
        'price': '₹3,999',
        'rating': '4.4 out of 5 stars',
        'reviews_count': '(2,345)',
        'url': 'https://www.amazon.in/dp/1',
        'image': 'N/A',
        'source': 'amazon',
        'price_value': 3999,
        'rating_value': 4.4,
        'reviews_value': 2345,
      },
    ],
    'flipkart': [],
    'web': [
      {
        'title': 'Nike Revolution 7',
        'price': '₹4,295',
        'rating': 'N/A',
        'reviews_count': 'N/A',
        'url': 'https://www.myntra.com/nike',
        'image': 'N/A',
        'source': 'Myntra',
        'price_value': 4295,
      },
    ],
  },
  'recommendation': {
    'product': {
      'title': 'ASICS Gel-Contend 8',
      'price': '₹3,999',
      'rating': '4.4 out of 5 stars',
      'url': 'https://www.amazon.in/dp/1',
      'image': 'N/A',
      'source': 'amazon',
      'price_value': 3999,
      'rating_value': 4.4,
    },
    'reason': 'Great cushioning and reviews well within your budget.',
  },
};

void main() {
  late List<http.Request> requests;

  setUp(() async {
    GoogleFonts.config.allowRuntimeFetching = false;
    SharedPreferences.setMockInitialValues({});
    requests = [];
    var chatTurns = 0;
    ApiService.instance = ApiService(
      MockClient((request) async {
        requests.add(request);
        final path = request.url.path;
        if (path == '/health') return http.Response('{"status":"ok"}', 200);
        if (path == '/api/chat') {
          chatTurns++;
          final body = chatTurns == 1
              ? {'message': "What's your budget?", 'is_ready_to_search': false, 'search_query': ''}
              : {
                  'message': 'Got it! Finding the best options.',
                  'is_ready_to_search': true,
                  'search_query': 'running shoes men size 9 under 5000',
                };
          return http.Response(jsonEncode(body), 200, headers: {'content-type': 'application/json'});
        }
        if (path == '/api/search') {
          await Future<void>.delayed(const Duration(seconds: 5)); // searches are slow
          return http.Response.bytes(utf8.encode(jsonEncode(_searchResult)), 200,
              headers: {'content-type': 'application/json; charset=utf-8'});
        }
        if (path == '/api/sessions') return http.Response('[]', 200);
        return http.Response('{"detail":"not found"}', 404);
      }),
      baseUrl: 'http://test',
    );
    await ApiService.instance.init();
  });

  void usePhoneScreen(WidgetTester tester) {
    tester.view.physicalSize = const Size(1170, 2532);
    tester.view.devicePixelRatio = 3.0;
    addTearDown(tester.view.reset);
  }

  Future<void> settle(WidgetTester tester) async {
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 200));
    }
  }

  testWidgets('chat → follow-up → search → results card', (tester) async {
    usePhoneScreen(tester);
    await tester.pumpWidget(const ShoppingAgentApp());
    await settle(tester);

    expect(find.text('What are you shopping for today?'), findsOneWidget);
    expect(find.textContaining('Online'), findsOneWidget);

    await tester.tap(find.text('Running shoes for men, size 9'));
    await settle(tester);
    expect(find.text("What's your budget?"), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'under 5000');
    await tester.pump();
    await tester.tap(find.byTooltip('Send'));
    await settle(tester);

    // While the search runs: the agent's acknowledgement plus the progress card.
    expect(find.text('Got it! Finding the best options.'), findsOneWidget);
    expect(find.text('running shoes men size 9 under 5000'), findsOneWidget);
    expect(find.text('Searching Amazon, Flipkart & more stores'), findsOneWidget);
    final input = tester.widget<TextField>(find.byType(TextField));
    expect(input.enabled, isFalse);

    await settle(tester);
    await settle(tester);

    expect(find.text('Compare all 2'), findsOneWidget);
    expect(find.text('ASICS Gel-Contend 8'), findsOneWidget);
    expect(find.textContaining("Flipkart didn't respond"), findsOneWidget);

    // Every API call carries the anonymous device ID.
    final apiCalls = requests.where((r) => r.url.path.startsWith('/api/'));
    expect(apiCalls, isNotEmpty);
    expect(apiCalls.every((r) => (r.headers['X-Client-ID'] ?? '').length == 32), isTrue);

    // The second chat turn includes the whole conversation so far.
    final lastChat = requests.lastWhere((r) => r.url.path == '/api/chat');
    final history = (jsonDecode(lastChat.body) as Map)['history'] as List;
    expect(history.map((m) => m['content']), contains('under 5000'));

    await tester.tap(find.text('Compare all 2'));
    await settle(tester);
    expect(find.text('Results'), findsOneWidget);
    expect(find.text('Nike Revolution 7'), findsOneWidget);

    await tester.pumpWidget(const SizedBox());
    await settle(tester);
  });

  testWidgets('shows a retryable error when the server is unreachable', (tester) async {
    usePhoneScreen(tester);
    ApiService.instance = ApiService(
      MockClient((request) async => throw http.ClientException('offline')),
      baseUrl: 'http://test',
    );
    await tester.pumpWidget(const ShoppingAgentApp());
    await settle(tester);

    expect(find.text("Can't reach the server right now."), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'laptop');
    await tester.pump();
    await tester.tap(find.byTooltip('Send'));
    await settle(tester);
    expect(find.textContaining("Can't reach the server. Check your connection"), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);

    await tester.pumpWidget(const SizedBox());
    await settle(tester);
  });
}
