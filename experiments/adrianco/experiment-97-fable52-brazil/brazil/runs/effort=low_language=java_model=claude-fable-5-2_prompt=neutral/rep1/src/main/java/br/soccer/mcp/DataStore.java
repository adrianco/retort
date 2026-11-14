package br.soccer.mcp;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Loads the six Kaggle CSV files into memory and normalises them into {@link Match} and {@link Player} lists. */
final class DataStore {
    static final String SERIE_A = "Brasileirão Serie A";
    static final String SERIE_B = "Brasileirão Serie B";
    static final String SERIE_C = "Brasileirão Serie C";
    static final String COPA_DO_BRASIL = "Copa do Brasil";
    static final String LIBERTADORES = "Copa Libertadores";
    static final List<String> COMPETITIONS = List.of(SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES);

    static final String F_BRASILEIRAO = "Brasileirao_Matches.csv";
    static final String F_CUP = "Brazilian_Cup_Matches.csv";
    static final String F_LIBERTADORES = "Libertadores_Matches.csv";
    static final String F_EXTENDED = "BR-Football-Dataset.csv";
    static final String F_HISTORICAL = "novo_campeonato_brasileiro.csv";
    static final String F_FIFA = "fifa_data.csv";

    private static final DateTimeFormatter BR_DATE = DateTimeFormatter.ofPattern("d/M/yyyy");

    final TeamNames teams = new TeamNames();
    final List<Match> matches = new ArrayList<>();
    final List<Player> players = new ArrayList<>();
    /** Rows loaded per file (matches or players). */
    final Map<String, Integer> rowCounts = new LinkedHashMap<>();

    /** Resolves the data directory: explicit argument, BRAZILIAN_SOCCER_DATA_DIR, or ./data/kaggle. */
    static Path defaultDataDir(String arg) {
        if (arg != null && !arg.isBlank()) return Path.of(arg);
        String env = System.getenv("BRAZILIAN_SOCCER_DATA_DIR");
        if (env != null && !env.isBlank()) return Path.of(env);
        return Path.of("data", "kaggle");
    }

    static DataStore load(Path dir) throws IOException {
        if (!Files.isDirectory(dir)) throw new IOException("Data directory not found: " + dir.toAbsolutePath());
        DataStore ds = new DataStore();
        // Load order is the tie-break priority when two files cover the same competition and season.
        ds.loadHistorical(dir.resolve(F_HISTORICAL));
        ds.loadBrasileirao(dir.resolve(F_BRASILEIRAO));
        ds.loadCup(dir.resolve(F_CUP));
        ds.loadLibertadores(dir.resolve(F_LIBERTADORES));
        ds.loadExtended(dir.resolve(F_EXTENDED));
        ds.finishMatches();
        ds.loadPlayers(dir.resolve(F_FIFA));
        return ds;
    }

    // ---------- parsing helpers ----------

    /** Parses "2023-09-24", "2012-05-19 18:30:00" and "29/03/2003". Returns null when unparseable. */
    static LocalDate parseDate(String s) {
        if (s == null) return null;
        s = s.trim();
        if (s.isEmpty() || s.equalsIgnoreCase("NA")) return null;
        try {
            if (s.contains("/")) return LocalDate.parse(s.split("[ T]")[0], BR_DATE);
            return LocalDate.parse(s.length() >= 10 ? s.substring(0, 10) : s);
        } catch (DateTimeParseException e) {
            return null;
        }
    }

    static String parseTime(String s) {
        if (s == null) return null;
        int i = s.trim().indexOf(' ');
        return i > 0 && s.trim().length() >= i + 6 ? s.trim().substring(i + 1, i + 6) : null;
    }

    /** Parses "2", "2.0"; returns null for blank / "NA" / garbage. */
    static Integer parseInt(String s) {
        if (s == null) return null;
        s = s.trim();
        if (s.isEmpty() || s.equalsIgnoreCase("NA") || s.equalsIgnoreCase("NaN")) return null;
        try {
            return (int) Math.round(Double.parseDouble(s));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static String blankToNull(String s) {
        return s == null || s.isBlank() || s.equalsIgnoreCase("NA") ? null : s.trim();
    }

    private Match base(String source, String competition, String home, String away, boolean topFlight) {
        Match m = new Match();
        m.source = source;
        m.competition = competition;
        m.homeRaw = home;
        m.awayRaw = away;
        if (home != null && !home.isBlank()) teams.register(home, topFlight);
        if (away != null && !away.isBlank()) teams.register(away, topFlight);
        return m;
    }

    private void add(String file, List<Match> loaded) {
        // a row without teams or without any season/date information cannot be queried meaningfully
        loaded.removeIf(m -> m.season == 0 || m.homeRaw == null || m.awayRaw == null || m.homeRaw.isBlank() || m.awayRaw.isBlank());
        matches.addAll(loaded);
        rowCounts.put(file, loaded.size());
    }

    // ---------- loaders ----------

    private void loadHistorical(Path f) throws IOException {
        List<Match> out = new ArrayList<>();
        for (Map<String, String> r : Csv.read(f)) {
            Match m = base(F_HISTORICAL, SERIE_A, r.get("Equipe_mandante"), r.get("Equipe_visitante"), true);
            m.date = parseDate(r.get("Data"));
            Integer year = parseInt(r.get("Ano"));
            m.season = year != null ? year : (m.date != null ? m.date.getYear() : 0);
            m.round = blankToNull(r.get("Rodada"));
            m.homeGoals = parseInt(r.get("Gols_mandante"));
            m.awayGoals = parseInt(r.get("Gols_visitante"));
            m.arena = blankToNull(r.get("Arena"));
            out.add(m);
        }
        add(F_HISTORICAL, out);
    }

    private void loadBrasileirao(Path f) throws IOException {
        List<Match> out = new ArrayList<>();
        for (Map<String, String> r : Csv.read(f)) {
            Match m = base(F_BRASILEIRAO, SERIE_A, r.get("home_team"), r.get("away_team"), true);
            m.date = parseDate(r.get("datetime"));
            m.time = parseTime(r.get("datetime"));
            Integer season = parseInt(r.get("season"));
            m.season = season != null ? season : (m.date != null ? m.date.getYear() : 0);
            m.round = blankToNull(r.get("round"));
            m.homeGoals = parseInt(r.get("home_goal"));
            m.awayGoals = parseInt(r.get("away_goal"));
            out.add(m);
        }
        add(F_BRASILEIRAO, out);
    }

    private void loadCup(Path f) throws IOException {
        List<Match> out = new ArrayList<>();
        for (Map<String, String> r : Csv.read(f)) {
            Match m = base(F_CUP, COPA_DO_BRASIL, r.get("home_team"), r.get("away_team"), false);
            m.date = parseDate(r.get("datetime"));
            m.time = parseTime(r.get("datetime"));
            Integer season = parseInt(r.get("season"));
            m.season = season != null ? season : (m.date != null ? m.date.getYear() : 0);
            m.round = blankToNull(r.get("round"));
            m.homeGoals = parseInt(r.get("home_goal"));
            m.awayGoals = parseInt(r.get("away_goal"));
            out.add(m);
        }
        // The file only has round numbers. Name the closing rounds by walking back from each season's
        // last round while the number of matches fits a two-legged final, semi-final, and so on.
        Map<Integer, TreeMap<Integer, List<Match>>> bySeason = new TreeMap<>();
        for (Match m : out) {
            Integer round = parseInt(m.round);
            if (round != null) {
                bySeason.computeIfAbsent(m.season, k -> new TreeMap<>()).computeIfAbsent(round, k -> new ArrayList<>()).add(m);
            }
        }
        String[] names = {"final", "semifinals", "quarterfinals", "round of 16"};
        for (TreeMap<Integer, List<Match>> rounds : bySeason.values()) {
            int i = 0, maxMatches = 2;
            for (List<Match> ms : rounds.descendingMap().values()) {
                if (i >= names.length || ms.size() > maxMatches) break;
                for (Match m : ms) m.stage = names[i];
                i++;
                maxMatches *= 2;
            }
        }
        add(F_CUP, out);
    }

    private void loadLibertadores(Path f) throws IOException {
        List<Match> out = new ArrayList<>();
        for (Map<String, String> r : Csv.read(f)) {
            Match m = base(F_LIBERTADORES, LIBERTADORES, r.get("home_team"), r.get("away_team"), false);
            m.date = parseDate(r.get("datetime"));
            m.time = parseTime(r.get("datetime"));
            Integer season = parseInt(r.get("season"));
            m.season = season != null ? season : (m.date != null ? m.date.getYear() : 0);
            m.stage = blankToNull(r.get("stage"));
            m.homeGoals = parseInt(r.get("home_goal"));
            m.awayGoals = parseInt(r.get("away_goal"));
            out.add(m);
        }
        add(F_LIBERTADORES, out);
    }

    private void loadExtended(Path f) throws IOException {
        List<Match> out = new ArrayList<>();
        for (Map<String, String> r : Csv.read(f)) {
            String t = r.getOrDefault("tournament", "");
            String comp = switch (t) {
                case "Serie A" -> SERIE_A;
                case "Serie B" -> SERIE_B;
                case "Serie C" -> SERIE_C;
                case "Copa do Brasil" -> COPA_DO_BRASIL;
                default -> t;
            };
            Match m = base(F_EXTENDED, comp, r.get("home"), r.get("away"), SERIE_A.equals(comp));
            m.date = parseDate(r.get("date"));
            String time = blankToNull(r.get("time"));
            m.time = time != null && time.length() >= 5 ? time.substring(0, 5) : time;
            // No season column: league seasons follow the calendar year, except that the
            // pandemic-delayed 2020 season finished in January/February 2021.
            if (m.date != null) {
                boolean league = !COPA_DO_BRASIL.equals(comp);
                m.season = league && m.date.getMonthValue() <= 2 ? m.date.getYear() - 1 : m.date.getYear();
            }
            m.homeGoals = parseInt(r.get("home_goal"));
            m.awayGoals = parseInt(r.get("away_goal"));
            m.homeCorners = parseInt(r.get("home_corner"));
            m.awayCorners = parseInt(r.get("away_corner"));
            m.homeShots = parseInt(r.get("home_shots"));
            m.awayShots = parseInt(r.get("away_shots"));
            m.homeAttacks = parseInt(r.get("home_attack"));
            m.awayAttacks = parseInt(r.get("away_attack"));
            out.add(m);
        }
        add(F_EXTENDED, out);
    }

    /** Assigns canonical team keys and marks which file is the primary source per competition+season. */
    private void finishMatches() {
        for (Match m : matches) {
            m.home = teams.canonicalAndRecord(m.homeRaw);
            m.away = teams.canonicalAndRecord(m.awayRaw);
        }
        // Several files overlap (e.g. Serie A 2012-2019 is in three of them). To avoid counting a
        // match twice, the file with the most scored matches for a competition+season is primary.
        Map<String, Map<String, Integer>> counts = new TreeMap<>();
        for (Match m : matches) {
            counts.computeIfAbsent(m.competition + "|" + m.season, k -> new LinkedHashMap<>())
                    .merge(m.source, m.played() ? 1 : 0, Integer::sum);
        }
        Map<String, String> best = new HashMap<>();
        counts.forEach((k, bySource) -> {
            String top = null;
            int max = -1;
            for (Map.Entry<String, Integer> e : bySource.entrySet()) {
                if (e.getValue() > max) { max = e.getValue(); top = e.getKey(); }
            }
            best.put(k, top);
        });
        for (Match m : matches) m.primary = m.source.equals(best.get(m.competition + "|" + m.season));
    }

    private void loadPlayers(Path f) throws IOException {
        for (Map<String, String> r : Csv.read(f)) {
            Player p = new Player();
            Integer id = parseInt(r.get("ID"));
            p.id = id == null ? 0 : id;
            p.name = r.getOrDefault("Name", "");
            p.nationality = r.getOrDefault("Nationality", "");
            p.club = r.getOrDefault("Club", "");
            p.position = r.getOrDefault("Position", "");
            p.height = r.getOrDefault("Height", "");
            p.weight = r.getOrDefault("Weight", "");
            p.value = r.getOrDefault("Value", "");
            p.wage = r.getOrDefault("Wage", "");
            p.preferredFoot = r.getOrDefault("Preferred Foot", "");
            p.jersey = r.getOrDefault("Jersey Number", "");
            Integer age = parseInt(r.get("Age")), ov = parseInt(r.get("Overall")), pot = parseInt(r.get("Potential"));
            p.age = age == null ? 0 : age;
            p.overall = ov == null ? 0 : ov;
            p.potential = pot == null ? 0 : pot;
            p.raw = r;
            if (!p.club.isBlank()) {
                String key = teams.canonical(p.club);
                if (teams.isKnown(key)) p.clubTeamKey = key;
            }
            players.add(p);
        }
        rowCounts.put(F_FIFA, players.size());
    }
}
