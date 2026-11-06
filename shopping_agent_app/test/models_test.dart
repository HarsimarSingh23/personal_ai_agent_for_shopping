import 'package:flutter_test/flutter_test.dart';
import 'package:shopping_agent_app/models/search_response.dart';
import 'package:shopping_agent_app/models/session.dart';
import 'package:shopping_agent_app/screens/search_results_screen.dart';
import 'package:shopping_agent_app/utils/formatters.dart';

Product _p(String title, {double? price, double? rating, int? reviews}) => Product(
      title: title,
      price: price == null ? 'N/A' : '₹$price',
      rating: rating?.toString() ?? 'N/A',
      reviewsCount: reviews?.toString() ?? 'N/A',
      url: 'https://x/$title',
      source: 'amazon',
      image: '',
      priceValue: price,
      ratingValue: rating,
      reviewsValue: reviews,
    );

void main() {
  group('Product.fromJson', () {
    test('uses numeric fields from the API', () {
      final p = Product.fromJson({
        'title': 'Sony WH-1000XM5',
        'price': '₹26,990',
        'rating': '4.4 out of 5 stars',
        'reviews_count': '(12,345)',
        'url': 'https://amazon.in/dp/1',
        'image': 'https://img/1.jpg',
        'source': 'amazon',
        'price_value': 26990,
        'rating_value': 4.4,
        'reviews_value': 12345,
      });
      expect(p.displayPrice, '₹26,990');
      expect(p.displayRating, '4.4');
      expect(p.displayReviews, '12.3K');
      expect(p.store, 'Amazon');
      expect(p.hasValidUrl, isTrue);
      expect(p.hasImage, isTrue);
    });

    test('derives numbers for legacy sessions and formats rupees', () {
      final p = Product.fromJson({
        'title': 'boAt Rockerz',
        'price': '₹129999',
        'rating': 4.2, // non-string values must not crash
        'reviews_count': 'N/A',
        'url': 'N/A',
        'image': 'N/A',
        'source': 'Croma',
      });
      expect(p.priceValue, 129999);
      expect(p.displayPrice, '₹1,29,999');
      expect(p.ratingValue, 4.2);
      expect(p.displayReviews, '');
      expect(p.hasValidUrl, isFalse);
      expect(p.hasImage, isFalse);
      expect(p.store, 'Croma');
    });

    test('keeps non-rupee prices and handles missing prices', () {
      expect(Product.fromJson({'title': 'a', 'price': r'$199'}).displayPrice, r'$199');
      expect(Product.fromJson({'title': 'a', 'price': 'Rs. 5,999'}).displayPrice, '₹5,999');
      expect(Product.fromJson({'title': 'a'}).displayPrice, 'See price');
    });
  });

  test('SearchResponse reports unavailable sources', () {
    final r = SearchResponse.fromJson({
      'query': 'headphones',
      'results': {'amazon': [], 'flipkart': [], 'web': []},
      'source_status': {'amazon': 'ok', 'flipkart': 'timeout', 'web': 'failed'},
      'recommendation': null,
    });
    expect(r.isEmpty, isTrue);
    expect(r.unavailableSources, ['Flipkart', 'Other stores']);
  });

  test('SessionSummary reads summary counts and full payloads', () {
    final summary = SessionSummary.fromJson({
      'session_id': 'a',
      'timestamp': '2026-11-01T10:00:00+00:00',
      'query_original': 'achhe headphones',
      'query_english': 'good headphones',
      'result_counts': {'amazon': 3, 'flipkart': 2, 'web': 1},
    });
    expect(summary.totalResults, 6);
    expect(summary.wasTranslated, isTrue);

    final full = SessionSummary.fromJson({
      'session_id': 'b',
      'timestamp': 'not a date',
      'query_original': 'x',
      'query_english': 'x',
      'results': {
        'amazon': [{}, {}],
        'web': [{}],
      },
    });
    expect(full.totalResults, 3);
    expect(full.wasTranslated, isFalse);
  });

  test('sortProducts puts unknown values last', () {
    final items = [_p('mid', price: 500, rating: 4.0), _p('none'), _p('cheap', price: 100, rating: 4.5)];
    expect(sortProducts(items, SortOption.priceLow).map((p) => p.title), ['cheap', 'mid', 'none']);
    expect(sortProducts(items, SortOption.priceHigh).map((p) => p.title), ['mid', 'cheap', 'none']);
    expect(sortProducts(items, SortOption.rating).map((p) => p.title), ['cheap', 'mid', 'none']);
    expect(sortProducts(items, SortOption.relevance).map((p) => p.title), ['mid', 'none', 'cheap']);
  });

  test('timeAgo', () {
    final now = DateTime.utc(2026, 11, 6, 12);
    expect(timeAgo(now.subtract(const Duration(seconds: 5)), now: now), 'Just now');
    expect(timeAgo(now.subtract(const Duration(minutes: 5)), now: now), '5m ago');
    expect(timeAgo(now.subtract(const Duration(hours: 3)), now: now), '3h ago');
    expect(timeAgo(now.subtract(const Duration(days: 1)), now: now), 'Yesterday');
  });
}
