import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/search_response.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/animated_search_bar.dart';
import '../widgets/recommendation_card.dart';
import '../widgets/product_card.dart';
import '../widgets/source_filter_bar.dart';
import '../widgets/loading_shimmer.dart';
import '../widgets/empty_state.dart';
import 'product_detail_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final TextEditingController _controller = TextEditingController();
  final ApiService _api = ApiService.instance;
  final ScrollController _scroll = ScrollController();

  bool _isLoading = false;
  SearchResponse? _response;
  String? _error;
  SourceFilter _filter = SourceFilter.all;


  Future<void> _search() async {
    final query = _controller.text.trim();
    if (query.isEmpty) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _isLoading = true;
      _error = null;
      _response = null;
      _filter = SourceFilter.all;
    });
    try {
      final res = await _api.search(query);
      setState(() {
        _response = res;
        _isLoading = false;
      });
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scroll.hasClients) {
          _scroll.animateTo(
            0,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOutCubic,
          );
        }
      });
    } catch (e) {
      setState(() {
        _error = e.toString().replaceAll('Exception: ', '');
        _isLoading = false;
      });
    }
  }


  List<Product> get _filteredProducts {
    if (_response == null) return [];
    return switch (_filter) {
      SourceFilter.all      => _response!.allProducts,
      SourceFilter.amazon   => _response!.amazon,
      SourceFilter.flipkart => _response!.flipkart,
      SourceFilter.web      => _response!.web,
    };
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(child: _buildBody()),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
      decoration: BoxDecoration(
        color: AppTheme.background,
        border: Border(bottom: BorderSide(color: AppTheme.border.withValues(alpha: 0.5))),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, color: AppTheme.primary, size: 24),
              const SizedBox(width: 8),
              const Text(
                'AI Shopper',
                style: TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.5,
                ),
              ),
              const Spacer(),
              if (_response != null)
                _ResultsBadge(count: _response!.allProducts.length),
            ],
          ),
          const SizedBox(height: 14),
          AnimatedSearchBar(
            controller: _controller,
            isLoading: _isLoading,
            onSearch: _search,
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const SearchLoadingShimmer();
    }

    if (_error != null) {
      return EmptyState(
        type: EmptyStateType.error,
        errorMessage: _error,
        onRetry: _search,
      );
    }

    if (_response == null) {
      return const EmptyState(type: EmptyStateType.idle);
    }

    final products = _filteredProducts;

    return CustomScrollView(
      controller: _scroll,
      physics: const BouncingScrollPhysics(),
      slivers: [

        if (_response!.recommendation != null)
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(0, 16, 0, 8),
              child: RecommendationCard(
                product: _response!.recommendation!,
                reason: _response!.recommendationReason,
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
            amazonCount: _response!.amazon.length,
            flipkartCount: _response!.flipkart.length,
            webCount: _response!.web.length,
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
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }
}

class _ResultsBadge extends StatelessWidget {
  final int count;
  const _ResultsBadge({required this.count});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: AppTheme.primary.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.3)),
      ),
      child: Text(
        '$count results',
        style: const TextStyle(
          color: AppTheme.primary,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    )
        .animate()
        .fadeIn(duration: 300.ms)
        .scale(begin: const Offset(0.8, 0.8), curve: Curves.easeOutBack);
  }
}
