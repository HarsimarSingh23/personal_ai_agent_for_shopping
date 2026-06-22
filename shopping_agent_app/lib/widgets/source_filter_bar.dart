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

  int get totalCount => amazonCount + flipkartCount + webCount;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          _FilterChip(
            label: 'All',
            count: totalCount,
            color: AppTheme.primary,
            icon: Icons.grid_view_rounded,
            isSelected: selected == SourceFilter.all,
            onTap: () => onChanged(SourceFilter.all),
          ),
          const SizedBox(width: 8),
          _FilterChip(
            label: 'Amazon',
            count: amazonCount,
            color: AppTheme.amazonColor,
            icon: Icons.shopping_bag_rounded,
            isSelected: selected == SourceFilter.amazon,
            onTap: () => onChanged(SourceFilter.amazon),
          ),
          const SizedBox(width: 8),
          _FilterChip(
            label: 'Flipkart',
            count: flipkartCount,
            color: AppTheme.flipkartColor,
            icon: Icons.local_mall_rounded,
            isSelected: selected == SourceFilter.flipkart,
            onTap: () => onChanged(SourceFilter.flipkart),
          ),
          const SizedBox(width: 8),
          _FilterChip(
            label: 'Web',
            count: webCount,
            color: AppTheme.webColor,
            icon: Icons.language_rounded,
            isSelected: selected == SourceFilter.web,
            onTap: () => onChanged(SourceFilter.web),
          ),
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
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOutCubic,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          color: isSelected ? color.withValues(alpha: 0.18) : AppTheme.surfaceCard,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: isSelected ? color.withValues(alpha: 0.6) : AppTheme.border,
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 14,
              color: isSelected ? color : AppTheme.textMuted,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color: isSelected ? color : AppTheme.textSecondary,
                fontSize: 13,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
            if (count > 0) ...[
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: isSelected ? color.withValues(alpha: 0.25) : AppTheme.surfaceElevated,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '$count',
                  style: TextStyle(
                    color: isSelected ? color : AppTheme.textMuted,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
