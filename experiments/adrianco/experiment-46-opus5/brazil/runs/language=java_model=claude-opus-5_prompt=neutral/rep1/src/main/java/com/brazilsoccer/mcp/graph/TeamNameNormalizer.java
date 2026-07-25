package com.brazilsoccer.mcp.graph;

import com.brazilsoccer.mcp.util.TextUtils;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Turns the 700+ raw club spellings found across the CSV files into a canonical
 * {@code (base name, state)} pair.
 *
 * <p>The datasets write the same club as {@code "Atlético-MG"}, {@code "Atletico Mineiro"},
 * {@code "Atlético - MG"} and {@code "Atletico Mineiro - MG"}, while at the same time using
 * {@code "Atlético-PR"} and {@code "Atlético-GO"} for two completely different clubs. The
 * normaliser therefore:
 *
 * <ol>
 *   <li>removes accents, punctuation and parenthetical remarks;</li>
 *   <li>peels off a trailing state (UF) or country code and keeps it as a separate field;</li>
 *   <li>drops legal-form noise words ("Esporte Clube", "FC", "SC", "do", "de", ...);</li>
 *   <li>applies a curated alias table for the clubs whose popular name differs from their
 *       formal name ("Athletico Paranaense" &rarr; {@code atletico/PR}).</li>
 * </ol>
 *
 * <p>The state is kept rather than discarded so that {@link TeamRegistry} can decide, from the
 * data itself, whether a base name is ambiguous (Atlético, Botafogo, América...) and therefore
 * needs the state as part of the node id.
 */
public final class TeamNameNormalizer {

    /** Result of normalising one raw team name. */
    public record NormalizedName(String base, String state, String display) {
    }

    private static final Pattern PARENTHESES = Pattern.compile("\\(([^)]*)\\)");

    /** Brazilian federative units. */
    static final Set<String> STATES = Set.of(
            "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa",
            "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to");

    /** Country codes used by the Libertadores file for non Brazilian clubs. */
    static final Set<String> COUNTRIES = Set.of(
            "uru", "par", "equ", "ecu", "per", "ven", "arg", "chi", "col", "bol", "mex", "bra");

    private static final Map<String, String> STATE_NAMES = Map.ofEntries(
            Map.entry("minas gerais", "MG"), Map.entry("rio de janeiro", "RJ"),
            Map.entry("sao paulo", "SP"), Map.entry("rio grande do sul", "RS"),
            Map.entry("santa catarina", "SC"), Map.entry("parana", "PR"),
            Map.entry("bahia", "BA"), Map.entry("pernambuco", "PE"),
            Map.entry("ceara", "CE"), Map.entry("goias", "GO"));

    /** Legal form / filler tokens that carry no identity. */
    private static final Set<String> NOISE_TOKENS = new HashSet<>(Arrays.asList(
            "fc", "ec", "sc", "ac", "ad", "cs", "cr", "se", "ge", "ca", "cd", "aa", "cf", "sa",
            "srl", "ltda", "do", "da", "de", "dos", "das", "del", "clube", "club", "futebol",
            "esporte", "associacao", "atletica", "sociedade", "sociedade esportiva", "regatas",
            "sporting"));

    /** Multi-word phrases removed before tokenising. */
    private static final List<String> NOISE_PHRASES = List.of(
            "esporte clube", "futebol clube", "clube de regatas", "sport club", "sporting club",
            "associacao desportiva", "associacao atletica", "sociedade esportiva",
            "gremio esportivo", "clube atletico", "esporte club");

    /**
     * Popular-name aliases: simplified raw base to {@code base|STATE} (state may be empty).
     * These are the clubs whose formal and popular names differ enough that the generic rules
     * cannot merge them.
     */
    private static final Map<String, String> ALIASES = buildAliases();

    /** Preferred display names keyed by {@code base|STATE} (state optional). */
    private static final Map<String, String> DISPLAY_NAMES = buildDisplayNames();

    private TeamNameNormalizer() {
    }

    /**
     * Normalises a raw club name.
     *
     * @param raw       club name exactly as written in the CSV file
     * @param stateHint optional state coming from a dedicated CSV column (may be {@code null})
     */
    public static NormalizedName normalize(String raw, String stateHint) {
        if (raw == null || raw.isBlank()) {
            return new NormalizedName("", null, "");
        }
        String cleaned = raw.trim().replaceAll("\\s+", " ");

        // 1. Parenthetical remarks: "(URU)" is a country, "(Minas Gerais)" a state, the rest noise.
        String parenState = null;
        Matcher matcher = PARENTHESES.matcher(cleaned);
        StringBuilder withoutParentheses = new StringBuilder();
        int last = 0;
        while (matcher.find()) {
            withoutParentheses.append(cleaned, last, matcher.start());
            last = matcher.end();
            String inner = TextUtils.simplify(matcher.group(1));
            if (COUNTRIES.contains(inner) || STATES.contains(inner)) {
                parenState = inner.toUpperCase(Locale.ROOT);
            } else if (STATE_NAMES.containsKey(inner)) {
                parenState = STATE_NAMES.get(inner);
            }
        }
        withoutParentheses.append(cleaned.substring(last));
        String display = withoutParentheses.toString().replaceAll("\\s+", " ").trim();

        // 2. Simplify and peel off trailing state / country codes.
        String simplified = TextUtils.simplify(display);
        for (String phrase : NOISE_PHRASES) {
            simplified = simplified.replace(phrase, " ");
        }
        simplified = simplified.replaceAll("\\s+", " ").trim();

        List<String> tokens = new java.util.ArrayList<>(Arrays.asList(simplified.split(" ")));
        String state = parenState;
        while (tokens.size() > 1) {
            String lastToken = tokens.get(tokens.size() - 1);
            if (STATES.contains(lastToken) || COUNTRIES.contains(lastToken)) {
                if (state == null) {
                    state = lastToken.toUpperCase(Locale.ROOT);
                }
                tokens.remove(tokens.size() - 1);
            } else {
                break;
            }
        }

        // 3. Drop legal-form noise, but never everything.
        List<String> meaningful = tokens.stream().filter(t -> !t.isBlank() && !NOISE_TOKENS.contains(t)).toList();
        if (meaningful.isEmpty()) {
            meaningful = tokens;
        }
        String base = String.join(" ", meaningful).trim();

        // 4. Curated aliases.
        String alias = ALIASES.get(base);
        if (alias != null) {
            String[] parts = alias.split("\\|", -1);
            base = parts[0];
            // An explicit state from the name or from a CSV column always wins: "Santos AP" must
            // not be turned into Santos-SP by the alias table.
            if (state == null && parts.length > 1 && !parts[1].isBlank()) {
                state = parts[1];
            }
        }
        if (state == null && stateHint != null && !stateHint.isBlank()) {
            String hint = TextUtils.simplify(stateHint);
            if (STATES.contains(hint) || COUNTRIES.contains(hint)) {
                state = hint.toUpperCase(Locale.ROOT);
            } else if (STATE_NAMES.containsKey(hint)) {
                state = STATE_NAMES.get(hint);
            }
        }
        return new NormalizedName(base, state, cleanDisplay(display));
    }

    /** Curated display name for a canonical node, or {@code null} when none is known. */
    public static String preferredDisplayName(String base, String state) {
        if (state != null) {
            String withState = DISPLAY_NAMES.get(base + "|" + state);
            if (withState != null) {
                return withState;
            }
        }
        return DISPLAY_NAMES.get(base);
    }

    /** Strips a trailing state suffix from the human readable form: "Palmeiras - SP" -> "Palmeiras". */
    private static String cleanDisplay(String display) {
        String result = display.replaceAll("(?i)\\s*[-–]\\s*[A-Za-zÀ-ú]{2,3}$", "").trim();
        String[] parts = result.split(" ");
        if (parts.length > 1) {
            String tail = TextUtils.simplify(parts[parts.length - 1]);
            if (STATES.contains(tail) || COUNTRIES.contains(tail)) {
                result = String.join(" ", Arrays.copyOf(parts, parts.length - 1)).trim();
            }
        }
        return result.isBlank() ? display : result;
    }

    private static Map<String, String> buildAliases() {
        Map<String, String> aliases = new HashMap<>();
        // Atlético / Athletico family - three different clubs sharing a base name.
        aliases.put("atletico mineiro", "atletico|MG");
        aliases.put("atletico mg", "atletico|MG");
        aliases.put("athletico mineiro", "atletico|MG");
        aliases.put("galo", "atletico|MG");
        aliases.put("athletico paranaense", "atletico|PR");
        aliases.put("atletico paranaense", "atletico|PR");
        aliases.put("athletico", "atletico|PR");
        aliases.put("operario ferroviario esporte c", "operario|PR");
        aliases.put("atletico goianiense", "atletico|GO");
        aliases.put("atletico cearense", "atletico|CE");
        aliases.put("atletico acreano", "atletico|AC");
        aliases.put("atletico alagoinhas", "atletico alagoinhas|BA");
        // Rio de Janeiro.
        aliases.put("vasco gama", "vasco|RJ");
        aliases.put("vasco", "vasco|RJ");
        aliases.put("flamengo", "flamengo|RJ");
        aliases.put("fluminense", "fluminense|RJ");
        aliases.put("botafogo", "botafogo|RJ");
        // São Paulo.
        aliases.put("sao paulo", "sao paulo|SP");
        aliases.put("corinthians", "corinthians|SP");
        aliases.put("corinthians paulista", "corinthians|SP");
        aliases.put("palmeiras", "palmeiras|SP");
        aliases.put("santos", "santos|SP");
        aliases.put("ponte preta", "ponte preta|SP");
        aliases.put("red bull bragantino", "bragantino|SP");
        aliases.put("red bull brasil", "red bull brasil|SP");
        aliases.put("bragantino", "bragantino|SP");
        aliases.put("portuguesa desportos", "portuguesa|SP");
        aliases.put("sao caetano", "sao caetano|SP");
        aliases.put("guarani", "guarani|SP");
        // South.
        aliases.put("gremio", "gremio|RS");
        aliases.put("internacional", "internacional|RS");
        aliases.put("inter", "internacional|RS");
        aliases.put("juventude", "juventude|RS");
        aliases.put("brasil pelotas", "brasil|RS");
        aliases.put("coritiba", "coritiba|PR");
        aliases.put("parana", "parana|PR");
        aliases.put("chapecoense", "chapecoense|SC");
        aliases.put("figueirense", "figueirense|SC");
        aliases.put("avai", "avai|SC");
        aliases.put("criciuma", "criciuma|SC");
        aliases.put("joinville", "joinville|SC");
        // Minas Gerais.
        aliases.put("cruzeiro", "cruzeiro|MG");
        aliases.put("america mineiro", "america|MG");
        aliases.put("america natal", "america|RN");
        aliases.put("america de natal", "america|RN");
        aliases.put("tombense", "tombense|MG");
        aliases.put("villa nova", "villa nova|MG");
        // Northeast.
        aliases.put("sport recife", "sport|PE");
        aliases.put("recife", "sport|PE"); // "Sport Club do Recife" in the player file
        aliases.put("sport", "sport|PE");
        aliases.put("nautico capibaribe", "nautico|PE");
        aliases.put("nautico", "nautico|PE");
        aliases.put("santa cruz", "santa cruz|PE");
        aliases.put("bahia", "bahia|BA");
        aliases.put("vitoria", "vitoria|BA");
        aliases.put("ceara sporting", "ceara|CE");
        aliases.put("ceara", "ceara|CE");
        aliases.put("fortaleza", "fortaleza|CE");
        aliases.put("sampaio correa", "sampaio correa|MA");
        aliases.put("confianca", "confianca|SE");
        aliases.put("csa", "csa|AL");
        aliases.put("crb", "crb|AL");
        aliases.put("abc", "abc|RN");
        aliases.put("treze", "treze|PB");
        // Centre-west and north.
        aliases.put("goias", "goias|GO");
        aliases.put("vila nova", "vila nova|GO");
        aliases.put("cuiaba", "cuiaba|MT");
        aliases.put("remo", "remo|PA");
        aliases.put("paysandu", "paysandu|PA");
        aliases.put("brasiliense", "brasiliense|DF");
        aliases.put("gama", "gama|DF");
        // Foreign clubs of the Libertadores / player files whose short name collides with a
        // Brazilian namesake; giving them their country keeps the two nodes apart.
        aliases.put("penarol", "penarol|URU");
        aliases.put("nacional", "nacional|URU");
        aliases.put("river plate", "river plate|ARG");
        aliases.put("libertad", "libertad|PAR");
        aliases.put("barcelona", "barcelona|ESP");
        aliases.put("emelec", "emelec|EQU");
        aliases.put("bolivar", "bolivar|BOL");
        aliases.put("danubio", "danubio|URU");
        return Map.copyOf(aliases);
    }

    private static Map<String, String> buildDisplayNames() {
        Map<String, String> names = new LinkedHashMap<>();
        names.put("atletico|MG", "Atlético Mineiro");
        names.put("atletico|PR", "Athletico Paranaense");
        names.put("atletico|GO", "Atlético Goianiense");
        names.put("america|MG", "América Mineiro");
        names.put("america|RN", "América de Natal");
        names.put("vasco", "Vasco da Gama");
        names.put("sao paulo", "São Paulo");
        names.put("gremio", "Grêmio");
        names.put("sport", "Sport Recife");
        names.put("nautico", "Náutico");
        names.put("bragantino|SP", "Red Bull Bragantino");
        names.put("ceara", "Ceará");
        names.put("goias", "Goiás");
        names.put("avai", "Avaí");
        names.put("cuiaba", "Cuiabá");
        names.put("vitoria|BA", "Vitória");
        names.put("botafogo|RJ", "Botafogo");
        names.put("botafogo|SP", "Botafogo-SP");
        names.put("botafogo|PB", "Botafogo-PB");
        names.put("parana", "Paraná");
        names.put("criciuma", "Criciúma");
        names.put("santa cruz|PE", "Santa Cruz");
        names.put("juventude", "Juventude");
        names.put("csa", "CSA");
        names.put("crb", "CRB");
        names.put("abc", "ABC");
        return Map.copyOf(names);
    }
}
