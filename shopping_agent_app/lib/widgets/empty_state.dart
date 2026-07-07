import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/app_theme.dart';

enum EmptyStateType { idle, noResults, error, noHistory }

class EmptyState extends StatelessWidget {
  final EmptyStateType type;
  final String? errorMessage;
  final VoidCallback? onRetry;

  const EmptyState({
    super.key,
    required this.type,
    this.errorMessage,
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildIcon(),
            const SizedBox(height: 24),
            Text(
              _title,
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.w700,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            Text(
              _subtitle,
              style: const TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 14,
                height: 1.6,
              ),
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 24),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppTheme.primary,
                  side: const BorderSide(color: AppTheme.primary),
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded, size: 16),
                label: const Text('Try Again', style: TextStyle(fontWeight: FontWeight.w600)),
              ),
            ],
          ],
        ),
      ),
    )
        .animate()
        .fadeIn(duration: 500.ms)
        .scale(begin: const Offset(0.95, 0.95), duration: 400.ms, curve: Curves.easeOutBack);
  }

  Widget _buildIcon() {
    switch (type) {
      case EmptyStateType.idle:
        return _GlowIcon(icon: Icons.shopping_bag_outlined, color: AppTheme.primary);
      case EmptyStateType.noResults:
        return _GlowIcon(icon: Icons.search_off_rounded, color: AppTheme.textMuted);
      case EmptyStateType.error:
        return _GlowIcon(icon: Icons.wifi_off_rounded, color: AppTheme.error);
      case EmptyStateType.noHistory:
        return _GlowIcon(icon: Icons.history_toggle_off_rounded, color: AppTheme.textMuted);
    }
  }

  String get _title {
    switch (type) {
      case EmptyStateType.idle:
        return 'Find the Best Deals';
      case EmptyStateType.noResults:
        return 'No Products Found';
      case EmptyStateType.error:
        return 'Connection Error';
      case EmptyStateType.noHistory:
        return 'No Search History';
    }
  }

  String get _subtitle {
    switch (type) {
      case EmptyStateType.idle:
        return 'Search in Hindi, Punjabi, or English.\nAI will compare prices across Amazon,\nFlipkart, and the web for you.';
      case EmptyStateType.noResults:
        return 'We couldn\'t find any products\nfor your query. Try different keywords.';
      case EmptyStateType.error:
        return errorMessage != null
            ? 'Could not connect to the server.\n$errorMessage'
            : 'Could not connect to the server.\nMake sure the backend is running.';
      case EmptyStateType.noHistory:
        return 'Your past searches will appear here\nonce you start looking for products.';
    }
  }
}

class _GlowIcon extends StatelessWidget {
  final IconData icon;
  final Color color;

  const _GlowIcon({required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 90,
      height: 90,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        shape: BoxShape.circle,
        border: Border.all(color: color.withValues(alpha: 0.15), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.12),
            blurRadius: 30,
            spreadRadius: 5,
          ),
        ],
      ),
      child: Icon(icon, size: 40, color: color.withValues(alpha: 0.7)),
    )
        .animate(onPlay: (c) => c.repeat(reverse: true))
        .scaleXY(end: 1.04, duration: 2.seconds, curve: Curves.easeInOut);
  }
}
