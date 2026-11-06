import 'search_response.dart';

enum ChatRole { user, agent }

enum ChatKind {
  /// Plain conversation; sent to the backend as chat history.
  text,

  /// Search results rendered as a rich card.
  results,

  /// A failed request with a retry action.
  error,
}

/// What to redo when the user taps "Try again" on an error message.
class RetryAction {
  final bool isSearch;
  final String? query;

  const RetryAction.chat() : isSearch = false, query = null;
  const RetryAction.search(String this.query) : isSearch = true;
}

class ChatMessage {
  final ChatRole role;
  final String text;
  final ChatKind kind;
  final SearchResponse? results;
  final RetryAction? retry;

  const ChatMessage._(this.role, this.text, this.kind, {this.results, this.retry});

  const ChatMessage.user(String text) : this._(ChatRole.user, text, ChatKind.text);

  const ChatMessage.agent(String text) : this._(ChatRole.agent, text, ChatKind.text);

  const ChatMessage.results(SearchResponse response)
      : this._(ChatRole.agent, '', ChatKind.results, results: response);

  const ChatMessage.error(String text, RetryAction retry)
      : this._(ChatRole.agent, text, ChatKind.error, retry: retry);

  bool get isUser => role == ChatRole.user;

  Map<String, String> toJson() => {
        'role': isUser ? 'user' : 'agent',
        'content': text,
      };
}
