package br.soccer;

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
import java.util.Set;
import java.util.TreeSet;

/**
 * Loads the six Kaggle CSV files into memory. Matches that appear in more than one file (the three
 * Brasileirão sources overlap heavily) are merged into a single {@link Match}.
 */
public final class DataStore {
    public static final String SERIE_A = "Brasileirão Série A";
    public static final String SERIE_B = "Brasileirão Série B";
    public static final String SERIE_C = "Brasileirão Série C";
    public static final String COPA_DO_BRASIL = "Copa do Brasil";
    public static final String LIBERTADORES = "Copa Libertadores";

    public static final String F_BRASILEIRAO = "Brasileirao_Matches.csv";
    public static final String F_HISTORICAL = "novo_campeonato_brasileiro.csv";
    public static final String F_CUP = "Brazilian_Cup_Matches.csv";
    public static final String F_LIBERTADORES = "Libertadores_Matches.csv";
    public static final String F_EXTENDED = "BR-Football-Dataset.csv";
    public static final String F_FIFA = "fifa_data.csv";

    private static final DateTimeFormatter BR_DATE = DateTimeFormatter.ofPattern("d/M/yyyy");
    private static final String[] SKILLS = {
        "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Dribbling", "BallControl",
        "Acceleration", "SprintSpeed", "ShotPower", "Stamina", "Strength", "LongShots", "Vision",
        "Penalties", "StandingTackle", "GKDiving", "GKReflexes"};

    private final List<Match> matches = new ArrayList<>();
    private final List<Player> players = new ArrayList<>();
    private final Map<String, List<Match>> byFixture = new HashMap<>();
    private final Set<String> teamKeys = new TreeSet<>();
    /** Per file: rows read, and rows usable (a parseable date, both teams and a final score). */
    private final Map<String, int[]> fileStats = new LinkedHashMap<>();

    public static DataStore load(Path dir) throws IOException {
        if (!Files.isDirectory(dir)) throw new IOException("Data directory not found: " + dir.toAbsolutePath());
        DataStore ds = new DataStore();
        ds.loadBrasileirao(dir.resolve(F_BRASILEIRAO));
        ds.loadHistorical(dir.resolve(F_HISTORICAL));
        ds.loadCup(dir.resolve(F_CUP));
        ds.loadLibertadores(dir.resolve(F_LIBERTADORES));
        ds.loadExtended(dir.resolve(F_EXTENDED));
        ds.loadPlayers(dir.resolve(F_FIFA));
        ds.labelCupFinals();
        return ds;
    }

    /** Default location: $BR_SOCCER_DATA_DIR, else ./data/kaggle. */
    public static Path defaultDir() {
        String env = System.getenv("BR_SOCCER_DATA_DIR");
        return Path.of(env != null && !env.isBlank() ? env : "data/kaggle");
    }

    public List<Match> matches() {
        return matches;
    }

    public List<Player> players() {
        return players;
    }

    public Set<String> teamKeys() {
        return teamKeys;
    }

    public Map<String, int[]> fileStats() {
        return fileStats;
    }

    /** Parses "2023-09-24", "2012-05-19 18:30:00" and "29/03/2003"; null when unparseable. */
    public static LocalDate parseDate(String s) {
        if (s == null) return null;
        s = s.trim();
        try {
            if (s.matches("\\d{4}-\\d{2}-\\d{2}.*")) return LocalDate.parse(s.substring(0, 10));
            if (s.matches("\\d{1,2}/\\d{1,2}/\\d{4}.*")) {
                return LocalDate.parse(s.split("[ T]")[0], BR_DATE);
            }
        } catch (DateTimeParseException e) {
            return null;
        }
        return null;
    }

    static Integer parseInt(String s) {
        if (s == null || s.isBlank()) return null;
        try {
            double d = Double.parseDouble(s.trim());
            if (Double.isNaN(d) || Double.isInfinite(d)) return null;
            return (int) Math.round(d);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private void count(String file, boolean usable) {
        int[] c = fileStats.computeIfAbsent(file, k -> new int[2]);
        c[0]++;
        if (usable) c[1]++;
    }

    /** Adds a match, or merges it into an already-loaded record of the same fixture. */
    private void add(String file, String competition, String dateStr, Integer season, String home,
                     String away, String hg, String ag, String round, String stage, String stadium,
                     Map<String, String> extra) {
        LocalDate date = parseDate(dateStr);
        Integer h = parseInt(hg), a = parseInt(ag);
        String hk = TeamNames.canonical(home), ak = TeamNames.canonical(away);
        boolean ok = date != null && h != null && a != null && h >= 0 && a >= 0
                && !hk.isEmpty() && !ak.isEmpty();
        count(file, ok);
        if (!ok) return;

        Match m = null;
        List<Match> same = byFixture.computeIfAbsent(competition + "|" + hk + "|" + ak, k -> new ArrayList<>());
        for (Match o : same) {
            // Kick-off dates differ by a day between sources (time zones). A Série A pairing is
            // played once per season at each ground, so across files the season alone identifies it.
            if (Math.abs(o.date.toEpochDay() - date.toEpochDay()) <= 2
                    || competition.equals(SERIE_A) && season != null && o.season == season
                            && !o.sources.contains(file)) m = o;
        }
        if (m == null) {
            m = new Match();
            m.date = date;
            m.competition = competition;
            m.season = season != null ? season : date.getYear();
            m.homeKey = hk;
            m.awayKey = ak;
            m.homeGoals = h;
            m.awayGoals = a;
            same.add(m);
            matches.add(m);
            teamKeys.add(hk);
            teamKeys.add(ak);
        }
        m.sources.add(file);
        if (m.round == null && round != null && !round.isBlank()) m.round = round;
        if (m.stage == null && stage != null && !stage.isBlank()) m.stage = stage;
        if (m.stadium == null && stadium != null && !stadium.isBlank()) m.stadium = stadium;
        if (extra != null && m.homeCorners == null) {
            m.homeCorners = parseInt(extra.get("home_corner"));
            m.awayCorners = parseInt(extra.get("away_corner"));
            m.homeShots = parseInt(extra.get("home_shots"));
            m.awayShots = parseInt(extra.get("away_shots"));
        }
    }

    private void loadBrasileirao(Path f) throws IOException {
        for (Map<String, String> r : Csv.read(f)) {
            add(F_BRASILEIRAO, SERIE_A, r.get("datetime"), parseInt(r.get("season")), r.get("home_team"),
                    r.get("away_team"), r.get("home_goal"), r.get("away_goal"), r.get("round"), null, null, null);
        }
    }

    private void loadHistorical(Path f) throws IOException {
        for (Map<String, String> r : Csv.read(f)) {
            add(F_HISTORICAL, SERIE_A, r.get("Data"), parseInt(r.get("Ano")), r.get("Equipe_mandante"),
                    r.get("Equipe_visitante"), r.get("Gols_mandante"), r.get("Gols_visitante"),
                    r.get("Rodada"), null, r.get("Arena"), null);
        }
    }

    private void loadCup(Path f) throws IOException {
        for (Map<String, String> r : Csv.read(f)) {
            add(F_CUP, COPA_DO_BRASIL, r.get("datetime"), parseInt(r.get("season")), r.get("home_team"),
                    r.get("away_team"), r.get("home_goal"), r.get("away_goal"), r.get("round"), null, null, null);
        }
    }

    private void loadLibertadores(Path f) throws IOException {
        for (Map<String, String> r : Csv.read(f)) {
            add(F_LIBERTADORES, LIBERTADORES, r.get("datetime"), parseInt(r.get("season")), r.get("home_team"),
                    r.get("away_team"), r.get("home_goal"), r.get("away_goal"), null, r.get("stage"), null, null);
        }
    }

    private void loadExtended(Path f) throws IOException {
        for (Map<String, String> r : Csv.read(f)) {
            String t = TeamNames.fold(r.get("tournament"));
            String comp = switch (t) {
                case "serie a" -> SERIE_A;
                case "serie b" -> SERIE_B;
                case "serie c" -> SERIE_C;
                case "copa do brasil" -> COPA_DO_BRASIL;
                default -> r.getOrDefault("tournament", "Unknown");
            };
            // This file has no season column. League seasons follow the calendar year, except the
            // 2020 season which finished in early 2021, so January/February league games belong
            // to the previous year's season.
            LocalDate d = parseDate(r.get("date"));
            Integer season = null;
            if (d != null) {
                boolean league = !comp.equals(COPA_DO_BRASIL);
                season = league && d.getMonthValue() <= 2 ? d.getYear() - 1 : d.getYear();
            }
            add(F_EXTENDED, comp, r.get("date"), season, r.get("home"), r.get("away"), r.get("home_goal"),
                    r.get("away_goal"), null, null, null, r);
        }
    }

    private void loadPlayers(Path f) throws IOException {
        for (Map<String, String> r : Csv.read(f)) {
            Integer id = parseInt(r.get("ID"));
            String name = r.getOrDefault("Name", "");
            boolean ok = id != null && !name.isEmpty();
            count(F_FIFA, ok);
            if (!ok) continue;
            Map<String, String> skills = new LinkedHashMap<>();
            for (String s : SKILLS) {
                String v = r.get(s);
                if (v != null && !v.isEmpty()) skills.put(s, v);
            }
            players.add(new Player(id, name, orZero(r.get("Age")), r.getOrDefault("Nationality", ""),
                    orZero(r.get("Overall")), orZero(r.get("Potential")), r.getOrDefault("Club", ""),
                    r.getOrDefault("Position", ""), r.getOrDefault("Jersey Number", ""),
                    r.getOrDefault("Height", ""), r.getOrDefault("Weight", ""), r.getOrDefault("Value", ""),
                    r.getOrDefault("Wage", ""), r.getOrDefault("Preferred Foot", ""), skills));
        }
    }

    private static int orZero(String s) {
        Integer i = parseInt(s);
        return i == null ? 0 : i;
    }

    /**
     * The cup file numbers its rounds; the final is the last round of a season, played over at
     * most two legs. Tags those matches with stage "final" so they can be searched for.
     */
    private void labelCupFinals() {
        Map<Integer, Integer> lastRound = new HashMap<>();
        Map<String, Integer> perRound = new HashMap<>();
        for (Match m : matches) {
            Integer r = m.competition.equals(COPA_DO_BRASIL) ? parseInt(m.round) : null;
            if (r == null) continue;
            lastRound.merge(m.season, r, Math::max);
            perRound.merge(m.season + "|" + r, 1, Integer::sum);
        }
        for (Match m : matches) {
            Integer r = m.competition.equals(COPA_DO_BRASIL) ? parseInt(m.round) : null;
            if (r == null || !r.equals(lastRound.get(m.season))) continue;
            if (perRound.get(m.season + "|" + r) <= 2) m.stage = "final";
        }
    }
}
