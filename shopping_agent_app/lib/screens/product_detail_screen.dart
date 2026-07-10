import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/search_response.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'checkout_success_screen.dart';

class ProductDetailScreen extends StatefulWidget {
  final Product product;

  const ProductDetailScreen({super.key, required this.product});

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  Product get product => widget.product;

  @override
  Widget build(BuildContext context) {
    final sourceColor = AppTheme.sourceColor(product.source);
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          _buildAppBar(context, sourceColor),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSourceBadge(sourceColor),
                  const SizedBox(height: 16),
                  _buildTitle(),
                  const SizedBox(height: 20),
                  _buildPriceRating(),
                  const SizedBox(height: 24),
                  _buildDivider(),
                  const SizedBox(height: 24),
                  _buildUrlSection(),
                  const SizedBox(height: 32),
                  _buildCTAButton(),
                  const SizedBox(height: 40),
                ],
              ).animate().fadeIn(duration: 400.ms).slideY(
                  begin: 0.06, duration: 400.ms, curve: Curves.easeOutCubic),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAppBar(BuildContext context, Color sourceColor) {
    return SliverAppBar(
      expandedHeight: product.hasImage ? 260 : 80,
      pinned: true,
      backgroundColor: AppTheme.surface,
      leading: GestureDetector(
        onTap: () => Navigator.pop(context),
        child: Container(
          margin: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AppTheme.surfaceElevated.withValues(alpha: 0.9),
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.arrow_back_rounded, color: AppTheme.textPrimary, size: 20),
        ),
      ),
      flexibleSpace: FlexibleSpaceBar(
        background: product.hasImage
            ? CachedNetworkImage(
                imageUrl: product.image,
                fit: BoxFit.cover,
                placeholder: (_, __) => Container(color: AppTheme.surface),
                errorWidget: (_, __, ___) => Container(
                  color: AppTheme.surface,
                  child: Icon(AppTheme.sourceIcon(product.source),
                      size: 60, color: sourceColor.withValues(alpha: 0.3)),
                ),
              )
            : Container(
                color: AppTheme.surface,
                child: Center(
                  child: Icon(AppTheme.sourceIcon(product.source),
                      size: 64, color: sourceColor.withValues(alpha: 0.3)),
                ),
              ),
      ),
    );
  }

  Widget _buildSourceBadge(Color sourceColor) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: sourceColor.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: sourceColor.withValues(alpha: 0.4)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(AppTheme.sourceIcon(product.source), color: sourceColor, size: 14),
              const SizedBox(width: 6),
              Text(
                product.source.toUpperCase(),
                style: TextStyle(
                  color: sourceColor,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTitle() {
    return Text(
      product.title,
      style: const TextStyle(
        color: AppTheme.textPrimary,
        fontSize: 20,
        fontWeight: FontWeight.w700,
        height: 1.4,
        letterSpacing: -0.2,
      ),
    );
  }

  Widget _buildPriceRating() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Price',
              style: TextStyle(color: AppTheme.textMuted, fontSize: 12, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 4),
            Text(
              product.price,
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 30,
                fontWeight: FontWeight.w900,
                letterSpacing: -1,
              ),
            ),
          ],
        ),
        const Spacer(),
        if (product.rating != 'N/A')
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              const Text(
                'Rating',
                style: TextStyle(color: AppTheme.textMuted, fontSize: 12, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  const Icon(Icons.star_rounded, color: AppTheme.gold, size: 22),
                  const SizedBox(width: 4),
                  Text(
                    product.rating,
                    style: const TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
              if (product.reviewsCount != 'N/A')
                Text(
                  '${product.reviewsCount} reviews',
                  style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
                ),
            ],
          ),
      ],
    );
  }

  Widget _buildDivider() {
    return Container(height: 1, color: AppTheme.border);
  }

  Widget _buildUrlSection() {
    if (!product.hasValidUrl) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Product Link',
          style: TextStyle(
            color: AppTheme.textMuted,
            fontSize: 12,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 8),
        GestureDetector(
          onTap: () async {
            final messenger = ScaffoldMessenger.of(context);
            await Clipboard.setData(ClipboardData(text: product.url));
            if (!context.mounted) return;
            messenger.showSnackBar(
              const SnackBar(content: Text('Link copied to clipboard!')),
            );
          },
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.surfaceElevated,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.border),
            ),
            child: Row(
              children: [
                const Icon(Icons.link_rounded, color: AppTheme.primary, size: 16),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    product.url,
                    style: const TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 12,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                const Icon(Icons.copy_rounded, color: AppTheme.textMuted, size: 14),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCTAButton() {
    return SizedBox(
      width: double.infinity,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: AppTheme.primaryGradient,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: AppTheme.primary.withValues(alpha: 0.4),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: ElevatedButton.icon(
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.transparent,
            shadowColor: Colors.transparent,
            padding: const EdgeInsets.symmetric(vertical: 18),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          ),
          icon: const Icon(Icons.flash_on_rounded, color: AppTheme.background, size: 24),
          label: const Text(
            'BUY WITH 1-CLICK',
            style: TextStyle(
              color: AppTheme.background,
              fontWeight: FontWeight.w900,
              fontSize: 16,
              letterSpacing: 1.2,
            ),
          ),
          onPressed: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => const CheckoutSuccessScreen()),
            );
          },
        ),
      ),
    );
  }
}
