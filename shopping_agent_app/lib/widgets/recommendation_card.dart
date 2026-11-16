import 'package:flutter/material.dart';

import '../models/search_response.dart';
import '../theme/app_theme.dart';
import 'product_bits.dart';

/// The suggested product, shown at the top of the results screen.
class RecommendationCard extends StatelessWidget {
  final Product product;
  final String reason;
  final VoidCallback? onTap;

  const RecommendationCard({super.key, required this.product, required this.reason, this.onTap});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      decoration: BoxDecoration(
        color: AppTheme.surfaceCard,
        borderRadius: BorderRadius.circular(AppTheme.radiusLg),
        border: Border.all(color: AppTheme.border),
      ),
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          borderRadius: BorderRadius.circular(AppTheme.radiusLg),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const AiPickChip(),
                const SizedBox(height: 12),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ProductImage(product: product, size: 96),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            product.title,
                            style: const TextStyle(
                              color: AppTheme.textPrimary,
                              fontSize: 15,
                              fontWeight: FontWeight.w500,
                              height: 1.35,
                            ),
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 8),
                          Text(product.displayPrice, style: AppTheme.display(20, weight: FontWeight.w700)),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              SourceBadge.of(product),
                              const SizedBox(width: 10),
                              Flexible(child: RatingLabel(product: product, size: 13)),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                if (reason.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  ReasonBox(reason: reason),
                ],
                const SizedBox(height: 14),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: product.hasValidUrl ? () => openProduct(context, product) : null,
                    child: Text('View on ${product.store}'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Plain "Best pick" label.
class AiPickChip extends StatelessWidget {
  const AiPickChip({super.key});

  @override
  Widget build(BuildContext context) {
    return const Text(
      'Best pick',
      style: TextStyle(color: AppTheme.primary, fontSize: 13, fontWeight: FontWeight.w600),
    );
  }
}

/// Why this product was suggested, as plain text.
class ReasonBox extends StatelessWidget {
  final String reason;
  final int? maxLines;

  const ReasonBox({super.key, required this.reason, this.maxLines});

  @override
  Widget build(BuildContext context) {
    return Text(
      reason,
      maxLines: maxLines,
      overflow: maxLines == null ? null : TextOverflow.ellipsis,
      style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14, height: 1.45),
    );
  }
}
