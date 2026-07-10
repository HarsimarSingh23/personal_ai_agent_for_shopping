import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:intl/intl.dart';
import '../models/session.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/empty_state.dart';
import 'search_results_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => HistoryScreenState();
}

class HistoryScreenState extends State<HistoryScreen>
    with WidgetsBindingObserver {
  final ApiService _api = ApiService.instance;
  List<SessionSummary>? _sessions;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  void reloadIfNeeded() {
    if (!_isLoading) _load();
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final sessions = await _api.getSessions();
      if (!mounted) return;
      setState(() {
        _sessions = sessions;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceAll('Exception: ', '');
        _isLoading = false;
      });
    }
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
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
      decoration: BoxDecoration(
        color: AppTheme.background,
        border: Border(bottom: BorderSide(color: AppTheme.border.withValues(alpha: 0.5))),
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppTheme.surfaceElevated,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.border),
            ),
            child: const Icon(Icons.history_rounded, color: AppTheme.textSecondary, size: 18),
          ),
          const SizedBox(width: 10),
          const Text(
            'Search History',
            style: TextStyle(
              color: AppTheme.textPrimary,
              fontSize: 20,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.3,
            ),
          ),
          const Spacer(),
          if (!_isLoading)
            IconButton(
              onPressed: _load,
              icon: const Icon(Icons.refresh_rounded, color: AppTheme.textSecondary, size: 20),
              tooltip: 'Refresh',
            ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return _buildLoadingList();

    if (_error != null) {
      return EmptyState(
        type: EmptyStateType.error,
        errorMessage: _error,
        onRetry: _load,
      );
    }

    if (_sessions == null || _sessions!.isEmpty) {
      return const EmptyState(type: EmptyStateType.noHistory);
    }

    return RefreshIndicator(
      onRefresh: _load,
      color: AppTheme.primary,
      backgroundColor: AppTheme.surfaceCard,
      child: ListView.builder(
        physics: const BouncingScrollPhysics(
          parent: AlwaysScrollableScrollPhysics(),
        ),
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 40),
        itemCount: _sessions!.length,
        itemBuilder: (context, i) => _SessionTile(
          session: _sessions![i],
          index: i,
        ),
      ),
    );
  }

  Widget _buildLoadingList() {
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 40),
      itemCount: 6,
      itemBuilder: (_, i) => Container(
        height: 90,
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(
          color: AppTheme.surfaceCard,
          borderRadius: BorderRadius.circular(16),
        ),
      ).animate(delay: Duration(milliseconds: i * 80))
       .shimmer(duration: 1.2.seconds, color: AppTheme.borderBright),
    );
  }
}

class _SessionTile extends StatelessWidget {
  final SessionSummary session;
  final int index;

  const _SessionTile({required this.session, required this.index});

  String _formatDate(DateTime dt) {
    final now = DateTime.now().toUtc();
    final utcDt = dt.isUtc ? dt : dt.toUtc();
    final diff = now.difference(utcDt);
    if (diff.inSeconds < 60) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return DateFormat('MMM d, yyyy').format(dt.toLocal());
  }

  @override
  Widget build(BuildContext context) {
    final rec = session.recommendation;
    return GestureDetector(
      onTap: session.sessionId != null
          ? () async {
              showDialog(
                context: context,
                barrierDismissible: false,
                builder: (context) => const Center(child: CircularProgressIndicator(color: AppTheme.primary)),
              );
              try {
                final fullResponse = await ApiService.instance.getSession(session.sessionId!);
                if (!context.mounted) return;
                Navigator.pop(context); // dismiss dialog
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => SearchResultsScreen(response: fullResponse)),
                );
              } catch (e) {
                if (!context.mounted) return;
                Navigator.pop(context); // dismiss dialog
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Could not load session: $e')),
                );
              }
            }
          : null,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(
          color: AppTheme.surfaceCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.border, width: 1),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          session.queryOriginal.isEmpty
                              ? session.queryEnglish
                              : session.queryOriginal,
                          style: const TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (session.queryEnglish != session.queryOriginal &&
                            session.queryEnglish.isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 2),
                            child: Text(
                              '→ ${session.queryEnglish}',
                              style: const TextStyle(
                                color: AppTheme.textMuted,
                                fontSize: 12,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    _formatDate(session.timestamp),
                    style: const TextStyle(
                      color: AppTheme.textMuted,
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  _StatChip(
                    icon: Icons.inventory_2_outlined,
                    label: '${session.totalResults} products',
                    color: AppTheme.primary,
                  ),
                  if (rec != null) ...[
                    const SizedBox(width: 8),
                    Expanded(
                      child: _StatChip(
                        icon: Icons.auto_awesome,
                        label: rec.price != 'N/A' ? rec.price : 'See pick',
                        color: AppTheme.gold,
                        truncate: true,
                      ),
                    ),
                  ],
                  const Spacer(),
                  if (rec != null && rec.hasValidUrl)
                    const Icon(Icons.arrow_outward_rounded,
                        size: 14, color: AppTheme.textMuted),
                ],
              ),
            ],
          ),
        ),
      ),
    )
        .animate(delay: Duration(milliseconds: 60 * (index % 10)))
        .fadeIn(duration: 300.ms)
        .slideY(begin: 0.04, duration: 300.ms, curve: Curves.easeOutCubic);
  }
}

class _StatChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final bool truncate;

  const _StatChip({
    required this.icon,
    required this.label,
    required this.color,
    this.truncate = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: truncate ? MainAxisSize.min : MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          truncate
              ? Flexible(
                  child: Text(label,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
                )
              : Text(label,
                  style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
