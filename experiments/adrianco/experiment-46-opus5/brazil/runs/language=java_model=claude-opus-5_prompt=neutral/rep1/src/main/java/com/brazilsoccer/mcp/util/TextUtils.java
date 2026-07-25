package com.brazilsoccer.mcp.util;

import java.text.Normalizer;
import java.util.Locale;

/** Text helpers shared by the name normaliser, the loaders and the query services. */
public final class TextUtils {

    private TextUtils() {
    }

    /** Removes diacritics: {@code "São Paulo" -> "Sao Paulo"}, {@code "Grêmio" -> "Gremio"}. */
    public static String stripAccents(String input) {
        if (input == null) {
            return null;
        }
        String decomposed = Normalizer.normalize(input, Normalizer.Form.NFD);
        return decomposed.replaceAll("\\p{M}+", "");
    }

    /** Lower-cased, accent-free, single-spaced form used for loose comparisons. */
    public static String simplify(String input) {
        if (input == null) {
            return "";
        }
        return stripAccents(input)
                .toLowerCase(Locale.ROOT)
                .replaceAll("[^a-z0-9]+", " ")
                .trim();
    }

    /** True when {@code haystack} contains {@code needle}, ignoring case and accents. */
    public static boolean containsIgnoringAccents(String haystack, String needle) {
        return simplify(haystack).contains(simplify(needle));
    }

    /** Right-pads with spaces so that fixed width tables line up in the tool output. */
    public static String pad(String value, int width) {
        String text = value == null ? "" : value;
        if (text.length() >= width) {
            return text;
        }
        return text + " ".repeat(width - text.length());
    }

    /** Left-pads with spaces (used for numeric table columns). */
    public static String padLeft(String value, int width) {
        String text = value == null ? "" : value;
        if (text.length() >= width) {
            return text;
        }
        return " ".repeat(width - text.length()) + text;
    }

    public static String percent(double numerator, double denominator) {
        if (denominator == 0) {
            return "0.0%";
        }
        return String.format(Locale.ROOT, "%.1f%%", 100.0 * numerator / denominator);
    }

    public static String round(double value, int decimals) {
        return String.format(Locale.ROOT, "%." + decimals + "f", value);
    }
}
