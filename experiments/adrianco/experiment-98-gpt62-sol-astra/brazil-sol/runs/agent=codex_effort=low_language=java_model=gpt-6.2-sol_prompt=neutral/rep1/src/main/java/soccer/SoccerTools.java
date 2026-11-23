package soccer;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.*;
import java.util.function.Function;
import java.util.function.Predicate;
import java.util.stream.Collectors;
import java.util.stream.Stream;

final class SoccerTools {
    record Answer(String text, Object data) {}

    private record Report(String team, int matches, int wins, int draws, int losses,
                          int goalsFor, int goalsAgainst, int goalDifference, int points, double winRate) {}

    private static final class Record {
        int wins, draws, losses, goalsFor, goalsAgainst;

        void add(int scored, int conceded) {
            goalsFor += scored;
            goalsAgainst += conceded;
            wins += scored > conceded ? 1 : 0;
            draws += scored == conceded ? 1 : 0;
            losses += scored < conceded ? 1 : 0;
        }

        Report report(String team) {
            int played = wins + draws + losses;
            return new Report(team, played, wins, draws, losses, goalsFor, goalsAgainst,
                    goalsFor - goalsAgainst, 3 * wins + draws, rate(wins, played));
        }
    }

    private static final Set<Set<String>> DERBIES = derbies();
    private static final Set<String> FORWARDS = Set.of("ST", "CF", "LF", "RF", "LS", "RS", "LW", "RW");
    private static final Comparator<Report> TABLE_ORDER = Comparator.comparingInt(Report::points).reversed()
            .thenComparing(Comparator.comparingInt(Report::wins).reversed())
            .thenComparing(Comparator.comparingInt(Report::goalDifference).reversed())
            .thenComparing(Comparator.comparingInt(Report::goalsFor).reversed())
            .thenComparing(Report::team);
    private final SoccerData data;

    SoccerTools(SoccerData data) {
        this.data = data;
    }

    Answer searchMatches(JsonNode args) {
        List<SoccerData.Match> matches = fixtures(args).toList();
        return page("fixtures", matches, args, SoccerData.Match::summary);
    }

    Answer headToHead(JsonNode args) {
        String team = required(args, "team");
        String opponent = required(args, "opponent");
        if (Names.teamKey(team).equals(Names.teamKey(opponent))) {
            throw new IllegalArgumentException("Choose two different teams.");
        }
        List<SoccerData.Match> matches = fixtures(args).toList();
        Report report = record(team, matches.stream(), null);
        Answer listing = page("head-to-head fixtures", matches, args, SoccerData.Match::summary);
        return new Answer(describe(report) + "\n" + listing.text, Map.of("record", report,
                "opponent", Names.team(opponent), "opponentWins", report.losses, "fixtures", listing.data));
    }

    Answer teamRecord(JsonNode args) {
        String team = required(args, "team");
        List<SoccerData.Match> matches = fixtures(args).toList();
        Report overall = record(team, matches.stream(), null);
        Report home = record(team, matches.stream(), "home");
        Report away = record(team, matches.stream(), "away");
        Map<String, Report> groups = new TreeMap<>();
        String groupBy = text(args, "groupBy");
        if ("season".equals(groupBy)) {
            for (var entry : matches.stream().filter(match -> match.season() != null)
                    .collect(Collectors.groupingBy(SoccerData.Match::season)).entrySet()) {
                groups.put(entry.getKey().toString(), record(team, entry.getValue().stream(), null));
            }
        } else {
            for (var entry : matches.stream().collect(Collectors.groupingBy(SoccerData.Match::competition)).entrySet()) {
                groups.put(entry.getKey(), record(team, entry.getValue().stream(), null));
            }
        }
        StringBuilder summary = new StringBuilder(describe(overall)).append("\nHome: ").append(describe(home))
                .append("\nAway: ").append(describe(away));
        groups.forEach((group, report) -> summary.append("\n").append(group).append(": ").append(describe(report)));
        return new Answer(summary.toString(), Map.of("overall", overall, "home", home, "away", away, "groups", groups));
    }

    Answer players(JsonNode args) {
        String name = text(args, "name");
        String club = text(args, "club");
        String country = text(args, "nationality");
        String position = text(args, "position");
        String nameKey = name == null ? "" : Names.fold(name);
        String countryKey = country == null ? "" : Names.fold(country);
        if (countryKey.equals("brazilian") || countryKey.equals("brasil")) {
            countryKey = "brazil";
        }
        String nationality = countryKey;
        String clubKey = club == null ? "" : Names.teamKey(club);
        List<SoccerData.Player> players = data.players.stream()
                .filter(player -> nameKey.isEmpty() || Names.fold(player.name()).contains(nameKey))
                .filter(player -> nationality.isEmpty() || Names.fold(player.nationality()).equals(nationality))
                .filter(player -> clubKey.isEmpty() || Names.teamKey(player.club()).equals(clubKey)
                        || (!data.byTeam.containsKey(clubKey) && Names.fold(player.club()).contains(Names.fold(club))))
                .filter(player -> position == null || positionMatches(position, player.position()))
                .toList();
        return page("FIFA snapshot players", players, args, player -> "%s | %s OVR | %s | %s | %s".formatted(
                player.name(), player.overall(), player.position(), player.club(), player.nationality()));
    }

    private static boolean positionMatches(String position, String actual) {
        return switch (Names.fold(position)) {
            case "forward", "forwards" -> FORWARDS.contains(actual);
            case "midfielder", "midfielders" -> actual.endsWith("M");
            case "defender", "defenders" -> actual.endsWith("B") || actual.endsWith("WB");
            case "goalkeeper", "goalkeepers" -> actual.equals("GK");
            default -> actual.equalsIgnoreCase(position);
        };
    }

    Answer clubProfile(JsonNode args) {
        Answer record = teamRecord(args);
        var rosterArgs = args.deepCopy();
        ((com.fasterxml.jackson.databind.node.ObjectNode) rosterArgs).put("club", required(args, "team"));
        Answer roster = players(rosterArgs);
        return new Answer(record.text + "\n\n" + roster.text, Map.of("matchRecord", record.data, "players", roster.data));
    }

    Answer standings(JsonNode args) {
        int season = requiredInt(args, "season");
        String competition = Optional.ofNullable(text(args, "competition")).map(Names::competition).orElse(SoccerData.LEAGUE);
        if (!competition.equals(SoccerData.LEAGUE) && !competition.equals("Série B")) {
            throw new IllegalArgumentException("Standings support Brasileirão Série A and Série B. Use search_matches for cup stages.");
        }
        List<SoccerData.Match> matches = fixtures(args).filter(match -> match.competition().equals(competition)).toList();
        if (competition.equals(SoccerData.LEAGUE) && !args.has("source")) {
            List<SoccerData.Match> dedicated = matches.stream().filter(match ->
                    match.sources().contains(SoccerData.SERIE_A) || match.sources().contains(SoccerData.HISTORICAL)).toList();
            if (!dedicated.isEmpty()) {
                matches = dedicated;
            }
        }
        List<Report> reports = table(matches.stream(), null).stream().sorted(TABLE_ORDER).toList();
        boolean complete = reports.size() >= 2 && reports.stream()
                .allMatch(report -> report.matches == 2 * (reports.size() - 1));
        List<String> bottom = complete && competition.equals(SoccerData.LEAGUE)
                ? reports.subList(Math.max(0, reports.size() - (season == 2003 ? 2 : 4)), reports.size())
                        .stream().map(Report::team).toList()
                : List.of();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("season", season);
        result.put("competition", competition);
        result.put("completeDoubleRoundRobin", complete);
        result.put("standings", reports);
        result.put("bottomPositions", bottom);
        if (complete) {
            result.put("leader", reports.get(0).team);
        }
        StringBuilder summary = new StringBuilder("%d %s standings from recorded scores%s\n".formatted(
                season, competition, complete ? "" : " (incomplete fixture coverage)"));
        for (int i = 0; i < reports.size(); i++) {
            summary.append(i + 1).append(". ").append(describe(reports.get(i))).append("\n");
        }
        if (!bottom.isEmpty()) {
            summary.append("Bottom positions: ").append(String.join(", ", bottom)).append("\n");
        }
        summary.append("Calculated table uses three points per win and excludes administrative adjustments.");
        return new Answer(summary.toString(), result);
    }

    Answer rankings(JsonNode args) {
        String metric = Optional.ofNullable(text(args, "metric")).orElse("winRate");
        Comparator<Report> comparator = switch (metric) {
            case "wins" -> Comparator.comparingInt(Report::wins);
            case "goals" -> Comparator.comparingInt(Report::goalsFor);
            case "winRate" -> Comparator.comparingDouble(Report::winRate);
            case "points" -> Comparator.comparingInt(Report::points);
            default -> throw new IllegalArgumentException("Unknown ranking metric.");
        };
        int minimum = integer(args, "minimumMatches", 1);
        List<Report> reports = table(fixtures(args), text(args, "venue")).stream()
                .filter(report -> report.matches >= minimum)
                .sorted(comparator.reversed().thenComparing(Comparator.comparingInt(Report::matches).reversed())
                        .thenComparing(Report::team)).toList();
        return page("teams ranked by " + metric, reports, args, SoccerTools::describe);
    }

    Answer statistics(JsonNode args) {
        List<SoccerData.Match> matches = fixtures(args).filter(SoccerData.Match::played).toList();
        return switch (Optional.ofNullable(text(args, "mode")).orElse("summary")) {
            case "biggestWins" -> page("victories by goal margin", matches.stream().filter(match -> match.margin() > 0)
                    .sorted(Comparator.comparingInt(SoccerData.Match::margin).reversed()).toList(),
                    args, SoccerData.Match::summary);
            case "bySeason" -> {
                Map<Integer, Map<String, Number>> seasons = new TreeMap<>();
                matches.stream().filter(match -> match.season() != null)
                        .collect(Collectors.groupingBy(SoccerData.Match::season))
                        .forEach((year, rows) -> seasons.put(year, aggregate(rows)));
                String summary = seasons.entrySet().stream()
                        .map(entry -> entry.getKey() + " | " + describeAggregate(entry.getValue()))
                        .collect(Collectors.joining("\n"));
                yield new Answer(summary.isBlank() ? "No scored fixtures found." : summary, seasons);
            }
            case "summary" -> {
                Map<String, Number> values = aggregate(matches);
                yield new Answer(describeAggregate(values), values);
            }
            default -> throw new IllegalArgumentException("Unknown statistics mode.");
        };
    }

    private Stream<SoccerData.Match> fixtures(JsonNode args) {
        String team = text(args, "team");
        String home = text(args, "home");
        String away = text(args, "away");
        String opponent = text(args, "opponent");
        String venue = text(args, "venue");
        String comp = text(args, "competition");
        String stage = text(args, "stage");
        String source = text(args, "source");
        String from = dateArgument(args, "from");
        String to = dateArgument(args, "to");
        Integer season = optionalInt(args, "season");
        Integer fromSeason = optionalInt(args, "fromSeason");
        Integer toSeason = optionalInt(args, "toSeason");
        if ((from != null && to != null && from.compareTo(to) > 0)
                || (fromSeason != null && toSeason != null && fromSeason > toSeason)) {
            throw new IllegalArgumentException("Range start must precede its end.");
        }
        if (opponent != null && team == null) {
            throw new IllegalArgumentException("Supply team when filtering by opponent.");
        }
        List<SoccerData.Match> base = source != null ? data.bySource.get(source)
                : team == null ? data.matches : data.byTeam.getOrDefault(Names.teamKey(team), List.of());
        if (base == null) {
            throw new IllegalArgumentException("Unknown match source: " + source);
        }
        Predicate<SoccerData.Match> forTeam = involving(team, venue);
        Predicate<SoccerData.Match> forOpponent = involving(opponent, null);
        Predicate<SoccerData.Match> forHome = involving(home, "home");
        Predicate<SoccerData.Match> forAway = involving(away, "away");
        String competition = comp == null ? null : Names.competition(comp);
        String stageKey = stage == null ? null : Names.fold(stage);
        if ("finals".equals(stageKey)) {
            stageKey = "final";
        }
        String filterStage = stageKey;
        return base.stream().filter(forTeam.and(forOpponent).and(forHome).and(forAway))
                .filter(match -> competition == null || match.competition().equalsIgnoreCase(competition))
                .filter(match -> filterStage == null || Names.fold(match.stage()).equals(filterStage)
                        || Names.fold(match.statistics().getOrDefault("sourceRound", "")).equals(filterStage))
                .filter(match -> season == null || season.equals(match.season()))
                .filter(match -> fromSeason == null || (match.season() != null && match.season() >= fromSeason))
                .filter(match -> toSeason == null || (match.season() != null && match.season() <= toSeason))
                .filter(match -> from == null || (!match.date().isEmpty() && match.date().compareTo(from) >= 0))
                .filter(match -> to == null || (!match.date().isEmpty() && match.date().compareTo(to) <= 0))
                .filter(match -> !args.path("playedOnly").asBoolean() || match.played())
                .filter(match -> !args.path("derby").asBoolean() || isDerby(match));
    }

    private static boolean isDerby(SoccerData.Match match) {
        String home = Names.teamKey(match.home());
        String away = Names.teamKey(match.away());
        return !home.equals(away) && DERBIES.contains(Set.of(home, away));
    }

    private static Set<Set<String>> derbies() {
        Set<Set<String>> rivals = new HashSet<>();
        for (List<String> group : List.of(List.of("Flamengo", "Fluminense", "Vasco", "Botafogo"),
                List.of("Corinthians", "Palmeiras", "São Paulo", "Santos"), List.of("Grêmio", "Internacional"),
                List.of("Atlético-MG", "Cruzeiro"), List.of("Athletico-PR", "Coritiba"), List.of("Bahia", "Vitória"),
                List.of("Ceará", "Fortaleza"), List.of("Sport", "Náutico", "Santa Cruz"),
                List.of("Goiás", "Vila Nova", "Atlético-GO"), List.of("Paysandu", "Remo"),
                List.of("Avaí", "Figueirense"), List.of("CRB", "CSA"), List.of("Ponte Preta", "Guarani"))) {
            for (int i = 0; i < group.size(); i++) {
                for (int j = i + 1; j < group.size(); j++) {
                    rivals.add(Set.of(Names.teamKey(group.get(i)), Names.teamKey(group.get(j))));
                }
            }
        }
        return Set.copyOf(rivals);
    }

    private static Predicate<SoccerData.Match> involving(String team, String venue) {
        if (team == null) {
            return match -> true;
        }
        String key = Names.teamKey(team);
        return match -> (!"away".equals(venue) && Names.teamKey(match.home()).equals(key))
                || (!"home".equals(venue) && Names.teamKey(match.away()).equals(key));
    }

    private static Report record(String team, Stream<SoccerData.Match> matches, String venue) {
        String key = Names.teamKey(team);
        Record totals = new Record();
        matches.filter(SoccerData.Match::played).filter(involving(team, venue)).forEach(match -> {
            boolean home = Names.teamKey(match.home()).equals(key);
            totals.add(home ? match.homeGoals() : match.awayGoals(), home ? match.awayGoals() : match.homeGoals());
        });
        return totals.report(Names.team(team));
    }

    private static List<Report> table(Stream<SoccerData.Match> matches, String venue) {
        Map<String, Record> totals = new HashMap<>();
        Map<String, String> labels = new HashMap<>();
        matches.filter(SoccerData.Match::played).forEach(match -> {
            if (!"away".equals(venue)) {
                String home = Names.teamKey(match.home());
                labels.putIfAbsent(home, match.home());
                totals.computeIfAbsent(home, team -> new Record()).add(match.homeGoals(), match.awayGoals());
            }
            if (!"home".equals(venue)) {
                String away = Names.teamKey(match.away());
                labels.putIfAbsent(away, match.away());
                totals.computeIfAbsent(away, team -> new Record()).add(match.awayGoals(), match.homeGoals());
            }
        });
        return totals.entrySet().stream().map(entry -> entry.getValue().report(labels.get(entry.getKey()))).toList();
    }

    private static Map<String, Number> aggregate(List<SoccerData.Match> matches) {
        int homeWins = 0, awayWins = 0, goals = 0;
        for (SoccerData.Match match : matches) {
            goals += match.homeGoals() + match.awayGoals();
            homeWins += match.homeGoals() > match.awayGoals() ? 1 : 0;
            awayWins += match.homeGoals() < match.awayGoals() ? 1 : 0;
        }
        int count = matches.size();
        return Map.of("matches", count, "goals", goals, "averageGoals", count == 0 ? 0.0 : (double) goals / count,
                "homeWins", homeWins, "awayWins", awayWins, "draws", count - homeWins - awayWins,
                "homeWinRate", rate(homeWins, count), "awayWinRate", rate(awayWins, count));
    }

    private static double rate(int wins, int played) {
        return played == 0 ? 0.0 : (double) wins / played;
    }

    private static String describe(Report report) {
        return String.format(Locale.ROOT, "%s | %d matches | %d W, %d D, %d L | %d GF, %d GA | %d pts | %.1f%% wins",
                report.team, report.matches, report.wins, report.draws, report.losses,
                report.goalsFor, report.goalsAgainst, report.points, 100 * report.winRate);
    }

    private static String describeAggregate(Map<String, Number> stats) {
        return String.format(Locale.ROOT, "%d scored fixtures | %.2f goals per match | %.1f%% home wins | %.1f%% away wins",
                stats.get("matches"), stats.get("averageGoals"), 100 * stats.get("homeWinRate").doubleValue(),
                100 * stats.get("awayWinRate").doubleValue());
    }

    private static <T> Answer page(String label, List<T> rows, JsonNode args, Function<T, String> format) {
        int offset = integer(args, "offset", 0);
        int limit = integer(args, "limit", 20);
        int start = Math.min(offset, rows.size());
        int end = start + Math.min(limit, rows.size() - start);
        List<T> items = rows.subList(start, end);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("total", rows.size());
        result.put("offset", offset);
        result.put("items", items);
        if (end < rows.size()) {
            result.put("nextOffset", end);
        }
        StringBuilder summary = new StringBuilder("%d %s found".formatted(rows.size(), label));
        if (!items.isEmpty()) {
            summary.append(" (showing ").append(start + 1).append("–").append(end).append(")");
        }
        items.forEach(item -> summary.append("\n- ").append(format.apply(item)));
        return new Answer(summary.toString(), result);
    }

    static String text(JsonNode args, String key) {
        return args.has(key) ? args.get(key).textValue().strip() : null;
    }

    private static String required(JsonNode args, String key) {
        return Optional.ofNullable(text(args, key)).orElseThrow(() -> new IllegalArgumentException("Supply " + key));
    }

    private static int integer(JsonNode args, String key, int defaultValue) {
        return args.has(key) ? args.get(key).intValue() : defaultValue;
    }

    private static int requiredInt(JsonNode args, String key) {
        return args.get(key).intValue();
    }

    private static Integer optionalInt(JsonNode args, String key) {
        return args.has(key) ? args.get(key).intValue() : null;
    }

    private static String dateArgument(JsonNode args, String key) {
        String value = text(args, key);
        if (value == null) {
            return null;
        }
        try {
            String normalized = SoccerData.date(value);
            if (!normalized.isEmpty()) {
                return normalized;
            }
        } catch (java.time.DateTimeException ignored) {
            // Return an actionable tool error for invalid calendar dates.
        }
        throw new IllegalArgumentException(key + " must be a date in YYYY-MM-DD or DD/MM/YYYY format.");
    }
}
