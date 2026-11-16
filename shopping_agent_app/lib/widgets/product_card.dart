import 'package:flutter/material.dart';

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
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: AppTheme.surfaceCard,
        borderRadius: BorderRadius.circular(AppTheme.radiusLg),
        child: InkWell(
          onTap: onTap ?? () => openProduct(context, product),
          borderRadius: BorderRadius.circular(AppTheme.radiusLg),
          child: Ink(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(AppTheme.radiusLg),
              border: Border.all(color: AppTheme.border),
            ),
            padding: const EdgeInsets.all(12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ProductImage(product: product, size: 80),
                const SizedBox(width: 12),
                Expanded(child: _info()),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _info() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          product.title,
          style: const TextStyle(
            color: AppTheme.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w500,
            height: 1.35,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 6),
        Text(
          product.displayPrice,
          style: AppTheme.display(16, weight: FontWeight.w700),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 4),
        Row(
          children: [
            SourceBadge.of(product),
            const SizedBox(width: 10),
            Expanded(child: product.hasRating ? RatingLabel(product: product) : const SizedBox.shrink()),
            if (isTopPick)
              const Text(
                'Best pick',
                style: TextStyle(color: AppTheme.primary, fontSize: 12, fontWeight: FontWeight.w600),
              ),
          ],
        ),
      ],
    );
  }
}
