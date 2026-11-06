import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../models/session.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../utils/formatters.dart';
import '../widgets/empty_state.dart';
import '../widgets/product_bits.dart';
import 'search_results_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => HistoryScreenState();
}

class HistoryScreenState extends State<HistoryScreen> {
  final ApiService _api = ApiService.instance;
  List<SessionSummary>? _sessions;
  bool _isLoading = true;
  String? _error;
  String? _opening;

  @override
  void initState() {
    super.initState();
    _load();
  }

  /// Called when the History tab becomes visible.
  void reloadIfNeeded() {
    if (!_isLoading) _load(silent: _sessions != null);
  }

  Future<void> _load({bool silent = false}) async {
    if (!mounted) return;
    setState(() {
      _isLoading = !silent;
      _error = null;
    });
    try {
      final sessions = await _api.getSessions();
      if (!mounted) return;
      setState(() {
        _sessions = sessions;
        _isLoading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        if (_sessions == null || !silent) _error = e.message;
        _isLoading = false;
      });
    }
  }

  Future<void> _open(SessionSummary s) async {
    if (s.sessionId == null || _opening != null) return;
    setState(() => _opening = s.sessionId);
    try {
      final response = await _api.getSession(s.sessionId!);
      if (!mounted) return;
      await Navigator.push(context, MaterialPageRoute(builder: (_) => SearchResultsScreen(response: response)));
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _opening = null);
    }
  }

  Future<bool> _delete(SessionSummary s) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await _api.deleteSession(s.sessionId!);
      HapticFeedback.mediumImpact();
      messenger.showSnackBar(const SnackBar(content: Text('Search deleted')));
      return true;
    } on ApiException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(e.message)));
      return false;
    }
  }

  Future<void> _clearAll() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Clear all history?'),
        content: const Text('This permanently deletes every saved search on this device.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: AppTheme.error, foregroundColor: Colors.white),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Clear all'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await _api.clearHistory();
      if (mounted) setState(() => _sessions = []);
      messenger.showSnackBar(const SnackBar(content: Text('History cleared')));
    } on ApiException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final count = _sessions?.length ?? 0;
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('History', style: AppTheme.display(20)),
            Text(
              count == 0 ? 'Your past searches' : '$count saved ${count == 1 ? 'search' : 'searches'}',
              style: const TextStyle(color: AppTheme.textMuted, fontSize: 12, fontWeight: FontWeight.w500),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
          if (count > 0)
            PopupMenuButton<String>(
              tooltip: 'More',
              onSelected: (_) => _clearAll(),
              itemBuilder: (_) => const [
                PopupMenuItem(
                  value: 'clear',
                  child: Row(
                    children: [
                      Icon(Icons.delete_sweep_outlined, size: 20, color: AppTheme.error),
                      SizedBox(width: 12),
                      Text('Clear all history'),
                    ],
                  ),
                ),
              ],
            ),
          const SizedBox(width: 4),
        ],
        bottom: const PreferredSize(preferredSize: Size.fromHeight(1), child: Divider(height: 1)),
      ),
      body: _body(),
    );
  }

  Widget _body() {
    if (_isLoading) return _skeleton();
    if (_error != null) {
      return EmptyState(type: EmptyStateType.error, message: _error, onAction: _load);
    }
    final sessions = _sessions ?? const [];
    if (sessions.isEmpty) {
      return RefreshIndicator(
        onRefresh: _load,
        child: LayoutBuilder(
          builder: (context, c) => SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            child: SizedBox(height: c.maxHeight, child: const EmptyState(type: EmptyStateType.noHistory)),
          ),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      color: AppTheme.primary,
      backgroundColor: AppTheme.surfaceCard,
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 32),
        itemCount: sessions.length + 1,
        itemBuilder: (context, i) {
          if (i == sessions.length) {
            return const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text(
                'Swipe left on a search to delete it.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppTheme.textMuted, fontSize: 12),
              ),
            );
          }
          final s = sessions[i];
          return Dismissible(
            key: ValueKey(s.sessionId ?? i),
            direction: s.sessionId == null ? DismissDirection.none : DismissDirection.endToStart,
            confirmDismiss: (_) => _delete(s),
            onDismissed: (_) => setState(() => _sessions!.remove(s)),
            background: Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.only(right: 22),
              alignment: Alignment.centerRight,
              decoration: BoxDecoration(
                color: AppTheme.error.withValues(alpha: 0.18),
                borderRadius: BorderRadius.circular(AppTheme.radiusLg),
              ),
              child: const Icon(Icons.delete_outline_rounded, color: AppTheme.error),
            ),
            child: _SessionTile(
              session: s,
              index: i,
              loading: _opening == s.sessionId,
              onTap: () => _open(s),
            ),
          );
        },
      ),
    );
  }

  Widget _skeleton() {
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 32),
      itemCount: 6,
      itemBuilder: (_, i) => Container(
        height: 92,
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(
          color: AppTheme.surfaceCard,
          borderRadius: BorderRadius.circular(AppTheme.radiusLg),
        ),
      ).animate(onPlay: (c) => c.repeat()).shimmer(duration: 1200.ms, color: AppTheme.surfaceElevated),
    );
  }
}

class _SessionTile extends StatelessWidget {
  final SessionSummary session;
  final int index;
  final bool loading;
  final VoidCallback onTap;

  const _SessionTile({required this.session, required this.index, required this.loading, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final rec = session.recommendation;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: AppTheme.surfaceCard,
        borderRadius: BorderRadius.circular(AppTheme.radiusLg),
        child: InkWell(
          onTap: session.sessionId == null ? null : onTap,
          borderRadius: BorderRadius.circular(AppTheme.radiusLg),
          child: Ink(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(AppTheme.radiusLg),
              border: Border.all(color: AppTheme.border),
            ),
            child: Row(
              children: [
                if (rec != null)
                  ProductImage(product: rec, size: 64, radius: 12)
                else
                  Container(
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceElevated,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.search_rounded, color: AppTheme.textMuted),
                  ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        session.title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: AppTheme.textPrimary, fontSize: 15, fontWeight: FontWeight.w700),
                      ),
                      if (session.wasTranslated)
                        Padding(
                          padding: const EdgeInsets.only(top: 2),
                          child: Text(
                            '→ ${session.queryEnglish}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
                          ),
                        ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          _Meta(text: timeAgo(session.timestamp)),
                          _Meta(text: '${session.totalResults} products'),
                          if (rec != null)
                            _Meta(text: 'Pick ${rec.displayPrice}', color: AppTheme.primary, icon: Icons.auto_awesome),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                loading
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.chevron_right_rounded, color: AppTheme.textMuted),
              ],
            ),
          ),
        ),
      ),
    )
        .animate(delay: Duration(milliseconds: 40 * (index % 10)))
        .fadeIn(duration: 260.ms)
        .slideY(begin: 0.05, duration: 260.ms, curve: Curves.easeOutCubic);
  }
}

class _Meta extends StatelessWidget {
  final String text;
  final Color color;
  final IconData? icon;

  const _Meta({required this.text, this.color = AppTheme.textMuted, this.icon});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[Icon(icon, size: 11, color: color), const SizedBox(width: 4)],
          Text(text, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
