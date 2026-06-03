/*
 * ============================================================================
 * TeamNames - team / text name normalisation utilities
 * ============================================================================
 * Context:
 *   The Kaggle datasets use inconsistent naming conventions for the same club:
 *     - With state suffix    : "Palmeiras-SP", "Flamengo-RJ", "America - MG"
 *     - With country code     : "Nacional (URU)", "Barcelona-EQU"
 *     - With parentheticals    : "Boavista Sport Club (antigo ...) - RJ"
 *     - Plain                 : "Palmeiras", "Sao Paulo"
 *   Text also contains Portuguese diacritics (Sao, Gremio, Avai) and cedillas.
 *
 *   Crucially, the state suffix is BOTH noise and signal:
 *     - Noise: one dataset writes "Palmeiras-SP", another "Palmeiras". The same
 *       club must unify across datasets.
 *     - Signal: "Atletico-MG" and "Atletico-PR" are *different* clubs that share
 *       a base name; dropping the state would merge them and corrupt standings.
 *
 *   So this class produces THREE forms from a raw name:
 *     - displayFull(): faithful cleaned name, suffix kept ("Atletico-MG").
 *     - fullKey()    : accent/case-folded identity WITH the state suffix; used to
 *       keep same-base clubs distinct (standings grouping).
 *     - baseKey()    : accent/case-folded identity WITHOUT the state suffix; used
 *       for cross-dataset matching, de-duplication and user search, where
 *       "Palmeiras" must find "Palmeiras-SP".
 *   normalize() is the shared accent/case folder reused for player fields too.
 * ============================================================================
 */
package com.brasilsoccer.mcp.util;

import java.text.Normalizer;
import java.util.regex.Pattern;

public final class TeamNames {

    // Trailing " - SP", "-SP", "- MG" style state / country qualifiers.
    private static final Pattern TRAILING_STATE = Pattern.compile("\\s*-\\s*[A-Za-z]{2,3}\\s*$");
    private static final Pattern PARENTHETICAL = Pattern.compile("\\([^)]*\\)");
    private static final Pattern DIACRITICS = Pattern.compile("\\p{InCombiningDiacriticalMarks}+");
    private static final Pattern MULTISPACE = Pattern.compile("\\s+");

    private TeamNames() {
    }

    /** Faithful, human-readable name: parentheticals removed, state suffix kept. */
    public static String displayFull(String raw) {
        if (raw == null) {
            return "";
        }
        String s = PARENTHETICAL.matcher(raw).replaceAll(" ");
        s = MULTISPACE.matcher(s).replaceAll(" ").trim();
        return s.isEmpty() ? raw.trim() : s;
    }

    /** Identity key that keeps the state suffix, so "Atletico-MG" != "Atletico-PR". */
    public static String fullKey(String raw) {
        return normalize(displayFull(raw));
    }

    /** Identity key without the state suffix, so "Palmeiras" == "Palmeiras-SP". */
    public static String baseKey(String raw) {
        String s = displayFull(raw);
        String prev;
        do {
            prev = s;
            s = TRAILING_STATE.matcher(s).replaceAll("");
        } while (!s.equals(prev));
        return normalize(s);
    }

    /**
     * Accent + case folding. "Sao Paulo" -> "sao paulo". Safe for arbitrary text
     * (nationalities, clubs, search terms).
     */
    public static String normalize(String raw) {
        if (raw == null) {
            return "";
        }
        String decomposed = Normalizer.normalize(raw, Normalizer.Form.NFD);
        String noAccents = DIACRITICS.matcher(decomposed).replaceAll("");
        return MULTISPACE.matcher(noAccents).replaceAll(" ").trim().toLowerCase();
    }
}
