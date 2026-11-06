import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  AppTheme._();

  // ── Palette ──────────────────────────────────────────────────────────────
  static const Color background = Color(0xFF0B0B0F);
  static const Color surface = Color(0xFF131318);
  static const Color surfaceCard = Color(0xFF1A1A21);
  static const Color surfaceElevated = Color(0xFF23232C);
  static const Color border = Color(0xFF2C2C36);
  static const Color borderBright = Color(0xFF45454F);

  static const Color primary = Color(0xFFE0FF00); // neon lime brand accent
  static const Color onPrimary = Color(0xFF0B0B0F); // text/icons on lime
  static const Color accent = Color(0xFFFF2E88); // hot pink
  static const Color accentLight = Color(0xFFFF6FAE);

  static const Color gold = Color(0xFFFBBF24);
  static const Color success = Color(0xFF22C55E);
  static const Color warning = Color(0xFFF59E0B);
  static const Color error = Color(0xFFFF5A5F);

  static const Color textPrimary = Color(0xFFF5F5F7);
  static const Color textSecondary = Color(0xFFB4B4BE);
  static const Color textMuted = Color(0xFF8B8B96); // ≥4.5:1 on background

  // ── Source badge colors ───────────────────────────────────────────────────
  static const Color amazonColor = Color(0xFFFF9900);
  static const Color flipkartColor = Color(0xFF4C8DFF);
  static const Color webColor = Color(0xFF34D399);

  // ── Shape ─────────────────────────────────────────────────────────────────
  static const double radiusSm = 10;
  static const double radiusMd = 14;
  static const double radiusLg = 20;

  // ── Gradients ─────────────────────────────────────────────────────────────
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primary, Color(0xFF9DFF6B)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient brandGradient = LinearGradient(
    colors: [primary, accent],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient recommendGradient = LinearGradient(
    colors: [Color(0xFF1C1F12), Color(0xFF17171E)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // ── Source helpers ────────────────────────────────────────────────────────
  static Color sourceColor(String source) {
    switch (source.toLowerCase()) {
      case 'amazon':
        return amazonColor;
      case 'flipkart':
        return flipkartColor;
      default:
        return webColor;
    }
  }

  static IconData sourceIcon(String source) {
    switch (source.toLowerCase()) {
      case 'amazon':
        return Icons.shopping_bag_rounded;
      case 'flipkart':
        return Icons.local_mall_rounded;
      default:
        return Icons.storefront_rounded;
    }
  }

  // ── Text ──────────────────────────────────────────────────────────────────
  static TextStyle display(double size, {FontWeight weight = FontWeight.w700, Color color = textPrimary}) =>
      GoogleFonts.outfit(fontSize: size, fontWeight: weight, color: color, letterSpacing: -0.3, height: 1.2);

  static const TextStyle overline = TextStyle(
    color: textMuted,
    fontSize: 11,
    fontWeight: FontWeight.w700,
    letterSpacing: 1.4,
  );

  // ── ThemeData ─────────────────────────────────────────────────────────────
  static ThemeData get dark {
    final base = ThemeData(brightness: Brightness.dark, useMaterial3: true);
    final textTheme = GoogleFonts.interTextTheme(base.textTheme).apply(
      bodyColor: textPrimary,
      displayColor: textPrimary,
    );

    return base.copyWith(
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        onPrimary: onPrimary,
        secondary: accent,
        onSecondary: Colors.white,
        surface: surface,
        onSurface: textPrimary,
        surfaceContainerHighest: surfaceElevated,
        outline: border,
        error: error,
        onError: Colors.white,
      ),
      textTheme: textTheme,
      splashFactory: InkSparkle.splashFactory,
      appBarTheme: AppBarTheme(
        backgroundColor: background,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: display(20),
        iconTheme: const IconThemeData(color: textPrimary),
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
          minimumSize: const Size(48, 48),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          textStyle: GoogleFonts.inter(fontWeight: FontWeight.w700, fontSize: 15),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusMd)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: textPrimary,
          minimumSize: const Size(48, 48),
          side: const BorderSide(color: borderBright),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          textStyle: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusMd)),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primary,
          textStyle: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceCard,
        hintStyle: const TextStyle(color: textMuted),
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(24),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(24),
          borderSide: const BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(24),
          borderSide: const BorderSide(color: primary, width: 1.4),
        ),
        disabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(24),
          borderSide: BorderSide(color: border.withValues(alpha: 0.5)),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: surfaceElevated,
        contentTextStyle: GoogleFonts.inter(color: textPrimary, fontSize: 14),
        actionTextColor: primary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusMd)),
        behavior: SnackBarBehavior.floating,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: surfaceCard,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusLg)),
        titleTextStyle: display(20),
        contentTextStyle: GoogleFonts.inter(color: textSecondary, fontSize: 14, height: 1.5),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: surfaceElevated,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusMd)),
        textStyle: GoogleFonts.inter(color: textPrimary, fontSize: 14),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        indicatorColor: primary.withValues(alpha: 0.16),
        height: 68,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => GoogleFonts.inter(
            fontSize: 12,
            fontWeight: states.contains(WidgetState.selected) ? FontWeight.w700 : FontWeight.w500,
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
        decoration: BoxDecoration(color: surfaceElevated, borderRadius: BorderRadius.circular(8)),
        textStyle: const TextStyle(color: textPrimary, fontSize: 12),
      ),
    );
  }
}
