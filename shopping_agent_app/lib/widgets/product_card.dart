import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/search_response.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';

class ProductCard extends StatelessWidget {
  final Product product;
  final int index;
  final VoidCallback? onTap;

  const ProductCard({
    super.key,
    required this.product,
    required this.index,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final sourceColor = AppTheme.sourceColor(product.source);
    return GestureDetector(
      onTap: onTap ?? () => ApiService.launchProductUrl(product.url),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(
          color: AppTheme.surfaceCard,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppTheme.border, width: 1),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.25),
              blurRadius: 10,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildImage(sourceColor),
              const SizedBox(width: 14),
              Expanded(child: _buildInfo(sourceColor)),
            ],
          ),
        ),
      )
          .animate(delay: Duration(milliseconds: 50 * (index % 10)))
          .fadeIn(duration: 300.ms)
          .slideX(begin: 0.05, duration: 300.ms, curve: Curves.easeOutCubic),
    );
  }

  Widget _buildImage(Color sourceColor) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Container(
        width: 80,
        height: 80,
        color: AppTheme.surfaceElevated,
        child: product.hasImage
            ? CachedNetworkImage(
                imageUrl: product.image,
                fit: BoxFit.cover,
                placeholder: (_, __) => const Center(
                  child: SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                        strokeWidth: 1.5, color: AppTheme.primary),
                  ),
                ),
                errorWidget: (_, __, ___) => _imageFallback(sourceColor),
              )
            : _imageFallback(sourceColor),
      ),
    );
  }

  Widget _imageFallback(Color sourceColor) {
    return Center(
      child: Icon(
        AppTheme.sourceIcon(product.source),
        color: sourceColor.withValues(alpha: 0.4),
        size: 28,
      ),
    );
  }

  Widget _buildInfo(Color sourceColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Source badge
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
          decoration: BoxDecoration(
            color: sourceColor.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            product.source.toUpperCase(),
            style: TextStyle(
              color: sourceColor,
              fontSize: 9,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
            ),
          ),
        ),
        const SizedBox(height: 6),
        // Title
        Text(
          product.title,
          style: const TextStyle(
            color: AppTheme.textPrimary,
            fontSize: 13,
            fontWeight: FontWeight.w600,
            height: 1.4,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 8),
        // Price + Rating
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Expanded(
              child: Text(
                product.price,
                style: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            if (product.rating != 'N/A') ...[
              const Icon(Icons.star_rounded, color: AppTheme.gold, size: 14),
              const SizedBox(width: 3),
              Text(
                product.rating,
                style: const TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
            const SizedBox(width: 10),
            Icon(
              Icons.arrow_outward_rounded,
              size: 16,
              color: AppTheme.textMuted,
            ),
          ],
        ),
      ],
    );
  }
}
