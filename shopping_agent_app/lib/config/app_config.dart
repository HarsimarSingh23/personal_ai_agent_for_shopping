import 'package:flutter/foundation.dart';

/// Build-time configuration, passed with `--dart-define`:
///
///   flutter run --dart-define=API_BASE_URL=https://api.example.com
///   flutter build apk --dart-define=API_BASE_URL=https://api.example.com --dart-define=API_KEY=...
///
/// Without API_BASE_URL the app talks to a backend on this machine
/// (10.0.2.2 is the host machine as seen from the Android emulator).
class AppConfig {
  AppConfig._();

  static const String _apiBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const String apiKey = String.fromEnvironment('API_KEY');

  static String get apiBaseUrl {
    if (_apiBaseUrl.isNotEmpty) {
      return _apiBaseUrl.endsWith('/')
          ? _apiBaseUrl.substring(0, _apiBaseUrl.length - 1)
          : _apiBaseUrl;
    }
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://127.0.0.1:8000';
  }

  static const Duration searchTimeout = Duration(seconds: 120);
  static const Duration chatTimeout = Duration(seconds: 60);
  static const Duration defaultTimeout = Duration(seconds: 15);
}
