import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb, defaultTargetPlatform, TargetPlatform;
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import '../models/search_response.dart';
import '../models/session.dart';

class ApiService {

  ApiService._();
  static final ApiService instance = ApiService._();

  static const Duration _searchTimeout = Duration(seconds: 70);
  static const Duration _defaultTimeout = Duration(seconds: 15);

  String get baseUrl {
    if (kIsWeb) return 'http://127.0.0.1:8000/api';
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000/api';
    }
    return 'http://127.0.0.1:8000/api';
  }

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };


  Future<SearchResponse> search(String query) async {
    final response = await http
        .post(
          Uri.parse('$baseUrl/search'),
          headers: _headers,
          body: jsonEncode({'query': query}),
        )
        .timeout(_searchTimeout);

    if (response.statusCode == 200) {
      return SearchResponse.fromJson(
          jsonDecode(utf8.decode(response.bodyBytes)));
    }
    final detail = _extractDetail(response.body);
    throw Exception('Search failed: $detail');
  }


  Future<List<SessionSummary>> getSessions() async {
    final response = await http
        .get(Uri.parse('$baseUrl/sessions'), headers: _headers)
        .timeout(_defaultTimeout);

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
      return data
          .whereType<Map<String, dynamic>>()
          .map(SessionSummary.fromJson)
          .toList();
    }
    final detail = _extractDetail(response.body);
    throw Exception('Failed to load sessions: $detail');
  }


  Future<bool> checkHealth() async {
    try {
      final response = await http
          .get(Uri.parse('${baseUrl.replaceAll('/api', '')}/health'))
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }


  static Future<bool> launchProductUrl(String url) async {
    if (url.isEmpty || url == 'N/A') return false;
    final uri = Uri.tryParse(url);
    if (uri == null) return false;
    try {
      return await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      return false;
    }
  }


  String _extractDetail(String body) {
    try {
      final json = jsonDecode(body) as Map<String, dynamic>;
      return json['detail']?.toString() ?? body;
    } catch (_) {
      return body.length > 200 ? body.substring(0, 200) : body;
    }
  }
}
