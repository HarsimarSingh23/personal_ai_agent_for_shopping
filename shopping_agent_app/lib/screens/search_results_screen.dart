import 'package:flutter/material.dart';

import '../models/search_response.dart';
import '../theme/app_theme.dart';
import '../widgets/empty_state.dart';
import '../widgets/product_card.dart';
import '../widgets/recommendation_card.dart';
import '../widgets/source_filter_bar.dart';
import 'product_detail_screen.dart';

enum SortOption {
  relevance('Best match', Icons.auto_awesome_outlined),
  priceLow('Price: low to high', Icons.arrow_upward_rounded),
  priceHigh('Price: high to low', Icons.arrow_downward_rounded),
  rating('Top rated', Icons.star_outline_rounded);

  const SortOption(this.label, this.icon);
  final String label;
  final IconData icon;
}

/// Sorts without mutating; products with no price/rating go last.
List<Product> sortProducts(List<Product> products, SortOption sort) {
  int byNullable(num? a, num? b, {bool desc = false}) {
    if (a == null && b == null) return 0;
    if (a == null) return 1;
    if (b == null) return -1;
    return desc ? b.compareTo(a) : a.compareTo(b);
  }

  final list = [...products];
  switch (sort) {
    case SortOption.relevance:
      break;
    case SortOption.priceLow:
      list.sort((a, b) => byNullable(a.priceValue, b.priceValue));
    case SortOption.priceHigh:
      list.sort((a, b) => byNullable(a.priceValue, b.priceValue, desc: true));
    case SortOption.rating:
      list.sort((a, b) {
        final r = byNullable(a.ratingValue, b.ratingValue, desc: true);
        return r != 0 ? r : byNullable(a.reviewsValue, b.reviewsValue, desc: true);
      });
  }
  return list;
}

class SearchResultsScreen extends StatefulWidget {
  final SearchResponse response;

  const SearchResultsScreen({super.key, required this.response});

  @override
  State<SearchResultsScreen> createState() => _SearchResultsScreenState();
}

class _SearchResultsScreenState extends State<SearchResultsScreen> {
  SourceFilter _filter = SourceFilter.all;
  SortOption _sort = SortOption.relevance;

  SearchResponse get r => widget.response;

  List<Product> get _visible {
    final products = switch (_filter) {
      SourceFilter.all => r.allProducts,
      SourceFilter.amazon => r.amazon,
      SourceFilter.flipkart => r.flipkart,
      SourceFilter.web => r.web,
    };
    return sortProducts(products, _sort);
  }

  void _openDetail(Product p) {
    final isPick = p.isSameAs(r.recommendation);
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ProductDetailScreen(product: p, aiReason: isPick ? r.recommendationReason : null),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final products = _visible;
    final missing = r.unavailableSources;

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Results', style: AppTheme.display(19)),
            if (r.query.isNotEmpty)
              Text(
                r.query,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: AppTheme.textMuted, fontSize: 12.5, fontWeight: FontWeight.w500),
              ),
          ],
        ),
        actions: [
          PopupMenuButton<SortOption>(
            tooltip: 'Sort',
            initialValue: _sort,
            onSelected: (s) => setState(() => _sort = s),
            icon: Icon(Icons.sort_rounded, color: _sort == SortOption.relevance ? null : AppTheme.primary),
            itemBuilder: (_) => [
              for (final s in SortOption.values)
                PopupMenuItem(
                  value: s,
                  child: Row(
                    children: [
                      Icon(s.icon, size: 18, color: s == _sort ? AppTheme.primary : AppTheme.textSecondary),
                      const SizedBox(width: 12),
                      Text(s.label, style: TextStyle(color: s == _sort ? AppTheme.primary : null)),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: CustomScrollView(
        slivers: [
          if (r.recommendation != null)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.only(top: 8, bottom: 8),
                child: RecommendationCard(
                  product: r.recommendation!,
                  reason: r.recommendationReason,
                  onTap: () => _openDetail(r.recommendation!),
                ),
              ),
            ),
          if (missing.isNotEmpty)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 4),
                child: _Notice(
                  text: "${missing.join(' and ')} didn't respond in time, so some deals may be missing.",
                ),
              ),
            ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
              child: Row(
                children: [
                  Text('ALL OPTIONS', style: AppTheme.overline),
                  const SizedBox(width: 12),
                  const Expanded(child: Divider()),
                  if (_sort != SortOption.relevance) ...[
                    const SizedBox(width: 12),
                    Text(
                      _sort.label,
                      style: const TextStyle(color: AppTheme.primary, fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                  ],
                ],
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: SourceFilterBar(
              selected: _filter,
              onChanged: (f) => setState(() => _filter = f),
              amazonCount: r.amazon.length,
              flipkartCount: r.flipkart.length,
              webCount: r.web.length,
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 12)),
          if (products.isEmpty)
            SliverFillRemaining(
              hasScrollBody: false,
              child: EmptyState(
                type: EmptyStateType.noResults,
                actionLabel: 'Show all stores',
                onAction: _filter == SourceFilter.all ? null : () => setState(() => _filter = SourceFilter.all),
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
              sliver: SliverList.builder(
                itemCount: products.length,
                itemBuilder: (context, i) => ProductCard(
                  key: ValueKey('${products[i].source}|${products[i].url}|${products[i].title}'),
                  product: products[i],
                  index: i,
                  isTopPick: products[i].isSameAs(r.recommendation),
                  onTap: () => _openDetail(products[i]),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  final String text;

  const _Notice({required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.warning.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppTheme.radiusMd),
        border: Border.all(color: AppTheme.warning.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline_rounded, color: AppTheme.warning, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12.5, height: 1.4)),
          ),
        ],
      ),
    );
  }
}
