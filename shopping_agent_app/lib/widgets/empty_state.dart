import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

enum EmptyStateType { noResults, error, noHistory }

class EmptyState extends StatelessWidget {
  final EmptyStateType type;
  final String? message;
  final VoidCallback? onAction;
  final String? actionLabel;

  const EmptyState({
    super.key,
    required this.type,
    this.message,
    this.onAction,
    this.actionLabel,
  });

  @override
  Widget build(BuildContext context) {
    final (icon, color, title, subtitle, defaultAction) = switch (type) {
      EmptyStateType.noResults => (
          Icons.search_off_rounded,
          AppTheme.textMuted,
          'No products here',
          'Try another store filter, or ask the assistant with different keywords.',
          'Back',
        ),
      EmptyStateType.error => (
          Icons.cloud_off_rounded,
          AppTheme.error,
          "Couldn't load this",
          message ?? "We couldn't reach the server. Check your connection and try again.",
          'Try again',
        ),
      EmptyStateType.noHistory => (
          Icons.history_rounded,
          AppTheme.textMuted,
          'No searches yet',
          'Ask the assistant for something you want to buy. Your searches will show up here.',
          'Start shopping',
        ),
    };

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 40, color: color),
            const SizedBox(height: 16),
            Text(title, style: AppTheme.display(18), textAlign: TextAlign.center),
            const SizedBox(height: 8),
            Text(
              subtitle,
              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14, height: 1.55),
              textAlign: TextAlign.center,
            ),
            if (onAction != null) ...[
              const SizedBox(height: 22),
              OutlinedButton.icon(
                onPressed: onAction,
                icon: Icon(type == EmptyStateType.error ? Icons.refresh_rounded : Icons.arrow_forward_rounded, size: 18),
                label: Text(actionLabel ?? defaultAction),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
