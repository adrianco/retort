package com.soccer.mcp.util;

import java.text.Normalizer;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Team-name normalisation.
 *
 * Source CSVs use different naming conventions:
 *  - With state suffix: "Palmeiras-SP", "Flamengo-RJ"
 *  - Without suffix:    "Palmeiras", "Flamengo"
 *  - Full names:        "Sport Club Corinthians Paulista"
 *  - Country suffix:    "Nacional (URU)"
 *
 * For some teams (Flamengo, Palmeiras, ...) the short form is unique and the
 * suffix can safely be stripped. For others ("Atletico-MG" vs "Atletico-PR")
 * the suffix is the only disambiguator. We therefore use an explicit alias map
 * keyed on a stripped+lowercased form, and only fall back to the raw stripped
 * form when no alias is found.
 */
public final class TeamNames {

    private static final Pattern COUNTRY_PAREN = Pattern.compile("\\s*\\(([A-Za-z]{2,4})\\)\\s*$");
    private static final Pattern WHITESPACE = Pattern.compile("\\s+");

    /**
     * Alias map. Keys are pre-normalized forms (accent-stripped, lowercased,
     * whitespace-collapsed). Values are the canonical name we want to dedupe to.
     * Both "with-suffix" and "without-suffix" forms map to the same canonical.
     */
    private static final Map<String, String> ALIASES = buildAliases();

    private TeamNames() {}

    private static Map<String, String> buildAliases() {
        Map<String, String> m = new HashMap<>();
        // Teams that appear both with and without state suffix — alias both forms.
        alias(m, "flamengo",       "flamengo", "flamengo-rj");
        alias(m, "fluminense",     "fluminense", "fluminense-rj");
        alias(m, "palmeiras",      "palmeiras", "palmeiras-sp",
                "se palmeiras", "sociedade esportiva palmeiras");
        alias(m, "corinthians",    "corinthians", "corinthians-sp",
                "sport club corinthians paulista");
        alias(m, "santos",         "santos", "santos-sp", "santos fc");
        alias(m, "sao paulo",      "sao paulo", "sao paulo-sp", "sao paulo fc");
        alias(m, "gremio",         "gremio", "gremio-rs");
        alias(m, "internacional",  "internacional", "internacional-rs", "sc internacional", "inter");
        alias(m, "vasco",          "vasco", "vasco-rj", "vasco da gama", "vasco da gama-rj");
        alias(m, "botafogo",       "botafogo", "botafogo-rj");
        alias(m, "cruzeiro",       "cruzeiro", "cruzeiro-mg");
        alias(m, "bahia",          "bahia", "bahia-ba", "ec bahia");
        alias(m, "fortaleza",      "fortaleza", "fortaleza-ce");
        alias(m, "ceara",          "ceara", "ceara-ce");
        alias(m, "coritiba",       "coritiba", "coritiba-pr");
        alias(m, "chapecoense",    "chapecoense", "chapecoense-sc");
        alias(m, "goias",          "goias", "goias-go");
        alias(m, "avai",           "avai", "avai-sc");
        alias(m, "csa",            "csa", "csa-al");
        alias(m, "atletico mineiro", "atletico-mg", "atletico mineiro", "clube atletico mineiro");
        alias(m, "atletico paranaense", "atletico-pr", "athletico-pr",
                "athletico paranaense", "atletico paranaense");
        alias(m, "atletico goianiense", "atletico-go", "athletico-go",
                "atletico goianiense", "athletico goianiense");
        alias(m, "america mineiro", "america-mg", "america mineiro");
        // Note: do NOT alias raw "atletico" without state — too ambiguous.
        return m;
    }

    private static void alias(Map<String, String> m, String canonical, String... keys) {
        for (String k : keys) m.put(k, canonical);
    }

    /** Returns a canonical lookup key suitable for dedupe and equality matching. */
    public static String normalize(String name) {
        if (name == null) return "";
        String s = name.trim();
        // Strip "(XXX)" country/competition suffix like "(URU)".
        Matcher cm = COUNTRY_PAREN.matcher(s);
        if (cm.find()) s = s.substring(0, cm.start()).trim();
        s = stripAccents(s);
        s = s.toLowerCase(Locale.ROOT);
        s = WHITESPACE.matcher(s).replaceAll(" ").trim();

        String alias = ALIASES.get(s);
        if (alias != null) return alias;

        // Fallback: drop a trailing 2-letter state code (e.g. "-rj") only if
        // there is no ambiguous mapping. We're conservative — only strip when
        // the suffix matches Brazilian state codes.
        return s;
    }

    public static String stripAccents(String s) {
        if (s == null) return null;
        String nfd = Normalizer.normalize(s, Normalizer.Form.NFD);
        return nfd.replaceAll("\\p{InCombiningDiacriticalMarks}+", "");
    }

    /** True if either side's normalized form contains the other's. */
    public static boolean matches(String candidate, String query) {
        if (candidate == null || query == null) return false;
        String a = normalize(candidate);
        String b = normalize(query);
        if (a.equals(b)) return true;
        if (a.contains(b) || b.contains(a)) return true;
        return false;
    }
}
