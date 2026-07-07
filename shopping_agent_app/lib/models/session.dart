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

  factory SessionSummary.fromJson(Map<String, dynamic> json) {
    final results = json['results'] as Map<String, dynamic>? ?? {};
    final amazonCount   = (results['amazon']   as List?)?.length ?? 0;
    final flipkartCount = (results['flipkart'] as List?)?.length ?? 0;
    final webCount      = (results['web']      as List?)?.length ?? 0;

    Product? rec;
    String recReason = '';
    final recData = json['recommendation'] as Map<String, dynamic>?;
    if (recData != null) {
      final prod = recData['product'] as Map<String, dynamic>?;
      if (prod != null) rec = Product.fromJson(prod);
      recReason = recData['reason'] as String? ?? '';
    }

    DateTime ts;
    try {
      ts = DateTime.parse(json['timestamp'] as String? ?? '');
    } catch (_) {
      ts = DateTime.now().toUtc();
    }

    return SessionSummary(
      sessionId:            json['session_id']    as String?,
      timestamp:            ts,
      queryOriginal:        json['query_original'] as String? ?? '',
      queryEnglish:         json['query_english']  as String? ?? '',
      recommendation:       rec,
      recommendationReason: recReason,
      totalResults:         amazonCount + flipkartCount + webCount,
    );
  }
}
