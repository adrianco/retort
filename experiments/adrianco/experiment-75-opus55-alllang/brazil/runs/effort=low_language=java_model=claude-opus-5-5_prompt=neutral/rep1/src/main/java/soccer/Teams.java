package soccer;

import java.text.Normalizer;
import java.util.Map;

/** Team-name normalization across datasets ("Palmeiras-SP", "Palmeiras", "América - MG", full names...). */
public final class Teams {
    private Teams() {}

    private static final Map<String, String> ALIASES = Map.ofEntries(
            Map.entry("sport club corinthians paulista", "corinthians"),
            Map.entry("sociedade esportiva palmeiras", "palmeiras"),
            Map.entry("clube de regatas do flamengo", "flamengo"),
            Map.entry("fluminense football club", "fluminense"),
            Map.entry("sao paulo futebol clube", "sao paulo"),
            Map.entry("sao paulo fc", "sao paulo"),
            Map.entry("santos fc", "santos"),
            Map.entry("athletico paranaense", "atletico-pr"),
            Map.entry("atletico paranaense", "atletico-pr"),
            Map.entry("atletico pr", "atletico-pr"),
            Map.entry("athletico pr", "atletico-pr"),
            Map.entry("atletico mineiro", "atletico-mg"),
            Map.entry("atletico mg", "atletico-mg"),
            Map.entry("atletico goianiense", "atletico-go"),
            Map.entry("atletico go", "atletico-go"),
            Map.entry("gremio", "gremio"),
            Map.entry("vasco da gama", "vasco"),
            Map.entry("cr vasco da gama", "vasco"),
            Map.entry("botafogo rj", "botafogo"),
            Map.entry("sport recife", "sport"),
            Map.entry("sport club do recife", "sport"),
            Map.entry("america mineiro", "america-mg"),
            Map.entry("america mg", "america-mg"),
            Map.entry("red bull bragantino", "bragantino"),
            Map.entry("rb bragantino", "bragantino"),
            Map.entry("abc", "abc"));

    public static String stripAccents(String s) {
        return Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}", "");
    }

    /** Canonical key used for matching. */
    public static String key(String raw) {
        if (raw == null) return "";
        String s = stripAccents(raw).trim();
        s = s.replaceAll("\\s*\\([^)]*\\)", "");            // parentheticals
        String lower = s.toLowerCase().replace('.', ' ').replaceAll("\\s+", " ").trim()
                .replace("athletico", "atletico");
        if (ALIASES.containsKey(lower)) return ALIASES.get(lower);
        // Keep state for clubs whose state disambiguates (Atletico-MG vs Atletico-PR, America-MG vs America-RN)
        java.util.regex.Matcher m = java.util.regex.Pattern.compile("^(.*?)(?:\\s*-\\s*|\\s+)([A-Za-z]{2})$").matcher(lower);
        if (m.matches() && isState(m.group(2))) {
            String base = m.group(1).trim();
            String withState = base + " " + m.group(2);
            if (ALIASES.containsKey(withState)) return ALIASES.get(withState);
            if (base.equals("atletico") || base.equals("america")) return base + "-" + m.group(2);
            lower = base;
        }
        return ALIASES.getOrDefault(lower, lower);
    }

    private static final java.util.Set<String> STATES = java.util.Set.of("ac","al","ap","am","ba","ce","df","es","go","ma","mt","ms","mg","pa","pb","pr","pe","pi","rj","rn","rs","ro","rr","sc","sp","se","to");

    static boolean isState(String s) { return STATES.contains(s.toLowerCase()); }

    /** True if a raw team name matches a user query (e.g. "Flamengo" matches "Flamengo-RJ"). */
    public static boolean matches(String raw, String query) {
        String k = key(raw), q = key(query);
        if (q.isEmpty()) return false;
        return k.equals(q) || k.startsWith(q + " ") || k.startsWith(q + "-");
    }

    /** Display name: strip state suffix/accents are kept. */
    public static String display(String raw) {
        String s = raw.replaceAll("\\s*-\\s*[A-Z]{2}$", "").trim();
        return s;
    }
}
