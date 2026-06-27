import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  AppTheme._();

  // ── Palette ──────────────────────────────────────────────────────────────
  static const Color background    = Color(0xFFF8FAFC);
  static const Color surface       = Color(0xFFFFFFFF);
  static const Color surfaceCard   = Color(0xFFFFFFFF);
  static const Color surfaceElevated = Color(0xFFF1F5F9);
  static const Color border        = Color(0xFFE2E8F0);
  static const Color borderBright  = Color(0xFFCBD5E1);

  static const Color primary       = Color(0xFF2563EB); // Blue 600
  static const Color primaryDark   = Color(0xFF1D4ED8); // Blue 700
  static const Color accent        = Color(0xFF7C3AED); // Violet 600
  static const Color accentLight   = Color(0xFF8B5CF6); // Violet 500

  static const Color gold          = Color(0xFFF59E0B);
  static const Color success       = Color(0xFF10B981);
  static const Color error         = Color(0xFFEF4444);

  static const Color textPrimary   = Color(0xFF0F172A); // Slate 900
  static const Color textSecondary = Color(0xFF475569); // Slate 600
  static const Color textMuted     = Color(0xFF94A3B8); // Slate 400

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
    colors: [Color(0xFFEFF6FF), Color(0xFFF5F3FF)], // Blue 50 to Violet 50
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient backgroundGradient = LinearGradient(
    colors: [Color(0xFFF8FAFC), Color(0xFFFFFFFF), Color(0xFFF8FAFC)],
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
  static ThemeData get light {
    final base = ThemeData.light(useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.light(
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
        backgroundColor: textPrimary,
        contentTextStyle: GoogleFonts.inter(color: Colors.white),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}
