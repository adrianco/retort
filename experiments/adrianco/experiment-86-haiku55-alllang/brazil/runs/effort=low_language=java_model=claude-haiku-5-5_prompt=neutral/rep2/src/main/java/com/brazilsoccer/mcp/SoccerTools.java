package com.brazilsoccer.mcp;

import com.brazilsoccer.data.DataLoader;
import com.brazilsoccer.data.Match;
import com.brazilsoccer.data.Player;
import com.brazilsoccer.query.SoccerQueries;
import com.brazilsoccer.query.SoccerQueries.HeadToHead;
import com.brazilsoccer.query.SoccerQueries.LeagueStats;
import com.brazilsoccer.query.SoccerQueries.MatchFilter;
import com.brazilsoccer.query.SoccerQueries.PlayerFilter;
import com.brazilsoccer.query.SoccerQueries.Venue;
import com.brazilsoccer.query.TeamTally;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.time.LocalDate;
import java.util.List;
import java.util.Locale;

/**
 * The MCP tools exposed to the LLM. Each tool parses its JSON arguments, calls {@link SoccerQueries},
 * and returns plain-text output formatted for a model to read. Invalid arguments throw
 * {@link IllegalArgumentException}, which the server reports back as a tool error.
 */
public final class SoccerTools {

    static final String DEFAULT_COMPETITION = DataLoader.SERIE_A;
    private static final int DEFAULT_LIMIT = 20;
    private static final int MAX_LIMIT = 100;

    private final SoccerQueries queries;
    private final ObjectMapper mapper;

    public SoccerTools(SoccerQueries queries, ObjectMapper mapper) {
        this.queries = queries;
        this.mapper = mapper;
    }

    /** The tool list returned by {@code tools/list}. */
    public ArrayNode definitions() {
        ArrayNode tools = mapper.createArrayNode();
        tools.add(tool("search_matches",
                "Find matches by team, opponent, competition, season, date range and venue. "
                        + "Competitions: Brasileirão (Série A/B/C), Copa do Brasil, Copa Libertadores.",
                props -> {
                    teamProps(props);
                    prop(props, "opponent", "string", "Second team; with team, returns only games between them");
                    prop(props, "competition", "string", "Competition name or part of it, e.g. 'Brasileirão' or 'Copa do Brasil'");
                    prop(props, "season", "integer", "Season year, e.g. 2023");
                    prop(props, "from", "string", "Earliest date, YYYY-MM-DD or DD/MM/YYYY");
                    prop(props, "to", "string", "Latest date, YYYY-MM-DD or DD/MM/YYYY");
                    prop(props, "venue", "string", "home, away or any (default any); applies to team");
                    prop(props, "limit", "integer", "Max matches to return (default 20, max 100)");
                }));
        tools.add(tool("team_record",
                "Wins, draws, losses, goals and win rate for one team, optionally by season, competition and venue.",
                props -> {
                    prop(props, "team", "string", "Team name, e.g. 'Palmeiras'");
                    prop(props, "season", "integer", "Season year");
                    prop(props, "competition", "string", "Competition name or part of it");
                    prop(props, "venue", "string", "home, away or any (default any)");
                }, "team"));
        tools.add(tool("head_to_head",
                "All-time head-to-head record between two teams in the dataset, with recent matches.",
                props -> {
                    prop(props, "team_a", "string", "First team");
                    prop(props, "team_b", "string", "Second team");
                    prop(props, "limit", "integer", "Recent matches to list (default 20, max 100)");
                }, "team_a", "team_b"));
        tools.add(tool("search_players",
                "Search FIFA player ratings by name, nationality, club, position or minimum overall rating.",
                props -> {
                    prop(props, "name", "string", "Full or partial player name, e.g. 'Neymar'");
                    prop(props, "nationality", "string", "Nationality, e.g. 'Brazil'");
                    prop(props, "club", "string", "Club name or part of it, e.g. 'Flamengo'");
                    prop(props, "position", "string", "Position code, e.g. ST, CM, GK");
                    prop(props, "min_overall", "integer", "Minimum overall rating");
                    prop(props, "limit", "integer", "Max players to return (default 20, max 100)");
                }));
        tools.add(tool("competition_standings",
                "League table for a Brasileirão season, calculated from match results.",
                props -> {
                    prop(props, "competition", "string", "Competition, default 'Brasileirão Série A'");
                    prop(props, "season", "integer", "Season year");
                }, "season"));
        tools.add(tool("league_stats",
                "Aggregate statistics for a competition: average goals, home/draw/away win rates, biggest wins.",
                props -> {
                    prop(props, "competition", "string", "Competition name or part of it");
                    prop(props, "season", "integer", "Season year");
                }));
        tools.add(tool("rank_teams",
                "Rank teams by win rate in a competition, for home, away or overall games.",
                props -> {
                    prop(props, "competition", "string", "Competition name or part of it");
                    prop(props, "season", "integer", "Season year");
                    prop(props, "venue", "string", "home, away or any (default any)");
                    prop(props, "min_matches", "integer", "Minimum matches played to be ranked (default 10)");
                    prop(props, "limit", "integer", "Teams to return (default 10, max 100)");
                }));
        return tools;
    }

    /** Runs the named tool and returns its text output. */
    public String call(String name, JsonNode args) {
        return switch (name) {
            case "search_matches" -> searchMatches(args);
            case "team_record" -> teamRecord(args);
            case "head_to_head" -> headToHead(args);
            case "search_players" -> searchPlayers(args);
            case "competition_standings" -> standings(args);
            case "league_stats" -> leagueStats(args);
            case "rank_teams" -> rankTeams(args);
            default -> throw new IllegalArgumentException("Unknown tool: " + name);
        };
    }

    private String searchMatches(JsonNode args) {
        MatchFilter filter = new MatchFilter(
                text(args, "team"), text(args, "opponent"), text(args, "competition"),
                integer(args, "season"), date(args, "from"), date(args, "to"),
                Venue.parse(text(args, "venue")));
        List<Match> matches = queries.findMatches(filter, limit(args, DEFAULT_LIMIT));
        if (matches.isEmpty()) {
            return "No matches found in dataset for the given criteria.";
        }
        StringBuilder out = new StringBuilder();
        matches.forEach(m -> out.append("- ").append(formatMatch(m)).append('\n'));
        return out.toString().stripTrailing();
    }

    private String teamRecord(JsonNode args) {
        String team = required(args, "team");
        TeamTally t = queries.teamRecord(team, integer(args, "season"), text(args, "competition"),
                Venue.parse(text(args, "venue")));
        if (t.played() == 0) {
            return "No results found in dataset for " + team + " with these filters.";
        }
        return "%s record: %d matches, %d wins, %d draws, %d losses%n"
                .formatted(team, t.played(), t.won(), t.drawn(), t.lost())
                + "Goals for: %d, Goals against: %d%n".formatted(t.goalsFor(), t.goalsAgainst())
                + "Win rate: %.1f%%".formatted(t.winRate());
    }

    private String headToHead(JsonNode args) {
        String a = required(args, "team_a");
        String b = required(args, "team_b");
        HeadToHead h = queries.headToHead(a, b, limit(args, DEFAULT_LIMIT));
        if (h.matches().isEmpty()) {
            return "No matches between %s and %s in dataset.".formatted(a, b);
        }
        StringBuilder out = new StringBuilder();
        out.append("%s vs %s in dataset: %d matches%n".formatted(a, b, h.matches().size()));
        out.append("%s wins: %d, Draws: %d, %s wins: %d%n".formatted(a, h.winsA(), h.draws(), b, h.winsB()));
        out.append("Goals: %s %d, %s %d%n".formatted(a, h.goalsA(), b, h.goalsB()));
        out.append("Most recent matches:\n");
        h.matches().forEach(m -> out.append("- ").append(formatMatch(m)).append('\n'));
        return out.toString().stripTrailing();
    }

    private String searchPlayers(JsonNode args) {
        PlayerFilter filter = new PlayerFilter(
                text(args, "name"), text(args, "nationality"), text(args, "club"),
                text(args, "position"), integer(args, "min_overall"));
        List<Player> players = queries.searchPlayers(filter, limit(args, DEFAULT_LIMIT));
        if (players.isEmpty()) {
            return "No players found in dataset for the given criteria.";
        }
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < players.size(); i++) {
            Player p = players.get(i);
            out.append("%d. %s - Overall: %s, Position: %s, Club: %s, Nationality: %s, Age: %s%n"
                    .formatted(i + 1, p.name(), orDash(p.overall()), orDash(p.position()),
                            orDash(p.club()), orDash(p.nationality()), orDash(p.age())));
        }
        return out.toString().stripTrailing();
    }

    private String standings(JsonNode args) {
        String competition = text(args, "competition");
        if (competition == null) {
            competition = DEFAULT_COMPETITION;
        }
        int season = requiredInteger(args, "season");
        List<TeamTally> table = queries.standings(competition, season);
        if (table.isEmpty()) {
            return "No results found for %s %d.".formatted(competition, season);
        }
        StringBuilder out = new StringBuilder("%s %d standings (calculated from matches):%n"
                .formatted(competition, season));
        for (int i = 0; i < table.size(); i++) {
            TeamTally t = table.get(i);
            out.append("%d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d)%n".formatted(
                    i + 1, t.team(), t.points(), t.won(), t.drawn(), t.lost(), t.goalsFor(), t.goalsAgainst()));
        }
        return out.toString().stripTrailing();
    }

    private String leagueStats(JsonNode args) {
        String competition = text(args, "competition");
        Integer season = integer(args, "season");
        LeagueStats s = queries.leagueStats(competition, season);
        if (s.matches() == 0) {
            return "No results found in dataset for these filters.";
        }
        StringBuilder out = new StringBuilder();
        out.append("Matches with results: %d%n".formatted(s.matches()));
        out.append("Average goals per match: %.2f%n".formatted(s.avgGoalsPerMatch()));
        out.append("Home win rate: %.1f%%, Draw rate: %.1f%%, Away win rate: %.1f%%%n"
                .formatted(s.homeWinPct(), s.drawPct(), s.awayWinPct()));
        out.append("Biggest wins:\n");
        s.biggestWins().forEach(m -> out.append("- ").append(formatMatch(m)).append('\n'));
        return out.toString().stripTrailing();
    }

    private String rankTeams(JsonNode args) {
        List<TeamTally> ranked = queries.rankTeams(
                text(args, "competition"), integer(args, "season"), Venue.parse(text(args, "venue")),
                intOr(args, "min_matches", 10), limit(args, 10));
        if (ranked.isEmpty()) {
            return "No teams meet the criteria in dataset.";
        }
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < ranked.size(); i++) {
            TeamTally t = ranked.get(i);
            out.append("%d. %s - win rate %.1f%% (%d wins from %d matches)%n"
                    .formatted(i + 1, t.team(), t.winRate(), t.won(), t.played()));
        }
        return out.toString().stripTrailing();
    }

    private static String formatMatch(Match m) {
        String scoreline = m.hasResult() ? "%d-%d".formatted(m.homeGoals(), m.awayGoals()) : "vs";
        String round = m.round() == null ? "" : ", " + roundLabel(m.round());
        return "%s: %s %s %s (%s%s)".formatted(m.date(), m.homeTeam(), scoreline, m.awayTeam(),
                m.competition(), round);
    }

    private static String roundLabel(String round) {
        return round.chars().allMatch(Character::isDigit) ? "Round " + round : round;
    }

    private static String orDash(Object value) {
        return value == null ? "-" : value.toString();
    }

    private static void teamProps(ObjectNode props) {
        prop(props, "team", "string", "Team name, e.g. 'Flamengo'. Accents and state suffixes are ignored.");
    }

    private ObjectNode tool(String name, String description, java.util.function.Consumer<ObjectNode> props,
                            String... required) {
        ObjectNode tool = mapper.createObjectNode();
        tool.put("name", name);
        tool.put("description", description);
        ObjectNode schema = tool.putObject("inputSchema");
        schema.put("type", "object");
        ObjectNode properties = schema.putObject("properties");
        props.accept(properties);
        if (required.length > 0) {
            ArrayNode req = schema.putArray("required");
            for (String r : required) {
                req.add(r);
            }
        }
        return tool;
    }

    private static void prop(ObjectNode props, String name, String type, String description) {
        ObjectNode p = props.putObject(name);
        p.put("type", type);
        p.put("description", description);
    }

    private static String text(JsonNode args, String key) {
        JsonNode node = args.get(key);
        if (node == null || node.isNull()) {
            return null;
        }
        String value = node.asText().trim();
        return value.isEmpty() ? null : value;
    }

    private static String required(JsonNode args, String key) {
        String value = text(args, key);
        if (value == null) {
            throw new IllegalArgumentException("Missing required argument: " + key);
        }
        return value;
    }

    private static Integer integer(JsonNode args, String key) {
        String value = text(args, key);
        if (value == null) {
            return null;
        }
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(key + " must be an integer, got: " + value);
        }
    }

    private static int requiredInteger(JsonNode args, String key) {
        Integer value = integer(args, key);
        if (value == null) {
            throw new IllegalArgumentException("Missing required argument: " + key);
        }
        return value;
    }

    private static int intOr(JsonNode args, String key, int fallback) {
        Integer value = integer(args, key);
        return value == null ? fallback : value;
    }

    private static LocalDate date(JsonNode args, String key) {
        String value = text(args, key);
        if (value == null) {
            return null;
        }
        LocalDate parsed = DataLoader.parseDate(value);
        if (parsed == null) {
            throw new IllegalArgumentException(key + " must be YYYY-MM-DD or DD/MM/YYYY, got: " + value);
        }
        return parsed;
    }

    private static int limit(JsonNode args, int fallback) {
        int value = intOr(args, "limit", fallback);
        if (value < 1) {
            throw new IllegalArgumentException("limit must be at least 1");
        }
        return Math.min(value, MAX_LIMIT);
    }
}
