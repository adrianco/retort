/*
 * ============================================================================
 *  Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 *  File    : TeamNames.java
 *  Purpose : Normalize the many spellings of Brazilian club names so that the
 *            same club matches across datasets.
 *
 *  Context : The datasets disagree on naming. The same club can appear as
 *            "Palmeiras-SP", "Palmeiras", "Sao Paulo", "São Paulo-SP",
 *            "Nacional (URU)" etc. To answer "all Flamengo matches" or a
 *            head-to-head we reduce every raw name to a canonical key:
 *              - strip a trailing state/country suffix ("-SP", " - RJ",
 *                "(URU)", "(EQU)")
 *              - drop accents/diacritics (São -> sao)
 *              - lower-case and collapse whitespace/punctuation
 *            A small alias table folds well-known full/legal names onto their
 *            common short form. The original display name is preserved
 *            elsewhere; this class only produces the matching key plus a tidy
 *            display label.
 *
 *  Used by : KnowledgeGraph, QueryService
 * ============================================================================
 */
package com.brasileirao.mcp.util;

import java.text.Normalizer;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Utilities for canonicalizing club names across the heterogeneous datasets. */
public final class TeamNames {

    private TeamNames() {
    }

    // Trailing "-SP", " - RJ", " (URU)", " (EQU)" hyphen/paren location suffix,
    // capturing the 2-3 letter state/country code.
    private static final Pattern STATE_SUFFIX =
            Pattern.compile("\\s*[-(]\\s*([A-Za-z]{2,3})\\s*\\)?\\s*$");
    // Trailing space-separated 2-letter state code, e.g. "America MG", "Americano RJ".
    private static final Pattern SPACE_STATE_SUFFIX =
            Pattern.compile("\\s+([A-Z]{2})$");
    private static final Pattern NON_ALNUM = Pattern.compile("[^a-z0-9]+");

    // Base names shared by multiple clubs: the state/country code must be kept
    // to tell them apart (Atlético-MG vs Atlético-PR vs Atlético-GO, etc.).
    private static final Set<String> AMBIGUOUS_BASES =
            Set.of("atletico", "athletico", "america", "nacional", "barcelona", "san lorenzo");

    /** Common legal/long names folded onto their short, canonical key. */
    private static final Map<String, String> ALIASES = Map.ofEntries(
            Map.entry("sport club corinthians paulista", "corinthians"),
            Map.entry("sociedade esportiva palmeiras", "palmeiras"),
            Map.entry("clube de regatas do flamengo", "flamengo"),
            Map.entry("fluminense football club", "fluminense"),
            Map.entry("sao paulo futebol clube", "sao paulo"),
            Map.entry("santos futebol clube", "santos"),
            Map.entry("gremio foot ball porto alegrense", "gremio"),
            Map.entry("sport club internacional", "internacional"),
            Map.entry("cruzeiro esporte clube", "cruzeiro"),
            // The three Atléticos and the two Américas, mapped to base+state keys.
            Map.entry("clube atletico mineiro", "atletico mg"),
            Map.entry("atletico mineiro", "atletico mg"),
            Map.entry("atletico paranaense", "atletico pr"),
            Map.entry("athletico paranaense", "atletico pr"),
            Map.entry("athletico", "atletico pr"),
            Map.entry("atletico goianiense", "atletico go"),
            Map.entry("america mineiro", "america mg"),
            Map.entry("america fc natal", "america rn"),
            Map.entry("vasco da gama", "vasco"),
            Map.entry("club de regatas vasco da gama", "vasco"),
            Map.entry("botafogo de futebol e regatas", "botafogo"),
            Map.entry("fortaleza esporte clube", "fortaleza"),
            Map.entry("red bull bragantino", "bragantino"));

    /**
     * Produce a canonical matching key for a raw team name.
     * Returns an empty string for null/blank input.
     */
    public static String canonical(String raw) {
        if (raw == null) {
            return "";
        }
        String s = raw.trim();
        if (s.isEmpty()) {
            return "";
        }

        // Pull off a trailing state/country suffix, remembering its code so we
        // can re-attach it for ambiguous base names.
        String code = null;
        boolean changed = true;
        while (changed) {
            changed = false;
            Matcher m1 = STATE_SUFFIX.matcher(s);
            if (m1.find()) {
                code = m1.group(1);
                s = s.substring(0, m1.start()).trim();
                changed = true;
                continue;
            }
            Matcher m2 = SPACE_STATE_SUFFIX.matcher(s);
            if (m2.find()) {
                code = m2.group(1);
                s = s.substring(0, m2.start()).trim();
                changed = true;
            }
        }

        String base = stripAccents(s).toLowerCase();
        base = NON_ALNUM.matcher(base).replaceAll(" ").trim().replaceAll("\\s+", " ");

        if (ALIASES.containsKey(base)) {
            return ALIASES.get(base);
        }
        // Keep the state code for clubs that share a base name.
        if (code != null && AMBIGUOUS_BASES.contains(base)) {
            String withCode = base + " " + code.toLowerCase();
            return ALIASES.getOrDefault(withCode, withCode);
        }
        return base;
    }

    /**
     * A clean, human-friendly label. The state suffix is dropped for unambiguous
     * clubs ("Palmeiras-SP" -> "Palmeiras") but kept when it is needed to tell
     * clubs apart ("Atletico-MG" stays "Atletico-MG").
     */
    public static String display(String raw) {
        if (raw == null) {
            return "";
        }
        String s = raw.trim();
        Matcher m = STATE_SUFFIX.matcher(s);
        if (m.find()) {
            String base = stripAccents(s.substring(0, m.start()).trim()).toLowerCase();
            base = NON_ALNUM.matcher(base).replaceAll(" ").trim();
            if (!AMBIGUOUS_BASES.contains(base)) {
                return s.substring(0, m.start()).trim();
            }
        }
        return s;
    }

    /** True if both raw names refer to the same canonical club. */
    public static boolean sameTeam(String a, String b) {
        String ca = canonical(a);
        return !ca.isEmpty() && ca.equals(canonical(b));
    }

    /** Remove diacritics: "São" -> "Sao", "Grêmio" -> "Gremio". */
    public static String stripAccents(String s) {
        String normalized = Normalizer.normalize(s, Normalizer.Form.NFD);
        return normalized.replaceAll("\\p{InCombiningDiacriticalMarks}+", "");
    }
}
