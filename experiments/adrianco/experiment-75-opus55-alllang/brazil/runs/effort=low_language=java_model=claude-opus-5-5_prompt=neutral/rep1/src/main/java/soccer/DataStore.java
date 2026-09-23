package soccer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;

/** Loads all six Kaggle CSV files into memory. */
public final class DataStore {
    public static final String BRASILEIRAO = "Brasileirão";
    public static final String COPA_DO_BRASIL = "Copa do Brasil";
    public static final String LIBERTADORES = "Libertadores";

    private final List<Match> matches = new ArrayList<>();
    private final List<Player> players = new ArrayList<>();
    private final Map<String, Integer> rowsPerFile = new LinkedHashMap<>();

    public static DataStore load(Path dir) throws IOException {
        DataStore d = new DataStore();
        List<Match> all = new ArrayList<>();
        all.addAll(d.loadBrasileirao(dir.resolve("Brasileirao_Matches.csv")));
        all.addAll(d.loadCup(dir.resolve("Brazilian_Cup_Matches.csv")));
        all.addAll(d.loadLibertadores(dir.resolve("Libertadores_Matches.csv")));
        all.addAll(d.loadHistorical(dir.resolve("novo_campeonato_brasileiro.csv")));
        all.addAll(d.loadExtended(dir.resolve("BR-Football-Dataset.csv")));
        d.players.addAll(d.loadPlayers(dir.resolve("fifa_data.csv")));
        // Several files cover the same competition/season; keep only the first-loaded source per
        // (competition, season) so results are not double-counted.
        Map<String, String> owner = new HashMap<>();
        for (Match m : all) owner.putIfAbsent(m.competition() + "|" + m.season(), m.source());
        for (Match m : all) if (owner.get(m.competition() + "|" + m.season()).equals(m.source())) d.matches.add(m);
        d.matches.sort(Comparator.comparing(Match::date));
        return d;
    }

    /** Locate data/kaggle relative to the working directory or a system property. */
    public static Path defaultDir() {
        String p = System.getProperty("soccer.data", System.getenv().getOrDefault("SOCCER_DATA", "data/kaggle"));
        return Path.of(p);
    }

    public List<Match> matches() { return matches; }
    public List<Player> players() { return players; }
    public Map<String, Integer> rowsPerFile() { return rowsPerFile; }

    // ---------- loaders ----------
    private List<Map<String, String>> read(Path f) throws IOException {
        if (!Files.exists(f)) throw new IOException("Missing data file " + f);
        List<Map<String, String>> rows = Csv.read(f);
        rowsPerFile.put(f.getFileName().toString(), rows.size());
        return rows;
    }

    private List<Match> loadBrasileirao(Path f) throws IOException {
        List<Match> out = new ArrayList<>();
        for (var r : read(f)) {
            Integer hg = num(r.get("home_goal")), ag = num(r.get("away_goal"));
            if (hg == null || ag == null) continue;
            out.add(new Match(date(r.get("datetime")), r.get("home_team"), r.get("away_team"), hg, ag,
                    BRASILEIRAO, num(r.get("season")), r.get("round"), f.getFileName().toString(), null));
        }
        return out;
    }

    private List<Match> loadCup(Path f) throws IOException {
        List<Match> out = new ArrayList<>();
        for (var r : read(f)) {
            Integer hg = num(r.get("home_goal")), ag = num(r.get("away_goal"));
            if (hg == null || ag == null) continue;
            out.add(new Match(date(r.get("datetime")), r.get("home_team"), r.get("away_team"), hg, ag,
                    COPA_DO_BRASIL, num(r.get("season")), r.get("round"), f.getFileName().toString(), null));
        }
        return out;
    }

    private List<Match> loadLibertadores(Path f) throws IOException {
        List<Match> out = new ArrayList<>();
        for (var r : read(f)) {
            Integer hg = num(r.get("home_goal")), ag = num(r.get("away_goal"));
            if (hg == null || ag == null) continue;
            out.add(new Match(date(r.get("datetime")), r.get("home_team"), r.get("away_team"), hg, ag,
                    LIBERTADORES, num(r.get("season")), r.get("stage"), f.getFileName().toString(), null));
        }
        return out;
    }

    private List<Match> loadHistorical(Path f) throws IOException {
        List<Match> out = new ArrayList<>();
        for (var r : read(f)) {
            Integer hg = num(r.get("Gols_mandante")), ag = num(r.get("Gols_visitante"));
            if (hg == null || ag == null) continue;
            out.add(new Match(date(r.get("Data")), r.get("Equipe_mandante"), r.get("Equipe_visitante"), hg, ag,
                    BRASILEIRAO, num(r.get("Ano")), r.get("Rodada"), f.getFileName().toString(), r.get("Arena")));
        }
        return out;
    }

    private List<Match> loadExtended(Path f) throws IOException {
        List<Match> out = new ArrayList<>();
        for (var r : read(f)) {
            Integer hg = num(r.get("home_goal")), ag = num(r.get("away_goal"));
            LocalDate d = date(r.get("date"));
            if (hg == null || ag == null || d == null) continue;
            String t = r.getOrDefault("tournament", "");
            String comp = t.equalsIgnoreCase("Serie A") ? BRASILEIRAO : t;
            out.add(new Match(d, r.get("home"), r.get("away"), hg, ag, comp, d.getYear(), "", f.getFileName().toString(), null));
        }
        return out;
    }

    private List<Player> loadPlayers(Path f) throws IOException {
        List<Player> out = new ArrayList<>();
        for (var r : read(f)) {
            Integer id = num(r.get("ID"));
            if (id == null) continue;
            out.add(new Player(id, r.get("Name"), orZero(num(r.get("Age"))), r.get("Nationality"),
                    orZero(num(r.get("Overall"))), orZero(num(r.get("Potential"))), r.getOrDefault("Club", ""),
                    r.getOrDefault("Position", ""), r.getOrDefault("Jersey Number", ""), r.getOrDefault("Height", ""),
                    r.getOrDefault("Weight", ""), r.getOrDefault("Value", "")));
        }
        return out;
    }

    // ---------- parsing helpers ----------
    static Integer num(String s) {
        if (s == null || s.isBlank()) return null;
        try { return (int) Math.round(Double.parseDouble(s.trim())); } catch (NumberFormatException e) { return null; }
    }

    private static int orZero(Integer i) { return i == null ? 0 : i; }

    private static final DateTimeFormatter BR = DateTimeFormatter.ofPattern("dd/MM/yyyy");

    /** Accepts "2023-09-24", "2012-05-19 18:30:00" and "29/03/2003". */
    public static LocalDate date(String s) {
        if (s == null || s.isBlank()) return null;
        s = s.trim();
        try {
            if (s.contains("/")) return LocalDate.parse(s.split(" ")[0], BR);
            return LocalDate.parse(s.substring(0, 10));
        } catch (RuntimeException e) {
            return null;
        }
    }
}
