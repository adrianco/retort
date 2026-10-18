package br.soccer.mcp;

import br.soccer.data.DataLoader;
import br.soccer.data.Dataset;
import br.soccer.data.Dataset.ClubSummary;
import br.soccer.data.Dataset.HeadToHead;
import br.soccer.data.Dataset.TeamRecord;
import br.soccer.data.Match;
import br.soccer.data.MatchFilter;
import br.soccer.data.MatchFilter.Venue;
import br.soccer.data.Player;
import br.soccer.data.PlayerFilter;
import br.soccer.data.Text;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.LocalDate;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * The MCP tool catalogue. Each tool takes structured arguments and returns plain text that an LLM
 * can relay directly. Natural-language understanding is left to the connected model, which picks the
 * tool and its arguments.
 */
public final class SoccerTools {

    private static final int DEFAULT_LIMIT = 20;
    private static final int MAX_LIMIT = 100;
    private static final ObjectMapper JSON = new ObjectMapper();

    @FunctionalInterface
    private interface Handler {
        String run(JsonNode args);
    }

    private final Dataset data;
    private final ArrayNode definitions = JSON.createArrayNode();
    private final Map<String, Handler> handlers = new LinkedHashMap<>();

    public SoccerTools(Dataset data) {
        this.data = data;

        define("search_matches",
                "Find matches by team, opponent, venue, competition, season, stage or date range. "
                        + "Use for fixtures, results, derbies and finals.",
                this::searchMatches,
                "team:string:Team name in any spelling, e.g. Flamengo or Palmeiras-SP",
                "opponent:string:Second team; returns only matches between the two",
                "venue:string:home, away or any (applies to team)",
                "competition:string:Competition name or part of it, e.g. 'Brasileirão Série A', 'Copa do Brasil', 'Copa Libertadores'",
                "season:integer:Season year, e.g. 2023",
                "stage:string:Stage text such as 'final', 'semifinal' or 'Round 22'",
                "from:string:Earliest date, YYYY-MM-DD",
                "to:string:Latest date, YYYY-MM-DD",
                "limit:integer:Maximum matches to list (default 20, max 100)");

        define("team_record",
                "Wins, draws, losses and goals for a team, optionally filtered by competition, season, venue or date range.",
                this::teamRecord,
                "*team:string:Team name in any spelling",
                "competition:string:Competition name or part of it",
                "season:integer:Season year",
                "venue:string:home, away or any",
                "from:string:Earliest date, YYYY-MM-DD",
                "to:string:Latest date, YYYY-MM-DD");

        define("head_to_head",
                "Head-to-head record between two teams in the dataset, with the most recent meetings.",
                this::headToHead,
                "*team:string:First team",
                "*opponent:string:Second team",
                "competition:string:Competition name or part of it",
                "limit:integer:Number of recent meetings to list (default 20)");

        define("standings",
                "League table for one season calculated from match results (3 points for a win, 1 for a draw).",
                this::standings,
                "*season:integer:Season year, e.g. 2019",
                "competition:string:League name (default 'Brasileirão Série A')");

        define("find_players",
                "Search FIFA player data by name, nationality, club or position, sorted by overall rating.",
                this::findPlayers,
                "name:string:Player name or part of it",
                "nationality:string:Nationality, e.g. Brazil",
                "club:string:Club name or part of it, e.g. Flamengo",
                "position:string:Position code, e.g. ST, GK, CAM",
                "min_overall:integer:Minimum overall rating",
                "limit:integer:Maximum players to list (default 20, max 100)");

        define("club_player_summary",
                "Number of players and average overall rating per club for a nationality.",
                this::clubPlayerSummary,
                "nationality:string:Nationality (default Brazil)",
                "min_overall:integer:Only count players at or above this overall rating",
                "limit:integer:Maximum clubs to list (default 20)");

        define("aggregate_stats",
                "Aggregate statistics: goals_per_match, outcome_rates, biggest_wins, best_home_record, best_away_record.",
                this::aggregateStats,
                "*metric:string:One of goals_per_match, outcome_rates, biggest_wins, best_home_record, best_away_record",
                "competition:string:Competition name or part of it",
                "season:integer:Season year",
                "from:string:Earliest date, YYYY-MM-DD",
                "to:string:Latest date, YYYY-MM-DD",
                "min_games:integer:Minimum games for record rankings (default 10)",
                "limit:integer:Rows to list (default 20)");
    }

    public ArrayNode definitions() {
        return definitions;
    }

    public boolean has(String name) {
        return handlers.containsKey(name);
    }

    /** Runs a tool. Invalid arguments raise IllegalArgumentException, whose message is shown to the caller. */
    public String call(String name, JsonNode args) {
        Handler handler = handlers.get(name);
        if (handler == null) {
            throw new IllegalArgumentException("Unknown tool: " + name);
        }
        return handler.run(args == null || args.isNull() ? JSON.createObjectNode() : args);
    }

    private String searchMatches(JsonNode a) {
        MatchFilter f = new MatchFilter(str(a, "team"), str(a, "opponent"), Venue.parse(str(a, "venue")),
                str(a, "competition"), intArg(a, "season"), dateArg(a, "from"), dateArg(a, "to"), str(a, "stage"));
        List<Match> found = data.findMatches(f);
        int limit = limit(a);
        StringBuilder out = new StringBuilder(unknownTeamNote(f.team(), f.opponent()));
        out.append("Matches found: ").append(found.size()).append('\n');
        if (found.isEmpty()) {
            out.append("No matches fit these filters.\n");
        }
        found.stream().limit(limit).forEach(m -> out.append("- ").append(matchLine(m)).append('\n'));
        if (found.size() > limit) {
            out.append("... (").append(found.size() - limit).append(" more matches in dataset)\n");
        }
        return out.toString();
    }

    private String teamRecord(JsonNode a) {
        MatchFilter f = new MatchFilter(required(a, "team"), null, Venue.parse(str(a, "venue")),
                str(a, "competition"), intArg(a, "season"), dateArg(a, "from"), dateArg(a, "to"), null);
        TeamRecord r = data.teamRecord(f);
        if (r.played() == 0) {
            return unknownTeamNote(f.team()) + "No matches found for " + f.team() + " (" + scope(f) + ").\n";
        }
        return "%s record (%s):\n".formatted(r.team(), scope(f))
                + "- Matches: %d\n".formatted(r.played())
                + "- Wins: %d, Draws: %d, Losses: %d\n".formatted(r.wins(), r.draws(), r.losses())
                + "- Goals For: %d, Goals Against: %d\n".formatted(r.goalsFor(), r.goalsAgainst())
                + "- Win rate: %s\n".formatted(pct(r.winRate()));
    }

    private String headToHead(JsonNode a) {
        String teamA = required(a, "team");
        String teamB = required(a, "opponent");
        String competition = str(a, "competition");
        HeadToHead h = data.headToHead(teamA, teamB, competition);
        if (h.matches().isEmpty()) {
            return unknownTeamNote(teamA, teamB) + "No matches between %s and %s in the dataset.\n".formatted(teamA, teamB);
        }
        StringBuilder out = new StringBuilder("%s vs %s (%s) - head-to-head in dataset:\n".formatted(
                h.a().team(), h.b().team(), competition == null ? "all competitions" : competition));
        out.append("- Matches: %d\n".formatted(h.matches().size()));
        out.append("- Head-to-head: %s %d wins, %s %d wins, %d draws\n".formatted(
                h.a().team(), h.a().wins(), h.b().team(), h.b().wins(), h.a().draws()));
        out.append("- Goals: %s %d, %s %d\n".formatted(
                h.a().team(), h.a().goalsFor(), h.b().team(), h.b().goalsFor()));
        out.append("Most recent:\n");
        h.matches().stream().limit(limit(a)).forEach(m -> out.append("- ").append(matchLine(m)).append('\n'));
        return out.toString();
    }

    private String standings(JsonNode a) {
        int season = requiredInt(a, "season");
        String competition = Objects.requireNonNullElse(str(a, "competition"), DataLoader.SERIE_A);
        List<TeamRecord> table = data.standings(season, competition);
        if (table.isEmpty()) {
            return "No matches for %s in %d.\n".formatted(competition, season);
        }
        boolean league = Text.fold(competition).contains("serie");
        StringBuilder out = new StringBuilder("%d %s standings (calculated from matches):\n".formatted(season, competition));
        int position = 0;
        for (TeamRecord r : table) {
            position++;
            String champion = league && position == 1 ? " - Champion" : "";
            out.append("%d. %s - %d pts (%dW, %dD, %dL) GF %d, GA %d%s\n".formatted(
                    position, r.team(), r.points(), r.wins(), r.draws(), r.losses(),
                    r.goalsFor(), r.goalsAgainst(), champion));
        }
        return out.toString();
    }

    private String findPlayers(JsonNode a) {
        PlayerFilter f = new PlayerFilter(str(a, "name"), str(a, "nationality"), str(a, "club"),
                str(a, "position"), intArg(a, "min_overall"));
        List<Player> all = data.findPlayers(f);
        int limit = limit(a);
        StringBuilder out = new StringBuilder("Players found: ").append(all.size()).append('\n');
        if (all.isEmpty()) {
            out.append("No players fit these filters.\n");
        }
        int rank = 0;
        for (Player p : all.subList(0, Math.min(limit, all.size()))) {
            rank++;
            out.append("%d. %s - Overall: %d, Potential: %d, Position: %s, Club: %s, Nationality: %s, Age: %d\n"
                    .formatted(rank, p.name(), p.overall(), p.potential(), p.position(), p.club(),
                            p.nationality(), p.age()));
        }
        return out.toString();
    }

    private String clubPlayerSummary(JsonNode a) {
        String nationality = Objects.requireNonNullElse(str(a, "nationality"), "Brazil");
        List<ClubSummary> clubs = data.clubSummary(
                new PlayerFilter(null, nationality, null, null, intArg(a, "min_overall")));
        StringBuilder out = new StringBuilder("%s players by club (count, average overall):\n".formatted(nationality));
        if (clubs.isEmpty()) {
            out.append("No players fit these filters.\n");
        }
        int rank = 0;
        for (ClubSummary c : clubs.subList(0, Math.min(limit(a), clubs.size()))) {
            rank++;
            out.append("%d. %s: %d players (avg rating: %.0f)\n".formatted(rank, c.club(), c.players(), c.averageOverall()));
        }
        return out.toString();
    }

    private String aggregateStats(JsonNode a) {
        String metric = required(a, "metric").toLowerCase(Locale.ROOT);
        MatchFilter f = new MatchFilter(null, null, Venue.ANY, str(a, "competition"), intArg(a, "season"),
                dateArg(a, "from"), dateArg(a, "to"), null);
        int limit = limit(a);
        int minGames = Objects.requireNonNullElse(intArg(a, "min_games"), 10);
        String scope = scope(f);
        return switch (metric) {
            case "goals_per_match" -> "Average goals per match (%s): %.2f over %d matches\n".formatted(
                    scope, data.goalsPerMatch(f), data.findMatches(f).size());
            case "outcome_rates" -> {
                Dataset.Rates r = data.outcomeRates(f);
                yield "Outcomes (%s, %d matches):\n".formatted(scope, r.matches())
                        + "- Home win rate: %s\n".formatted(pct(r.homeWinRate()))
                        + "- Draw rate: %s\n".formatted(pct(r.drawRate()))
                        + "- Away win rate: %s\n".formatted(pct(r.awayWinRate()));
            }
            case "biggest_wins" -> {
                StringBuilder out = new StringBuilder("Biggest wins (%s):\n".formatted(scope));
                int rank = 0;
                for (Match m : data.biggestWins(f, limit)) {
                    out.append("%d. %s\n".formatted(++rank, matchLine(m)));
                }
                yield out.toString();
            }
            case "best_home_record" -> rankedRecords("home", scope,
                    data.venueRecords(f, Venue.HOME, minGames, limit));
            case "best_away_record" -> rankedRecords("away", scope,
                    data.venueRecords(f, Venue.AWAY, minGames, limit));
            default -> throw new IllegalArgumentException("Unknown metric '" + metric
                    + "'. Use goals_per_match, outcome_rates, biggest_wins, best_home_record or best_away_record.");
        };
    }

    private static String rankedRecords(String side, String scope, List<TeamRecord> records) {
        StringBuilder out = new StringBuilder("Best %s records (%s):\n".formatted(side, scope));
        if (records.isEmpty()) {
            out.append("No teams meet the minimum number of games.\n");
        }
        int rank = 0;
        for (TeamRecord r : records) {
            out.append("%d. %s - %d wins in %d %s matches (%s win rate)\n".formatted(
                    ++rank, r.team(), r.wins(), r.played(), side, pct(r.winRate())));
        }
        return out.toString();
    }

    private String unknownTeamNote(String... names) {
        StringBuilder note = new StringBuilder();
        for (String name : names) {
            if (name != null && !data.knowsTeam(name)) {
                note.append("Unknown team '").append(name).append("' - check the spelling.\n");
            }
        }
        return note.toString();
    }

    private static String matchLine(Match m) {
        String where = m.stage() == null ? m.competition() : m.competition() + ", " + m.stage();
        return "%s: %s %d-%d %s (%s)".formatted(m.date(), m.home(), m.homeGoals(), m.awayGoals(), m.away(), where);
    }

    private static String scope(MatchFilter f) {
        String venue = f.venue() == Venue.ANY ? null : f.venue().name().toLowerCase(Locale.ROOT) + " matches";
        String season = f.season() == null ? null : String.valueOf(f.season());
        String joined = join(", ", f.competition(), season, venue);
        return joined.isEmpty() ? "all competitions" : joined;
    }

    private static String join(String separator, String... parts) {
        return Arrays.stream(parts).filter(Objects::nonNull).collect(Collectors.joining(separator));
    }

    private static String pct(double rate) {
        return String.format(Locale.ROOT, "%.1f%%", rate * 100);
    }

    private void define(String name, String description, Handler handler, String... params) {
        ObjectNode schema = JSON.createObjectNode().put("type", "object");
        ObjectNode properties = schema.putObject("properties");
        ArrayNode requiredNames = schema.putArray("required");
        for (String param : params) {
            boolean isRequired = param.startsWith("*");
            String[] parts = (isRequired ? param.substring(1) : param).split(":", 3);
            properties.putObject(parts[0]).put("type", parts[1]).put("description", parts[2]);
            if (isRequired) {
                requiredNames.add(parts[0]);
            }
        }
        ObjectNode definition = definitions.addObject();
        definition.put("name", name);
        definition.put("description", description);
        definition.set("inputSchema", schema);
        handlers.put(name, handler);
    }

    private static String str(JsonNode a, String key) {
        JsonNode n = a.get(key);
        if (n == null || n.isNull() || n.asText().isBlank()) {
            return null;
        }
        return n.asText().trim();
    }

    private static String required(JsonNode a, String key) {
        String value = str(a, key);
        if (value == null) {
            throw new IllegalArgumentException("Missing required argument '" + key + "'");
        }
        return value;
    }

    private static Integer intArg(JsonNode a, String key) {
        String value = str(a, key);
        if (value == null) {
            return null;
        }
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("'" + key + "' must be an integer");
        }
    }

    private static int requiredInt(JsonNode a, String key) {
        Integer value = intArg(a, key);
        if (value == null) {
            throw new IllegalArgumentException("Missing required argument '" + key + "'");
        }
        return value;
    }

    private static LocalDate dateArg(JsonNode a, String key) {
        String value = str(a, key);
        if (value == null) {
            return null;
        }
        LocalDate date = Text.parseDate(value);
        if (date == null) {
            throw new IllegalArgumentException("'" + key + "' must be a date such as 2023-09-03");
        }
        return date;
    }

    private static int limit(JsonNode a) {
        Integer value = intArg(a, "limit");
        return value == null ? DEFAULT_LIMIT : Math.max(1, Math.min(value, MAX_LIMIT));
    }
}
