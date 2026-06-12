/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    TeamNames.java
 * Purpose: Normalizes the many team-name spellings found across the datasets so
 *          that "Palmeiras-SP", "Palmeiras" and "PALMEIRAS" all match. Provides
 *          a human-friendly display name (suffix stripped) and an accent- and
 *          case-insensitive canonical key for equality/matching.
 * Part of: model package (cross-cutting name handling used by loaders/queries).
 * ============================================================================
 */
package com.example.brsoccer.model;

import java.text.Normalizer;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Utilities for normalizing and comparing Brazilian club / team names. */
public final class TeamNames {

    // Trailing " (XXX)" parenthetical country/state code, e.g. "Nacional (URU)".
    private static final Pattern PARENS_SUFFIX = Pattern.compile("\\s*\\([A-Za-z]{2,4}\\)\\s*$");
    // Trailing "-SP" / " - MG" / "-EQU" style state or country code.
    private static final Pattern HYPHEN_SUFFIX = Pattern.compile("\\s*-\\s*[A-Za-z]{2,3}\\s*$");
    private static final Pattern MULTISPACE = Pattern.compile("\\s+");

    // Lower-cased forms used while building a canonical key.
    private static final Pattern PARENS_CODE = Pattern.compile("\\s*\\(([a-z]{2,4})\\)\\s*$");
    private static final Pattern HYPHEN_CODE = Pattern.compile("\\s*-\\s*([a-z]{2,3})\\s*$");

    /**
     * Base names shared by several distinct clubs, for which the state code is
     * significant and must be preserved to keep the clubs apart (e.g. Atlético
     * Mineiro vs Atlético Paranaense vs Atlético Goianiense).
     */
    private static final Set<String> AMBIGUOUS_BASES = Set.of("atletico", "america");

    /** Full-name regional adjectives that identify the club's state. */
    private static final Map<String, String> KEYWORD_STATE = Map.of(
            "mineiro", "mg",
            "paranaense", "pr",
            "goianiense", "go");

    private TeamNames() {
    }

    /** A cleaned, display-ready name with any trailing state/country suffix removed. */
    public static String displayName(String raw) {
        if (raw == null) {
            return "";
        }
        String s = raw.trim();
        s = PARENS_SUFFIX.matcher(s).replaceAll("");
        s = HYPHEN_SUFFIX.matcher(s).replaceAll("");
        s = MULTISPACE.matcher(s).replaceAll(" ").trim();
        return s.isEmpty() ? raw.trim() : s;
    }

    /**
     * A canonical identity key: accent-folded and lower-cased. State/country
     * suffixes are dropped so "Palmeiras-SP" matches "Palmeiras" -- except for
     * base names shared by several clubs (see {@link #AMBIGUOUS_BASES}), where
     * the state is retained so the clubs stay distinct. Hyphen ("Atletico-MG")
     * and full-name ("Atletico Mineiro") spellings of the same club collapse to
     * the same key.
     */
    public static String canonicalKey(String raw) {
        if (raw == null) {
            return "";
        }
        // Fold accents, lower-case, unify the Athletico/Atletico spelling.
        String s = Normalizer.normalize(raw.trim(), Normalizer.Form.NFD)
                .replaceAll("\\p{InCombiningDiacriticalMarks}+", "")
                .toLowerCase();
        s = MULTISPACE.matcher(s).replaceAll(" ").trim();
        s = s.replace("athletico", "atletico");

        // Extract a state/country code from a trailing suffix if present.
        String state = null;
        Matcher parens = PARENS_CODE.matcher(s);
        if (parens.find()) {
            state = parens.group(1);
            s = parens.replaceAll("");
        } else {
            Matcher hyphen = HYPHEN_CODE.matcher(s);
            if (hyphen.find()) {
                state = hyphen.group(1);
                s = hyphen.replaceAll("");
            }
        }

        // Otherwise infer the state from a regional adjective and remove it.
        if (state == null) {
            for (Map.Entry<String, String> e : KEYWORD_STATE.entrySet()) {
                if (s.contains(e.getKey())) {
                    state = e.getValue();
                    s = s.replace(e.getKey(), "");
                    break;
                }
            }
        }

        String base = MULTISPACE.matcher(s).replaceAll(" ").trim();
        if (AMBIGUOUS_BASES.contains(base) && state != null) {
            return base + "-" + state;
        }
        return base;
    }

    /** True when two raw names refer to the same team after normalization. */
    public static boolean matches(String a, String b) {
        return canonicalKey(a).equals(canonicalKey(b));
    }
}
