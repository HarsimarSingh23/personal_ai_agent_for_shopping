import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../models/chat_message.dart';
import '../models/search_response.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/chat_widgets.dart';
import 'product_detail_screen.dart';
import 'search_results_screen.dart';

class AgentChatScreen extends StatefulWidget {
  const AgentChatScreen({super.key});

  @override
  State<AgentChatScreen> createState() => _AgentChatScreenState();
}

class _AgentChatScreenState extends State<AgentChatScreen> {
  static const _maxInputChars = 500;
  static const _suggestions = [
    (Icons.headphones_rounded, 'Noise-cancelling earbuds under ₹5,000'),
    (Icons.laptop_mac_rounded, 'Laptop for college under ₹60,000'),
    (Icons.directions_run_rounded, 'Running shoes for men, size 9'),
    (Icons.photo_camera_rounded, 'Best camera phone under ₹30,000'),
    (Icons.watch_rounded, 'Smartwatch with an AMOLED display'),
    (Icons.soup_kitchen_rounded, 'Air fryer for a family of four'),
  ];

  final ApiService _api = ApiService.instance;
  final List<ChatMessage> _messages = [];
  final TextEditingController _input = TextEditingController();
  final ScrollController _scroll = ScrollController();
  final FocusNode _focus = FocusNode();

  /// Messages before this index belong to an earlier search and are not
  /// replayed to the model; the last search query is passed as context instead.
  int _contextStart = 0;
  String? _lastSearchQuery;

  bool _typing = false;
  String? _searchingFor;
  bool? _serverOnline;

  bool get _busy => _typing || _searchingFor != null;

  @override
  void initState() {
    super.initState();
    _input.addListener(() => setState(() {}));
    _checkServer();
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    _focus.dispose();
    super.dispose();
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  Future<void> _checkServer() async {
    final online = await _api.checkHealth();
    if (mounted) setState(() => _serverOnline = online);
  }

  void _send([String? preset]) {
    final text = (preset ?? _input.text).trim();
    if (text.isEmpty || _busy) return;
    HapticFeedback.lightImpact();
    _input.clear();
    setState(() => _messages.add(ChatMessage.user(text)));
    _scrollToBottom();
    _requestReply();
  }

  List<Map<String, String>> _history() {
    final history = <Map<String, String>>[
      if (_lastSearchQuery != null)
        {'role': 'agent', 'content': 'Earlier in this chat I searched for "$_lastSearchQuery" and showed the results.'},
      for (final m in _messages.skip(_contextStart))
        if (m.kind == ChatKind.text && m.text.isNotEmpty) m.toJson(),
    ];
    return history.length > 30 ? history.sublist(history.length - 30) : history;
  }

  Future<void> _requestReply() async {
    setState(() => _typing = true);
    _scrollToBottom();
    try {
      final reply = await _api.chat(_history());
      if (!mounted) return;
      setState(() {
        _typing = false;
        _messages.add(ChatMessage.agent(reply.message));
      });
      _scrollToBottom();
      if (reply.isReadyToSearch && reply.searchQuery.isNotEmpty) {
        await _runSearch(reply.searchQuery);
      }
    } on ApiException catch (e) {
      _fail(e, const RetryAction.chat());
    }
  }

  Future<void> _runSearch(String query) async {
    setState(() => _searchingFor = query);
    _scrollToBottom();
    try {
      final response = await _api.search(query);
      if (!mounted) return;
      HapticFeedback.mediumImpact();
      setState(() {
        _searchingFor = null;
        if (response.isEmpty) {
          _messages.add(ChatMessage.agent(
            "I couldn't find anything for \"${response.query.isEmpty ? query : response.query}\". "
            'Try describing it differently, or with fewer details.',
          ));
        } else {
          _messages.add(ChatMessage.results(response));
          _lastSearchQuery = response.query.isEmpty ? query : response.query;
          _contextStart = _messages.length;
        }
      });
      _scrollToBottom();
    } on ApiException catch (e) {
      _fail(e, RetryAction.search(query));
    }
  }

  void _fail(ApiException e, RetryAction retry) {
    if (!mounted) return;
    setState(() {
      _typing = false;
      _searchingFor = null;
      _messages.add(ChatMessage.error(e.message, retry));
      if (e.isNetworkError) _serverOnline = false;
    });
    _scrollToBottom();
    if (e.isNetworkError) _checkServer();
  }

  void _retry(ChatMessage error) {
    if (_busy) return;
    setState(() => _messages.remove(error));
    final action = error.retry!;
    if (action.isSearch) {
      _runSearch(action.query!);
    } else {
      _requestReply();
    }
  }

  Future<void> _newChat() async {
    if (_busy) return;
    if (_messages.isNotEmpty) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Start a new chat?'),
          content: const Text('This clears the conversation. Your searches stay in History.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('New chat')),
          ],
        ),
      );
      if (ok != true) return;
    }
    setState(() {
      _messages.clear();
      _contextStart = 0;
      _lastSearchQuery = null;
    });
  }

  void _openResults(SearchResponse response) {
    Navigator.push(context, MaterialPageRoute(builder: (_) => SearchResultsScreen(response: response)));
  }

  void _openPick(SearchResponse response) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ProductDetailScreen(
          product: response.recommendation!,
          aiReason: response.recommendationReason,
        ),
      ),
    );
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOutCubic,
        );
      }
    });
  }

  // ── UI ────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _appBar(),
      body: SafeArea(
        top: false,
        child: Column(
          children: [
            if (_serverOnline == false) _OfflineBanner(onRetry: _checkServer),
            Expanded(
              child: GestureDetector(
                onTap: () => _focus.unfocus(),
                behavior: HitTestBehavior.translucent,
                child: _messages.isEmpty && !_busy ? _welcome() : _conversation(),
              ),
            ),
            _composer(),
          ],
        ),
      ),
    );
  }

  PreferredSizeWidget _appBar() {
    final status = switch (_serverOnline) {
      true => ('Online · Amazon, Flipkart & more', AppTheme.success),
      false => ('Offline', AppTheme.error),
      null => ('Connecting…', AppTheme.textMuted),
    };
    return AppBar(
      titleSpacing: 16,
      title: Row(
        children: [
          const AgentAvatar(size: 36),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('AI Shopper', style: AppTheme.display(18)),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Container(
                      width: 7,
                      height: 7,
                      decoration: BoxDecoration(color: status.$2, shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        status.$1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: AppTheme.textMuted, fontSize: 12, fontWeight: FontWeight.w500),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
      actions: [
        IconButton(
          tooltip: 'New chat',
          onPressed: _busy || _messages.isEmpty ? null : _newChat,
          icon: const Icon(Icons.edit_square),
        ),
        const SizedBox(width: 4),
      ],
      bottom: const PreferredSize(
        preferredSize: Size.fromHeight(1),
        child: Divider(height: 1),
      ),
    );
  }

  Widget _welcome() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 28, 20, 20),
      children: [
        Center(
          child: Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(color: AppTheme.primary.withValues(alpha: 0.25), blurRadius: 40, spreadRadius: 2),
              ],
            ),
            child: const AgentAvatar(size: 68),
          ),
        ).animate().scale(begin: const Offset(0.8, 0.8), duration: 450.ms, curve: Curves.easeOutBack),
        const SizedBox(height: 22),
        Text(
          'What are you shopping for today?',
          textAlign: TextAlign.center,
          style: AppTheme.display(26),
        ),
        const SizedBox(height: 10),
        const Text(
          "Tell me what you need, in English, Hindi or Punjabi. I'll compare Amazon, Flipkart and "
          'other stores, then pick the best deal for you.',
          textAlign: TextAlign.center,
          style: TextStyle(color: AppTheme.textSecondary, fontSize: 14.5, height: 1.55),
        ),
        const SizedBox(height: 28),
        Text('TRY ASKING', style: AppTheme.overline),
        const SizedBox(height: 12),
        LayoutBuilder(
          builder: (context, constraints) {
            final width = (constraints.maxWidth - 10) / 2;
            return Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                for (var i = 0; i < _suggestions.length; i++)
                  SizedBox(
                    width: width,
                    child: _SuggestionCard(
                      icon: _suggestions[i].$1,
                      text: _suggestions[i].$2,
                      onTap: _serverOnline == false ? null : () => _send(_suggestions[i].$2),
                    ),
                  )
                      .animate(delay: (80 + 50 * i).ms)
                      .fadeIn(duration: 300.ms)
                      .slideY(begin: 0.15, duration: 300.ms, curve: Curves.easeOutCubic),
              ],
            );
          },
        ),
        const SizedBox(height: 24),
        const Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.lock_outline_rounded, size: 13, color: AppTheme.textMuted),
            SizedBox(width: 6),
            Flexible(
              child: Text(
                'Never share card numbers or passwords in chat.',
                style: TextStyle(color: AppTheme.textMuted, fontSize: 12),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _conversation() {
    final itemCount = _messages.length + (_busy ? 1 : 0);
    return ListView.builder(
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(14, 16, 14, 12),
      itemCount: itemCount,
      itemBuilder: (context, i) {
        if (i == _messages.length) {
          return ChatRow(
            isUser: false,
            wide: _searchingFor != null,
            child: _searchingFor != null
                ? SearchProgressCard(query: _searchingFor!)
                : const Align(alignment: Alignment.centerLeft, child: TypingIndicator()),
          );
        }
        final msg = _messages[i];
        final prevIsAgent = i > 0 && !_messages[i - 1].isUser;
        return ChatRow(
          isUser: msg.isUser,
          showAvatar: !prevIsAgent,
          wide: msg.kind == ChatKind.results,
          child: switch (msg.kind) {
            ChatKind.text => MessageBubble(text: msg.text, isUser: msg.isUser),
            ChatKind.error => ErrorBubble(text: msg.text, onRetry: _busy ? null : () => _retry(msg)),
            ChatKind.results => ResultsMessageCard(
                response: msg.results!,
                onViewAll: () => _openResults(msg.results!),
                onOpenPick: () => _openPick(msg.results!),
              ),
          },
        );
      },
    );
  }

  Widget _composer() {
    final canSend = _input.text.trim().isNotEmpty && !_busy;
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 10),
      decoration: const BoxDecoration(
        color: AppTheme.background,
        border: Border(top: BorderSide(color: AppTheme.border)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: TextField(
              controller: _input,
              focusNode: _focus,
              enabled: !_busy,
              minLines: 1,
              maxLines: 4,
              textCapitalization: TextCapitalization.sentences,
              textInputAction: TextInputAction.send,
              inputFormatters: [LengthLimitingTextInputFormatter(_maxInputChars)],
              onSubmitted: (_) => _send(),
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 15),
              decoration: InputDecoration(
                hintText: _searchingFor != null
                    ? 'Finding the best deals…'
                    : (_messages.isEmpty ? 'Describe what you want to buy…' : 'Reply or refine your search…'),
              ),
            ),
          ),
          const SizedBox(width: 8),
          AnimatedScale(
            scale: canSend ? 1 : 0.92,
            duration: const Duration(milliseconds: 150),
            child: IconButton.filled(
              tooltip: 'Send',
              onPressed: canSend ? _send : null,
              style: IconButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: AppTheme.onPrimary,
                disabledBackgroundColor: AppTheme.surfaceElevated,
                disabledForegroundColor: AppTheme.textMuted,
                fixedSize: const Size(50, 50),
              ),
              icon: const Icon(Icons.arrow_upward_rounded),
            ),
          ),
        ],
      ),
    );
  }
}

class _SuggestionCard extends StatelessWidget {
  final IconData icon;
  final String text;
  final VoidCallback? onTap;

  const _SuggestionCard({required this.icon, required this.text, this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.surfaceCard,
      borderRadius: BorderRadius.circular(AppTheme.radiusMd),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppTheme.radiusMd),
        child: Ink(
          height: 108,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppTheme.radiusMd),
            border: Border.all(color: AppTheme.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 20, color: AppTheme.primary),
              const Spacer(),
              Text(
                text,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13, fontWeight: FontWeight.w500, height: 1.3),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _OfflineBanner extends StatelessWidget {
  final VoidCallback onRetry;

  const _OfflineBanner({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 6, 6, 6),
      color: AppTheme.error.withValues(alpha: 0.12),
      child: Row(
        children: [
          const Icon(Icons.cloud_off_rounded, size: 18, color: AppTheme.error),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              "Can't reach the server right now.",
              style: TextStyle(color: AppTheme.textPrimary, fontSize: 13),
            ),
          ),
          TextButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    ).animate().fadeIn(duration: 250.ms).slideY(begin: -0.3, duration: 250.ms);
  }
}
