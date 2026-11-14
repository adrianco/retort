package br.soccer.mcp;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Normalises the many team-name spellings found in the datasets to one canonical key per club.
 *
 * <p>A raw name is split into a base ("sao paulo") and an optional Brazilian state ("SP"):
 * "Palmeiras-SP", "Palmeiras - SP", "Palmeiras SP" and "Palmeiras" all give base "palmeiras".
 * The state is kept in the key only where it is needed to tell clubs apart
 * ("atletico-mg" vs "atletico-pr", "flamengo" (RJ) vs "flamengo-pi").
 */
final class TeamNames {
    private static final Set<String> UFS = Set.of("AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT",
            "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO");
    private static final Pattern STATE_SUFFIX = Pattern.compile("^(.*?)[\\s\\-/]+([A-Za-z]{2})$");
    private static final Pattern COUNTRY_SUFFIX = Pattern.compile("^(.*?)\\s*(?:-\\s*([A-Z]{3})|\\(([A-Z]{3})\\))$");
    private static final Set<String> NOISE = Set.of("ec", "fc", "sc", "ac", "se", "esporte clube", "futebol clube");

    /** alias base -> {base, default state or null}. Keys are accent-free lower case. */
    private static final Map<String, String[]> ALIASES = new HashMap<>();
    private static final Map<String, String> DISPLAY_OVERRIDES = Map.of(
            "atletico-pr", "Athletico-PR", "csa", "CSA", "crb", "CRB", "abc", "ABC", "asa", "ASA");

    private static void alias(String base, String state, String... names) {
        for (String n : names) ALIASES.put(n, new String[] {base, state});
    }

    static {
        alias("atletico", "MG", "atletico mineiro", "clube atletico mineiro", "galo");
        alias("atletico", "PR", "atletico paranaense", "athletico paranaense", "athletico", "club athletico paranaense");
        alias("atletico", "GO", "atletico goianiense");
        alias("america", "MG", "america mineiro", "america fc (minas gerais)", "america fc minas gerais");
        alias("vasco", null, "vasco da gama", "cr vasco da gama");
        alias("sport", null, "sport recife", "sport club do recife");
        alias("nautico", null, "nautico capibaribe");
        alias("bragantino", "SP", "red bull bragantino", "rb bragantino");
        alias("portuguesa", null, "portuguesa desportos", "portuguesa de desportos");
        alias("corinthians", null, "sport club corinthians paulista", "corinthians paulista");
        alias("remo", null, "clube do remo");
        alias("ceara", null, "ceara sporting club");
        alias("flamengo", "PI", "flamengo do piaui");
        alias("flamengo", null, "clube de regatas do flamengo", "cr flamengo");
        alias("gremio", null, "gremio foot-ball porto alegrense", "gremio fbpa");
        alias("internacional", null, "sport club internacional", "inter de porto alegre");
        alias("palmeiras", null, "sociedade esportiva palmeiras");
        alias("santos", null, "santos futebol clube");
        alias("fluminense", null, "fluminense football club");
        alias("botafogo", null, "botafogo de futebol e regatas");
        alias("cruzeiro", null, "cruzeiro esporte clube");
        alias("bahia", null, "esporte clube bahia");
        alias("vitoria", null, "esporte clube vitoria");
        alias("chapecoense", null, "associacao chapecoense de futebol");
        alias("parana", null, "parana clube");
        alias("santa cruz", null, "santa cruz futebol clube");
    }

    private record Parsed(String base, String state, String displayBase) {}

    private final Map<String, Set<String>> serieAStates = new HashMap<>();
    private final Map<String, Set<String>> allStates = new HashMap<>();
    private final Map<String, String> display = new HashMap<>();
    private final Map<String, Integer> displayScore = new HashMap<>();
    private final Set<String> known = new TreeSet<>();
    private final Map<String, String> cache = new HashMap<>();

    /** Strips accents, lower-cases and collapses whitespace. */
    static String fold(String s) {
        if (s == null) return "";
        String t = Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}+", "");
        return t.toLowerCase().replace('.', ' ').replaceAll("\\s+", " ").trim();
    }

    private static Parsed parse(String raw) {
        String s = raw == null ? "" : raw.trim().replaceAll("\\s+", " ");
        // drop explanatory parentheses such as "(antigo Esporte Clube Barreira)", but keep "(URU)" / "(Minas Gerais)"
        s = s.replaceAll("\\s*\\(antigo[^)]*\\)", "").trim();
        String state = null;
        Matcher c = COUNTRY_SUFFIX.matcher(s);
        if (c.matches() && !c.group(1).isBlank()) {
            // foreign clubs: "Nacional (URU)" and "Nacional-URU" -> "nacional (uru)"
            String country = c.group(2) != null ? c.group(2) : c.group(3);
            String b = c.group(1).trim();
            return new Parsed(fold(b) + " (" + country.toLowerCase() + ")", null, b + " (" + country + ")");
        }
        Matcher m = STATE_SUFFIX.matcher(s);
        if (m.matches() && UFS.contains(m.group(2).toUpperCase()) && !m.group(1).isBlank()
                && (m.group(2).equals(m.group(2).toUpperCase()) || s.contains("-"))) {
            state = m.group(2).toUpperCase();
            s = m.group(1).trim();
        }
        String displayBase = s;
        String base = fold(s);
        String[] al = ALIASES.get(base);
        if (al == null) {
            base = stripNoise(base);
            al = ALIASES.get(base);
        }
        if (al != null) {
            base = al[0];
            if (state == null) state = al[1];
        }
        return new Parsed(base, state, displayBase);
    }

    private static String stripNoise(String base) {
        String b = base;
        boolean changed = true;
        while (changed) {
            changed = false;
            for (String n : NOISE) {
                if (b.startsWith(n + " ") && b.length() > n.length() + 1) { b = b.substring(n.length() + 1); changed = true; }
                if (b.endsWith(" " + n) && b.length() > n.length() + 1) { b = b.substring(0, b.length() - n.length() - 1); changed = true; }
            }
        }
        return b;
    }

    /** Phase 1: record a raw name seen in the data. {@code serieA} marks names from top-flight files. */
    void register(String raw, boolean serieA) {
        Parsed p = parse(raw);
        if (p.state != null) {
            allStates.computeIfAbsent(p.base, k -> new HashSet<>()).add(p.state);
            if (serieA) serieAStates.computeIfAbsent(p.base, k -> new HashSet<>()).add(p.state);
        }
        cache.clear();
    }

    /** Phase 2: canonical key for a raw name; also records it as a known team with a display name. */
    String canonicalAndRecord(String raw) {
        Parsed p = parse(raw);
        String key = key(p);
        known.add(key);
        int score = Normalizer.normalize(p.displayBase, Normalizer.Form.NFD).equals(p.displayBase) ? 1 : 2; // prefer accented spellings
        if (score > displayScore.getOrDefault(key, 0)) {
            displayScore.put(key, score);
            display.put(key, p.displayBase);
        }
        return key;
    }

    /** Canonical key for any name (data or user query). Does not need to be a known team. */
    String canonical(String raw) {
        return cache.computeIfAbsent(raw == null ? "" : raw, r -> key(parse(r)));
    }

    private String key(Parsed p) {
        if (p.state == null) return p.base;
        Set<String> top = serieAStates.getOrDefault(p.base, Set.of());
        if (top.size() == 1) return top.contains(p.state) ? p.base : p.base + "-" + p.state.toLowerCase();
        if (top.size() > 1) return p.base + "-" + p.state.toLowerCase();
        // never in Serie A: the state only matters if several states share the base name
        return allStates.getOrDefault(p.base, Set.of()).size() > 1 ? p.base + "-" + p.state.toLowerCase() : p.base;
    }

    boolean isKnown(String key) { return known.contains(key); }

    Set<String> knownTeams() { return known; }

    /** Human-readable name for a canonical key, e.g. "São Paulo", "Atlético-MG". */
    String display(String key) {
        String o = DISPLAY_OVERRIDES.get(key);
        if (o != null) return o;
        String d = display.get(key);
        if (d == null) return key;
        int dash = key.lastIndexOf('-');
        if (dash > 0 && key.length() - dash == 3 && UFS.contains(key.substring(dash + 1).toUpperCase())
                && !fold(d).endsWith(key.substring(dash))) {
            return d + "-" + key.substring(dash + 1).toUpperCase();
        }
        return d;
    }

    /**
     * Resolves a user-supplied team name to known canonical keys. An exact canonical match wins;
     * otherwise every known team whose name contains all the query words is returned
     * (so "Atlético" matches Atlético-MG, Atlético-GO, ...).
     */
    List<String> resolve(String query) {
        String key = canonical(query);
        if (known.contains(key)) return List.of(key);
        Set<String> out = new LinkedHashSet<>();
        List<String> q = tokens(key);
        if (q.isEmpty()) return List.of();
        for (String k : known) {
            if (new HashSet<>(tokens(k)).containsAll(q)) out.add(k);
        }
        if (out.isEmpty()) {
            for (String k : known) if (k.contains(key)) out.add(k);
        }
        return new ArrayList<>(out);
    }

    private static List<String> tokens(String s) {
        List<String> t = new ArrayList<>(Arrays.asList(s.split("[^a-z0-9]+")));
        t.removeIf(String::isEmpty);
        return t;
    }
}
