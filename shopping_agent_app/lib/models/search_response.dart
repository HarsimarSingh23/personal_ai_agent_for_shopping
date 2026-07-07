class Product {
  final String title;
  final String price;
  final String rating;
  final String reviewsCount;
  final String url;
  final String source;
  final String image;

  const Product({
    required this.title,
    required this.price,
    required this.rating,
    required this.reviewsCount,
    required this.url,
    required this.source,
    required this.image,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      title:        json['title']         as String? ?? 'N/A',
      price:        json['price']         as String? ?? 'N/A',
      rating:       json['rating']        as String? ?? 'N/A',
      reviewsCount: json['reviews_count'] as String? ?? 'N/A',
      url:          json['url']           as String? ?? '',
      source:       json['source']        as String? ?? 'web',
      image:        json['image']         as String? ?? '',
    );
  }

  bool get hasValidUrl => url.isNotEmpty && url != 'N/A';
  bool get hasImage    => image.isNotEmpty && image != 'N/A' && image.startsWith('http');

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Product &&
          runtimeType == other.runtimeType &&
          url == other.url &&
          title == other.title &&
          source == other.source;

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

  const SearchResponse({
    this.sessionId,
    required this.query,
    required this.amazon,
    required this.flipkart,
    required this.web,
    this.recommendation,
    required this.recommendationReason,
    this.message,
  });

  List<Product> get allProducts => [...amazon, ...flipkart, ...web];

  factory SearchResponse.fromJson(Map<String, dynamic> json) {
    final results = json['results'] as Map<String, dynamic>? ?? {};

    final amazonList   = _parseList(results['amazon']);
    final flipkartList = _parseList(results['flipkart']);
    final webList      = _parseList(results['web']);

    Product? recProduct;
    String recReason = 'No recommendation available';

    final rec = json['recommendation'] as Map<String, dynamic>?;
    if (rec != null) {
      final prod = rec['product'] as Map<String, dynamic>?;
      if (prod != null) recProduct = Product.fromJson(prod);
      recReason = rec['reason'] as String? ?? recReason;
    }

    return SearchResponse(
      sessionId:              json['session_id'] as String?,
      query:                  json['query']      as String? ?? '',
      amazon:                 amazonList,
      flipkart:               flipkartList,
      web:                    webList,
      recommendation:         recProduct,
      recommendationReason:   recReason,
      message:                json['message']    as String?,
    );
  }

  static List<Product> _parseList(dynamic raw) {
    if (raw is List) {
      return raw
          .whereType<Map<String, dynamic>>()
          .map(Product.fromJson)
          .toList();
    }
    return [];
  }
}
