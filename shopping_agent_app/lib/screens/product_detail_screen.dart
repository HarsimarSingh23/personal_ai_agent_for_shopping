import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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
                      if (isPick) ...[const SizedBox(width: 12), const AiPickChip()],
                    ],
                  ),
                  const SizedBox(height: 10),
                  SelectableText(
                    product.title,
                    style: const TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 18,
                      fontWeight: FontWeight.w500,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Expanded(
                        child: Text(product.displayPrice, style: AppTheme.display(26, weight: FontWeight.w700)),
                      ),
                      if (product.hasRating) RatingLabel(product: product, size: 15),
                    ],
                  ),
                  if (isPick) ...[
                    const SizedBox(height: 20),
                    const Text('Why this was suggested', style: AppTheme.overline),
                    const SizedBox(height: 6),
                    ReasonBox(reason: aiReason!),
                  ],
                  const SizedBox(height: 22),
                  const Divider(),
                  const SizedBox(height: 16),
                  const _InfoRow(
                    icon: Icons.verified_user_outlined,
                    text: "You buy the product on the store's own website. This app never handles payments.",
                  ),
                  const SizedBox(height: 12),
                  const _InfoRow(
                    icon: Icons.schedule_rounded,
                    text: 'Prices and stock change often. Check the final price on the store before buying.',
                  ),
                ],
              ),
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
          color: AppTheme.textMuted,
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
            color: AppTheme.textMuted,
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
                fixedSize: const Size(48, 48),
                side: const BorderSide(color: AppTheme.borderBright),
              ),
              icon: const Icon(Icons.link_rounded),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: SizedBox(
                height: 48,
                child: FilledButton(
                  onPressed: () => openProduct(context, product),
                  child: Text('Buy on ${product.store}'),
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
