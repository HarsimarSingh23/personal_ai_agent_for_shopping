import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../models/search_response.dart';
import '../theme/app_theme.dart';
import '../widgets/product_bits.dart';
import '../widgets/recommendation_card.dart';

class ProductDetailScreen extends StatelessWidget {
  final Product product;

  /// Set when this product is the AI's pick, to explain why.
  final String? aiReason;

  const ProductDetailScreen({super.key, required this.product, this.aiReason});

  Future<void> _copyLink(BuildContext context) async {
    final messenger = ScaffoldMessenger.of(context);
    await Clipboard.setData(ClipboardData(text: product.url));
    HapticFeedback.selectionClick();
    messenger.showSnackBar(const SnackBar(content: Text('Link copied')));
  }

  @override
  Widget build(BuildContext context) {
    final isPick = aiReason != null && aiReason!.isNotEmpty;
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 320,
            pinned: true,
            backgroundColor: AppTheme.surface,
            leading: Padding(
              padding: const EdgeInsets.all(8),
              child: IconButton.filledTonal(
                tooltip: 'Back',
                style: IconButton.styleFrom(backgroundColor: AppTheme.background.withValues(alpha: 0.75)),
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.arrow_back_rounded, color: AppTheme.textPrimary),
              ),
            ),
            flexibleSpace: FlexibleSpaceBar(background: _hero()),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      SourceBadge.of(product, large: true),
                      if (isPick) ...[const SizedBox(width: 8), const AiPickChip()],
                    ],
                  ),
                  const SizedBox(height: 14),
                  SelectableText(
                    product.title,
                    style: const TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 19,
                      fontWeight: FontWeight.w700,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Expanded(
                        child: Text(product.displayPrice, style: AppTheme.display(32, weight: FontWeight.w800)),
                      ),
                      if (product.hasRating) RatingLabel(product: product, size: 15),
                    ],
                  ),
                  if (isPick) ...[
                    const SizedBox(height: 22),
                    Text('WHY THE AI PICKED THIS', style: AppTheme.overline),
                    const SizedBox(height: 10),
                    ReasonBox(reason: aiReason!),
                  ],
                  const SizedBox(height: 22),
                  const Divider(),
                  const SizedBox(height: 16),
                  const _InfoRow(
                    icon: Icons.verified_user_outlined,
                    text: "You'll complete your purchase securely on the store's own site. "
                        'AI Shopper never handles payments.',
                  ),
                  const SizedBox(height: 12),
                  const _InfoRow(
                    icon: Icons.schedule_rounded,
                    text: 'Prices and stock change often. Check the final price on the store before buying.',
                  ),
                ],
              ).animate().fadeIn(duration: 350.ms).slideY(begin: 0.04, duration: 350.ms, curve: Curves.easeOutCubic),
            ),
          ),
        ],
      ),
      bottomNavigationBar: product.hasValidUrl ? _buyBar(context) : null,
    );
  }

  Widget _hero() {
    if (!product.hasImage) {
      return Container(
        color: AppTheme.surface,
        alignment: Alignment.center,
        child: Icon(
          AppTheme.sourceIcon(product.source),
          size: 72,
          color: AppTheme.sourceColor(product.source).withValues(alpha: 0.35),
        ),
      );
    }
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(32, 72, 32, 24),
      child: Hero(
        tag: product.image,
        child: CachedNetworkImage(
          imageUrl: product.image,
          fit: BoxFit.contain,
          errorWidget: (_, _, _) => Icon(
            AppTheme.sourceIcon(product.source),
            size: 72,
            color: AppTheme.sourceColor(product.source).withValues(alpha: 0.35),
          ),
        ),
      ),
    );
  }

  Widget _buyBar(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      decoration: const BoxDecoration(
        color: AppTheme.surface,
        border: Border(top: BorderSide(color: AppTheme.border)),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            IconButton.outlined(
              tooltip: 'Copy link',
              onPressed: () => _copyLink(context),
              style: IconButton.styleFrom(
                fixedSize: const Size(52, 52),
                side: const BorderSide(color: AppTheme.borderBright),
              ),
              icon: const Icon(Icons.link_rounded),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: SizedBox(
                height: 52,
                child: FilledButton.icon(
                  onPressed: () => openProduct(context, product),
                  icon: const Icon(Icons.shopping_cart_checkout_rounded),
                  label: Text('Buy on ${product.store}'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String text;

  const _InfoRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 18, color: AppTheme.textMuted),
        const SizedBox(width: 10),
        Expanded(
          child: Text(text, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13, height: 1.5)),
        ),
      ],
    );
  }
}
