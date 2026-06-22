import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  AppTheme._();

  // ── Palette ──────────────────────────────────────────────────────────────
  static const Color background    = Color(0xFF080B14);
  static const Color surface       = Color(0xFF0F1523);
  static const Color surfaceCard   = Color(0xFF141927);
  static const Color surfaceElevated = Color(0xFF1A2035);
  static const Color border        = Color(0xFF1E2940);
  static const Color borderBright  = Color(0xFF2A3A5C);

  static const Color primary       = Color(0xFF4F8EF7);
  static const Color primaryDark   = Color(0xFF2D6FE8);
  static const Color accent        = Color(0xFF7C3AED);
  static const Color accentLight   = Color(0xFF9F67FF);

  static const Color gold          = Color(0xFFFBBF24);
  static const Color success       = Color(0xFF10B981);
  static const Color error         = Color(0xFFEF4444);

  static const Color textPrimary   = Color(0xFFF1F5F9);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted     = Color(0xFF475569);

  // ── Source badge colors ───────────────────────────────────────────────────
  static const Color amazonColor   = Color(0xFFFF9900);
  static const Color flipkartColor = Color(0xFF2874F0);
  static const Color webColor      = Color(0xFF10B981);

  // ── Gradients ─────────────────────────────────────────────────────────────
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primary, accent],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient recommendGradient = LinearGradient(
    colors: [Color(0xFF1E3A5F), Color(0xFF2D1B69)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient backgroundGradient = LinearGradient(
    colors: [Color(0xFF080B14), Color(0xFF0D1220), Color(0xFF080B14)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  // ── Source color helper ────────────────────────────────────────────────────
  static Color sourceColor(String source) {
    switch (source.toLowerCase()) {
      case 'amazon':   return amazonColor;
      case 'flipkart': return flipkartColor;
      default:         return webColor;
    }
  }

  static IconData sourceIcon(String source) {
    switch (source.toLowerCase()) {
      case 'amazon':   return Icons.shopping_bag;
      case 'flipkart': return Icons.local_mall;
      default:         return Icons.language;
    }
  }

  // ── ThemeData ─────────────────────────────────────────────────────────────
  static ThemeData get dark {
    final base = ThemeData.dark(useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        secondary: accent,
        surface: surface,
        error: error,
      ),
      textTheme: GoogleFonts.interTextTheme(base.textTheme).apply(
        bodyColor: textPrimary,
        displayColor: textPrimary,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.inter(
          color: textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
        ),
        iconTheme: const IconThemeData(color: textPrimary),
      ),
      cardColor: surfaceCard,
      dividerColor: border,
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceElevated,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: primary, width: 1.5),
        ),
        hintStyle: const TextStyle(color: textMuted),
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: surfaceElevated,
        contentTextStyle: GoogleFonts.inter(color: textPrimary),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}
