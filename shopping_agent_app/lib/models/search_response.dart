import '../utils/formatters.dart';

String _str(dynamic value, [String fallback = 'N/A']) {
  if (value == null) return fallback;
  final text = value.toString().trim();
  return text.isEmpty ? fallback : text;
}

double? _num(dynamic value) => value is num ? value.toDouble() : null;

class Product {
  final String title;
  final String price;
  final String rating;
  final String reviewsCount;
  final String url;
  final String source;
  final String image;

  /// Numeric companions (null when the store didn't provide a value).
  final double? priceValue;
  final double? ratingValue;
  final int? reviewsValue;

  const Product({
    required this.title,
    required this.price,
    required this.rating,
    required this.reviewsCount,
    required this.url,
    required this.source,
    required this.image,
    this.priceValue,
    this.ratingValue,
    this.reviewsValue,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    final price = _str(json['price']);
    final rating = _str(json['rating']);
    final reviews = _str(json['reviews_count']);
    // Older saved sessions predate the numeric fields; derive them.
    final ratingValue = _num(json['rating_value']) ?? parseNumber(rating);
    return Product(
      title: _str(json['title']),
      price: price,
      rating: rating,
      reviewsCount: reviews,
      url: _str(json['url'], ''),
      source: _str(json['source'], 'web'),
      image: _str(json['image'], ''),
      priceValue: _num(json['price_value']) ?? parseNumber(price),
      ratingValue: (ratingValue != null && ratingValue <= 5) ? ratingValue : null,
      reviewsValue: _num(json['reviews_value'])?.toInt() ?? parseNumber(reviews)?.toInt(),
    );
  }

  bool get hasValidUrl => url.startsWith('http');
  bool get hasImage => image.startsWith('http');
  bool get hasRating => ratingValue != null;

  static final RegExp _rupeePrice =
      RegExp(r'^(?:₹|rs\.?|inr)?\s*[\d,]+(?:\.\d+)?$', caseSensitive: false);

  /// Price for display, e.g. "₹1,29,999".
  String get displayPrice {
    if (priceValue != null && _rupeePrice.hasMatch(price.trim())) {
      return formatInr(priceValue!);
    }
    return price == 'N/A' ? 'See price' : price;
  }

  String get displayRating => ratingValue?.toStringAsFixed(1) ?? '';

  String get displayReviews => reviewsValue != null && reviewsValue! > 0 ? compactCount(reviewsValue!) : '';

  String get store => storeName(source);

  bool isSameAs(Product? other) =>
      other != null && (hasValidUrl ? url == other.url : title == other.title);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Product && url == other.url && title == other.title && source == other.source;

  @override
  int get hashCode => Object.hash(url, title, source);
}

class SearchResponse {
  final String? sessionId;
  final String query;
  final List<Product> amazon;
  final List<Product> flipkart;
  final List<Product> web;
  final Product? recommendation;
  final String recommendationReason;
  final String? message;

  /// Per-source outcome: ok | empty | failed | timeout.
  final Map<String, String> sourceStatus;

  const SearchResponse({
    this.sessionId,
    required this.query,
    required this.amazon,
    required this.flipkart,
    required this.web,
    this.recommendation,
    required this.recommendationReason,
    this.message,
    this.sourceStatus = const {},
  });

  List<Product> get allProducts => [...amazon, ...flipkart, ...web];

  int get totalCount => amazon.length + flipkart.length + web.length;

  bool get isEmpty => totalCount == 0;

  /// Sources that failed or timed out, as store names ("Flipkart").
  List<String> get unavailableSources => sourceStatus.entries
      .where((e) => e.value == 'failed' || e.value == 'timeout')
      .map((e) => e.key == 'web' ? 'Other stores' : storeName(e.key))
      .toList();

  factory SearchResponse.fromJson(Map<String, dynamic> json) {
    final results = json['results'] as Map<String, dynamic>? ?? {};

    Product? recProduct;
    String recReason = '';
    final rec = json['recommendation'];
    if (rec is Map<String, dynamic>) {
      final prod = rec['product'];
      if (prod is Map<String, dynamic>) recProduct = Product.fromJson(prod);
      recReason = _str(rec['reason'], '');
    }

    final status = json['source_status'];
    return SearchResponse(
      sessionId: json['session_id'] as String?,
      query: _str(json['query'] ?? json['query_english'], ''),
      amazon: _parseList(results['amazon']),
      flipkart: _parseList(results['flipkart']),
      web: _parseList(results['web']),
      recommendation: recProduct,
      recommendationReason: recReason,
      message: json['message'] as String?,
      sourceStatus: status is Map
          ? status.map((k, v) => MapEntry(k.toString(), v.toString()))
          : const {},
    );
  }

  static List<Product> _parseList(dynamic raw) {
    if (raw is! List) return const [];
    return raw.whereType<Map<String, dynamic>>().map(Product.fromJson).toList();
  }
}
