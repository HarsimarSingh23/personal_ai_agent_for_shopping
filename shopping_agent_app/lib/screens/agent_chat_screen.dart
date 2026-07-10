import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/search_response.dart';
import '../theme/app_theme.dart';
import 'search_results_screen.dart';
import 'package:google_fonts/google_fonts.dart';

class AgentChatScreen extends StatefulWidget {
  const AgentChatScreen({Key? key}) : super(key: key);

  @override
  _AgentChatScreenState createState() => _AgentChatScreenState();
}

class _AgentChatScreenState extends State<AgentChatScreen> {
  final List<Map<String, String>> _messages = [
    {
      "role": "agent",
      "content": "Hi there! What are you looking to buy today?"
    }
  ];
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _isTyping = false;
  bool _isSearching = false;
  SearchResponse? _lastResults;

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _sendMessage() async {
    if (_textController.text.trim().isEmpty) return;
    final userMessage = _textController.text.trim();
    _textController.clear();

    setState(() {
      _messages.add({"role": "user", "content": userMessage});
      _isTyping = true;
    });
    _scrollToBottom();

    try {
      final response = await ApiService.instance.chat(_messages);
      if (!mounted) return;
      
      setState(() {
        _isTyping = false;
        _messages.add({"role": "agent", "content": response['message']});
      });
      _scrollToBottom();

      if (response['is_ready_to_search'] == true) {
        _performSearch(response['search_query']);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isTyping = false;
        _messages.add({"role": "agent", "content": "Oops, something went wrong. Try again!"});
      });
      _scrollToBottom();
    }
  }

  void _performSearch(String query) async {
    setState(() {
      _isSearching = true;
    });

    try {
      final results = await ApiService.instance.search(query);
      if (!mounted) return;
      setState(() {
        _isSearching = false;
        _lastResults = results;
      });
      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => SearchResultsScreen(
              response: results,
            ),
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isSearching = false;
        _messages.add({"role": "agent", "content": "Couldn't find anything for that... Let's try something else!"});
      });
      _scrollToBottom();
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('AI Shopping Assistant', style: GoogleFonts.outfit(fontWeight: FontWeight.bold, color: AppTheme.primary, fontSize: 18)),
        centerTitle: true,
        actions: [
          if (_lastResults != null)
            IconButton(
              icon: const Icon(Icons.list_alt, color: AppTheme.primary),
              tooltip: 'View Results',
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => SearchResultsScreen(response: _lastResults!),
                  ),
                );
              },
            ),
          IconButton(
            icon: const Icon(Icons.add_comment, color: AppTheme.textSecondary),
            tooltip: 'New Chat',
            onPressed: () {
              setState(() {
                _messages.clear();
                _messages.add({
                  "role": "agent",
                  "content": "Hi there! What are you looking to buy today?"
                });
                _lastResults = null;
              });
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16.0),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                final isUser = msg["role"] == "user";
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 4.0),
                    padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
                    decoration: BoxDecoration(
                      color: isUser ? AppTheme.primary.withOpacity(0.2) : AppTheme.surfaceElevated,
                      borderRadius: BorderRadius.only(
                        topLeft: const Radius.circular(16),
                        topRight: const Radius.circular(16),
                        bottomLeft: isUser ? const Radius.circular(16) : const Radius.circular(0),
                        bottomRight: isUser ? const Radius.circular(0) : const Radius.circular(16),
                      ),
                      border: Border.all(color: isUser ? AppTheme.primary.withOpacity(0.5) : AppTheme.border),
                    ),
                    child: Text(
                      msg["content"]!,
                      style: GoogleFonts.inter(
                        color: AppTheme.textPrimary,
                        fontSize: 15,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          if (_isTyping)
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: Text("AI Assistant is typing...", style: GoogleFonts.inter(color: AppTheme.textMuted, fontStyle: FontStyle.italic)),
            ),
          if (_isSearching)
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                children: [
                  const CircularProgressIndicator(color: AppTheme.primary),
                  const SizedBox(height: 8),
                  Text("Finding the best options...", style: GoogleFonts.inter(color: AppTheme.textSecondary)),
                ],
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _textController,
                    enabled: !_isTyping && !_isSearching,
                    style: GoogleFonts.inter(color: AppTheme.textPrimary),
                    decoration: InputDecoration(
                      hintText: "Type a message...",
                      hintStyle: const TextStyle(color: AppTheme.textMuted),
                      filled: true,
                      fillColor: AppTheme.surfaceCard,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(30),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                    ),
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  decoration: const BoxDecoration(
                    color: AppTheme.primary,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    icon: const Icon(Icons.send, color: AppTheme.background),
                    onPressed: (_isTyping || _isSearching) ? null : _sendMessage,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
