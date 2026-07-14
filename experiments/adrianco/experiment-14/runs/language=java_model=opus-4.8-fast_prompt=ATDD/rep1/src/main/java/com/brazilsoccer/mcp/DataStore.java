package com.brazilsoccer.mcp;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.apache.commons.csv.DuplicateHeaderMode;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Loads all provided CSV datasets into in-memory collections.
 *
 * <p>Several files overlap (the Brasileirão appears in three of them). Matches are
 * de-duplicated by {@link Match#dedupeKey()}, keeping the first source loaded. To
 * avoid double-counting league tables, the extended statistics file does not
 * contribute matches for any (competition, season) already covered by a primary
 * source — it only extends coverage (e.g. Série B/C, newer seasons).
 */
public final class DataStore {

    private static final Pattern HAS_STATE_SUFFIX = Pattern.compile("[\\s-]+[A-Z]{2,3}\\s*$");

    private final List<Match> matches;
    private final List<Player> players;

    private DataStore(List<Match> matches, List<Player> players) {
        this.matches = matches;
        this.players = players;
    }

    public List<Match> matches() {
        return matches;
    }

    public List<Player> players() {
        return players;
    }

    public static DataStore load(Path dataDir) {
        List<Match> matches = new ArrayList<>();
        Set<String> seen = new HashSet<>();

        // Sources are loaded in priority order. Each later source is gated against the
        // (competition, season) coverage already established, so overlapping datasets
        // (the Brasileirão appears in three files) never double-count a league.
        loadBrasileirao(dataDir.resolve("Brasileirao_Matches.csv"), matches, seen, Set.of());
        loadNovo(dataDir.resolve("novo_campeonato_brasileiro.csv"), matches, seen, coverageOf(matches));
        loadLibertadores(dataDir.resolve("Libertadores_Matches.csv"), matches, seen, coverageOf(matches));
        loadCup(dataDir.resolve("Brazilian_Cup_Matches.csv"), matches, seen, coverageOf(matches));
        loadExtended(dataDir.resolve("BR-Football-Dataset.csv"), matches, seen, coverageOf(matches));

        List<Player> players = loadPlayers(dataDir.resolve("fifa_data.csv"));
        return new DataStore(matches, players);
    }

    /** Snapshot of the (competition, season) pairs already loaded. */
    private static Set<String> coverageOf(List<Match> matches) {
        Set<String> coverage = new LinkedHashSet<>();
        for (Match m : matches) {
            if (m.season > 0) {
                coverage.add(m.competition + "|" + m.season);
            }
        }
        return coverage;
    }

    // ---- Match loaders -------------------------------------------------------

    private static void loadBrasileirao(Path file, List<Match> out, Set<String> seen, Set<String> covered) {
        forEachRecord(file, record -> {
            int season = parseSeason(get(record, "season"), get(record, "datetime"));
            Match m = buildMatch(Competition.SERIE_A, season,
                    parseDate(get(record, "datetime")), get(record, "round"),
                    get(record, "home_team"), get(record, "home_team_state"),
                    get(record, "away_team"), get(record, "away_team_state"),
                    get(record, "home_goal"), get(record, "away_goal"));
            add(m, out, seen, covered);
        });
    }

    private static void loadNovo(Path file, List<Match> out, Set<String> seen, Set<String> covered) {
        forEachRecord(file, record -> {
            int season = parseSeason(get(record, "Ano"), get(record, "Data"));
            Match m = buildMatch(Competition.SERIE_A, season,
                    parseDate(get(record, "Data")), get(record, "Rodada"),
                    get(record, "Equipe_mandante"), get(record, "Mandante_UF"),
                    get(record, "Equipe_visitante"), get(record, "Visitante_UF"),
                    get(record, "Gols_mandante"), get(record, "Gols_visitante"));
            add(m, out, seen, covered);
        });
    }

    private static void loadLibertadores(Path file, List<Match> out, Set<String> seen, Set<String> covered) {
        forEachRecord(file, record -> {
            int season = parseSeason(get(record, "season"), get(record, "datetime"));
            Match m = buildMatch(Competition.LIBERTADORES, season,
                    parseDate(get(record, "datetime")), get(record, "stage"),
                    get(record, "home_team"), null,
                    get(record, "away_team"), null,
                    get(record, "home_goal"), get(record, "away_goal"));
            add(m, out, seen, covered);
        });
    }

    private static void loadCup(Path file, List<Match> out, Set<String> seen, Set<String> covered) {
        forEachRecord(file, record -> {
            int season = parseSeason(get(record, "season"), get(record, "datetime"));
            Match m = buildMatch(Competition.COPA_DO_BRASIL, season,
                    parseDate(get(record, "datetime")), get(record, "round"),
                    get(record, "home_team"), null,
                    get(record, "away_team"), null,
                    get(record, "home_goal"), get(record, "away_goal"));
            add(m, out, seen, covered);
        });
    }

    private static void loadExtended(Path file, List<Match> out, Set<String> seen, Set<String> covered) {
        forEachRecord(file, record -> {
            Competition comp = Competition.fromTournamentLabel(get(record, "tournament"));
            if (comp == null) {
                return;
            }
            String date = parseDate(get(record, "date"));
            int season = parseSeason(null, date);
            Match m = buildMatch(comp, season, date, null,
                    get(record, "home"), null,
                    get(record, "away"), null,
                    get(record, "home_goal"), get(record, "away_goal"));
            add(m, out, seen, covered);
        });
    }

    private static void add(Match m, List<Match> out, Set<String> seen, Set<String> covered) {
        if (m == null) {
            return;
        }
        // Skip a (competition, season) already owned by a higher-priority source.
        if (m.season > 0 && covered.contains(m.competition + "|" + m.season)) {
            return;
        }
        if (!seen.add(m.dedupeKey())) {
            return;
        }
        out.add(m);
    }

    private static Match buildMatch(Competition comp, int season, String date, String round,
                                    String homeRaw, String homeUf, String awayRaw, String awayUf,
                                    String homeGoalRaw, String awayGoalRaw) {
        int hg = parseGoals(homeGoalRaw);
        int ag = parseGoals(awayGoalRaw);
        if (hg < 0 || ag < 0) {
            return null; // unplayed / malformed row
        }
        String round0 = blankToNull(round);
        return new Match(comp, season, date, round0,
                display(homeRaw, homeUf), display(awayRaw, awayUf),
                TeamNames.matchKey(homeRaw), TeamNames.matchKey(awayRaw),
                TeamNames.identityKey(homeRaw, homeUf), TeamNames.identityKey(awayRaw, awayUf),
                hg, ag);
    }

    /** Human-readable team label, always including the state code when known. */
    static String display(String rawName, String stateColumn) {
        String cleaned = rawName == null ? "" : rawName.replaceAll("\\s*\\([^)]*\\)\\s*", " ").trim();
        if (HAS_STATE_SUFFIX.matcher(cleaned).find()) {
            return cleaned;
        }
        if (stateColumn != null) {
            String uf = stateColumn.trim();
            if (!uf.isEmpty() && !uf.equalsIgnoreCase("na")) {
                return cleaned + "-" + uf.toUpperCase(Locale.ROOT);
            }
        }
        return cleaned;
    }

    // ---- Player loader -------------------------------------------------------

    private static List<Player> loadPlayers(Path file) {
        List<Player> players = new ArrayList<>();
        forEachRecord(file, record -> {
            String name = get(record, "Name");
            if (name == null || name.isBlank()) {
                return;
            }
            players.add(new Player(
                    name,
                    parseInt(get(record, "Age"), 0),
                    orEmpty(get(record, "Nationality")),
                    parseInt(get(record, "Overall"), 0),
                    parseInt(get(record, "Potential"), 0),
                    orEmpty(get(record, "Club")),
                    orEmpty(get(record, "Position")),
                    orEmpty(get(record, "Jersey Number"))));
        });
        return players;
    }

    // ---- CSV plumbing --------------------------------------------------------

    private interface RecordConsumer {
        void accept(CSVRecord record);
    }

    private static void forEachRecord(Path file, RecordConsumer consumer) {
        CSVFormat format = CSVFormat.DEFAULT.builder()
                .setHeader()
                .setSkipHeaderRecord(true)
                .setIgnoreSurroundingSpaces(true)
                .setAllowMissingColumnNames(true)
                .setDuplicateHeaderMode(DuplicateHeaderMode.ALLOW_ALL)
                .build();
        try (BufferedReader reader = newBomSafeReader(file);
             CSVParser parser = CSVParser.parse(reader, format)) {
            for (CSVRecord record : parser) {
                consumer.accept(record);
            }
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to read " + file, e);
        }
    }

    private static BufferedReader newBomSafeReader(Path file) throws IOException {
        BufferedReader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8);
        reader.mark(1);
        if (reader.read() != 0xFEFF) {
            reader.reset();
        }
        return reader;
    }

    private static String get(CSVRecord record, String column) {
        if (!record.isMapped(column)) {
            return null;
        }
        String v = record.get(column);
        return v == null ? null : v.trim();
    }

    // ---- Parsing helpers -----------------------------------------------------

    static int parseGoals(String raw) {
        if (raw == null || raw.isBlank()) {
            return -1;
        }
        try {
            return (int) Math.round(Double.parseDouble(raw.trim()));
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    static int parseInt(String raw, int fallback) {
        if (raw == null || raw.isBlank()) {
            return fallback;
        }
        try {
            return (int) Math.round(Double.parseDouble(raw.trim()));
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    static int parseSeason(String seasonRaw, String dateRaw) {
        int s = parseInt(seasonRaw, -1);
        if (s > 0) {
            return s;
        }
        String date = parseDate(dateRaw);
        if (date != null && date.length() >= 4) {
            return parseInt(date.substring(0, 4), -1);
        }
        return -1;
    }

    /** Normalizes the various date formats to ISO yyyy-MM-dd. */
    static String parseDate(String raw) {
        if (raw == null) {
            return null;
        }
        String v = raw.trim();
        if (v.isEmpty()) {
            return null;
        }
        if (v.contains("/")) {
            String[] parts = v.split("/");
            if (parts.length == 3 && parts[2].length() == 4) {
                return String.format("%s-%02d-%02d",
                        parts[2], parseInt(parts[1], 0), parseInt(parts[0], 0));
            }
            return null;
        }
        String datePart = v.contains(" ") ? v.substring(0, v.indexOf(' ')) : v;
        return datePart.length() >= 10 ? datePart.substring(0, 10) : datePart;
    }

    private static String blankToNull(String s) {
        return (s == null || s.isBlank()) ? null : s;
    }

    private static String orEmpty(String s) {
        return s == null ? "" : s;
    }
}
