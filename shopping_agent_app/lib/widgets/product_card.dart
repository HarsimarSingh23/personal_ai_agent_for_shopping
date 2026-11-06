import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../models/search_response.dart';
import '../theme/app_theme.dart';
import 'product_bits.dart';

class ProductCard extends StatelessWidget {
  final Product product;
  final int index;
  final bool isTopPick;
  final VoidCallback? onTap;

  const ProductCard({
    super.key,
    required this.product,
    required this.index,
    this.isTopPick = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: AppTheme.surfaceCard,
        borderRadius: BorderRadius.circular(AppTheme.radiusLg),
        child: InkWell(
          onTap: onTap ?? () => openProduct(context, product),
          borderRadius: BorderRadius.circular(AppTheme.radiusLg),
          child: Ink(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(AppTheme.radiusLg),
              border: Border.all(
                color: isTopPick ? AppTheme.primary.withValues(alpha: 0.45) : AppTheme.border,
              ),
            ),
            padding: const EdgeInsets.all(12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ProductImage(product: product, size: 88),
                const SizedBox(width: 14),
                Expanded(child: _info()),
              ],
            ),
          ),
        ),
      ),
    )
        .animate(delay: Duration(milliseconds: 40 * (index % 8)))
        .fadeIn(duration: 280.ms)
        .slideY(begin: 0.06, duration: 280.ms, curve: Curves.easeOutCubic);
  }

  Widget _info() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            SourceBadge.of(product),
            if (isTopPick) ...[
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(
                  color: AppTheme.primary,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  'AI PICK',
                  style: TextStyle(
                    color: AppTheme.onPrimary,
                    fontSize: 9.5,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.8,
                  ),
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 6),
        Text(
          product.title,
          style: const TextStyle(
            color: AppTheme.textPrimary,
            fontSize: 13.5,
            fontWeight: FontWeight.w600,
            height: 1.35,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 8),
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Expanded(
              child: Text(
                product.displayPrice,
                style: AppTheme.display(17, weight: FontWeight.w800),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            RatingLabel(product: product),
          ],
        ),
      ],
    );
  }
}
