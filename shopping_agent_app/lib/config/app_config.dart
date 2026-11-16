import 'package:flutter/foundation.dart';

/// App configuration.
///
/// The server address comes from, in order:
///   1. the address typed in the app (Server address dialog), saved on the device;
///   2. the build-time value passed with `--dart-define`:
///        flutter run --dart-define=API_BASE_URL=https://api.example.com
///        flutter build apk --dart-define=API_BASE_URL=https://api.example.com --dart-define=API_KEY=...
///   3. a backend on this machine (10.0.2.2 is the host machine as seen from
///      the Android emulator).
class AppConfig {
  AppConfig._();

  static const String _apiBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const String apiKey = String.fromEnvironment('API_KEY');

  /// Port the backend uses when the user types only an IP or host name.
  static const int defaultPort = 8000;

  static String? _serverOverride;

  /// The address chosen in the app, or null when the built-in one is used.
  static String? get serverOverride => _serverOverride;

  /// Set (or clear with null) the address chosen in the app. Pass a value
  /// already cleaned by [normalizeServerUrl].
  static void setServerOverride(String? url) {
    _serverOverride = (url == null || url.trim().isEmpty) ? null : url.trim();
  }

  /// The address this build was made with (ignores the in-app choice).
  static String get builtInBaseUrl {
    if (_apiBaseUrl.isNotEmpty) return _stripSlash(_apiBaseUrl);
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:$defaultPort';
    }
    return 'http://127.0.0.1:$defaultPort';
  }

  static String get apiBaseUrl => _serverOverride ?? builtInBaseUrl;

  /// Cleans what the user typed into a base URL, or returns null if it is not
  /// a usable address.
  ///
  ///   192.168.1.5            → http://192.168.1.5:8000
  ///   192.168.1.5:9000       → http://192.168.1.5:9000
  ///   http://my-pc.local/    → http://my-pc.local
  ///   https://api.site.com/api → https://api.site.com
  static String? normalizeServerUrl(String input) {
    var text = input.trim();
    if (text.isEmpty) return null;
    final hadScheme = text.contains('://');
    if (!hadScheme) text = 'http://$text';

    final uri = Uri.tryParse(text);
    if (uri == null || uri.host.isEmpty || (uri.scheme != 'http' && uri.scheme != 'https')) {
      return null;
    }
    var path = _stripSlash(uri.path);
    if (path.endsWith('/api')) path = path.substring(0, path.length - 4);
    final port = uri.hasPort ? uri.port : (hadScheme ? null : defaultPort);
    return Uri(scheme: uri.scheme, host: uri.host, port: port, path: path).toString();
  }

  static String _stripSlash(String url) {
    var out = url;
    while (out.endsWith('/')) {
      out = out.substring(0, out.length - 1);
    }
    return out;
  }

  static const Duration searchTimeout = Duration(seconds: 120);
  static const Duration chatTimeout = Duration(seconds: 60);
  static const Duration defaultTimeout = Duration(seconds: 15);
}
