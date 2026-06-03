/*
 * ===========================================================================
 * Context: Brazilian Soccer MCP Server
 * File:    server/SoccerTools.java
 * Purpose: Defines the catalogue of MCP tools exposed to the LLM and renders
 *          their results as readable text in the style shown in the spec. Each
 *          tool maps user-facing arguments onto the SoccerQueries engine and
 *          formats matches, standings, player lists and statistics. This is the
 *          bridge between the MCP protocol layer and the query engine.
 * ===========================================================================
 */
package com.brazilsoccer.mcp.server;

import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Player;
import com.brazilsoccer.mcp.query.QueryResults.HeadToHead;
import com.brazilsoccer.mcp.query.QueryResults.StandingRow;
import com.brazilsoccer.mcp.query.QueryResults.TeamStats;
import com.brazilsoccer.mcp.query.SoccerQueries;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

public final class SoccerTools {

    private final SoccerQueries q;
    private final ObjectMapper mapper = new ObjectMapper();

    public SoccerTools(SoccerQueries queries) {
        this.q = queries;
    }

    /** Build the full tool catalogue. */
    public List<Tool> tools() {
        List<Tool> tools = new ArrayList<>();

        tools.add(new Tool("search_matches",
                "Search matches by team, competition, season and/or date range. "
                        + "All filters are optional; returns matches newest first.",
                schema(prop("team", "string", "Team name (any spelling/variation)"),
                        prop("competition", "string",
                                "Competition filter: Brasileirão, Copa do Brasil or Libertadores"),
                        prop("season", "integer", "Season year, e.g. 2019"),
                        prop("date_from", "string", "Inclusive start date (YYYY-MM-DD)"),
                        prop("date_to", "string", "Inclusive end date (YYYY-MM-DD)"),
                        prop("limit", "integer", "Maximum matches to return (default 25)")),
                this::searchMatches));

        tools.add(new Tool("matches_between",
                "List all matches between two specific teams (a derby/head-to-head fixture list).",
                schema(req("team_a", "string", "First team"),
                        req("team_b", "string", "Second team"),
                        prop("limit", "integer", "Maximum matches to return (default 25)")),
                this::matchesBetween));

        tools.add(new Tool("head_to_head",
                "Head-to-head record summary between two teams (wins, draws, goals).",
                schema(req("team_a", "string", "First team"),
                        req("team_b", "string", "Second team")),
                this::headToHead));

        tools.add(new Tool("team_stats",
                "Aggregated statistics for a team: matches, wins, draws, losses, goals, win rate. "
                        + "Optionally restrict by competition, season and venue.",
                schema(req("team", "string", "Team name"),
                        prop("competition", "string", "Competition filter"),
                        prop("season", "integer", "Season year"),
                        prop("venue", "string", "home, away or all (default all)")),
                this::teamStats));

        tools.add(new Tool("standings",
                "Computed final league table for a competition and season "
                        + "(3 pts win / 1 pt draw), including relegation zone.",
                schema(req("season", "integer", "Season year, e.g. 2019"),
                        prop("competition", "string",
                                "Competition (default Brasileirão Série A)")),
                this::standings));

        tools.add(new Tool("search_players",
                "Search FIFA player database by (partial) name, ranked by overall rating.",
                schema(req("name", "string", "Full or partial player name"),
                        prop("limit", "integer", "Maximum players to return (default 15)")),
                this::searchPlayers));

        tools.add(new Tool("find_players",
                "Find players by nationality, club and/or position, ranked by overall rating. "
                        + "Useful for 'top Brazilian players' or 'forwards at Flamengo'.",
                schema(prop("nationality", "string", "Nationality, e.g. Brazil"),
                        prop("club", "string", "Club name, e.g. Flamengo"),
                        prop("position", "string", "Position code, e.g. ST, GK, CB"),
                        prop("limit", "integer", "Maximum players to return (default 15)")),
                this::findPlayers));

        tools.add(new Tool("average_goals",
                "Average goals per match, optionally filtered by competition and season.",
                schema(prop("competition", "string", "Competition filter"),
                        prop("season", "integer", "Season year")),
                this::averageGoals));

        tools.add(new Tool("biggest_wins",
                "Largest-margin victories, optionally filtered by competition and season.",
                schema(prop("competition", "string", "Competition filter"),
                        prop("season", "integer", "Season year"),
                        prop("limit", "integer", "Maximum matches to return (default 10)")),
                this::biggestWins));

        tools.add(new Tool("list_competitions",
                "List the competitions and season range available in the loaded data.",
                schema(),
                this::listCompetitions));

        return tools;
    }

    // ---- tool handlers -----------------------------------------------------

    private String searchMatches(JsonNode a) {
        String team = str(a, "team");
        String comp = str(a, "competition");
        Integer season = intOrNull(a, "season");
        LocalDate from = dateOrNull(a, "date_from");
        LocalDate to = dateOrNull(a, "date_to");
        int limit = intOr(a, "limit", 25);
        List<Match> matches = q.findMatches(team, comp, season, from, to);
        if (matches.isEmpty()) {
            return "No matches found for the given criteria.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append(matches.size()).append(" match(es) found");
        if (team != null) sb.append(" for ").append(team);
        sb.append(":\n");
        appendMatchList(sb, matches, limit);
        return sb.toString();
    }

    private String matchesBetween(JsonNode a) {
        String teamA = str(a, "team_a");
        String teamB = str(a, "team_b");
        if (teamA == null || teamB == null) {
            return "Both team_a and team_b are required.";
        }
        int limit = intOr(a, "limit", 25);
        List<Match> matches = q.findMatchesBetween(teamA, teamB);
        HeadToHead h = q.headToHead(teamA, teamB);
        StringBuilder sb = new StringBuilder();
        sb.append(h.teamA()).append(" vs ").append(h.teamB()).append(":\n");
        if (matches.isEmpty()) {
            return sb.append("No matches found between these teams.").toString();
        }
        appendMatchList(sb, matches, limit);
        sb.append("\nHead-to-head in dataset: ")
                .append(h.teamA()).append(' ').append(h.teamAWins()).append(" wins, ")
                .append(h.teamB()).append(' ').append(h.teamBWins()).append(" wins, ")
                .append(h.draws()).append(" draws");
        return sb.toString();
    }

    private String headToHead(JsonNode a) {
        String teamA = str(a, "team_a");
        String teamB = str(a, "team_b");
        if (teamA == null || teamB == null) {
            return "Both team_a and team_b are required.";
        }
        HeadToHead h = q.headToHead(teamA, teamB);
        if (h.totalMatches() == 0) {
            return "No matches found between " + teamA + " and " + teamB + ".";
        }
        return h.teamA() + " vs " + h.teamB() + " head-to-head:\n"
                + "- Matches: " + h.totalMatches() + "\n"
                + "- " + h.teamA() + " wins: " + h.teamAWins() + "\n"
                + "- " + h.teamB() + " wins: " + h.teamBWins() + "\n"
                + "- Draws: " + h.draws() + "\n"
                + "- Goals: " + h.teamA() + " " + h.teamAGoals()
                + ", " + h.teamB() + " " + h.teamBGoals();
    }

    private String teamStats(JsonNode a) {
        String team = str(a, "team");
        if (team == null) {
            return "team is required.";
        }
        String comp = str(a, "competition");
        Integer season = intOrNull(a, "season");
        String venue = str(a, "venue");
        boolean homeOnly = "home".equalsIgnoreCase(venue);
        boolean awayOnly = "away".equalsIgnoreCase(venue);
        TeamStats s = q.teamStats(team, comp, season, homeOnly, awayOnly);
        StringBuilder sb = new StringBuilder();
        sb.append(s.team()).append(' ');
        if (homeOnly) sb.append("home ");
        if (awayOnly) sb.append("away ");
        sb.append("record");
        if (season != null || comp != null) {
            sb.append(" (");
            if (season != null) sb.append(season).append(' ');
            sb.append(comp != null ? comp : "all competitions");
            sb.append(')');
        }
        sb.append(":\n");
        sb.append("- Matches: ").append(s.matches()).append('\n');
        sb.append("- Wins: ").append(s.wins())
                .append(", Draws: ").append(s.draws())
                .append(", Losses: ").append(s.losses()).append('\n');
        sb.append("- Goals For: ").append(s.goalsFor())
                .append(", Goals Against: ").append(s.goalsAgainst())
                .append(" (GD: ").append(formatSigned(s.goalDifference())).append(")\n");
        sb.append("- Points: ").append(s.points()).append('\n');
        sb.append("- Win rate: ").append(pct(s.winRate()));
        return sb.toString();
    }

    private String standings(JsonNode a) {
        Integer season = intOrNull(a, "season");
        if (season == null) {
            return "season is required.";
        }
        String comp = a.hasNonNull("competition") ? str(a, "competition")
                : "Brasileirão Série A";
        List<StandingRow> table = q.standings(comp, season);
        if (table.isEmpty()) {
            return "No standings could be computed for " + comp + " " + season + ".";
        }
        StringBuilder sb = new StringBuilder();
        sb.append(season).append(' ').append(comp)
                .append(" final standings (calculated from matches):\n");
        int total = table.size();
        for (StandingRow r : table) {
            sb.append(String.format("%2d. %-28s %3d pts (%dW %dD %dL, GF %d GA %d, GD %s)",
                    r.position(), r.team(), r.points(), r.wins(), r.draws(), r.losses(),
                    r.goalsFor(), r.goalsAgainst(), formatSigned(r.goalDifference())));
            if (r.position() == 1) {
                sb.append("  <- Champion");
            } else if (r.position() > total - 4) {
                sb.append("  <- Relegation zone");
            }
            sb.append('\n');
        }
        return sb.toString().stripTrailing();
    }

    private String searchPlayers(JsonNode a) {
        String name = str(a, "name");
        if (name == null) {
            return "name is required.";
        }
        int limit = intOr(a, "limit", 15);
        List<Player> players = q.searchPlayersByName(name, limit);
        if (players.isEmpty()) {
            return "No players found matching '" + name + "'.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Players matching '").append(name).append("':\n");
        appendPlayerList(sb, players);
        return sb.toString().stripTrailing();
    }

    private String findPlayers(JsonNode a) {
        String nat = str(a, "nationality");
        String club = str(a, "club");
        String pos = str(a, "position");
        int limit = intOr(a, "limit", 15);
        List<Player> players = q.findPlayers(nat, club, pos, limit);
        if (players.isEmpty()) {
            return "No players found for the given filters.";
        }
        StringBuilder sb = new StringBuilder();
        sb.append("Players");
        if (pos != null) sb.append(" (position ").append(pos).append(')');
        if (nat != null) sb.append(" from ").append(nat);
        if (club != null) sb.append(" at ").append(club);
        sb.append(", ranked by overall rating:\n");
        appendPlayerList(sb, players);
        return sb.toString().stripTrailing();
    }

    private String averageGoals(JsonNode a) {
        String comp = str(a, "competition");
        Integer season = intOrNull(a, "season");
        double avg = q.averageGoalsPerMatch(comp, season);
        StringBuilder sb = new StringBuilder("Average goals per match");
        if (comp != null) sb.append(" in ").append(comp);
        if (season != null) sb.append(" (").append(season).append(')');
        sb.append(": ").append(String.format("%.2f", avg));
        return sb.toString();
    }

    private String biggestWins(JsonNode a) {
        String comp = str(a, "competition");
        Integer season = intOrNull(a, "season");
        int limit = intOr(a, "limit", 10);
        List<Match> matches = q.biggestWins(comp, season, limit);
        if (matches.isEmpty()) {
            return "No matches found for the given criteria.";
        }
        StringBuilder sb = new StringBuilder("Biggest victories");
        if (comp != null) sb.append(" in ").append(comp);
        if (season != null) sb.append(" (").append(season).append(')');
        sb.append(":\n");
        int i = 1;
        for (Match m : matches) {
            sb.append(String.format("%2d. %s%n", i++, formatMatch(m)));
        }
        return sb.toString().stripTrailing();
    }

    private String listCompetitions(JsonNode a) {
        var byComp = new java.util.TreeMap<String, int[]>(); // comp -> [count, minSeason, maxSeason]
        for (Match m : q.data().matches()) {
            int[] agg = byComp.computeIfAbsent(m.competition(),
                    k -> new int[]{0, Integer.MAX_VALUE, Integer.MIN_VALUE});
            agg[0]++;
            if (m.season() != null) {
                agg[1] = Math.min(agg[1], m.season());
                agg[2] = Math.max(agg[2], m.season());
            }
        }
        StringBuilder sb = new StringBuilder("Competitions in loaded data:\n");
        byComp.forEach((comp, agg) -> {
            sb.append("- ").append(comp).append(": ").append(agg[0]).append(" matches");
            if (agg[1] != Integer.MAX_VALUE) {
                sb.append(" (").append(agg[1]).append('-').append(agg[2]).append(')');
            }
            sb.append('\n');
        });
        sb.append("Players loaded: ").append(q.data().players().size());
        return sb.toString();
    }

    // ---- formatting helpers ------------------------------------------------

    private void appendMatchList(StringBuilder sb, List<Match> matches, int limit) {
        int shown = Math.min(limit > 0 ? limit : matches.size(), matches.size());
        for (int i = 0; i < shown; i++) {
            sb.append("- ").append(formatMatch(matches.get(i))).append('\n');
        }
        if (matches.size() > shown) {
            sb.append("- ... (").append(matches.size() - shown).append(" more in dataset)\n");
        }
    }

    private String formatMatch(Match m) {
        String date = m.date() != null ? m.date().toString()
                : (m.season() != null ? String.valueOf(m.season()) : "????");
        String score = m.hasScore() ? m.homeGoal() + "-" + m.awayGoal() : "vs";
        StringBuilder ctx = new StringBuilder(m.competition());
        if (m.round() != null) ctx.append(" Round ").append(m.round());
        if (m.stage() != null) ctx.append(" - ").append(m.stage());
        return String.format("%s: %s %s %s (%s)",
                date, m.homeTeam(), score, m.awayTeam(), ctx);
    }

    private void appendPlayerList(StringBuilder sb, List<Player> players) {
        int i = 1;
        for (Player p : players) {
            sb.append(String.format("%2d. %s - Overall: %s, Position: %s, Club: %s, Nationality: %s%n",
                    i++, p.name(),
                    p.overall() == null ? "?" : p.overall(),
                    p.position() == null ? "?" : p.position(),
                    p.club() == null || p.club().isBlank() ? "Free agent" : p.club(),
                    p.nationality()));
        }
    }

    private static String formatSigned(int v) {
        return (v > 0 ? "+" : "") + v;
    }

    private static String pct(double ratio) {
        return String.format("%.1f%%", ratio * 100);
    }

    // ---- JSON-Schema + argument helpers ------------------------------------

    private ObjectNode schema(ObjectNode... props) {
        ObjectNode s = mapper.createObjectNode();
        s.put("type", "object");
        ObjectNode properties = mapper.createObjectNode();
        ArrayNode required = mapper.createArrayNode();
        for (ObjectNode p : props) {
            String name = p.get("__name").asText();
            boolean isReq = p.path("__required").asBoolean(false);
            ObjectNode clean = p.deepCopy();
            clean.remove("__name");
            clean.remove("__required");
            properties.set(name, clean);
            if (isReq) {
                required.add(name);
            }
        }
        s.set("properties", properties);
        if (!required.isEmpty()) {
            s.set("required", required);
        }
        return s;
    }

    private ObjectNode prop(String name, String type, String description) {
        ObjectNode p = mapper.createObjectNode();
        p.put("__name", name);
        p.put("type", type);
        p.put("description", description);
        return p;
    }

    private ObjectNode req(String name, String type, String description) {
        ObjectNode p = prop(name, type, description);
        p.put("__required", true);
        return p;
    }

    private static String str(JsonNode args, String field) {
        if (args == null) return null;
        JsonNode n = args.get(field);
        if (n == null || n.isNull()) return null;
        String s = n.asText().trim();
        return s.isEmpty() ? null : s;
    }

    private static Integer intOrNull(JsonNode args, String field) {
        if (args == null) return null;
        JsonNode n = args.get(field);
        if (n == null || n.isNull()) return null;
        if (n.isNumber()) return n.asInt();
        try {
            return Integer.parseInt(n.asText().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static int intOr(JsonNode args, String field, int fallback) {
        Integer v = intOrNull(args, field);
        return v == null ? fallback : v;
    }

    private static LocalDate dateOrNull(JsonNode args, String field) {
        String s = str(args, field);
        if (s == null) return null;
        try {
            return LocalDate.parse(s);
        } catch (RuntimeException e) {
            return null;
        }
    }
}
