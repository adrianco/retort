package com.braziliansoccer.mcp;

import java.util.Locale;

/** Canonicalizes Portuguese team and player text for tolerant cross-file matching. */
final class Normalizer {
    private Normalizer() {}
    static String key(String value) {
        if (value == null) return "";
        String text = java.text.Normalizer.normalize(value, java.text.Normalizer.Form.NFD).replaceAll("\\p{M}", "")
                .toLowerCase(Locale.ROOT).trim().replaceAll("\\s+", " ");
        text = text.replaceAll("\\s*-\\s*[a-z]{2}$", ""); // Palmeiras-SP / América - MG
        return text.replaceAll("[^a-z0-9 ]", "").replaceAll("\\s+", " ").trim()
                .replaceAll("^(sport club|clube atletico|esporte clube) ", "");
    }
    static boolean matches(String candidate, String query) {
        String a = key(candidate), b = key(query);
        return !b.isBlank() && (a.equals(b) || a.contains(b) || b.contains(a));
    }
}
