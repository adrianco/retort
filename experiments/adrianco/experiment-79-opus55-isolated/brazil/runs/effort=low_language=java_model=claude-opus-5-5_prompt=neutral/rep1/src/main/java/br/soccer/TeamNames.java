package br.soccer;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Normalizes the team naming conventions used across the datasets ("Palmeiras-SP", "Sao Paulo",
 * "São Paulo - SP", "Sport Club Corinthians Paulista", ...) to one canonical key per club.
 */
public final class TeamNames {
    private TeamNames() {}

    private static final Set<String> STATES = Set.of(
            "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa",
            "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to");

    /** Names where the state suffix distinguishes a club from a better-known namesake. */
    private static final Set<String> KEEP_STATE = Set.of(
            "botafogo sp", "botafogo pb", "america rn", "santos ap", "bragantino pa",
            "santa cruz rn", "atletico ac", "fluminense pi", "vitoria es", "nacional am");

    private static final Set<String> AMBIGUOUS = Set.of("atletico", "america", "nacional");

    private static final Set<String> AFFIXES = Set.of("fc", "ec", "sc");

    private static final Map<String, String> ALIASES = new HashMap<>();
    private static final Map<String, String> DISPLAY = new HashMap<>();

    private static void alias(String canonical, String... variants) {
        for (String v : variants) ALIASES.put(v, canonical);
    }

    static {
        alias("atletico mineiro", "atletico mg", "galo");
        alias("athletico paranaense", "atletico pr", "athletico pr", "atletico paranaense",
                "athletico", "club athletico paranaense");
        alias("atletico goianiense", "atletico go");
        alias("america mineiro", "america mg", "america fc minas gerais");
        alias("vasco", "vasco da gama", "cr vasco da gama");
        alias("sport", "sport recife", "sport club do recife");
        alias("nautico", "nautico capibaribe");
        alias("bragantino", "red bull bragantino", "rb bragantino");
        alias("remo", "clube do remo");
        alias("portuguesa", "portuguesa desportos");
        alias("csa", "cs alagoano");
        alias("brasil de pelotas", "brasil");
        alias("confianca", "ad confianca");
        alias("gama", "se gama");
        alias("boavista", "boavista sport club", "boavista sc saquarema");
        alias("ceara", "ceara sporting club");
        alias("macae", "macae esporte");
        alias("moto club", "moto clube", "moto club de sao luis");
        alias("novorizontino", "gremio novorizontino");
        alias("corinthians", "sport club corinthians paulista", "corinthians paulista");
        alias("flamengo", "cr flamengo", "clube de regatas do flamengo");
        alias("palmeiras", "se palmeiras", "sociedade esportiva palmeiras");
        alias("internacional", "sc internacional", "inter");
        alias("gremio", "gremio fbpa");
        alias("fortaleza", "fortaleza esporte clube");
        alias("sao paulo", "sao paulo futebol clube", "spfc");
        alias("botafogo", "botafogo rj");

        String[][] display = {
            {"sao paulo", "São Paulo"}, {"gremio", "Grêmio"}, {"atletico mineiro", "Atlético Mineiro"},
            {"athletico paranaense", "Athletico Paranaense"}, {"atletico goianiense", "Atlético Goianiense"},
            {"america mineiro", "América Mineiro"}, {"america rn", "América-RN"}, {"goias", "Goiás"},
            {"ceara", "Ceará"}, {"avai", "Avaí"}, {"vitoria", "Vitória"}, {"criciuma", "Criciúma"},
            {"cuiaba", "Cuiabá"}, {"parana", "Paraná"}, {"nautico", "Náutico"}, {"csa", "CSA"},
            {"crb", "CRB"}, {"abc", "ABC"}, {"asa", "ASA"}, {"botafogo sp", "Botafogo-SP"},
            {"botafogo pb", "Botafogo-PB"}, {"confianca", "Confiança"}, {"sao caetano", "São Caetano"},
            {"santo andre", "Santo André"}, {"gremio prudente", "Grêmio Prudente"},
            {"operario", "Operário"}, {"macae", "Macaé"}, {"sao bento", "São Bento"},
        };
        for (String[] d : display) DISPLAY.put(d[0], d[1]);
    }

    /** Lower-cases, strips accents and collapses punctuation to single spaces. */
    public static String fold(String s) {
        if (s == null) return "";
        String n = Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}", "");
        return n.toLowerCase().replaceAll("[^a-z0-9]+", " ").trim();
    }

    /** Canonical key for a raw team name from any dataset or user query. */
    public static String canonical(String raw) {
        if (raw == null) return "";
        String s = fold(raw.replaceAll("(?i)\\(antigo[^)]*\\)", " "));
        // Spelled-out initials: "A.s.a." -> "asa", "C.R.B." -> "crb".
        if (s.matches("[a-z]( [a-z])+( [a-z]{2})?")) {
            s = s.replaceAll("\\b([a-z]) (?=[a-z]\\b)", "$1");
        }
        String a = ALIASES.get(s);
        if (a != null) return a;

        List<String> tokens = new ArrayList<>(Arrays.asList(s.split(" ")));
        if (tokens.size() > 1 && STATES.contains(tokens.get(tokens.size() - 1))) {
            if (KEEP_STATE.contains(s)) return s;
            // Several unrelated clubs share these names, so the state is what identifies them.
            if (tokens.size() == 2 && AMBIGUOUS.contains(tokens.get(0))) return s;
            tokens.remove(tokens.size() - 1);
            s = String.join(" ", tokens);
            a = ALIASES.get(s);
            if (a != null) return a;
        }
        while (tokens.size() > 1 && AFFIXES.contains(tokens.get(tokens.size() - 1))) {
            tokens.remove(tokens.size() - 1);
        }
        while (tokens.size() > 1 && AFFIXES.contains(tokens.get(0))) tokens.remove(0);
        s = String.join(" ", tokens);
        a = ALIASES.get(s);
        return a != null ? a : s;
    }

    /** Human-readable name for a canonical key. */
    public static String display(String key) {
        String d = DISPLAY.get(key);
        if (d != null) return d;
        StringBuilder b = new StringBuilder();
        for (String t : key.split(" ")) {
            if (t.isEmpty()) continue;
            if (b.length() > 0) b.append(' ');
            boolean upper = t.length() == 3 && Set.of("uru", "par", "equ", "per", "ven").contains(t);
            if (upper || STATES.contains(t) && b.length() > 0) {
                b.append(t.toUpperCase());
            } else if (Set.of("de", "do", "da", "del").contains(t) && b.length() > 0) {
                b.append(t);
            } else {
                b.append(Character.toUpperCase(t.charAt(0))).append(t.substring(1));
            }
        }
        return b.toString();
    }
}
