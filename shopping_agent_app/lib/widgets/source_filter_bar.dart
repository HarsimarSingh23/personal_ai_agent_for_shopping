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
      (SourceFilter.all, 'All', amazonCount + flipkartCount + webCount),
      (SourceFilter.amazon, 'Amazon', amazonCount),
      (SourceFilter.flipkart, 'Flipkart', flipkartCount),
      (SourceFilter.web, 'Other stores', webCount),
    ];
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          for (final (filter, label, count) in chips) ...[
            _FilterChip(
              label: label,
              count: count,
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
  final bool isSelected;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.count,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: isSelected,
      button: true,
      label: '$label, $count results',
      excludeSemantics: true,
      child: Material(
        color: isSelected ? AppTheme.primary : AppTheme.surfaceCard,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: isSelected ? AppTheme.primary : AppTheme.borderBright),
        ),
        child: InkWell(
          onTap: onTap,
          customBorder: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            child: Text(
              '$label ($count)',
              style: TextStyle(
                color: isSelected ? AppTheme.onPrimary : AppTheme.textSecondary,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
