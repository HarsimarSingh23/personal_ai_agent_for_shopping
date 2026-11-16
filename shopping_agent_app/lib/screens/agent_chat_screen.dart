import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/chat_message.dart';
import '../models/search_response.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/chat_widgets.dart';
import '../widgets/server_dialog.dart';
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
    'Noise-cancelling earbuds under ₹5,000',
    'Laptop for college under ₹60,000',
    'Running shoes for men, size 9',
    'Best camera phone under ₹30,000',
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

  Future<void> _editServer() async {
    final changed = await showServerDialog(context, api: _api);
    if (!changed || !mounted) return;
    setState(() => _serverOnline = null); // "Connecting…" while we check the new address
    await _checkServer();
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
            if (_serverOnline == false) _OfflineBanner(onRetry: _checkServer, onChangeServer: _editServer),
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
      true => ('Online', AppTheme.success),
      false => ('Offline', AppTheme.error),
      null => ('Connecting…', AppTheme.textMuted),
    };
    return AppBar(
      titleSpacing: 16,
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('AI Shopper', style: AppTheme.display(18)),
          const SizedBox(height: 2),
          Text(
            status.$1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(color: status.$2, fontSize: 12),
          ),
        ],
      ),
      actions: [
        IconButton(
          tooltip: 'Server address',
          onPressed: _busy ? null : _editServer,
          icon: const Icon(Icons.settings_outlined),
        ),
        IconButton(
          tooltip: 'New chat',
          onPressed: _busy || _messages.isEmpty ? null : _newChat,
          icon: const Icon(Icons.add_comment_outlined),
        ),
        const SizedBox(width: 4),
      ],
    );
  }

  Widget _welcome() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 24, 16, 20),
      children: [
        Text('What do you want to buy?', style: AppTheme.display(22)),
        const SizedBox(height: 6),
        const Text(
          'Type it in English, Hindi or Punjabi. The app compares Amazon, Flipkart and other stores '
          'and suggests one product.',
          style: TextStyle(color: AppTheme.textSecondary, fontSize: 14.5, height: 1.5),
        ),
        const SizedBox(height: 24),
        const Text('Examples', style: AppTheme.overline),
        const SizedBox(height: 8),
        for (final text in _suggestions)
          _SuggestionCard(text: text, onTap: _serverOnline == false ? null : () => _send(text)),
        const SizedBox(height: 16),
        const Text(
          'Do not share card numbers or passwords in the chat.',
          style: TextStyle(color: AppTheme.textMuted, fontSize: 12),
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
        color: AppTheme.surface,
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
                    ? 'Searching…'
                    : (_messages.isEmpty ? 'For example: earbuds under ₹2,000' : 'Type a reply…'),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            tooltip: 'Send',
            onPressed: canSend ? _send : null,
            style: IconButton.styleFrom(
              backgroundColor: AppTheme.primary,
              foregroundColor: AppTheme.onPrimary,
              disabledBackgroundColor: AppTheme.surfaceElevated,
              disabledForegroundColor: AppTheme.textMuted,
              fixedSize: const Size(48, 48),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusLg)),
            ),
            icon: const Icon(Icons.send_rounded, size: 20),
          ),
        ],
      ),
    );
  }
}

class _SuggestionCard extends StatelessWidget {
  final String text;
  final VoidCallback? onTap;

  const _SuggestionCard({required this.text, this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: AppTheme.surfaceCard,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppTheme.radiusMd),
          side: const BorderSide(color: AppTheme.border),
        ),
        child: InkWell(
          onTap: onTap,
          customBorder: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusMd)),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
            child: Text(
              text,
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14.5),
            ),
          ),
        ),
      ),
    );
  }
}

class _OfflineBanner extends StatelessWidget {
  final VoidCallback onRetry;
  final VoidCallback onChangeServer;

  const _OfflineBanner({required this.onRetry, required this.onChangeServer});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 6, 6, 6),
      color: const Color(0xFFFDF0F0),
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
          TextButton(onPressed: onChangeServer, child: const Text('Change')),
          TextButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}
