import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

enum SourceFilter { all, amazon, flipkart, web }

class SourceFilterBar extends StatelessWidget {
  final SourceFilter selected;
  final ValueChanged<SourceFilter> onChanged;
  final int amazonCount;
  final int flipkartCount;
  final int webCount;

  const SourceFilterBar({
    super.key,
    required this.selected,
    required this.onChanged,
    required this.amazonCount,
    required this.flipkartCount,
    required this.webCount,
  });

  @override
  Widget build(BuildContext context) {
    final chips = [
      (SourceFilter.all, 'All', amazonCount + flipkartCount + webCount, AppTheme.primary, Icons.grid_view_rounded),
      (SourceFilter.amazon, 'Amazon', amazonCount, AppTheme.amazonColor, Icons.shopping_bag_rounded),
      (SourceFilter.flipkart, 'Flipkart', flipkartCount, AppTheme.flipkartColor, Icons.local_mall_rounded),
      (SourceFilter.web, 'Other stores', webCount, AppTheme.webColor, Icons.storefront_rounded),
    ];
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          for (final (filter, label, count, color, icon) in chips) ...[
            _FilterChip(
              label: label,
              count: count,
              color: color,
              icon: icon,
              isSelected: selected == filter,
              onTap: () => onChanged(filter),
            ),
            const SizedBox(width: 8),
          ],
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final int count;
  final Color color;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.count,
    required this.color,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final fg = isSelected ? color : AppTheme.textSecondary;
    return Semantics(
      selected: isSelected,
      button: true,
      label: '$label, $count results',
      excludeSemantics: true,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(24),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOutCubic,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
            decoration: BoxDecoration(
              color: isSelected ? color.withValues(alpha: 0.16) : AppTheme.surfaceCard,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: isSelected ? color.withValues(alpha: 0.6) : AppTheme.border,
                width: isSelected ? 1.4 : 1,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 14, color: isSelected ? color : AppTheme.textMuted),
                const SizedBox(width: 6),
                Text(
                  label,
                  style: TextStyle(
                    color: fg,
                    fontSize: 13,
                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  '$count',
                  style: TextStyle(
                    color: isSelected ? color : AppTheme.textMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
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
