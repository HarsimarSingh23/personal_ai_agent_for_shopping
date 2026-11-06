import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../models/search_response.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

/// Small coloured pill naming the store a product comes from.
class SourceBadge extends StatelessWidget {
  final String source;
  final String label;
  final bool large;

  const SourceBadge({super.key, required this.source, required this.label, this.large = false});

  factory SourceBadge.of(Product p, {bool large = false}) =>
      SourceBadge(source: p.source, label: p.store, large: large);

  @override
  Widget build(BuildContext context) {
    final color = AppTheme.sourceColor(source);
    return Container(
      padding: EdgeInsets.symmetric(horizontal: large ? 10 : 7, vertical: large ? 5 : 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(large ? 20 : 6),
        border: large ? Border.all(color: color.withValues(alpha: 0.4)) : null,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(AppTheme.sourceIcon(source), color: color, size: large ? 13 : 10),
          SizedBox(width: large ? 5 : 4),
          Text(
            label.toUpperCase(),
            style: TextStyle(
              color: color,
              fontSize: large ? 11 : 9.5,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
            ),
          ),
        ],
      ),
    );
  }
}

/// Product photo on a white tile (store photos are shot on white), with a
/// store-coloured icon when there is no image or it fails to load.
class ProductImage extends StatelessWidget {
  final Product product;
  final double size;
  final double radius;

  const ProductImage({super.key, required this.product, this.size = 84, this.radius = AppTheme.radiusMd});

  @override
  Widget build(BuildContext context) {
    final color = AppTheme.sourceColor(product.source);
    final fallback = Container(
      color: AppTheme.surfaceElevated,
      alignment: Alignment.center,
      child: Icon(AppTheme.sourceIcon(product.source), color: color.withValues(alpha: 0.5), size: size * 0.36),
    );
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: SizedBox(
        width: size,
        height: size,
        child: product.hasImage
            ? CachedNetworkImage(
                imageUrl: product.image,
                fadeInDuration: const Duration(milliseconds: 200),
                // The white tile is only drawn once the photo has loaded.
                imageBuilder: (_, provider) => Container(
                  color: Colors.white,
                  padding: EdgeInsets.all(size * 0.06),
                  child: Image(image: provider, fit: BoxFit.contain),
                ),
                placeholder: (_, _) => const ColoredBox(color: AppTheme.surfaceElevated),
                errorWidget: (_, _, _) => fallback,
              )
            : fallback,
      ),
    );
  }
}

/// ★ 4.3 · 12K
class RatingLabel extends StatelessWidget {
  final Product product;
  final double size;

  const RatingLabel({super.key, required this.product, this.size = 12});

  @override
  Widget build(BuildContext context) {
    if (!product.hasRating) return const SizedBox.shrink();
    return Semantics(
      label: 'Rated ${product.displayRating} out of 5'
          '${product.displayReviews.isNotEmpty ? ' from ${product.displayReviews} reviews' : ''}',
      excludeSemantics: true,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.star_rounded, color: AppTheme.gold, size: size + 3),
          const SizedBox(width: 3),
          Text(
            product.displayRating,
            style: TextStyle(color: AppTheme.textPrimary, fontSize: size, fontWeight: FontWeight.w700),
          ),
          if (product.displayReviews.isNotEmpty)
            Text(
              ' · ${product.displayReviews}',
              style: TextStyle(color: AppTheme.textMuted, fontSize: size - 0.5),
            ),
        ],
      ),
    );
  }
}

/// Opens a product page in the store's app or the browser, with feedback on failure.
Future<void> openProduct(BuildContext context, Product product) async {
  final messenger = ScaffoldMessenger.of(context);
  final opened = product.hasValidUrl && await ApiService.launchProductUrl(product.url);
  if (!opened) {
    messenger.showSnackBar(const SnackBar(content: Text("Couldn't open the product page.")));
  }
}
