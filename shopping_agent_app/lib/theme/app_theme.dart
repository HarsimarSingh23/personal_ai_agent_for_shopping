import 'package:flutter/material.dart';

/// A plain, light theme: white surfaces, grey borders and one blue accent.
/// Uses the phone's own font (Roboto on Android, San Francisco on iPhone).
class AppTheme {
  AppTheme._();

  // ── Palette ──────────────────────────────────────────────────────────────
  static const Color background = Color(0xFFF6F7F9);
  static const Color surface = Colors.white;
  static const Color surfaceCard = Colors.white;
  static const Color surfaceElevated = Color(0xFFF0F1F4);
  static const Color border = Color(0xFFE2E4E9);
  static const Color borderBright = Color(0xFFCDD1D8);

  static const Color primary = Color(0xFF2155C4); // the one accent colour
  static const Color onPrimary = Colors.white;

  static const Color gold = Color(0xFFE5A100); // rating star
  static const Color success = Color(0xFF15803D);
  static const Color warning = Color(0xFFB45309);
  static const Color error = Color(0xFFC62828);

  static const Color textPrimary = Color(0xFF1C1E22);
  static const Color textSecondary = Color(0xFF4B5059);
  static const Color textMuted = Color(0xFF6B7280); // ≥4.5:1 on white

  // ── Shape ─────────────────────────────────────────────────────────────────
  static const double radiusSm = 8;
  static const double radiusMd = 10;
  static const double radiusLg = 12;

  // ── Store helpers ─────────────────────────────────────────────────────────
  static IconData sourceIcon(String source) {
    switch (source.toLowerCase()) {
      case 'amazon':
      case 'flipkart':
        return Icons.shopping_bag_outlined;
      default:
        return Icons.storefront_outlined;
    }
  }

  // ── Text ──────────────────────────────────────────────────────────────────
  static TextStyle display(double size, {FontWeight weight = FontWeight.w600, Color color = textPrimary}) =>
      TextStyle(fontSize: size, fontWeight: weight, color: color, height: 1.25);

  /// Small grey section label, e.g. "All results".
  static const TextStyle overline = TextStyle(
    color: textMuted,
    fontSize: 13,
    fontWeight: FontWeight.w600,
  );

  // ── ThemeData ─────────────────────────────────────────────────────────────
  static ThemeData get light {
    final base = ThemeData(brightness: Brightness.light, useMaterial3: true);
    final textTheme = base.textTheme.apply(bodyColor: textPrimary, displayColor: textPrimary);
    final rounded = RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusMd));

    return base.copyWith(
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.light(
        primary: primary,
        onPrimary: onPrimary,
        secondary: primary,
        onSecondary: onPrimary,
        surface: surface,
        onSurface: textPrimary,
        surfaceContainerHighest: surfaceElevated,
        outline: border,
        error: error,
        onError: Colors.white,
      ),
      textTheme: textTheme,
      appBarTheme: AppBarTheme(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: display(18),
        iconTheme: const IconThemeData(color: textPrimary),
        shape: const Border(bottom: BorderSide(color: border)),
      ),
      cardColor: surfaceCard,
      dividerColor: border,
      dividerTheme: const DividerThemeData(color: border, thickness: 1, space: 1),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(foregroundColor: textSecondary),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: onPrimary,
          disabledBackgroundColor: surfaceElevated,
          disabledForegroundColor: textMuted,
          minimumSize: const Size(48, 46),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
          shape: rounded,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: textPrimary,
          minimumSize: const Size(48, 46),
          side: const BorderSide(color: borderBright),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
          shape: rounded,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primary,
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        hintStyle: const TextStyle(color: textMuted),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusLg),
          borderSide: const BorderSide(color: borderBright),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusLg),
          borderSide: const BorderSide(color: borderBright),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusLg),
          borderSide: const BorderSide(color: primary, width: 1.4),
        ),
        disabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusLg),
          borderSide: const BorderSide(color: border),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: textPrimary,
        contentTextStyle: const TextStyle(color: Colors.white, fontSize: 14),
        actionTextColor: const Color(0xFF9DB9F5),
        shape: rounded,
        behavior: SnackBarBehavior.floating,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusLg)),
        titleTextStyle: display(18),
        contentTextStyle: const TextStyle(color: textSecondary, fontSize: 14, height: 1.5),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: surface,
        surfaceTintColor: Colors.transparent,
        shape: rounded,
        textStyle: const TextStyle(color: textPrimary, fontSize: 14),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        indicatorColor: primary.withValues(alpha: 0.10),
        height: 64,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            fontSize: 12,
            fontWeight: states.contains(WidgetState.selected) ? FontWeight.w600 : FontWeight.w500,
            color: states.contains(WidgetState.selected) ? primary : textMuted,
          ),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected) ? primary : textMuted,
            size: 24,
          ),
        ),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(color: primary),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(color: textPrimary, borderRadius: BorderRadius.circular(6)),
        textStyle: const TextStyle(color: Colors.white, fontSize: 12),
      ),
    );
  }
}
