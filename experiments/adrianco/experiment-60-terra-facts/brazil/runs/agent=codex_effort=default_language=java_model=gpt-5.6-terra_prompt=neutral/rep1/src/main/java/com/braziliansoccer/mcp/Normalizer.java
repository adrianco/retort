package com.braziliansoccer.mcp;

import java.util.Locale;
import java.util.Map;

/** Canonicalizes Portuguese team and player text for tolerant cross-file matching. */
final class Normalizer {
    /*
     * These are identity aliases, not display aliases.  State suffixes are normally
     * deliberately ignored so that Palmeiras and Palmeiras-SP match, but that rule
     * would turn Atletico-MG and Atletico-PR into the same club.  Keep the two
     * ambiguous Atletico identities distinct and collapse the historical spelling
     * change from Atletico to Athletico for the Parana club.
     */
    private static final Map<String, String> TEAM_ALIASES = Map.ofEntries(
            Map.entry("atletico pr", "atletico paranaense"),
            Map.entry("athletico pr", "atletico paranaense"),
            Map.entry("atletico paranaense", "atletico paranaense"),
            Map.entry("athletico paranaense", "atletico paranaense"),
            Map.entry("atletico mg", "atletico mineiro"),
            Map.entry("atletico mineiro", "atletico mineiro"),
            Map.entry("vasco", "vasco da gama"),
            Map.entry("vasco da gama", "vasco da gama")
    );

    private Normalizer() {}
    static String key(String value) {
        if (value == null) return "";
        String text = java.text.Normalizer.normalize(value, java.text.Normalizer.Form.NFD).replaceAll("\\p{M}", "")
                .toLowerCase(Locale.ROOT).trim();
        String withState = text.replaceAll("[^a-z0-9]+", " ").replaceAll("\\s+", " ").trim();
        String alias = TEAM_ALIASES.get(withState);
        if (alias != null) return alias;
        return withState.replaceAll("\\s+[a-z]{2}$", "") // Palmeiras-SP / América - MG
                .replaceAll("^(sport club|clube atletico|esporte clube) ", "");
    }
    static boolean matches(String candidate, String query) {
        String a = key(candidate), b = key(query);
        return !b.isBlank() && (a.equals(b) || a.contains(b) || b.contains(a));
    }
}
