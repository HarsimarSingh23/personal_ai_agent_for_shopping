import 'package:intl/intl.dart';

final NumberFormat _inr = NumberFormat.currency(
  locale: 'en_IN',
  symbol: '₹',
  decimalDigits: 0,
);
final NumberFormat _compact = NumberFormat.compact(locale: 'en_IN');

/// ₹1,29,999 (Indian digit grouping).
String formatInr(double value) => _inr.format(value);

/// 12345 → "12K"
String compactCount(int value) => _compact.format(value);

/// Pulls the first number out of strings like "₹1,299.00" or "Rs. 5,999".
double? parseNumber(String? text) {
  if (text == null) return null;
  final match = RegExp(r'\d[\d,]*(?:\.\d+)?').firstMatch(text);
  if (match == null) return null;
  final value = double.tryParse(match.group(0)!.replaceAll(',', ''));
  return (value == null || value <= 0) ? null : value;
}

String timeAgo(DateTime time, {DateTime? now}) {
  final current = (now ?? DateTime.now()).toUtc();
  final diff = current.difference(time.toUtc());
  if (diff.inSeconds < 60) return 'Just now';
  if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
  if (diff.inHours < 24) return '${diff.inHours}h ago';
  if (diff.inDays == 1) return 'Yesterday';
  if (diff.inDays < 7) return '${diff.inDays}d ago';
  return DateFormat('d MMM yyyy').format(time.toLocal());
}

/// "amazon" → "Amazon"; retailer names from the web ("Croma") pass through.
String storeName(String source) {
  switch (source.toLowerCase()) {
    case 'amazon':
      return 'Amazon';
    case 'flipkart':
      return 'Flipkart';
    case 'web':
      return 'Web';
    default:
      return source;
  }
}
