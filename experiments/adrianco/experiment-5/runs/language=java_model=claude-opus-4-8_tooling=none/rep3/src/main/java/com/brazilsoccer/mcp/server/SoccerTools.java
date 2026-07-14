/*
 * ============================================================================
 * SoccerTools.java
 * ============================================================================
 * Context:
 *   The bridge between the MCP transport (McpServer) and the query services.
 *   It (a) declares the set of MCP tools with their JSON input schemas and
 *   (b) executes a tool call, formatting the structured query results into the
 *   human-readable text blocks shown in the spec's "Example answer format"
 *   sections.
 *
 *   Keeping declaration + dispatch + formatting here lets McpServer stay a thin
 *   JSON-RPC loop and lets tests exercise the full tool surface directly via
 *   {@link #call(String, JsonNode)} without going through stdio.
 * ============================================================================
 */
package com.brazilsoccer.mcp.server;

import com.brazilsoccer.mcp.data.DataStore;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Player;
import com.brazilsoccer.mcp.query.CompetitionService;
import com.brazilsoccer.mcp.query.MatchService;
import com.brazilsoccer.mcp.query.PlayerService;
import com.brazilsoccer.mcp.query.StatsService;
import com.brazilsoccer.mcp.query.TeamRecord;
import com.brazilsoccer.mcp.query.TeamService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.time.LocalDate;
import java.util.List;

/** Declares and executes the MCP tools backed by the query services. */
public final class SoccerTools {

    private final ObjectMapper json = new ObjectMapper();
    private final MatchService matchService;
    private final TeamService teamService;
    private final PlayerService playerService;
    private final CompetitionService competitionService;
    private final StatsService statsService;

    public SoccerTools(DataStore store) {
        this.matchService = new MatchService(store);
        this.teamService = new TeamService(store);
        this.playerService = new PlayerService(store);
        this.competitionService = new CompetitionService(store);
        this.statsService = new StatsService(store);
    }

    // ------------------------------------------------------------------
    // Tool declarations (tools/list)
    // ------------------------------------------------------------------

    /** Build the JSON array of tool definitions returned by tools/list. */
    public ArrayNode toolDefinitions() {
        ArrayNode tools = json.createArrayNode();

        tools.add(tool("search_matches",
                "Find soccer matches by team, opponent, competition, season and/or date range. "
                        + "Searches Brasileirão, Copa do Brasil, Copa Libertadores and more.",
                schema -> {
                    prop(schema, "team", "string", "Team name (matches home or away), e.g. 'Flamengo'");
                    prop(schema, "opponent", "string", "Restrict to matches also involving this team");
                    prop(schema, "competition", "string",
                            "Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'");
                    prop(schema, "season", "integer", "Season year, e.g. 2019");
                    prop(schema, "date_from", "string", "Inclusive start date (YYYY-MM-DD)");
                    prop(schema, "date_to", "string", "Inclusive end date (YYYY-MM-DD)");
                    prop(schema, "limit", "integer", "Max matches to return (default 50)");
                }));

        tools.add(tool("team_record",
                "Get a team's win/draw/loss and goal record, optionally filtered by season, "
                        + "competition and venue (home/away/all).",
                schema -> {
                    propRequired(schema, "team", "string", "Team name, e.g. 'Corinthians'");
                    prop(schema, "season", "integer", "Season year, e.g. 2022");
                    prop(schema, "competition", "string", "Competition filter");
                    prop(schema, "venue", "string", "One of: all, home, away (default all)");
                }));

        tools.add(tool("head_to_head",
                "Compare two teams head-to-head: wins, draws and the list of matches between them.",
                schema -> {
                    propRequired(schema, "team1", "string", "First team");
                    propRequired(schema, "team2", "string", "Second team");
                    prop(schema, "season", "integer", "Optional season filter");
                    prop(schema, "competition", "string", "Optional competition filter");
                }));

        tools.add(tool("search_players",
                "Search the FIFA player database by name, nationality, club, position and/or "
                        + "minimum overall rating. Results are sorted by overall rating.",
                schema -> {
                    prop(schema, "name", "string", "Player name substring, e.g. 'Neymar'");
                    prop(schema, "nationality", "string", "Nationality, e.g. 'Brazil'");
                    prop(schema, "club", "string", "Club name, e.g. 'Flamengo'");
                    prop(schema, "position", "string", "Position code, e.g. 'GK', 'ST', 'CB'");
                    prop(schema, "min_overall", "integer", "Minimum FIFA overall rating");
                    prop(schema, "limit", "integer", "Max players to return (default 25)");
                }));

        tools.add(tool("competition_standings",
                "Calculate final league standings (points, W/D/L, goals) for a competition and "
                        + "season from match results.",
                schema -> {
                    propRequired(schema, "competition", "string",
                            "Competition, e.g. 'Brasileirão'");
                    propRequired(schema, "season", "integer", "Season year, e.g. 2019");
                    prop(schema, "limit", "integer", "Max teams to show (default all)");
                }));

        tools.add(tool("league_stats",
                "Aggregate statistics for a competition/season: average goals per match, home/away "
                        + "win rate, draw rate, and the biggest victories.",
                schema -> {
                    prop(schema, "competition", "string", "Competition filter");
                    prop(schema, "season", "integer", "Season year");
                    prop(schema, "limit", "integer", "Number of biggest wins to list (default 5)");
                }));

        tools.add(tool("top_scoring_teams",
                "Rank teams by total goals scored in a competition/season.",
                schema -> {
                    prop(schema, "competition", "string", "Competition filter");
                    prop(schema, "season", "integer", "Season year");
                    prop(schema, "limit", "integer", "Number of teams to list (default 10)");
                }));

        return tools;
    }

    // ------------------------------------------------------------------
    // Tool dispatch (tools/call)
    // ------------------------------------------------------------------

    /**
     * Execute a tool by name with the given arguments node, returning the
     * formatted text response. Throws IllegalArgumentException for unknown
     * tools or invalid arguments.
     */
    public String call(String name, JsonNode args) {
        if (args == null || args.isNull()) {
            args = json.createObjectNode();
        }
        return switch (name) {
            case "search_matches" -> searchMatches(args);
            case "team_record" -> teamRecord(args);
            case "head_to_head" -> headToHead(args);
            case "search_players" -> searchPlayers(args);
            case "competition_standings" -> standings(args);
            case "league_stats" -> leagueStats(args);
            case "top_scoring_teams" -> topScoringTeams(args);
            default -> throw new IllegalArgumentException("Unknown tool: " + name);
        };
    }

    private String searchMatches(JsonNode a) {
        MatchService.Criteria c = new MatchService.Criteria();
        c.team = str(a, "team");
        c.opponent = str(a, "opponent");
        c.competition = str(a, "competition");
        c.season = intOrNull(a, "season");
        c.from = date(a, "date_from");
        c.to = date(a, "date_to");
        c.limit = intOr(a, "limit", 50);

        List<Match> results = matchService.search(c);
        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(results.size()).append(" match(es)");
        if (c.limit > 0) sb.append(" (showing up to ").append(c.limit).append(")");
        sb.append(":\n");
        if (results.isEmpty()) {
            sb.append("  (no matches found for the given criteria)");
        }
        for (Match m : results) {
            sb.append("- ").append(m.describe())
                    .append("  [").append(m.competition());
            if (m.round() != null) sb.append(", Round ").append(m.round());
            if (m.stage() != null) sb.append(", ").append(m.stage());
            sb.append(", ").append(m.season()).append("]\n");
        }
        return sb.toString().stripTrailing();
    }

    private String teamRecord(JsonNode a) {
        String team = required(a, "team");
        Integer season = intOrNull(a, "season");
        String competition = str(a, "competition");
        TeamService.Venue venue = venue(str(a, "venue"));

        TeamRecord r = teamService.record(team, season, competition, venue);
        StringBuilder sb = new StringBuilder();
        sb.append(r.team).append(" record");
        StringBuilder scope = new StringBuilder();
        if (venue != TeamService.Venue.ALL) scope.append(venue.name().toLowerCase()).append(" ");
        if (season != null) scope.append(season).append(" ");
        if (competition != null) scope.append(competition).append(" ");
        if (scope.length() > 0) sb.append(" (").append(scope.toString().trim()).append(")");
        sb.append(":\n");
        sb.append("- Matches: ").append(r.matches).append("\n");
        sb.append("- Wins: ").append(r.wins)
                .append(", Draws: ").append(r.draws)
                .append(", Losses: ").append(r.losses).append("\n");
        sb.append("- Goals For: ").append(r.goalsFor)
                .append(", Goals Against: ").append(r.goalsAgainst)
                .append(" (GD ").append(signed(r.goalDifference())).append(")\n");
        sb.append("- Win rate: ").append(pct(r.winRate()));
        return sb.toString();
    }

    private String headToHead(JsonNode a) {
        String t1 = required(a, "team1");
        String t2 = required(a, "team2");
        Integer season = intOrNull(a, "season");
        String competition = str(a, "competition");

        TeamService.HeadToHead h = teamService.headToHead(t1, t2, season, competition);
        StringBuilder sb = new StringBuilder();
        sb.append(h.teamA).append(" vs ").append(h.teamB).append(" head-to-head");
        if (season != null) sb.append(" (").append(season).append(")");
        sb.append(":\n");
        sb.append("- Matches in dataset: ").append(h.matches.size()).append("\n");
        sb.append("- ").append(h.teamA).append(" wins: ").append(h.teamAWins)
                .append(", ").append(h.teamB).append(" wins: ").append(h.teamBWins)
                .append(", Draws: ").append(h.draws).append("\n");
        sb.append("- Goals: ").append(h.teamA).append(" ").append(h.teamAGoals)
                .append(" - ").append(h.teamBGoals).append(" ").append(h.teamB).append("\n");
        int shown = Math.min(h.matches.size(), 15);
        if (shown > 0) sb.append("Recent meetings:\n");
        for (int i = 0; i < shown; i++) {
            Match m = h.matches.get(i);
            sb.append("  - ").append(m.describe())
                    .append(" (").append(m.competition()).append(", ").append(m.season()).append(")\n");
        }
        if (h.matches.size() > shown) {
            sb.append("  ... (").append(h.matches.size() - shown).append(" more)");
        }
        return sb.toString().stripTrailing();
    }

    private String searchPlayers(JsonNode a) {
        PlayerService.Criteria c = new PlayerService.Criteria();
        c.name = str(a, "name");
        c.nationality = str(a, "nationality");
        c.club = str(a, "club");
        c.position = str(a, "position");
        c.minOverall = intOrNull(a, "min_overall");
        c.limit = intOr(a, "limit", 25);

        List<Player> players = playerService.search(c);
        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(players.size()).append(" player(s):\n");
        if (players.isEmpty()) {
            sb.append("  (no players matched the given criteria)");
        }
        int rank = 1;
        for (Player p : players) {
            sb.append(rank++).append(". ").append(p.describe());
            if (p.nationality() != null) sb.append(" [").append(p.nationality()).append("]");
            sb.append("\n");
        }
        return sb.toString().stripTrailing();
    }

    private String standings(JsonNode a) {
        String competition = required(a, "competition");
        int season = requiredInt(a, "season");
        int limit = intOr(a, "limit", 0);

        List<TeamRecord> table = competitionService.standings(competition, season);
        StringBuilder sb = new StringBuilder();
        sb.append(season).append(" ").append(competition)
                .append(" standings (calculated from matches):\n");
        if (table.isEmpty()) {
            return sb.append("  (no match data found for this competition/season)").toString();
        }
        int n = limit > 0 ? Math.min(limit, table.size()) : table.size();
        for (int i = 0; i < n; i++) {
            TeamRecord r = table.get(i);
            sb.append(String.format("%2d. %-24s %3d pts (%2dW %2dD %2dL) GF:%d GA:%d GD:%s%s%n",
                    i + 1, r.team, r.points(), r.wins, r.draws, r.losses,
                    r.goalsFor, r.goalsAgainst, signed(r.goalDifference()),
                    i == 0 ? "  - Champion" : ""));
        }
        return sb.toString().stripTrailing();
    }

    private String leagueStats(JsonNode a) {
        String competition = str(a, "competition");
        Integer season = intOrNull(a, "season");
        int limit = intOr(a, "limit", 5);

        StatsService.LeagueStats s = statsService.leagueStats(competition, season);
        List<Match> biggest = statsService.biggestWins(competition, season, limit);

        StringBuilder sb = new StringBuilder();
        sb.append("Statistics");
        StringBuilder scope = new StringBuilder();
        if (competition != null) scope.append(competition).append(" ");
        if (season != null) scope.append(season);
        if (scope.length() > 0) sb.append(" for ").append(scope.toString().trim());
        sb.append(":\n");
        sb.append("- Matches with scores: ").append(s.matches).append("\n");
        sb.append("- Average goals per match: ").append(String.format("%.2f", s.goalsPerMatch())).append("\n");
        sb.append("- Home win rate: ").append(pct(s.homeWinRate())).append("\n");
        sb.append("- Away win rate: ").append(pct(s.awayWinRate())).append("\n");
        sb.append("- Draw rate: ").append(pct(s.drawRate())).append("\n");
        if (!biggest.isEmpty()) {
            sb.append("Biggest victories:\n");
            for (Match m : biggest) {
                sb.append("  - ").append(m.describe())
                        .append(" (").append(m.competition()).append(", ").append(m.season()).append(")\n");
            }
        }
        return sb.toString().stripTrailing();
    }

    private String topScoringTeams(JsonNode a) {
        String competition = str(a, "competition");
        Integer season = intOrNull(a, "season");
        int limit = intOr(a, "limit", 10);

        List<TeamRecord> teams = statsService.topScoringTeams(competition, season, limit);
        StringBuilder sb = new StringBuilder();
        sb.append("Top scoring teams");
        StringBuilder scope = new StringBuilder();
        if (competition != null) scope.append(competition).append(" ");
        if (season != null) scope.append(season);
        if (scope.length() > 0) sb.append(" (").append(scope.toString().trim()).append(")");
        sb.append(":\n");
        if (teams.isEmpty()) {
            return sb.append("  (no match data found)").toString();
        }
        int rank = 1;
        for (TeamRecord r : teams) {
            sb.append(rank++).append(". ").append(r.team)
                    .append(" - ").append(r.goalsFor).append(" goals in ")
                    .append(r.matches).append(" matches\n");
        }
        return sb.toString().stripTrailing();
    }

    // ------------------------------------------------------------------
    // Schema-building helpers
    // ------------------------------------------------------------------

    private interface SchemaBuilder { void build(ObjectNode properties); }

    private ObjectNode tool(String name, String description, SchemaBuilder propsBuilder) {
        ObjectNode t = json.createObjectNode();
        t.put("name", name);
        t.put("description", description);
        ObjectNode schema = json.createObjectNode();
        schema.put("type", "object");
        ObjectNode properties = json.createObjectNode();
        propsBuilder.build(properties);
        schema.set("properties", properties);
        // Collect required field names recorded via propRequired.
        ArrayNode required = json.createArrayNode();
        properties.fields().forEachRemaining(e -> {
            JsonNode req = e.getValue().get("__required");
            if (req != null && req.asBoolean()) {
                required.add(e.getKey());
                ((ObjectNode) e.getValue()).remove("__required");
            }
        });
        if (!required.isEmpty()) schema.set("required", required);
        t.set("inputSchema", schema);
        return t;
    }

    private void prop(ObjectNode properties, String name, String type, String description) {
        ObjectNode p = json.createObjectNode();
        p.put("type", type);
        p.put("description", description);
        properties.set(name, p);
    }

    private void propRequired(ObjectNode properties, String name, String type, String description) {
        prop(properties, name, type, description);
        ((ObjectNode) properties.get(name)).put("__required", true);
    }

    // ------------------------------------------------------------------
    // Argument extraction & formatting helpers
    // ------------------------------------------------------------------

    private static String str(JsonNode a, String field) {
        JsonNode n = a.get(field);
        if (n == null || n.isNull()) return null;
        String s = n.asText().trim();
        return s.isEmpty() ? null : s;
    }

    private static String required(JsonNode a, String field) {
        String v = str(a, field);
        if (v == null) throw new IllegalArgumentException("Missing required argument: " + field);
        return v;
    }

    private static Integer intOrNull(JsonNode a, String field) {
        JsonNode n = a.get(field);
        if (n == null || n.isNull()) return null;
        if (n.isNumber()) return n.asInt();
        try {
            return Integer.parseInt(n.asText().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static int intOr(JsonNode a, String field, int def) {
        Integer v = intOrNull(a, field);
        return v == null ? def : v;
    }

    private static int requiredInt(JsonNode a, String field) {
        Integer v = intOrNull(a, field);
        if (v == null) throw new IllegalArgumentException("Missing required integer argument: " + field);
        return v;
    }

    private static LocalDate date(JsonNode a, String field) {
        String s = str(a, field);
        if (s == null) return null;
        try {
            return LocalDate.parse(s);
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid date (expected YYYY-MM-DD): " + s);
        }
    }

    private static TeamService.Venue venue(String s) {
        if (s == null) return TeamService.Venue.ALL;
        return switch (s.toLowerCase()) {
            case "home" -> TeamService.Venue.HOME;
            case "away" -> TeamService.Venue.AWAY;
            default -> TeamService.Venue.ALL;
        };
    }

    private static String pct(double v) {
        return String.format("%.1f%%", v);
    }

    private static String signed(int v) {
        return (v >= 0 ? "+" : "") + v;
    }
}
