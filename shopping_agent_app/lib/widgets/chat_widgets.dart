import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../models/search_response.dart';
import '../theme/app_theme.dart';
import 'product_bits.dart';
import 'recommendation_card.dart';

/// Gradient "spark" mark used for the assistant.
class AgentAvatar extends StatelessWidget {
  final double size;

  const AgentAvatar({super.key, this.size = 30});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: const BoxDecoration(gradient: AppTheme.brandGradient, shape: BoxShape.circle),
      child: Icon(Icons.auto_awesome, size: size * 0.52, color: AppTheme.onPrimary),
    );
  }
}

/// Lays out an agent row (avatar + content) or a right-aligned user row.
class ChatRow extends StatelessWidget {
  final bool isUser;
  final Widget child;
  final bool showAvatar;

  /// Rich cards (results, progress) use the full row width.
  final bool wide;

  const ChatRow({super.key, required this.isUser, required this.child, this.showAvatar = true, this.wide = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth;
          final maxWidth = wide ? width : width * (isUser ? 0.8 : 0.85);
          return Row(
            mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (!isUser) ...[
                showAvatar ? const AgentAvatar() : const SizedBox(width: 30),
                const SizedBox(width: 8),
              ],
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
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 11),
        decoration: BoxDecoration(
          color: isUser ? AppTheme.primary : AppTheme.surfaceCard,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(20),
            topRight: const Radius.circular(20),
            bottomLeft: Radius.circular(isUser ? 20 : 6),
            bottomRight: Radius.circular(isUser ? 6 : 20),
          ),
          border: isUser ? null : Border.all(color: AppTheme.border),
        ),
        child: Text(
          text,
          style: TextStyle(
            color: isUser ? AppTheme.onPrimary : AppTheme.textPrimary,
            fontSize: 15,
            height: 1.42,
            fontWeight: isUser ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    ).animate().fadeIn(duration: 220.ms).slideY(begin: 0.15, duration: 220.ms, curve: Curves.easeOutCubic);
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
        color: AppTheme.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppTheme.error.withValues(alpha: 0.35)),
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
              child: TextButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: const Text('Try again'),
              ),
            ),
        ],
      ),
    ).animate().fadeIn(duration: 220.ms).shakeX(hz: 3, amount: 2, duration: 300.ms);
  }
}

/// Three bouncing dots.
class TypingIndicator extends StatefulWidget {
  const TypingIndicator({super.key});

  @override
  State<TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<TypingIndicator> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1100))..repeat();

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
          color: AppTheme.surfaceCard,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(20),
            topRight: Radius.circular(20),
            bottomRight: Radius.circular(20),
            bottomLeft: Radius.circular(6),
          ),
          border: Border.all(color: AppTheme.border),
        ),
        child: AnimatedBuilder(
          animation: _c,
          builder: (context, _) => Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(3, (i) {
              final t = (_c.value - i * 0.18) % 1.0;
              final lift = math.sin(t * math.pi).clamp(0.0, 1.0);
              return Padding(
                padding: EdgeInsets.only(right: i < 2 ? 5 : 0),
                child: Transform.translate(
                  offset: Offset(0, -4 * lift),
                  child: Container(
                    width: 7,
                    height: 7,
                    decoration: BoxDecoration(
                      color: Color.lerp(AppTheme.textMuted, AppTheme.primary, lift),
                      shape: BoxShape.circle,
                    ),
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

/// Shows the agent's progress while a search runs (usually 15–40 s).
class SearchProgressCard extends StatefulWidget {
  final String query;

  const SearchProgressCard({super.key, required this.query});

  @override
  State<SearchProgressCard> createState() => _SearchProgressCardState();
}

class _SearchProgressCardState extends State<SearchProgressCard> {
  static const _steps = [
    (Icons.translate_rounded, 'Understanding your request', 0),
    (Icons.travel_explore_rounded, 'Searching Amazon, Flipkart & more stores', 3),
    (Icons.compare_arrows_rounded, 'Comparing prices, ratings & reviews', 12),
    (Icons.auto_awesome, 'Picking the best deal for you', 20),
  ];

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

  int get _active {
    var index = 0;
    for (var i = 0; i < _steps.length; i++) {
      if (_elapsed >= _steps[i].$3) index = i;
    }
    return index;
  }

  @override
  Widget build(BuildContext context) {
    final active = _active;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceCard,
        borderRadius: BorderRadius.circular(AppTheme.radiusLg),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Searching for', style: AppTheme.overline),
          const SizedBox(height: 4),
          Text(
            widget.query,
            style: const TextStyle(color: AppTheme.textPrimary, fontSize: 15, fontWeight: FontWeight.w700),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 14),
          for (var i = 0; i < _steps.length; i++)
            _StepRow(
              icon: _steps[i].$1,
              label: _steps[i].$2,
              state: i < active ? _StepState.done : (i == active ? _StepState.active : _StepState.pending),
            ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: const LinearProgressIndicator(minHeight: 3, backgroundColor: AppTheme.surfaceElevated),
          ),
          const SizedBox(height: 8),
          Text(
            _elapsed < 30 ? 'This usually takes 15–30 seconds' : 'Some stores are slow today — almost there…',
            style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms);
  }
}

enum _StepState { done, active, pending }

class _StepRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final _StepState state;

  const _StepRow({required this.icon, required this.label, required this.state});

  @override
  Widget build(BuildContext context) {
    final Widget leading = switch (state) {
      _StepState.done => const Icon(Icons.check_circle_rounded, size: 18, color: AppTheme.success),
      _StepState.active => const SizedBox(
          width: 18,
          height: 18,
          child: Padding(padding: EdgeInsets.all(2), child: CircularProgressIndicator(strokeWidth: 2)),
        ),
      _StepState.pending => Icon(icon, size: 18, color: AppTheme.textMuted.withValues(alpha: 0.6)),
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          leading,
          const SizedBox(width: 10),
          Expanded(
            child: AnimatedDefaultTextStyle(
              duration: const Duration(milliseconds: 250),
              style: TextStyle(
                fontSize: 13.5,
                color: state == _StepState.pending ? AppTheme.textMuted : AppTheme.textPrimary,
                fontWeight: state == _StepState.active ? FontWeight.w600 : FontWeight.w400,
              ),
              child: Text(label),
            ),
          ),
        ],
      ),
    );
  }
}

/// Compact results summary inside the conversation.
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
        gradient: AppTheme.recommendGradient,
        borderRadius: BorderRadius.circular(AppTheme.radiusLg),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.35)),
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
                    const AiPickChip(),
                    const Spacer(),
                    Text(
                      '${response.totalCount} found',
                      style: const TextStyle(color: AppTheme.textMuted, fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
                if (pick != null) ...[
                  const SizedBox(height: 12),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ProductImage(product: pick, size: 72),
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
                                fontSize: 13.5,
                                fontWeight: FontWeight.w600,
                                height: 1.35,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Row(
                              children: [
                                Flexible(
                                  child: Text(
                                    pick.displayPrice,
                                    style: AppTheme.display(18, weight: FontWeight.w800),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                SourceBadge.of(pick),
                              ],
                            ),
                            const SizedBox(height: 4),
                            RatingLabel(product: pick),
                          ],
                        ),
                      ),
                    ],
                  ),
                  if (response.recommendationReason.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    ReasonBox(reason: response.recommendationReason, maxLines: 4),
                  ],
                ],
                if (missing.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      const Icon(Icons.info_outline_rounded, size: 14, color: AppTheme.warning),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          "${missing.join(' and ')} didn't respond, so results may be incomplete.",
                          style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
                        ),
                      ),
                    ],
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
    ).animate().fadeIn(duration: 350.ms).slideY(begin: 0.08, duration: 350.ms, curve: Curves.easeOutCubic);
  }
}
