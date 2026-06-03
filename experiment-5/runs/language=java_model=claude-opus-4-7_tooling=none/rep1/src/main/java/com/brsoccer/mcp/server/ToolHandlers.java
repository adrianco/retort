package com.brsoccer.mcp.server;

import com.brsoccer.mcp.model.Competition;
import com.brsoccer.mcp.model.Match;
import com.brsoccer.mcp.model.Player;
import com.brsoccer.mcp.service.TeamService;
import com.brsoccer.mcp.service.TeamStats;
import com.fasterxml.jackson.databind.JsonNode;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Maps MCP tool calls to SoccerKnowledgeBase queries.
 * Each handler returns a plain text rendering suitable for an LLM tool-call response.
 */
public class ToolHandlers {

    private final SoccerKnowledgeBase kb;

    public ToolHandlers(SoccerKnowledgeBase kb) {
        this.kb = kb;
    }

    public String dispatch(String tool, JsonNode args) {
        if (args == null) args = com.fasterxml.jackson.databind.node.MissingNode.getInstance();
        switch (tool) {
            case "find_matches_between_teams":
                return findMatchesBetween(args.path("team_a").asText(""), args.path("team_b").asText(""), optInt(args, "limit", 20));
            case "find_matches_by_team":
                return findMatchesByTeam(args.path("team").asText(""),
                    SoccerKnowledgeBase.parseCompetition(args.path("competition").asText(null)),
                    optInt(args, "season", null),
                    optInt(args, "limit", 20));
            case "team_stats":
                return teamStats(args.path("team").asText(""),
                    SoccerKnowledgeBase.parseCompetition(args.path("competition").asText(null)),
                    optInt(args, "season", null),
                    args.path("location").asText("all"));
            case "head_to_head":
                return headToHead(args.path("team_a").asText(""), args.path("team_b").asText(""));
            case "find_players_by_name":
                return findPlayersByName(args.path("name").asText(""), optInt(args, "limit", 10));
            case "find_players_by_nationality":
                return findPlayersByNationality(args.path("nationality").asText("Brazil"), optInt(args, "limit", 20));
            case "find_players_by_club":
                return findPlayersByClub(args.path("club").asText(""), optInt(args, "limit", 25));
            case "top_rated_players":
                return topPlayers(optInt(args, "limit", 10), args.path("nationality").asText(null));
            case "season_standings":
                return standings(SoccerKnowledgeBase.parseCompetition(args.path("competition").asText("brasileirao")),
                    args.path("season").asInt(), optInt(args, "limit", 20));
            case "season_champion":
                return champion(SoccerKnowledgeBase.parseCompetition(args.path("competition").asText("brasileirao")),
                    args.path("season").asInt());
            case "biggest_wins":
                return biggestWins(SoccerKnowledgeBase.parseCompetition(args.path("competition").asText(null)),
                    optInt(args, "limit", 10));
            case "competition_summary":
                return competitionSummary(SoccerKnowledgeBase.parseCompetition(args.path("competition").asText(null)),
                    optInt(args, "season", null));
            default:
                throw new IllegalArgumentException("Unknown tool: " + tool);
        }
    }

    // --- tool implementations ------------------------------------------

    public String findMatchesBetween(String a, String b, int limit) {
        if (a.isEmpty() || b.isEmpty()) return "Usage: provide team_a and team_b.";
        List<Match> ms = kb.matches().findBetween(a, b);
        if (ms.isEmpty()) return "No matches found between " + a + " and " + b + ".";
        StringBuilder sb = new StringBuilder();
        sb.append(a).append(" vs ").append(b).append(":\n");
        int winsA = 0, winsB = 0, draws = 0, gA = 0, gB = 0;
        String na = com.brsoccer.mcp.data.TeamNameNormalizer.normalize(a);
        for (Match m : ms.subList(0, Math.min(limit, ms.size()))) {
            sb.append("- ").append(m.getDate()).append(": ")
              .append(m.getHomeTeam()).append(" ").append(m.getHomeGoals())
              .append("-").append(m.getAwayGoals()).append(" ").append(m.getAwayTeam())
              .append(" (").append(m.getCompetition().getDisplayName()).append(")\n");
        }
        for (Match m : ms) {
            if (m.getHomeGoals() == null || m.getAwayGoals() == null) continue;
            boolean aHome = na.equals(m.getHomeTeamNormalized());
            int ga = aHome ? m.getHomeGoals() : m.getAwayGoals();
            int gb = aHome ? m.getAwayGoals() : m.getHomeGoals();
            gA += ga; gB += gb;
            if (ga > gb) winsA++;
            else if (gb > ga) winsB++;
            else draws++;
        }
        sb.append("\nTotal matches in dataset: ").append(ms.size())
          .append(". Head-to-head: ").append(a).append(" ").append(winsA)
          .append(" wins, ").append(b).append(" ").append(winsB)
          .append(" wins, ").append(draws).append(" draws. Goals: ")
          .append(gA).append("-").append(gB).append(".");
        return sb.toString();
    }

    public String findMatchesByTeam(String team, Competition c, Integer season, int limit) {
        if (team.isBlank()) return "Usage: provide team.";
        List<Match> ms = kb.matches().filter(team, c, season);
        if (ms.isEmpty()) return "No matches for " + team + ".";
        StringBuilder sb = new StringBuilder();
        sb.append(team)
          .append(c == null ? "" : " in " + c.getDisplayName())
          .append(season == null ? "" : " season " + season)
          .append(" (").append(ms.size()).append(" matches):\n");
        for (Match m : ms.subList(0, Math.min(limit, ms.size()))) {
            sb.append("- ").append(m.getDate()).append(": ")
              .append(m.getHomeTeam()).append(" ").append(m.getHomeGoals())
              .append("-").append(m.getAwayGoals()).append(" ").append(m.getAwayTeam())
              .append(" (").append(m.getCompetition().getDisplayName()).append(")\n");
        }
        return sb.toString();
    }

    public String teamStats(String team, Competition c, Integer season, String location) {
        if (team.isBlank()) return "Usage: provide team.";
        TeamStats s;
        switch (location == null ? "all" : location.toLowerCase()) {
            case "home": s = kb.teams().homeStats(team, c, season); break;
            case "away": s = kb.teams().awayStats(team, c, season); break;
            default:     s = kb.teams().stats(team, c, season); break;
        }
        return String.format("%s %s%s%s record:%n- Matches: %d%n- Wins: %d, Draws: %d, Losses: %d%n- Goals For: %d, Goals Against: %d%n- Win rate: %.1f%%%n- Points: %d",
            team,
            location == null ? "" : location,
            c == null ? "" : " " + c.getDisplayName(),
            season == null ? "" : " " + season,
            s.matches, s.wins, s.draws, s.losses, s.goalsFor, s.goalsAgainst,
            s.winRate() * 100.0, s.points());
    }

    public String headToHead(String a, String b) {
        if (a.isBlank() || b.isBlank()) return "Usage: provide team_a and team_b.";
        TeamService.HeadToHead h = kb.teams().headToHead(a, b);
        return String.format("Head-to-head %s vs %s:%n- Total: %d%n- %s wins: %d%n- %s wins: %d%n- Draws: %d%n- Goals: %s %d - %d %s",
            a, b, h.matches, a, h.winsA, b, h.winsB, h.draws, a, h.goalsA, h.goalsB, b);
    }

    public String findPlayersByName(String name, int limit) {
        List<Player> ps = kb.players().searchByName(name);
        if (ps.isEmpty()) return "No players matching '" + name + "'.";
        return renderPlayers(ps, limit, "Players matching '" + name + "':");
    }

    public String findPlayersByNationality(String nat, int limit) {
        List<Player> ps = kb.players().byNationality(nat);
        if (ps.isEmpty()) return "No players from " + nat + ".";
        return renderPlayers(ps, limit, "Players from " + nat + " (" + ps.size() + " total):");
    }

    public String findPlayersByClub(String club, int limit) {
        List<Player> ps = kb.players().byClub(club);
        if (ps.isEmpty()) return "No players at " + club + ".";
        return renderPlayers(ps, limit, "Players at " + club + " (" + ps.size() + " total):");
    }

    public String topPlayers(int limit, String nationalityFilter) {
        List<Player> ps;
        if (nationalityFilter != null && !nationalityFilter.isBlank()) {
            ps = kb.players().byNationality(nationalityFilter);
        } else {
            ps = kb.players().topRated(limit);
        }
        return renderPlayers(ps, limit, "Top-rated players" + (nationalityFilter != null ? " from " + nationalityFilter : "") + ":");
    }

    public String standings(Competition c, int season, int limit) {
        if (c == null) c = Competition.BRASILEIRAO;
        List<TeamStats> ts = kb.competitions().standings(c, season);
        if (ts.isEmpty()) return "No standings for " + c.getDisplayName() + " " + season + ".";
        StringBuilder sb = new StringBuilder();
        sb.append(season).append(" ").append(c.getDisplayName()).append(" Final Standings (").append(ts.size()).append(" teams):\n");
        int rank = 1;
        for (TeamStats s : ts.subList(0, Math.min(limit, ts.size()))) {
            sb.append(rank++).append(". ").append(s.team)
              .append(" - ").append(s.points()).append(" pts")
              .append(" (").append(s.wins).append("W, ").append(s.draws).append("D, ").append(s.losses).append("L")
              .append(", GF ").append(s.goalsFor).append(", GA ").append(s.goalsAgainst).append(")\n");
        }
        return sb.toString();
    }

    public String champion(Competition c, int season) {
        if (c == null) c = Competition.BRASILEIRAO;
        TeamStats champ = kb.competitions().champion(c, season);
        if (champ == null) return "No data for " + c.getDisplayName() + " " + season + ".";
        return String.format("Champion of %d %s: %s (%d pts, %dW %dD %dL, GF %d, GA %d)",
            season, c.getDisplayName(), champ.team, champ.points(), champ.wins, champ.draws, champ.losses,
            champ.goalsFor, champ.goalsAgainst);
    }

    public String biggestWins(Competition c, int limit) {
        List<Match> ms = kb.stats().biggestWins(c, limit);
        StringBuilder sb = new StringBuilder();
        sb.append("Biggest victories").append(c == null ? "" : " in " + c.getDisplayName()).append(":\n");
        for (Match m : ms) {
            sb.append("- ").append(m.getDate()).append(": ")
              .append(m.getHomeTeam()).append(" ").append(m.getHomeGoals())
              .append("-").append(m.getAwayGoals()).append(" ").append(m.getAwayTeam())
              .append(" (").append(m.getCompetition().getDisplayName()).append(")\n");
        }
        return sb.toString();
    }

    public String competitionSummary(Competition c, Integer season) {
        double avg = kb.stats().averageGoalsPerMatch(c, season);
        double homeWin = kb.stats().homeWinRate(c, season);
        StringBuilder sb = new StringBuilder();
        sb.append("Summary").append(c == null ? "" : " for " + c.getDisplayName()).append(season == null ? "" : " " + season).append(":\n");
        sb.append(String.format("- Average goals per match: %.2f%n", avg));
        sb.append(String.format("- Home win rate: %.1f%%", homeWin * 100));
        return sb.toString();
    }

    private static String renderPlayers(List<Player> ps, int limit, String header) {
        StringBuilder sb = new StringBuilder();
        sb.append(header).append("\n");
        int rank = 1;
        for (Player p : ps.stream().limit(limit).collect(Collectors.toList())) {
            sb.append(rank++).append(". ").append(p.getName())
              .append(" - Overall: ").append(p.getOverall())
              .append(", Position: ").append(p.getPosition())
              .append(", Club: ").append(p.getClub())
              .append(", Nationality: ").append(p.getNationality())
              .append("\n");
        }
        return sb.toString();
    }

    private static Integer optInt(JsonNode args, String key, Integer dflt) {
        JsonNode n = args.get(key);
        if (n == null || n.isNull() || n.isMissingNode()) return dflt;
        if (n.isInt()) return n.asInt();
        if (n.isTextual()) {
            try { return Integer.parseInt(n.asText().trim()); }
            catch (NumberFormatException e) { return dflt; }
        }
        return dflt;
    }

    /** Tool definitions exposed to MCP clients. */
    public static Map<String, Map<String, Object>> toolDefinitions() {
        Map<String, Map<String, Object>> tools = new LinkedHashMap<>();
        tools.put("find_matches_between_teams", toolSchema(
            "Find all matches between two teams.",
            Map.of(
                "team_a", strProp("First team name"),
                "team_b", strProp("Second team name"),
                "limit", intProp("Maximum matches to list")
            ),
            List.of("team_a", "team_b")));
        tools.put("find_matches_by_team", toolSchema(
            "Find matches involving a team, optionally filtered by competition/season.",
            Map.of(
                "team", strProp("Team name"),
                "competition", strProp("brasileirao | copa_do_brasil | libertadores | historical"),
                "season", intProp("Season year"),
                "limit", intProp("Maximum matches to list")
            ),
            List.of("team")));
        tools.put("team_stats", toolSchema(
            "Get aggregate stats (wins/draws/losses, goals) for a team.",
            Map.of(
                "team", strProp("Team name"),
                "competition", strProp("Optional competition filter"),
                "season", intProp("Optional season filter"),
                "location", strProp("all | home | away")
            ),
            List.of("team")));
        tools.put("head_to_head", toolSchema(
            "Head-to-head record between two teams.",
            Map.of(
                "team_a", strProp("First team"),
                "team_b", strProp("Second team")
            ),
            List.of("team_a", "team_b")));
        tools.put("find_players_by_name", toolSchema(
            "Search FIFA players by name substring.",
            Map.of(
                "name", strProp("Name search"),
                "limit", intProp("Max results")
            ),
            List.of("name")));
        tools.put("find_players_by_nationality", toolSchema(
            "Get players for a given nationality (e.g. Brazil).",
            Map.of(
                "nationality", strProp("Country"),
                "limit", intProp("Max results")
            ),
            List.of("nationality")));
        tools.put("find_players_by_club", toolSchema(
            "Get players currently at a given club.",
            Map.of(
                "club", strProp("Club name"),
                "limit", intProp("Max results")
            ),
            List.of("club")));
        tools.put("top_rated_players", toolSchema(
            "List top-rated players, optionally filtered by nationality.",
            Map.of(
                "limit", intProp("Max results"),
                "nationality", strProp("Optional nationality filter")
            ),
            List.of()));
        tools.put("season_standings", toolSchema(
            "Compute end-of-season standings from match results.",
            Map.of(
                "competition", strProp("Competition (default brasileirao)"),
                "season", intProp("Year"),
                "limit", intProp("Number of teams to list")
            ),
            List.of("season")));
        tools.put("season_champion", toolSchema(
            "Get the champion (top-of-table) for a season.",
            Map.of(
                "competition", strProp("Competition"),
                "season", intProp("Year")
            ),
            List.of("season")));
        tools.put("biggest_wins", toolSchema(
            "List the biggest winning margins.",
            Map.of(
                "competition", strProp("Optional competition filter"),
                "limit", intProp("Max results")
            ),
            List.of()));
        tools.put("competition_summary", toolSchema(
            "Aggregated stats (avg goals/match, home win rate) for a competition/season.",
            Map.of(
                "competition", strProp("Optional competition"),
                "season", intProp("Optional season")
            ),
            List.of()));
        return tools;
    }

    private static Map<String, Object> toolSchema(String description, Map<String, Object> properties, List<String> required) {
        Map<String, Object> schema = new LinkedHashMap<>();
        schema.put("type", "object");
        schema.put("properties", properties);
        if (!required.isEmpty()) schema.put("required", required);
        Map<String, Object> tool = new LinkedHashMap<>();
        tool.put("description", description);
        tool.put("inputSchema", schema);
        return tool;
    }

    private static Map<String, Object> strProp(String desc) {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("type", "string");
        p.put("description", desc);
        return p;
    }

    private static Map<String, Object> intProp(String desc) {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("type", "integer");
        p.put("description", desc);
        return p;
    }
}
