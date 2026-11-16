import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/search_response.dart';
import '../theme/app_theme.dart';
import 'product_bits.dart';
import 'recommendation_card.dart';

/// Lays out an assistant row (left) or a user row (right).
class ChatRow extends StatelessWidget {
  final bool isUser;
  final Widget child;

  /// Kept for older call sites; the plain design shows no avatar.
  final bool showAvatar;

  /// Rich cards (results, progress) use the full row width.
  final bool wide;

  const ChatRow({super.key, required this.isUser, required this.child, this.showAvatar = true, this.wide = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth;
          final maxWidth = wide ? width : width * 0.82;
          return Row(
            mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
            children: [
              Flexible(child: ConstrainedBox(constraints: BoxConstraints(maxWidth: maxWidth), child: child)),
            ],
          );
        },
      ),
    );
  }
}

class MessageBubble extends StatelessWidget {
  final String text;
  final bool isUser;

  const MessageBubble({super.key, required this.text, required this.isUser});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onLongPress: () {
        Clipboard.setData(ClipboardData(text: text));
        HapticFeedback.mediumImpact();
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Message copied')));
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isUser ? AppTheme.primary : AppTheme.surfaceElevated,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(
          text,
          style: TextStyle(
            color: isUser ? AppTheme.onPrimary : AppTheme.textPrimary,
            fontSize: 15,
            height: 1.4,
          ),
        ),
      ),
    );
  }
}

class ErrorBubble extends StatelessWidget {
  final String text;
  final VoidCallback? onRetry;

  const ErrorBubble({super.key, required this.text, this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 8, 8),
      decoration: BoxDecoration(
        color: const Color(0xFFFDF0F0),
        borderRadius: BorderRadius.circular(AppTheme.radiusLg),
        border: Border.all(color: const Color(0xFFF2C4C4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.error_outline_rounded, color: AppTheme.error, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(text, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14, height: 1.4)),
              ),
            ],
          ),
          if (onRetry != null)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(onPressed: onRetry, child: const Text('Try again')),
            ),
        ],
      ),
    );
  }
}

/// Three dots that fade in turn while the assistant is replying.
class TypingIndicator extends StatefulWidget {
  const TypingIndicator({super.key});

  @override
  State<TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<TypingIndicator> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1200))..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Assistant is typing',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: AppTheme.surfaceElevated,
          borderRadius: BorderRadius.circular(16),
        ),
        child: AnimatedBuilder(
          animation: _c,
          builder: (context, _) => Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(3, (i) {
              final t = (_c.value - i * 0.2) % 1.0;
              final strength = math.sin(t * math.pi).clamp(0.0, 1.0);
              return Padding(
                padding: EdgeInsets.only(right: i < 2 ? 5 : 0),
                child: Container(
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(
                    color: AppTheme.textMuted.withValues(alpha: 0.35 + 0.65 * strength),
                    shape: BoxShape.circle,
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}

/// Shown while a search runs (usually 10–30 s).
class SearchProgressCard extends StatefulWidget {
  final String query;

  const SearchProgressCard({super.key, required this.query});

  @override
  State<SearchProgressCard> createState() => _SearchProgressCardState();
}

class _SearchProgressCardState extends State<SearchProgressCard> {
  late final Timer _timer;
  int _elapsed = 0;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) => setState(() => _elapsed++));
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceCard,
        borderRadius: BorderRadius.circular(AppTheme.radiusLg),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Searching Amazon, Flipkart & more stores',
            style: TextStyle(color: AppTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 4),
          Text(
            widget.query,
            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 12),
          const LinearProgressIndicator(minHeight: 3, backgroundColor: AppTheme.surfaceElevated),
          const SizedBox(height: 8),
          Text(
            _elapsed < 30 ? 'This usually takes 10–30 seconds' : 'Some stores are slow, almost done…',
            style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

/// Short results summary inside the conversation.
class ResultsMessageCard extends StatelessWidget {
  final SearchResponse response;
  final VoidCallback onViewAll;
  final VoidCallback onOpenPick;

  const ResultsMessageCard({
    super.key,
    required this.response,
    required this.onViewAll,
    required this.onOpenPick,
  });

  @override
  Widget build(BuildContext context) {
    final pick = response.recommendation;
    final missing = response.unavailableSources;
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surfaceCard,
        borderRadius: BorderRadius.circular(AppTheme.radiusLg),
        border: Border.all(color: AppTheme.border),
      ),
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          borderRadius: BorderRadius.circular(AppTheme.radiusLg),
          onTap: pick != null ? onOpenPick : onViewAll,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    if (pick != null) const AiPickChip(),
                    const Spacer(),
                    Text(
                      '${response.totalCount} products found',
                      style: const TextStyle(color: AppTheme.textMuted, fontSize: 12.5),
                    ),
                  ],
                ),
                if (pick != null) ...[
                  const SizedBox(height: 10),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ProductImage(product: pick, size: 68),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              pick.title,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: AppTheme.textPrimary,
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                                height: 1.35,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              pick.displayPrice,
                              style: AppTheme.display(17, weight: FontWeight.w700),
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 2),
                            Row(
                              children: [
                                SourceBadge.of(pick),
                                const SizedBox(width: 10),
                                Flexible(child: RatingLabel(product: pick)),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  if (response.recommendationReason.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    ReasonBox(reason: response.recommendationReason, maxLines: 4),
                  ],
                ],
                if (missing.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    "${missing.join(' and ')} didn't respond, so results may be incomplete.",
                    style: const TextStyle(color: AppTheme.warning, fontSize: 12.5),
                  ),
                ],
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: onViewAll,
                        style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 12)),
                        child: Text('Compare all ${response.totalCount}', maxLines: 1),
                      ),
                    ),
                    if (pick != null && pick.hasValidUrl) ...[
                      const SizedBox(width: 10),
                      Expanded(
                        child: FilledButton(
                          onPressed: () => openProduct(context, pick),
                          style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 12)),
                          child: const Text('View deal', maxLines: 1),
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
