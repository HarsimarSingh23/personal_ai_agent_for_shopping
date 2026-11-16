import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:shopping_agent_app/config/app_config.dart';
import 'package:shopping_agent_app/main.dart';
import 'package:shopping_agent_app/services/api_service.dart';

void main() {
  late List<Uri> calls;

  setUp(() async {
    GoogleFonts.config.allowRuntimeFetching = false;
    SharedPreferences.setMockInitialValues({});
    AppConfig.setServerOverride(null);
    calls = [];
    ApiService.instance = ApiService(MockClient((request) async {
      calls.add(request.url);
      if (request.url.path == '/api/sessions') return http.Response('[]', 200);
      return http.Response('{"status":"ok"}', 200);
    }));
    await ApiService.instance.init();
  });

  group('normalizeServerUrl', () {
    final cases = {
      '192.168.1.5': 'http://192.168.1.5:8000',
      ' 192.168.1.5:9000 ': 'http://192.168.1.5:9000',
      'http://192.168.1.5:8000/': 'http://192.168.1.5:8000',
      'http://my-pc.local': 'http://my-pc.local',
      'https://api.example.com/api': 'https://api.example.com',
      'https://api.example.com/shop/api/': 'https://api.example.com/shop',
    };
    cases.forEach((input, expected) {
      test('"$input" → $expected', () => expect(AppConfig.normalizeServerUrl(input), expected));
    });

    for (final bad in ['', '   ', 'ftp://192.168.1.5', 'http://']) {
      test('rejects "$bad"', () => expect(AppConfig.normalizeServerUrl(bad), isNull));
    }
  });

  test('the chosen address is used at once and remembered after a restart', () async {
    await ApiService.instance.setServerUrl('http://192.168.1.5:8000');
    expect(ApiService.instance.serverUrl, 'http://192.168.1.5:8000');

    await ApiService.instance.checkHealth();
    expect(calls.single.toString(), 'http://192.168.1.5:8000/health');

    // "Restart": forget the in-memory value, then load from storage.
    AppConfig.setServerOverride(null);
    await ApiService.instance.init();
    expect(ApiService.instance.serverUrl, 'http://192.168.1.5:8000');

    await ApiService.instance.setServerUrl(null);
    expect(ApiService.instance.serverUrl, AppConfig.builtInBaseUrl);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('server_url'), isNull);
  });

  testWidgets('the Server address dialog changes where the app connects', (tester) async {
    tester.view.physicalSize = const Size(1170, 2532);
    tester.view.devicePixelRatio = 3.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(const ShoppingAgentApp());
    await tester.pump(const Duration(milliseconds: 500));

    await tester.tap(find.byTooltip('Server address'));
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('Server address'), findsWidgets);

    await tester.enterText(find.byKey(const Key('server-url-field')), 'not a url ://');
    await tester.tap(find.text('Save'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.textContaining('Enter an address like'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('server-url-field')), '192.168.1.5');
    await tester.tap(find.text('Save'));
    for (var i = 0; i < 5; i++) {
      await tester.pump(const Duration(milliseconds: 200));
    }

    expect(ApiService.instance.serverUrl, 'http://192.168.1.5:8000');
    expect(calls.last.toString(), 'http://192.168.1.5:8000/health');
    expect(find.textContaining('Online'), findsOneWidget);
  });
}
