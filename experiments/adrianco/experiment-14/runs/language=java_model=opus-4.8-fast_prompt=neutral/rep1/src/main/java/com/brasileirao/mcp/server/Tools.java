/*
 * ============================================================================
 *  Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 *  File    : Tools.java
 *  Purpose : Define the MCP tool catalogue and dispatch tool calls to the
 *            QueryService, formatting results as human-readable text.
 *
 *  Context : The MCP transport (McpServer) is deliberately thin; all of the
 *            "what tools exist and what do they return" logic lives here so it
 *            can be unit-tested without a live JSON-RPC session. Each tool maps
 *            to one capability category from the spec. callTool() takes the tool
 *            name plus a parsed JSON argument object and returns the answer text
 *            that the LLM will read. Tool input schemas are advertised via
 *            listTools() so an MCP client knows how to call them.
 *
 *  Used by : McpServer (transport) and ToolsTest (assertions).
 * ============================================================================
 */
package com.brasileirao.mcp.server;

import com.brasileirao.mcp.data.KnowledgeGraph;
import com.brasileirao.mcp.model.Match;
import com.brasileirao.mcp.model.Player;
import com.brasileirao.mcp.query.QueryService;
import com.brasileirao.mcp.query.QueryService.GoalStats;
import com.brasileirao.mcp.query.QueryService.HeadToHead;
import com.brasileirao.mcp.query.QueryService.MatchQuery;
import com.brasileirao.mcp.query.QueryService.PlayerQuery;
import com.brasileirao.mcp.query.QueryService.Scope;
import com.brasileirao.mcp.query.QueryService.StandingRow;
import com.brasileirao.mcp.query.QueryService.TeamRecord;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.time.LocalDate;
import java.util.List;
import java.util.Locale;

/** MCP tool catalogue and dispatcher. */
public final class Tools {

    private static final ObjectMapper M = new ObjectMapper();

    private final QueryService query;

    public Tools(QueryService query) {
        this.query = query;
    }

    // ------------------------------------------------------------- catalogue

    /** Build the {@code tools} array advertised by tools/list. */
    public ArrayNode listTools() {
        ArrayNode tools = M.createArrayNode();

        tools.add(tool("search_matches",
                "Search matches across all Brazilian competitions (Brasileirão, Copa do Brasil, "
                        + "Libertadores and more). Filter by team, opponent, competition, season or date range.",
                schema(p -> {
                    p.set("team", str("Team on either side of the match, e.g. 'Flamengo'."));
                    p.set("opponent", str("Restrict to matches against this opponent."));
                    p.set("home_team", str("Team that must be playing at home."));
                    p.set("away_team", str("Team that must be playing away."));
                    p.set("competition", str("Competition name or fragment, e.g. 'Brasileirão', 'Libertadores'."));
                    p.set("season", intp("Season year, e.g. 2019."));
                    p.set("date_from", str("Earliest match date, ISO YYYY-MM-DD."));
                    p.set("date_to", str("Latest match date, ISO YYYY-MM-DD."));
                    p.set("limit", intp("Maximum matches to return (default 50)."));
                })));

        tools.add(tool("head_to_head",
                "Aggregate head-to-head record between two teams across all competitions.",
                schema(p -> {
                    p.set("team_a", str("First team."));
                    p.set("team_b", str("Second team."));
                }, "team_a", "team_b")));

        tools.add(tool("team_record",
                "Win/draw/loss and goal record for a team, optionally scoped by season, "
                        + "competition and home/away.",
                schema(p -> {
                    p.set("team", str("Team name, e.g. 'Corinthians'."));
                    p.set("season", intp("Season year."));
                    p.set("competition", str("Competition name or fragment."));
                    p.set("scope", strEnum("Match scope.", "all", "home", "away"));
                }, "team")));

        tools.add(tool("search_players",
                "Search the FIFA player database by name, nationality, club, position or minimum "
                        + "overall rating. Results are sorted by overall rating.",
                schema(p -> {
                    p.set("name", str("Player name fragment, e.g. 'Neymar'."));
                    p.set("nationality", str("Nationality, e.g. 'Brazil'."));
                    p.set("club", str("Club name, e.g. 'Flamengo'."));
                    p.set("position", str("Position code, e.g. 'GK', 'ST', 'CB'."));
                    p.set("min_overall", intp("Minimum FIFA overall rating."));
                    p.set("limit", intp("Maximum players to return (default 25)."));
                })));

        tools.add(tool("standings",
                "Final league table for a competition and season, computed from match results "
                        + "(3 points per win, 1 per draw).",
                schema(p -> {
                    p.set("competition", str("Competition name or fragment, e.g. 'Brasileirão'."));
                    p.set("season", intp("Season year, e.g. 2019."));
                }, "competition", "season")));

        tools.add(tool("match_statistics",
                "Aggregate statistics over a set of matches: number of matches, total and average "
                        + "goals per match, and home/away/draw win rates. Optionally filter by "
                        + "competition and season.",
                schema(p -> {
                    p.set("competition", str("Competition name or fragment."));
                    p.set("season", intp("Season year."));
                })));

        tools.add(tool("biggest_wins",
                "Largest-margin victories, optionally filtered by competition and season.",
                schema(p -> {
                    p.set("competition", str("Competition name or fragment."));
                    p.set("season", intp("Season year."));
                    p.set("limit", intp("How many to return (default 10)."));
                })));

        tools.add(tool("best_records",
                "Rank teams by win rate over a scope (all/home/away), optionally filtered by "
                        + "competition and season. Useful for 'best home record' style questions.",
                schema(p -> {
                    p.set("competition", str("Competition name or fragment."));
                    p.set("season", intp("Season year."));
                    p.set("scope", strEnum("Match scope.", "all", "home", "away"));
                    p.set("min_matches", intp("Minimum matches to qualify (default 5)."));
                    p.set("limit", intp("How many teams to return (default 10)."));
                })));

        tools.add(tool("list_competitions",
                "List the competitions available in the dataset and overall corpus size.",
                schema(p -> {
                })));

        return tools;
    }

    // ------------------------------------------------------------- dispatch

    /** Execute a tool by name with the given JSON arguments; return answer text. */
    public String callTool(String name, JsonNode args) {
        if (args == null || args.isNull()) {
            args = M.createObjectNode();
        }
        return switch (name) {
            case "search_matches" -> searchMatches(args);
            case "head_to_head" -> headToHead(args);
            case "team_record" -> teamRecord(args);
            case "search_players" -> searchPlayers(args);
            case "standings" -> standings(args);
            case "match_statistics" -> matchStatistics(args);
            case "biggest_wins" -> biggestWins(args);
            case "best_records" -> bestRecords(args);
            case "list_competitions" -> listCompetitions();
            default -> throw new IllegalArgumentException("Unknown tool: " + name);
        };
    }

    // ------------------------------------------------------------- handlers

    private String searchMatches(JsonNode a) {
        MatchQuery q = new MatchQuery();
        q.team = text(a, "team");
        q.opponent = text(a, "opponent");
        q.homeTeam = text(a, "home_team");
        q.awayTeam = text(a, "away_team");
        q.competition = text(a, "competition");
        q.season = integer(a, "season");
        q.dateFrom = date(a, "date_from");
        q.dateTo = date(a, "date_to");
        q.limit = a.hasNonNull("limit") ? a.get("limit").asInt() : 50;

        List<Match> matches = query.searchMatches(q);
        if (matches.isEmpty()) {
            return "No matches found for the given criteria.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(matches.size()).append(" match(es):\n");
        for (Match m : matches) {
            sb.append("- ").append(m.describe()).append('\n');
        }
        // If both a team and opponent were supplied, append the head-to-head summary.
        if (q.team != null && q.opponent != null) {
            HeadToHead h = query.headToHead(q.team, q.opponent);
            sb.append('\n').append(formatH2HLine(h));
        }
        return sb.toString().stripTrailing();
    }

    private String headToHead(JsonNode a) {
        String teamA = required(a, "team_a");
        String teamB = required(a, "team_b");
        HeadToHead h = query.headToHead(teamA, teamB);
        if (h.total() == 0 && h.matches().isEmpty()) {
            return "No matches found between " + teamA + " and " + teamB + ".";
        }
        StringBuilder sb = new StringBuilder();
        sb.append(h.teamA()).append(" vs ").append(h.teamB()).append(" head-to-head:\n");
        sb.append(formatH2HLine(h)).append('\n');
        sb.append("Goals: ").append(h.teamA()).append(' ').append(h.goalsA())
                .append(", ").append(h.teamB()).append(' ').append(h.goalsB()).append('\n');
        sb.append("\nRecent meetings:\n");
        int shown = 0;
        for (Match m : h.matches()) {
            if (shown++ >= 15) {
                sb.append("- ... (").append(h.matches().size() - 15).append(" more)\n");
                break;
            }
            sb.append("- ").append(m.describe()).append('\n');
        }
        return sb.toString().stripTrailing();
    }

    private String formatH2HLine(HeadToHead h) {
        return String.format(Locale.ROOT,
                "Head-to-head: %s %d wins, %s %d wins, %d draws (%d total)",
                h.teamA(), h.aWins(), h.teamB(), h.bWins(), h.draws(), h.total());
    }

    private String teamRecord(JsonNode a) {
        String team = required(a, "team");
        Integer season = integer(a, "season");
        String competition = text(a, "competition");
        Scope scope = scope(text(a, "scope"));
        TeamRecord r = query.teamRecord(team, season, competition, scope);
        if (r.matches() == 0) {
            return "No matches found for " + team + " with the given filters.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append(r.team()).append(' ').append(r.scope()).append(" record");
        if (season != null || competition != null) {
            sb.append(" (");
            if (season != null) {
                sb.append(season).append(' ');
            }
            sb.append(competition != null ? competition : "all competitions");
            sb.append(')');
        }
        sb.append(":\n");
        sb.append("- Matches: ").append(r.matches()).append('\n');
        sb.append("- Wins: ").append(r.wins()).append(", Draws: ").append(r.draws())
                .append(", Losses: ").append(r.losses()).append('\n');
        sb.append("- Goals For: ").append(r.goalsFor()).append(", Goals Against: ")
                .append(r.goalsAgainst()).append(" (GD ").append(signed(r.goalDifference())).append(")\n");
        sb.append("- Points: ").append(r.points()).append('\n');
        sb.append(String.format(Locale.ROOT, "- Win rate: %.1f%%", r.winRate()));
        return sb.toString();
    }

    private String searchPlayers(JsonNode a) {
        PlayerQuery q = new PlayerQuery();
        q.name = text(a, "name");
        q.nationality = text(a, "nationality");
        q.club = text(a, "club");
        q.position = text(a, "position");
        q.minOverall = integer(a, "min_overall");
        q.limit = a.hasNonNull("limit") ? a.get("limit").asInt() : 25;

        List<Player> players = query.searchPlayers(q);
        if (players.isEmpty()) {
            return "No players found for the given criteria.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(players.size()).append(" player(s):\n");
        int i = 1;
        for (Player p : players) {
            sb.append(i++).append(". ").append(p.describe()).append('\n');
        }
        return sb.toString().stripTrailing();
    }

    private String standings(JsonNode a) {
        String competition = required(a, "competition");
        Integer season = integer(a, "season");
        if (season == null) {
            return "A season year is required for standings.";
        }
        List<StandingRow> rows = query.standings(competition, season);
        if (rows.isEmpty()) {
            return "No standings could be computed for " + competition + " " + season + ".";
        }
        String resolved = query.resolveCompetition(competition, season);
        StringBuilder sb = new StringBuilder();
        sb.append(season).append(' ').append(resolved == null ? competition : resolved)
                .append(" final standings (computed from matches):\n");
        for (StandingRow r : rows) {
            sb.append(String.format(Locale.ROOT,
                    "%2d. %-28s %3d pts (%2dW %2dD %2dL, GF %d GA %d, GD %s)%n",
                    r.position(), r.team(), r.points(), r.wins(), r.draws(), r.losses(),
                    r.goalsFor(), r.goalsAgainst(), signed(r.goalDifference())));
        }
        return sb.toString().stripTrailing();
    }

    private String matchStatistics(JsonNode a) {
        String competition = text(a, "competition");
        Integer season = integer(a, "season");
        GoalStats s = query.averageGoals(competition, season);
        if (s.matches() == 0) {
            return "No matches found for the given filters.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Match statistics");
        if (competition != null || season != null) {
            sb.append(" (");
            if (season != null) {
                sb.append(season).append(' ');
            }
            sb.append(competition != null ? competition : "all competitions").append(')');
        }
        sb.append(":\n");
        sb.append("- Matches: ").append(s.matches()).append('\n');
        sb.append("- Total goals: ").append(s.totalGoals()).append('\n');
        sb.append(String.format(Locale.ROOT, "- Average goals per match: %.2f%n", s.averageGoals()));
        sb.append(String.format(Locale.ROOT, "- Home wins: %d (%.1f%%)%n", s.homeWins(), s.homeWinRate()));
        sb.append("- Away wins: ").append(s.awayWins()).append('\n');
        sb.append("- Draws: ").append(s.draws());
        return sb.toString();
    }

    private String biggestWins(JsonNode a) {
        String competition = text(a, "competition");
        Integer season = integer(a, "season");
        int limit = a.hasNonNull("limit") ? a.get("limit").asInt() : 10;
        List<Match> wins = query.biggestWins(competition, season, limit);
        if (wins.isEmpty()) {
            return "No matches found for the given filters.";
        }
        StringBuilder sb = new StringBuilder("Biggest victories:\n");
        int i = 1;
        for (Match m : wins) {
            int margin = Math.abs(m.homeGoals() - m.awayGoals());
            sb.append(i++).append(". ").append(m.describe())
                    .append("  [margin ").append(margin).append("]\n");
        }
        return sb.toString().stripTrailing();
    }

    private String bestRecords(JsonNode a) {
        String competition = text(a, "competition");
        Integer season = integer(a, "season");
        Scope scope = scope(text(a, "scope"));
        int minMatches = a.hasNonNull("min_matches") ? a.get("min_matches").asInt() : 5;
        int limit = a.hasNonNull("limit") ? a.get("limit").asInt() : 10;
        List<TeamRecord> records = query.bestRecords(competition, season, scope, minMatches, limit);
        if (records.isEmpty()) {
            return "No teams matched the given filters.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Best ").append(scope.name().toLowerCase(Locale.ROOT)).append(" records");
        if (competition != null || season != null) {
            sb.append(" (");
            if (season != null) {
                sb.append(season).append(' ');
            }
            sb.append(competition != null ? competition : "all competitions").append(')');
        }
        sb.append(":\n");
        int i = 1;
        for (TeamRecord r : records) {
            sb.append(String.format(Locale.ROOT,
                    "%2d. %-28s %.1f%% (%dW %dD %dL, GF %d GA %d)%n",
                    i++, r.team(), r.winRate(), r.wins(), r.draws(), r.losses(),
                    r.goalsFor(), r.goalsAgainst()));
        }
        return sb.toString().stripTrailing();
    }

    private String listCompetitions() {
        StringBuilder sb = new StringBuilder("Available competitions:\n");
        for (String c : query.graph().competitions()) {
            sb.append("- ").append(c).append('\n');
        }
        sb.append('\n');
        sb.append("Corpus: ").append(query.graph().matchCount()).append(" matches, ")
                .append(query.graph().playerCount()).append(" players.");
        return sb.toString();
    }

    // ------------------------------------------------------------- arg helpers

    private static String text(JsonNode a, String field) {
        JsonNode n = a.get(field);
        if (n == null || n.isNull()) {
            return null;
        }
        String s = n.asText().trim();
        return s.isEmpty() ? null : s;
    }

    private static String required(JsonNode a, String field) {
        String v = text(a, field);
        if (v == null) {
            throw new IllegalArgumentException("Missing required argument: " + field);
        }
        return v;
    }

    private static Integer integer(JsonNode a, String field) {
        JsonNode n = a.get(field);
        if (n == null || n.isNull()) {
            return null;
        }
        if (n.isInt() || n.isLong()) {
            return n.asInt();
        }
        try {
            return Integer.valueOf(n.asText().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static LocalDate date(JsonNode a, String field) {
        String v = text(a, field);
        if (v == null) {
            return null;
        }
        try {
            return LocalDate.parse(v.length() >= 10 ? v.substring(0, 10) : v);
        } catch (Exception e) {
            return null;
        }
    }

    private static Scope scope(String s) {
        if (s == null) {
            return Scope.ALL;
        }
        return switch (s.toLowerCase(Locale.ROOT)) {
            case "home" -> Scope.HOME;
            case "away" -> Scope.AWAY;
            default -> Scope.ALL;
        };
    }

    private static String signed(int v) {
        return (v > 0 ? "+" : "") + v;
    }

    // ------------------------------------------------------------- schema helpers

    private interface Props {
        void define(ObjectNode properties);
    }

    private static ObjectNode tool(String name, String description, ObjectNode inputSchema) {
        ObjectNode t = M.createObjectNode();
        t.put("name", name);
        t.put("description", description);
        t.set("inputSchema", inputSchema);
        return t;
    }

    private static ObjectNode schema(Props props, String... required) {
        ObjectNode s = M.createObjectNode();
        s.put("type", "object");
        ObjectNode properties = M.createObjectNode();
        props.define(properties);
        s.set("properties", properties);
        if (required.length > 0) {
            ArrayNode req = M.createArrayNode();
            for (String r : required) {
                req.add(r);
            }
            s.set("required", req);
        }
        return s;
    }

    private static ObjectNode str(String description) {
        ObjectNode n = M.createObjectNode();
        n.put("type", "string");
        n.put("description", description);
        return n;
    }

    private static ObjectNode strEnum(String description, String... values) {
        ObjectNode n = str(description);
        ArrayNode e = M.createArrayNode();
        for (String v : values) {
            e.add(v);
        }
        n.set("enum", e);
        return n;
    }

    private static ObjectNode intp(String description) {
        ObjectNode n = M.createObjectNode();
        n.put("type", "integer");
        n.put("description", description);
        return n;
    }
}
