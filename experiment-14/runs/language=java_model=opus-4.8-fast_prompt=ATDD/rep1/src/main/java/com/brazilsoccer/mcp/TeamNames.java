package com.brazilsoccer.mcp;

import java.text.Normalizer;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Team-name normalization.
 *
 * <p>The datasets spell the same club in many ways: "Palmeiras-SP", "Palmeiras",
 * "São Paulo" vs "Sao Paulo", "Nacional (URU)", "América - MG". To match and
 * aggregate consistently we reduce a raw name to two keys:
 *
 * <ul>
 *   <li>{@link #matchKey} — accent/case-insensitive base name with any state or
 *       country suffix removed. Used for fuzzy user-facing search.</li>
 *   <li>{@link #identityKey} — the base name plus the team's state/country code,
 *       so that Atlético-MG, Atlético-PR and Atlético-GO remain distinct clubs.</li>
 * </ul>
 */
public final class TeamNames {

    /** A separator (space or dash) followed by a 2-3 letter UPPERCASE code at the end. */
    private static final Pattern SUFFIX = Pattern.compile("[\\s-]+([A-Z]{2,3})\\s*$");
    private static final Pattern PARENS = Pattern.compile("\\s*\\([^)]*\\)\\s*");
    private static final Pattern DIACRITICS = Pattern.compile("\\p{M}+");
    private static final Pattern WHITESPACE = Pattern.compile("\\s+");

    private TeamNames() {
    }

    /** Accent/case-insensitive base name with any state/country suffix stripped. */
    public static String matchKey(String rawName) {
        return parse(rawName, null).base;
    }

    /** Base name combined with the team's state/country code (if any). */
    public static String identityKey(String rawName, String stateColumn) {
        Parsed p = parse(rawName, stateColumn);
        return p.state.isEmpty() ? p.base : p.base + "-" + p.state;
    }

    static Parsed parse(String rawName, String stateColumn) {
        String cleaned = PARENS.matcher(nullToEmpty(rawName)).replaceAll(" ").trim();

        String state = "";
        Matcher m = SUFFIX.matcher(cleaned);
        if (m.find()) {
            state = normalize(m.group(1));
            cleaned = cleaned.substring(0, m.start()).trim();
        }

        String base = normalize(cleaned);

        if (state.isEmpty() && stateColumn != null) {
            String s = normalize(stateColumn);
            if (!s.isEmpty() && !s.equals("na")) {
                state = s;
            }
        }
        return new Parsed(base, state);
    }

    /** Lower-cases, strips accents and collapses whitespace. */
    static String normalize(String value) {
        String decomposed = Normalizer.normalize(nullToEmpty(value), Normalizer.Form.NFD);
        String noAccents = DIACRITICS.matcher(decomposed).replaceAll("");
        String collapsed = WHITESPACE.matcher(noAccents).replaceAll(" ").trim();
        return collapsed.toLowerCase(Locale.ROOT);
    }

    private static String nullToEmpty(String s) {
        return s == null ? "" : s;
    }

    static final class Parsed {
        final String base;
        final String state;

        Parsed(String base, String state) {
            this.base = base;
            this.state = state;
        }
    }
}
