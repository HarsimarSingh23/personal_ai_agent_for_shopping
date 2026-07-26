import 'package:flutter/material.dart';

import '../models/search_response.dart';
import '../theme/app_theme.dart';
import '../widgets/recommendation_card.dart';
import '../widgets/product_card.dart';
import '../widgets/source_filter_bar.dart';
import '../widgets/empty_state.dart';
import 'product_detail_screen.dart';

class SearchResultsScreen extends StatefulWidget {
  final SearchResponse response;

  const SearchResultsScreen({super.key, required this.response});

  @override
  State<SearchResultsScreen> createState() => _SearchResultsScreenState();
}

class _SearchResultsScreenState extends State<SearchResultsScreen> {
  final ScrollController _scroll = ScrollController();
  SourceFilter _filter = SourceFilter.all;

  List<Product> get _filteredProducts {
    return switch (_filter) {
      SourceFilter.all      => widget.response.allProducts,
      SourceFilter.amazon   => widget.response.amazon,
      SourceFilter.flipkart => widget.response.flipkart,
      SourceFilter.web      => widget.response.web,
    };
  }

  @override
  Widget build(BuildContext context) {
    final products = _filteredProducts;
    
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('Search Results', style: TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold)),
        backgroundColor: AppTheme.surface,
        iconTheme: const IconThemeData(color: AppTheme.textPrimary),
      ),
      body: CustomScrollView(
        controller: _scroll,
        physics: const BouncingScrollPhysics(),
        slivers: [
          if (widget.response.recommendation != null)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(0, 16, 0, 8),
                child: RecommendationCard(
                  product: widget.response.recommendation!,
                  reason: widget.response.recommendationReason,
                ),
              ),
            ),

          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const Text(
                    'ALL OPTIONS',
                    style: TextStyle(
                      color: AppTheme.textMuted,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Container(height: 1, color: AppTheme.border),
                  ),
                ],
              ),
            ),
          ),

          SliverToBoxAdapter(
            child: SourceFilterBar(
              selected: _filter,
              onChanged: (f) => setState(() => _filter = f),
              amazonCount: widget.response.amazon.length,
              flipkartCount: widget.response.flipkart.length,
              webCount: widget.response.web.length,
            ),
          ),

          const SliverToBoxAdapter(child: SizedBox(height: 12)),

          if (products.isEmpty)
            const SliverFillRemaining(
              child: EmptyState(type: EmptyStateType.noResults),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 40),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, i) => ProductCard(
                    product: products[i],
                    index: i,
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => ProductDetailScreen(product: products[i]),
                      ),
                    ),
                  ),
                  childCount: products.length,
                ),
              ),
            ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }
}
