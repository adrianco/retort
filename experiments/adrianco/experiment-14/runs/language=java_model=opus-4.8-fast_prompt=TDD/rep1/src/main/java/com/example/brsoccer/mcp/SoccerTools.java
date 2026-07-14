/*
 * ============================================================================
 * Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * File:    SoccerTools.java
 * Purpose: The catalogue of MCP tools exposed to an LLM and the bridge between
 *          JSON tool arguments and the SoccerDatabase query engine. Each tool
 *          parses its arguments, runs the corresponding query and renders a
 *          human-readable, LLM-friendly text answer in the formats shown in the
 *          specification (match lists, head-to-head, records, standings,
 *          player lists and aggregate statistics).
 * Part of: mcp package (consumed by McpServer; depends on query + model).
 * ============================================================================
 */
package com.example.brsoccer.mcp;

import com.example.brsoccer.model.Match;
import com.example.brsoccer.model.Player;
import com.example.brsoccer.query.HeadToHead;
import com.example.brsoccer.query.MatchQuery;
import com.example.brsoccer.query.PlayerQuery;
import com.example.brsoccer.query.SoccerDatabase;
import com.example.brsoccer.query.StandingRow;
import com.example.brsoccer.query.TeamRecord;
import com.example.brsoccer.query.Venue;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Registers and dispatches the Brazilian-soccer MCP tools. */
public final class SoccerTools {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final SoccerDatabase db;

    public SoccerTools(SoccerDatabase db) {
        this.db = db;
    }

    /** Dispatch a tool call by name, returning rendered text (never throws). */
    public String call(String toolName, JsonNode args) {
        try {
            return switch (toolName) {
                case "find_matches" -> findMatches(args);
                case "head_to_head" -> headToHead(args);
                case "team_record" -> teamRecord(args);
                case "competition_standings" -> standings(args);
                case "search_players" -> searchPlayers(args);
                case "match_statistics" -> statistics(args);
                case "list_competitions" -> listCompetitions();
                default -> "Unknown tool: " + toolName;
            };
        } catch (RuntimeException e) {
            return "Error handling tool '" + toolName + "': " + e.getMessage();
        }
    }

    // --------------------------------------------------------------- tool impls

    private String findMatches(JsonNode a) {
        MatchQuery q = new MatchQuery()
                .team(str(a, "team"))
                .opponent(str(a, "opponent"))
                .competition(str(a, "competition"))
                .season(integer(a, "season"))
                .from(date(a, "from"))
                .to(date(a, "to"))
                .venue(venue(str(a, "venue")));
        List<Match> matches = db.findMatches(q);
        int limit = intOr(a, "limit", 30);
        if (matches.isEmpty()) {
            return "No matches found for the given criteria.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(matches.size()).append(" match(es)");
        if (matches.size() > limit) {
            sb.append(" (showing first ").append(limit).append(")");
        }
        sb.append(":\n");
        appendMatchLines(sb, matches, limit);
        return sb.toString().stripTrailing();
    }

    private String headToHead(JsonNode a) {
        String teamA = str(a, "team_a");
        String teamB = str(a, "team_b");
        if (teamA == null || teamB == null) {
            return "Please provide both team_a and team_b.";
        }
        HeadToHead h = db.headToHead(teamA, teamB);
        if (h.totalMatches() == 0) {
            return "No matches found between " + h.teamA() + " and " + h.teamB() + " in the dataset.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Head-to-head: ").append(h.teamA()).append(" vs ").append(h.teamB()).append('\n');
        sb.append("Total matches: ").append(h.totalMatches()).append('\n');
        sb.append(h.teamA()).append(" wins: ").append(h.teamAWins())
                .append(" | ").append(h.teamB()).append(" wins: ").append(h.teamBWins())
                .append(" | Draws: ").append(h.draws()).append('\n');
        sb.append("Recent meetings:\n");
        appendMatchLines(sb, h.matches(), 10);
        return sb.toString().stripTrailing();
    }

    private String teamRecord(JsonNode a) {
        String team = str(a, "team");
        if (team == null) {
            return "Please provide a team.";
        }
        Integer season = integer(a, "season");
        String competition = str(a, "competition");
        Venue venue = venue(str(a, "venue"));
        TeamRecord r = db.teamRecord(team, season, competition, venue);
        if (r.played() == 0) {
            return "No matches found for " + r.team() + " with the given criteria.";
        }
        String scope = describeScope(season, competition, venue);
        return r.team() + " record" + scope + ":\n"
                + "Played: " + r.played() + " | Wins: " + r.wins()
                + " | Draws: " + r.draws() + " | Losses: " + r.losses() + "\n"
                + "Goals for: " + r.goalsFor() + " | Goals against: " + r.goalsAgainst()
                + " | Goal difference: " + signed(r.goalDifference()) + "\n"
                + "Points: " + r.points() + " | Win rate: " + pct(r.winRate());
    }

    private String standings(JsonNode a) {
        String competition = strOr(a, "competition", "Brasileirão");
        Integer season = integer(a, "season");
        if (season == null) {
            return "Please provide a season for the standings.";
        }
        List<StandingRow> table = db.standings(competition, season);
        if (table.isEmpty()) {
            return "No data found for " + competition + " " + season + ".";
        }
        int limit = intOr(a, "limit", table.size());
        StringBuilder sb = new StringBuilder();
        sb.append(competition).append(' ').append(season)
                .append(" standings (computed from matches):\n");
        for (StandingRow row : table) {
            if (row.position() > limit) {
                break;
            }
            TeamRecord r = row.record();
            sb.append(String.format("%2d. %-28s %3d pts (%dW %dD %dL) GF%d GA%d GD%s%n",
                    row.position(), r.team(), r.points(), r.wins(), r.draws(), r.losses(),
                    r.goalsFor(), r.goalsAgainst(), signed(r.goalDifference())));
        }
        return sb.toString().stripTrailing();
    }

    private String searchPlayers(JsonNode a) {
        PlayerQuery q = new PlayerQuery()
                .name(str(a, "name"))
                .nationality(str(a, "nationality"))
                .club(str(a, "club"))
                .position(str(a, "position"))
                .minOverall(integer(a, "min_overall"))
                .limit(intOr(a, "limit", 25));
        List<Player> players = db.searchPlayers(q);
        if (players.isEmpty()) {
            return "No players found for the given criteria.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Found ").append(players.size()).append(" player(s):\n");
        int rank = 1;
        for (Player p : players) {
            sb.append(String.format("%2d. %s - Overall %s, Pos %s, Club %s, %s%n",
                    rank++, p.name(), value(p.overall()), value(p.position()),
                    value(p.club()), value(p.nationality())));
        }
        return sb.toString().stripTrailing();
    }

    private String statistics(JsonNode a) {
        MatchQuery q = new MatchQuery()
                .competition(str(a, "competition"))
                .season(integer(a, "season"))
                .team(str(a, "team"));
        List<Match> matches = db.findMatches(q);
        if (matches.isEmpty()) {
            return "No matches found for the given criteria.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Statistics for ").append(describeStatsScope(a)).append(":\n");
        sb.append("Matches: ").append(matches.size()).append('\n');
        sb.append("Average goals per match: ")
                .append(String.format(Locale.US, "%.2f", db.averageGoalsPerMatch(q))).append('\n');
        sb.append("Home win rate: ").append(pct(db.homeWinRate(q))).append('\n');
        sb.append("Biggest wins:\n");
        appendMatchLines(sb, db.biggestWins(q, 5), 5);
        return sb.toString().stripTrailing();
    }

    private String listCompetitions() {
        List<String> comps = db.competitions();
        StringBuilder sb = new StringBuilder("Available competitions:\n");
        for (String c : comps) {
            sb.append("- ").append(c).append('\n');
        }
        sb.append("Loaded ").append(db.matchCount()).append(" matches and ")
                .append(db.playerCount()).append(" players.");
        return sb.toString();
    }

    // ------------------------------------------------------------- definitions

    /** Tool metadata used to answer MCP tools/list. */
    public List<ToolDefinition> definitions() {
        List<ToolDefinition> defs = new ArrayList<>();
        defs.add(new ToolDefinition("find_matches",
                "Find soccer matches by team, opponent, competition, season, date range or venue.",
                schema(prop("team", "string", "Team name (any spelling, suffix optional)"),
                        prop("opponent", "string", "Restrict to matches against this opponent"),
                        prop("competition", "string", "Competition name, e.g. Brasileirão, Copa do Brasil, Libertadores"),
                        prop("season", "integer", "Season year"),
                        prop("from", "string", "Start date (YYYY-MM-DD)"),
                        prop("to", "string", "End date (YYYY-MM-DD)"),
                        prop("venue", "string", "home, away or any"),
                        prop("limit", "integer", "Maximum matches to return"))));
        defs.add(new ToolDefinition("head_to_head",
                "Summarize the head-to-head record between two teams.",
                schema(prop("team_a", "string", "First team"),
                        prop("team_b", "string", "Second team"))));
        defs.add(new ToolDefinition("team_record",
                "Aggregate a team's win/draw/loss and goal record, optionally by season, competition and venue.",
                schema(prop("team", "string", "Team name"),
                        prop("season", "integer", "Season year"),
                        prop("competition", "string", "Competition name"),
                        prop("venue", "string", "home, away or any"))));
        defs.add(new ToolDefinition("competition_standings",
                "Compute the league standings for a competition and season from match results.",
                schema(prop("competition", "string", "Competition name (default Brasileirão)"),
                        prop("season", "integer", "Season year"),
                        prop("limit", "integer", "Number of teams to show"))));
        defs.add(new ToolDefinition("search_players",
                "Search FIFA players by name, nationality, club, position and minimum overall rating.",
                schema(prop("name", "string", "Player name substring"),
                        prop("nationality", "string", "Nationality, e.g. Brazil"),
                        prop("club", "string", "Club name substring"),
                        prop("position", "string", "Position code, e.g. ST, GK, CB"),
                        prop("min_overall", "integer", "Minimum FIFA overall rating"),
                        prop("limit", "integer", "Maximum players to return"))));
        defs.add(new ToolDefinition("match_statistics",
                "Aggregate statistics (average goals, home-win rate, biggest wins) for a filter.",
                schema(prop("competition", "string", "Competition name"),
                        prop("season", "integer", "Season year"),
                        prop("team", "string", "Restrict to a single team"))));
        defs.add(new ToolDefinition("list_competitions",
                "List the competitions available in the loaded data.",
                schema()));
        return defs;
    }

    // -------------------------------------------------------------- formatting

    private void appendMatchLines(StringBuilder sb, List<Match> matches, int limit) {
        int shown = 0;
        for (Match m : matches) {
            if (shown++ >= limit) {
                break;
            }
            sb.append("- ").append(formatMatch(m)).append('\n');
        }
    }

    static String formatMatch(Match m) {
        String date = m.date() == null ? "unknown date" : m.date().toString();
        StringBuilder line = new StringBuilder();
        line.append(date).append(": ")
                .append(m.homeTeam()).append(' ').append(m.homeGoal())
                .append('-').append(m.awayGoal()).append(' ').append(m.awayTeam());
        line.append(" (").append(m.competition());
        if (m.round() != null && !m.round().isBlank()) {
            line.append(", ").append(roundLabel(m.round()));
        }
        line.append(')');
        return line.toString();
    }

    private static String roundLabel(String round) {
        // A bare number is a league round; anything else (e.g. "group stage") is a stage.
        return round.chars().allMatch(Character::isDigit) ? "Round " + round : round;
    }

    private String describeScope(Integer season, String competition, Venue venue) {
        List<String> parts = new ArrayList<>();
        if (season != null) {
            parts.add(String.valueOf(season));
        }
        if (competition != null) {
            parts.add(competition);
        }
        if (venue == Venue.HOME) {
            parts.add("home matches");
        } else if (venue == Venue.AWAY) {
            parts.add("away matches");
        }
        return parts.isEmpty() ? "" : " (" + String.join(" ", parts) + ")";
    }

    private String describeStatsScope(JsonNode a) {
        String competition = str(a, "competition");
        Integer season = integer(a, "season");
        String team = str(a, "team");
        StringBuilder sb = new StringBuilder();
        if (team != null) {
            sb.append(team).append(' ');
        }
        sb.append(competition == null ? "all competitions" : competition);
        if (season != null) {
            sb.append(' ').append(season);
        }
        return sb.toString();
    }

    private static String pct(double value) {
        return String.format(Locale.US, "%.1f%%", value);
    }

    private static String signed(int value) {
        return (value >= 0 ? "+" : "") + value;
    }

    private static String value(Object o) {
        return o == null ? "?" : o.toString();
    }

    // --------------------------------------------------------------- arg helpers

    private static String str(JsonNode a, String field) {
        JsonNode n = a == null ? null : a.get(field);
        if (n == null || n.isNull()) {
            return null;
        }
        String s = n.asText().trim();
        return s.isEmpty() ? null : s;
    }

    private static String strOr(JsonNode a, String field, String fallback) {
        String v = str(a, field);
        return v == null ? fallback : v;
    }

    private static Integer integer(JsonNode a, String field) {
        JsonNode n = a == null ? null : a.get(field);
        if (n == null || n.isNull()) {
            return null;
        }
        if (n.isInt() || n.isLong()) {
            return n.asInt();
        }
        try {
            return Integer.parseInt(n.asText().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static int intOr(JsonNode a, String field, int fallback) {
        Integer v = integer(a, field);
        return v == null ? fallback : v;
    }

    private static LocalDate date(JsonNode a, String field) {
        String s = str(a, field);
        if (s == null) {
            return null;
        }
        try {
            return LocalDate.parse(s);
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static Venue venue(String s) {
        if (s == null) {
            return Venue.ANY;
        }
        return switch (s.toLowerCase(Locale.ROOT)) {
            case "home" -> Venue.HOME;
            case "away" -> Venue.AWAY;
            default -> Venue.ANY;
        };
    }

    private static ObjectNode prop(String name, String type, String description) {
        ObjectNode p = MAPPER.createObjectNode();
        p.put("__name", name);
        p.put("type", type);
        p.put("description", description);
        return p;
    }

    private static ObjectNode schema(ObjectNode... props) {
        ObjectNode schema = MAPPER.createObjectNode();
        schema.put("type", "object");
        ObjectNode properties = MAPPER.createObjectNode();
        for (ObjectNode p : props) {
            String name = p.get("__name").asText();
            ObjectNode copy = p.deepCopy();
            copy.remove("__name");
            properties.set(name, copy);
        }
        schema.set("properties", properties);
        return schema;
    }
}
