package soccer;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVRecord;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.ResolverStyle;
import java.util.*;
import java.util.function.Consumer;
import java.util.stream.Collectors;

final class SoccerData {
    static final String LEAGUE = "Brasileirão";
    static final String CUP = "Copa do Brasil";
    static final String LIBERTADORES = "Libertadores";
    static final String HISTORICAL = "novo_campeonato_brasileiro.csv";
    static final String SERIE_A = "Brasileirao_Matches.csv";
    static final String CUP_FILE = "Brazilian_Cup_Matches.csv";
    static final String LIBERTADORES_FILE = "Libertadores_Matches.csv";
    static final String EXTENDED = "BR-Football-Dataset.csv";
    static final String FIFA = "fifa_data.csv";

    record Match(String date, String time, Integer season, String competition, String stage,
                 String home, String away, Integer homeGoals, Integer awayGoals,
                 String stadium, Map<String, String> statistics, List<String> sources) {
        boolean played() {
            return homeGoals != null && awayGoals != null;
        }

        int margin() {
            return Math.abs(homeGoals - awayGoals);
        }

        String summary() {
            String score = played() ? homeGoals + "–" + awayGoals : "vs";
            return "%s | %s %s %s | %s%s%s".formatted(date.isEmpty() ? "Date unavailable" : date,
                    home, score, away, competition, stage.isEmpty() ? "" : " " + stage,
                    played() ? "" : " (score unavailable)");
        }
    }

    record Player(int id, String name, int overall, String nationality, String club, String position,
                  Map<String, String> attributes) {}

    private record Fixture(String competition, Integer season, String day, String home, String away) {}
    private record DayFixture(String competition, String day, String home, String away) {}

    final Map<String, List<Match>> bySource;
    final List<Match> matches;
    final Map<String, List<Match>> byTeam;
    final List<Player> players;

    SoccerData(Path root) throws IOException {
        Map<String, List<Match>> sources = new LinkedHashMap<>();
        sources.put(HISTORICAL, matches(root, HISTORICAL));
        sources.put(SERIE_A, matches(root, SERIE_A));
        sources.put(CUP_FILE, matches(root, CUP_FILE));
        sources.put(LIBERTADORES_FILE, matches(root, LIBERTADORES_FILE));
        sources.put(EXTENDED, matches(root, EXTENDED));
        bySource = Collections.unmodifiableMap(sources);

        Map<Fixture, Match> fixtures = new LinkedHashMap<>();
        Map<DayFixture, Fixture> calendar = new HashMap<>();
        Map<Fixture, Set<Fixture>> leaguePairings = new HashMap<>();
        for (List<Match> rows : sources.values()) {
            for (Match match : rows) {
                String home = Names.teamKey(match.home);
                String away = Names.teamKey(match.away);
                // Série A's dedicated sources include round numbers even when fixture dates differ.
                boolean league = match.competition.equals(LEAGUE);
                String roundOrDay = league && !match.stage.isEmpty() ? match.stage : match.date;
                Fixture fixture = new Fixture(match.competition, match.season, roundOrDay, home, away);
                Fixture pairing = new Fixture(match.competition, match.season, "", home, away);
                DayFixture dateKey = new DayFixture(match.competition, match.date, home, away);
                Fixture existing = calendar.get(dateKey);
                if (existing == null && match.sources.contains(EXTENDED) && !match.date.isEmpty()) {
                    // The extended feed sometimes dates evening games one day later.
                    LocalDate date = LocalDate.parse(match.date);
                    for (int shift : new int[]{-1, 1}) {
                        Fixture nearby = calendar.get(new DayFixture(match.competition,
                                date.plusDays(shift).toString(), home, away));
                        if (nearby != null) {
                            existing = nearby;
                            break;
                        }
                    }
                }
                if (existing == null && league && match.sources.contains(EXTENDED)) {
                    Set<Fixture> candidates = leaguePairings.getOrDefault(pairing, Set.of());
                    if (candidates.size() == 1) {
                        existing = candidates.iterator().next();
                    }
                }
                if (existing != null) {
                    fixture = existing;
                }
                if (league && !match.sources.contains(EXTENDED)) {
                    leaguePairings.computeIfAbsent(pairing, key -> new HashSet<>()).add(fixture);
                }
                calendar.putIfAbsent(dateKey, fixture);
                fixtures.merge(fixture, match, SoccerData::merge);
            }
        }
        matches = sorted(fixtures.values());
        Map<String, List<Match>> teams = new HashMap<>();
        for (Match match : matches) {
            teams.computeIfAbsent(Names.teamKey(match.home), key -> new ArrayList<>()).add(match);
            if (!Names.teamKey(match.home).equals(Names.teamKey(match.away))) {
                teams.computeIfAbsent(Names.teamKey(match.away), key -> new ArrayList<>()).add(match);
            }
        }
        teams.replaceAll((name, rows) -> List.copyOf(rows));
        byTeam = Map.copyOf(teams);

        List<Player> roster = new ArrayList<>();
        read(root.resolve(FIFA), row -> {
            Map<String, String> fields = row.toMap();
            fields.remove("\uFEFF");
            fields.remove("");
            fields.values().removeIf(String::isBlank);
            roster.add(new Player(number(row.get("ID")), row.get("Name"), number(row.get("Overall")),
                    row.get("Nationality"), row.get("Club"), row.get("Position"), Map.copyOf(fields)));
        });
        players = roster.stream().sorted(Comparator.comparingInt(Player::overall).reversed()
                .thenComparing(Player::name).thenComparingInt(Player::id)).toList();
    }

    private static Match merge(Match first, Match other) {
        Match result = first.played() ? first : other;
        Map<String, String> statistics = new LinkedHashMap<>(other.statistics);
        statistics.putAll(first.statistics);
        List<String> sources = java.util.stream.Stream.concat(first.sources.stream(), other.sources.stream())
                .distinct().toList();
        return new Match(result.date, prefer(result.time, prefer(first.time, other.time)),
                first.season, first.competition, prefer(first.stage, other.stage),
                first.home, first.away, result.homeGoals, result.awayGoals,
                prefer(first.stadium, other.stadium), Map.copyOf(statistics), sources);
    }

    private static String prefer(String first, String other) {
        return first.isBlank() ? other : first;
    }

    private static List<Match> matches(Path root, String source) throws IOException {
        List<Match> rows = new ArrayList<>();
        read(root.resolve(source), row -> rows.add(parseMatch(source, row)));
        if (source.equals(CUP_FILE)) {
            Map<Integer, List<Match>> seasons = rows.stream().collect(Collectors.groupingBy(Match::season));
            Set<Match> finals = new HashSet<>();
            for (List<Match> season : seasons.values()) {
                int lastRound = season.stream().mapToInt(match -> Integer.parseInt(match.stage.substring(6))).max().orElseThrow();
                finals.addAll(finalLegs(season.stream().filter(match -> match.stage.equals("Round " + lastRound)).toList()));
            }
            rows.replaceAll(match -> finals.contains(match) ? withStage(match, "final") : match);
        }
        if (source.equals(EXTENDED)) {
            Map<Integer, List<Match>> cup = rows.stream().filter(match -> match.competition.equals(CUP))
                    .collect(Collectors.groupingBy(Match::season));
            Set<Match> finals = new HashSet<>();
            for (int season : cup.keySet()) {
                if (season >= 2021) {
                    finals.addAll(finalLegs(sorted(cup.get(season)).stream().limit(2).toList()));
                }
            }
            rows.replaceAll(match -> finals.contains(match) ? withStage(match, "final") : match);
        }
        return sorted(rows);
    }

    private static List<Match> finalLegs(List<Match> matches) {
        if (matches.size() == 2 && matches.get(0).home.equals(matches.get(1).away)
                && matches.get(0).away.equals(matches.get(1).home)) {
            return matches;
        }
        return List.of();
    }

    private static Match withStage(Match match, String stage) {
        Map<String, String> statistics = new LinkedHashMap<>(match.statistics);
        if (!match.stage.isEmpty()) {
            statistics.put("sourceRound", match.stage);
        }
        return new Match(match.date, match.time, match.season, match.competition, stage, match.home, match.away,
                match.homeGoals, match.awayGoals, match.stadium, Map.copyOf(statistics), match.sources);
    }

    private static List<Match> sorted(Collection<Match> rows) {
        return rows.stream().sorted(Comparator.comparing(Match::date).thenComparing(Match::time).reversed()
                .thenComparing(Match::competition).thenComparing(Match::home).thenComparing(Match::away)).toList();
    }

    private static Match parseMatch(String source, CSVRecord row) {
        if (source.equals(HISTORICAL)) {
            return new Match(date(row.get("Data")), "", number(row.get("Ano")), LEAGUE,
                    "Round " + row.get("Rodada"), Names.team(row.get("Equipe_mandante")),
                    Names.team(row.get("Equipe_visitante")), number(row.get("Gols_mandante")),
                    number(row.get("Gols_visitante")), row.get("Arena"), Map.of(
                        "id", row.get("ID"), "homeState", row.get("Mandante_UF"), "awayState", row.get("Visitante_UF"),
                        "winner", row.get("Vencedor"), "notes", row.get("OBS")), List.of(source));
        }
        if (source.equals(EXTENDED)) {
            String date = date(row.get("date"));
            Map<String, String> statistics = row.toMap();
            for (String key : List.of("date", "time", "home", "away", "home_goal", "away_goal", "tournament")) {
                statistics.remove(key);
            }
            return new Match(date, row.get("time"), Integer.parseInt(date.substring(0, 4)),
                    Names.competition(row.get("tournament")), "", Names.team(row.get("home")),
                    Names.team(row.get("away")), number(row.get("home_goal")), number(row.get("away_goal")),
                    "", Map.copyOf(statistics), List.of(source));
        }
        String[] datetime = row.get("datetime").split(" ", 2);
        String stage = source.equals(LIBERTADORES_FILE) ? row.get("stage") : "Round " + row.get("round");
        String competition = switch (source) {
            case SERIE_A -> LEAGUE;
            case CUP_FILE -> CUP;
            default -> LIBERTADORES;
        };
        Map<String, String> states = source.equals(SERIE_A)
                ? Map.of("homeState", row.get("home_team_state"), "awayState", row.get("away_team_state"))
                : Map.of();
        return new Match(date(datetime[0]), datetime.length == 2 ? datetime[1] : "", number(row.get("season")),
                competition, stage, Names.team(row.get("home_team")), Names.team(row.get("away_team")),
                number(row.get("home_goal")), number(row.get("away_goal")), "", states, List.of(source));
    }

    static String date(String value) {
        if (value.equals("NA")) {
            return "";
        }
        DateTimeFormatter formatter = value.contains("/")
                ? DateTimeFormatter.ofPattern("d/M/uuuu").withResolverStyle(ResolverStyle.STRICT)
                : DateTimeFormatter.ISO_LOCAL_DATE;
        return LocalDate.parse(value, formatter).toString();
    }

    private static Integer number(String value) {
        return switch (value) {
            case "", "NA", "-" -> null;
            default -> new java.math.BigDecimal(value).intValueExact();
        };
    }

    private static void read(Path path, Consumer<CSVRecord> consumer) throws IOException {
        try (var reader = Files.newBufferedReader(path);
             var csv = CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).build().parse(reader)) {
            for (CSVRecord row : csv) {
                try {
                    consumer.accept(row);
                } catch (RuntimeException exception) {
                    throw new IOException(path + ", record " + row.getRecordNumber(), exception);
                }
            }
        }
    }
}
