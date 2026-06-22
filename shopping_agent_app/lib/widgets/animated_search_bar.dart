import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/app_theme.dart';

class AnimatedSearchBar extends StatefulWidget {
  final TextEditingController controller;
  final bool isLoading;
  final VoidCallback onSearch;

  const AnimatedSearchBar({
    super.key,
    required this.controller,
    required this.isLoading,
    required this.onSearch,
  });

  @override
  State<AnimatedSearchBar> createState() => _AnimatedSearchBarState();
}

class _AnimatedSearchBarState extends State<AnimatedSearchBar> {
  final FocusNode _focus = FocusNode();
  bool _focused = false;

  @override
  void initState() {
    super.initState();
    _focus.addListener(() => setState(() => _focused = _focus.hasFocus));
  }

  @override
  void dispose() {
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOutCubic,
      decoration: BoxDecoration(
        color: AppTheme.surfaceElevated,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: _focused ? AppTheme.primary : AppTheme.border,
          width: _focused ? 1.5 : 1.0,
        ),
        boxShadow: _focused
            ? [
                BoxShadow(
                  color: AppTheme.primary.withValues(alpha: 0.15),
                  blurRadius: 24,
                  spreadRadius: 2,
                ),
              ]
            : [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.4),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
      ),
      child: Row(
        children: [
          const SizedBox(width: 16),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 200),
            child: _focused
                ? const Icon(Icons.search, color: AppTheme.primary, size: 22)
                : const Icon(Icons.search, color: AppTheme.textMuted, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: TextField(
              controller: widget.controller,
              focusNode: _focus,
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 15,
                fontWeight: FontWeight.w400,
              ),
              decoration: InputDecoration(
                hintText: 'Search in Hindi, Punjabi, or English…',
                hintStyle: const TextStyle(
                  color: AppTheme.textMuted,
                  fontSize: 15,
                ),
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                filled: false,
                contentPadding: const EdgeInsets.symmetric(vertical: 18),
              ),
              onSubmitted: (_) => widget.onSearch(),
              textInputAction: TextInputAction.search,
            ),
          ),
          const SizedBox(width: 8),
          _buildSendButton(),
          const SizedBox(width: 8),
        ],
      ),
    );
  }

  Widget _buildSendButton() {
    if (widget.isLoading) {
      return Container(
        width: 42,
        height: 42,
        margin: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          gradient: AppTheme.primaryGradient,
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Center(
          child: SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: Colors.white,
            ),
          ),
        ),
      );
    }

    return GestureDetector(
      onTap: widget.onSearch,
      child: Container(
        width: 42,
        height: 42,
        margin: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          gradient: AppTheme.primaryGradient,
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: AppTheme.primary.withValues(alpha: 0.4),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: const Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 20),
      )
          .animate(onPlay: (c) => c.repeat(reverse: true))
          .shimmer(delay: 2.seconds, duration: 1.5.seconds, color: Colors.white24),
    );
  }
}
