import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../models/search_response.dart';
import '../theme/app_theme.dart';
import 'product_bits.dart';

/// The AI's top pick, shown at the top of the results screen.
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
        gradient: AppTheme.recommendGradient,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.35), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primary.withValues(alpha: 0.08),
            blurRadius: 32,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          borderRadius: BorderRadius.circular(24),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const AiPickChip(),
                    const Spacer(),
                    SourceBadge.of(product, large: true),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ProductImage(product: product, size: 104, radius: 16),
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
                              fontWeight: FontWeight.w700,
                              height: 1.35,
                            ),
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 10),
                          Text(product.displayPrice, style: AppTheme.display(24, weight: FontWeight.w800)),
                          const SizedBox(height: 4),
                          RatingLabel(product: product, size: 13),
                        ],
                      ),
                    ),
                  ],
                ),
                if (reason.isNotEmpty) ...[
                  const SizedBox(height: 14),
                  ReasonBox(reason: reason),
                ],
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: product.hasValidUrl ? () => openProduct(context, product) : null,
                    icon: const Icon(Icons.open_in_new_rounded, size: 18),
                    label: Text('View deal on ${product.store}'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    ).animate().fadeIn(duration: 350.ms).slideY(begin: 0.06, duration: 350.ms, curve: Curves.easeOutCubic);
  }
}

class AiPickChip extends StatelessWidget {
  const AiPickChip({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        gradient: AppTheme.brandGradient,
        borderRadius: BorderRadius.circular(20),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.auto_awesome, color: AppTheme.onPrimary, size: 13),
          SizedBox(width: 5),
          Text(
            'AI TOP PICK',
            style: TextStyle(
              color: AppTheme.onPrimary,
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.1,
            ),
          ),
        ],
      ),
    );
  }
}

class ReasonBox extends StatelessWidget {
  final String reason;
  final int? maxLines;

  const ReasonBox({super.key, required this.reason, this.maxLines});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.28),
        borderRadius: BorderRadius.circular(AppTheme.radiusMd),
        border: Border.all(color: AppTheme.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 1),
            child: Icon(Icons.lightbulb_outline_rounded, color: AppTheme.gold, size: 16),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              reason,
              maxLines: maxLines,
              overflow: maxLines == null ? null : TextOverflow.ellipsis,
              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13, height: 1.5),
            ),
          ),
        ],
      ),
    );
  }
}
