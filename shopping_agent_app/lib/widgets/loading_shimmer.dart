import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';
import '../theme/app_theme.dart';

class SearchLoadingShimmer extends StatelessWidget {
  const SearchLoadingShimmer({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 40),
      physics: const NeverScrollableScrollPhysics(),
      children: [
        // Recommendation skeleton
        _shimmerBox(
          height: 300,
          borderRadius: 24,
          margin: const EdgeInsets.only(bottom: 24),
        ),
        // Filter chips skeleton
        _shimmerRow(),
        const SizedBox(height: 20),
        // Product card skeletons
        for (int i = 0; i < 5; i++)
          _shimmerProductCard(i),
      ],
    );
  }

  Widget _shimmerBox({
    required double height,
    double borderRadius = 18,
    EdgeInsets margin = EdgeInsets.zero,
  }) {
    return Shimmer.fromColors(
      baseColor: AppTheme.surfaceElevated,
      highlightColor: AppTheme.borderBright,
      period: const Duration(milliseconds: 1400),
      child: Container(
        height: height,
        margin: margin,
        decoration: BoxDecoration(
          color: AppTheme.surfaceElevated,
          borderRadius: BorderRadius.circular(borderRadius),
        ),
      ),
    );
  }

  Widget _shimmerRow() {
    return Row(
      children: [
        for (int i = 0; i < 4; i++) ...[
          Shimmer.fromColors(
            baseColor: AppTheme.surfaceElevated,
            highlightColor: AppTheme.borderBright,
            child: Container(
              width: 80,
              height: 36,
              decoration: BoxDecoration(
                color: AppTheme.surfaceElevated,
                borderRadius: BorderRadius.circular(24),
              ),
            ),
          ),
          if (i < 3) const SizedBox(width: 8),
        ],
      ],
    );
  }

  Widget _shimmerProductCard(int index) {
    return Shimmer.fromColors(
      baseColor: AppTheme.surfaceElevated,
      highlightColor: AppTheme.borderBright,
      period: Duration(milliseconds: 1400 + (index * 100)),
      child: Container(
        height: 96,
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(
          color: AppTheme.surfaceElevated,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(
          children: [
            Container(
              width: 80,
              height: 80,
              margin: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppTheme.border,
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    Container(height: 8, width: 50, 
                        decoration: BoxDecoration(color: AppTheme.border, borderRadius: BorderRadius.circular(4))),
                    Container(height: 10, 
                        decoration: BoxDecoration(color: AppTheme.border, borderRadius: BorderRadius.circular(4))),
                    Container(height: 10, width: 160, 
                        decoration: BoxDecoration(color: AppTheme.border, borderRadius: BorderRadius.circular(4))),
                    Container(height: 12, width: 80, 
                        decoration: BoxDecoration(color: AppTheme.border, borderRadius: BorderRadius.circular(4))),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Simple inline shimmer box for reuse elsewhere
class ShimmerBox extends StatelessWidget {
  final double width;
  final double height;
  final double borderRadius;

  const ShimmerBox({
    super.key,
    required this.width,
    required this.height,
    this.borderRadius = 8,
  });

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppTheme.surfaceElevated,
      highlightColor: AppTheme.borderBright,
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: AppTheme.surfaceElevated,
          borderRadius: BorderRadius.circular(borderRadius),
        ),
      ),
    );
  }
}
