import 'package:flutter/material.dart';

import '../config/app_config.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

/// Lets the user point the app at their own backend, e.g. a laptop on the same
/// Wi-Fi (http://192.168.1.5:8000), without rebuilding the app.
///
/// Returns true when the address was changed.
Future<bool> showServerDialog(BuildContext context, {ApiService? api}) async {
  final service = api ?? ApiService.instance;
  final changed = await showDialog<bool>(
    context: context,
    builder: (ctx) => _ServerDialog(api: service),
  );
  return changed ?? false;
}

class _ServerDialog extends StatefulWidget {
  final ApiService api;

  const _ServerDialog({required this.api});

  @override
  State<_ServerDialog> createState() => _ServerDialogState();
}

class _ServerDialogState extends State<_ServerDialog> {
  late final TextEditingController _controller = TextEditingController(text: widget.api.serverUrl);
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final url = AppConfig.normalizeServerUrl(_controller.text);
    if (url == null) {
      setState(() => _error = 'Enter an address like 192.168.1.5 or http://192.168.1.5:8000');
      return;
    }
    // Saving the built-in address is the same as resetting.
    await widget.api.setServerUrl(url == AppConfig.builtInBaseUrl ? null : url);
    if (mounted) Navigator.of(context).pop(true);
  }

  Future<void> _reset() async {
    await widget.api.setServerUrl(null);
    if (mounted) Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Server address'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            "The computer running the shopping agent backend. On a phone, use the computer's "
            'Wi-Fi IP address (run ipconfig on Windows).',
            style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
          ),
          const SizedBox(height: 16),
          TextField(
            key: const Key('server-url-field'),
            controller: _controller,
            autofocus: true,
            keyboardType: TextInputType.url,
            autocorrect: false,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => _save(),
            onChanged: (_) {
              if (_error != null) setState(() => _error = null);
            },
            decoration: InputDecoration(
              hintText: 'http://192.168.1.5:${AppConfig.defaultPort}',
              errorText: _error,
              errorMaxLines: 2,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Built-in: ${AppConfig.builtInBaseUrl}',
            style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
          ),
        ],
      ),
      actions: [
        if (AppConfig.serverOverride != null) TextButton(onPressed: _reset, child: const Text('Reset')),
        TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
        FilledButton(onPressed: _save, child: const Text('Save')),
      ],
    );
  }
}
