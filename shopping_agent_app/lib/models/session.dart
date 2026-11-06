import 'search_response.dart';

class SessionSummary {
  final String? sessionId;
  final DateTime timestamp;
  final String queryOriginal;
  final String queryEnglish;
  final Product? recommendation;
  final String recommendationReason;
  final int totalResults;

  const SessionSummary({
    required this.sessionId,
    required this.timestamp,
    required this.queryOriginal,
    required this.queryEnglish,
    this.recommendation,
    required this.recommendationReason,
    required this.totalResults,
  });

  String get title => queryOriginal.isNotEmpty ? queryOriginal : queryEnglish;

  bool get wasTranslated =>
      queryEnglish.isNotEmpty && queryEnglish.toLowerCase() != queryOriginal.toLowerCase();

  factory SessionSummary.fromJson(Map<String, dynamic> json) {
    // Summary payloads carry counts; full payloads carry the product lists.
    int total = 0;
    final counts = json['result_counts'];
    if (counts is Map) {
      for (final v in counts.values) {
        if (v is num) total += v.toInt();
      }
    } else {
      final results = json['results'] as Map<String, dynamic>? ?? {};
      for (final key in const ['amazon', 'flipkart', 'web']) {
        total += (results[key] as List?)?.length ?? 0;
      }
    }

    Product? rec;
    String recReason = '';
    final recData = json['recommendation'];
    if (recData is Map<String, dynamic>) {
      final prod = recData['product'];
      if (prod is Map<String, dynamic>) rec = Product.fromJson(prod);
      recReason = recData['reason'] as String? ?? '';
    }

    return SessionSummary(
      sessionId: json['session_id'] as String?,
      timestamp: DateTime.tryParse(json['timestamp'] as String? ?? '') ?? DateTime.now().toUtc(),
      queryOriginal: json['query_original'] as String? ?? '',
      queryEnglish: json['query_english'] as String? ?? '',
      recommendation: rec,
      recommendationReason: recReason,
      totalResults: total,
    );
  }
}
