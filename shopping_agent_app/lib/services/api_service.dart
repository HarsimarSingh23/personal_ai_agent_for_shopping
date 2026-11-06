import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/app_config.dart';
import '../models/search_response.dart';
import '../models/session.dart';

/// A request failure with a message that is safe to show to the user.
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  const ApiException(this.message, {this.statusCode});

  bool get isNetworkError => statusCode == null;

  @override
  String toString() => message;
}

class ChatReply {
  final String message;
  final bool isReadyToSearch;
  final String searchQuery;

  const ChatReply({required this.message, required this.isReadyToSearch, required this.searchQuery});

  factory ChatReply.fromJson(Map<String, dynamic> json) => ChatReply(
        message: (json['message'] as String?)?.trim().isNotEmpty == true
            ? json['message'] as String
            : "Let me look that up for you.",
        isReadyToSearch: json['is_ready_to_search'] == true,
        searchQuery: (json['search_query'] as String?)?.trim() ?? '',
      );
}

class ApiService {
  ApiService(this._client, {String? baseUrl}) : _baseUrl = baseUrl ?? AppConfig.apiBaseUrl;

  /// Shared instance. Tests may replace it with one backed by a MockClient.
  static ApiService instance = ApiService(http.Client());

  static const _clientIdKey = 'client_id';

  final http.Client _client;
  final String _baseUrl;
  String? _clientId;

  String get _api => '$_baseUrl/api';

  /// Loads (or creates) the anonymous install ID that scopes search history.
  Future<void> init() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _clientId = prefs.getString(_clientIdKey);
      if (_clientId == null) {
        _clientId = _newClientId();
        await prefs.setString(_clientIdKey, _clientId!);
      }
    } catch (e) {
      debugPrint('Could not persist client id: $e');
      _clientId ??= _newClientId();
    }
  }

  static String _newClientId() {
    final rnd = Random.secure();
    return List.generate(16, (_) => rnd.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (_clientId != null) 'X-Client-ID': _clientId!,
        if (AppConfig.apiKey.isNotEmpty) 'X-API-Key': AppConfig.apiKey,
      };

  // ── Endpoints ─────────────────────────────────────────────────────────────

  Future<ChatReply> chat(List<Map<String, String>> history) async {
    final json = await _request(
      () => _client.post(Uri.parse('$_api/chat'), headers: _headers, body: jsonEncode({'history': history})),
      AppConfig.chatTimeout,
    );
    return ChatReply.fromJson(json as Map<String, dynamic>);
  }

  Future<SearchResponse> search(String query) async {
    final json = await _request(
      () => _client.post(Uri.parse('$_api/search'), headers: _headers, body: jsonEncode({'query': query})),
      AppConfig.searchTimeout,
    );
    return SearchResponse.fromJson(json as Map<String, dynamic>);
  }

  Future<List<SessionSummary>> getSessions({int limit = 50, int offset = 0}) async {
    final uri = Uri.parse('$_api/sessions').replace(queryParameters: {
      'limit': '$limit',
      'offset': '$offset',
      'summary': 'true',
    });
    final json = await _request(() => _client.get(uri, headers: _headers), AppConfig.defaultTimeout);
    return (json as List).whereType<Map<String, dynamic>>().map(SessionSummary.fromJson).toList();
  }

  Future<SearchResponse> getSession(String sessionId) async {
    final json = await _request(
      () => _client.get(Uri.parse('$_api/sessions/$sessionId'), headers: _headers),
      AppConfig.defaultTimeout,
    );
    return SearchResponse.fromJson(json as Map<String, dynamic>);
  }

  Future<void> deleteSession(String sessionId) async {
    await _request(
      () => _client.delete(Uri.parse('$_api/sessions/$sessionId'), headers: _headers),
      AppConfig.defaultTimeout,
    );
  }

  Future<void> clearHistory() async {
    await _request(() => _client.delete(Uri.parse('$_api/sessions'), headers: _headers), AppConfig.defaultTimeout);
  }

  Future<bool> checkHealth() async {
    try {
      final response = await _client.get(Uri.parse('$_baseUrl/health')).timeout(const Duration(seconds: 6));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  static Future<bool> launchProductUrl(String url) async {
    final uri = Uri.tryParse(url);
    if (uri == null || !uri.hasScheme || !(uri.scheme == 'https' || uri.scheme == 'http')) return false;
    try {
      return await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      return false;
    }
  }

  // ── Plumbing ──────────────────────────────────────────────────────────────

  Future<dynamic> _request(Future<http.Response> Function() send, Duration timeout) async {
    final http.Response response;
    try {
      response = await send().timeout(timeout);
    } on TimeoutException {
      throw const ApiException('This is taking longer than usual. Please try again.');
    } on http.ClientException {
      throw const ApiException("Can't reach the server. Check your connection and try again.");
    } catch (e) {
      debugPrint('Request failed: $e');
      throw const ApiException("Can't reach the server. Check your connection and try again.");
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.bodyBytes.isEmpty) return null;
      try {
        return jsonDecode(utf8.decode(response.bodyBytes));
      } catch (_) {
        throw ApiException('The server sent an unexpected response.', statusCode: response.statusCode);
      }
    }
    throw ApiException(_errorMessage(response), statusCode: response.statusCode);
  }

  String _errorMessage(http.Response response) {
    String? detail;
    try {
      final body = jsonDecode(utf8.decode(response.bodyBytes));
      if (body is Map && body['detail'] is String) detail = body['detail'] as String;
    } catch (_) {}

    switch (response.statusCode) {
      case 401:
      case 403:
        return 'This app is not authorised to use the server.';
      case 404:
        return detail ?? 'Not found.';
      case 422:
        return 'Please rephrase that and try again.';
      case 429:
        return detail ?? "You're going a bit fast. Please wait a moment.";
      case 503:
        return detail ?? 'The service is temporarily unavailable. Please try again soon.';
    }
    if (response.statusCode >= 500) return 'Something went wrong on our side. Please try again.';
    return detail ?? 'Request failed (${response.statusCode}).';
  }
}
