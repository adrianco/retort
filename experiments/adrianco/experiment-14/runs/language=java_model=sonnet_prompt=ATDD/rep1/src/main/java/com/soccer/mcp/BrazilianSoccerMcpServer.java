package com.soccer.mcp;

import com.soccer.mcp.model.Match;
import com.soccer.mcp.model.Player;
import com.soccer.mcp.model.Standing;
import com.soccer.mcp.model.TeamStats;
import com.soccer.mcp.service.DataLoader;
import com.soccer.mcp.service.MatchService;
import com.soccer.mcp.service.PlayerService;
import com.soccer.mcp.service.TeamNameNormalizer;
import io.modelcontextprotocol.server.McpServer;
import io.modelcontextprotocol.server.McpServerFeatures;
import io.modelcontextprotocol.server.transport.StdioServerTransportProvider;
import io.modelcontextprotocol.spec.McpSchema;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

/**
 * MCP Server for Brazilian soccer data.
 * Exposes 6 MCP tools for querying match, player, and statistics data.
 */
public class BrazilianSoccerMcpServer {

    private final MatchService matchService;
    private final PlayerService playerService;
    private final TeamNameNormalizer normalizer;

    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    public BrazilianSoccerMcpServer() {
        String dataPath = System.getProperty("data.path", "data/kaggle");
        DataLoader loader = new DataLoader(dataPath);
        List<Match> matches = loader.loadAllMatches();
        List<Player> players = loader.loadPlayers();
        this.normalizer = new TeamNameNormalizer();
        this.matchService = new MatchService(matches, normalizer);
        this.playerService = new PlayerService(players);
    }

    // ---- MCP Tool Methods (public API) ----

    /**
     * Find matches by team, competition, season, or date range.
     */
    public String findMatches(String team, String homeTeam, String awayTeam,
                               String competition, Integer season,
                               String dateFrom, String dateTo, Integer limit) {
        int lim = limit != null ? limit : 20;
        LocalDate from = parseDate(dateFrom);
        LocalDate to = parseDate(dateTo);

        List<Match> results = matchService.findMatches(team, homeTeam, awayTeam,
                competition, season, from, to, lim);

        if (results.isEmpty()) {
            return "No matches found for the specified criteria.";
        }

        StringBuilder sb = new StringBuilder();
        sb.append(String.format("Found %d matches:\n", results.size()));
        sb.append("=".repeat(60)).append("\n");
        for (Match m : results) {
            String dateStr = m.getDate() != null ? m.getDate().toString() : "unknown";
            String roundStr = m.getRound() != null ? ", Round " + m.getRound() : "";
            String stageStr = m.getStage() != null ? ", " + m.getStage() : "";
            sb.append(String.format("[%s] %s %d-%d %s (%s%s%s)\n",
                    m.getCompetition(), m.getHomeTeam(), m.getHomeGoals(), m.getAwayGoals(),
                    m.getAwayTeam(), dateStr, roundStr, stageStr));
        }
        return sb.toString();
    }

    /**
     * Get team statistics for wins, draws, losses, goals for a competition/season.
     */
    public String getTeamStats(String team, String competition, Integer season) {
        TeamStats stats = matchService.getTeamStats(team, competition, season);

        StringBuilder sb = new StringBuilder();
        String competitionStr = competition != null ? competition : "all competitions";
        String seasonStr = season != null ? String.valueOf(season) : "all seasons";
        sb.append(String.format("Team Statistics: %s\n", team));
        sb.append(String.format("Competition: %s | Season: %s\n", competitionStr, seasonStr));
        sb.append("=".repeat(50)).append("\n");
        sb.append(String.format("Matches played: %d\n", stats.getMatchesPlayed()));
        sb.append(String.format("Wins: %d\n", stats.getWins()));
        sb.append(String.format("Draws: %d\n", stats.getDraws()));
        sb.append(String.format("Losses: %d\n", stats.getLosses()));
        sb.append(String.format("Goals scored: %d\n", stats.getGoalsScored()));
        sb.append(String.format("Goals conceded: %d\n", stats.getGoalsConceded()));
        sb.append(String.format("Goal difference: %+d\n", stats.getGoalDifference()));
        sb.append(String.format("Points: %d\n", stats.getPoints()));
        return sb.toString();
    }

    /**
     * Find players by name, nationality, club, position, or minimum overall rating.
     */
    public String findPlayers(String name, String nationality, String club,
                               String position, Integer minOverall, Integer limit) {
        int lim = limit != null ? limit : 20;
        List<Player> results = playerService.findPlayers(name, nationality, club, position, minOverall, lim);

        if (results.isEmpty()) {
            return "No players found for the specified criteria.";
        }

        StringBuilder sb = new StringBuilder();
        sb.append(String.format("Found %d players:\n", results.size()));
        sb.append("=".repeat(60)).append("\n");
        for (Player p : results) {
            sb.append(String.format("%-30s | %s | %s | Overall: %d | Potential: %d | Club: %s\n",
                    p.getName(), p.getPosition(), p.getNationality(),
                    p.getOverall(), p.getPotential(), p.getClub()));
        }
        return sb.toString();
    }

    /**
     * Get standings table for a competition and optional season.
     */
    public String getStandings(Integer season, String competition, Integer limit) {
        int lim = limit != null ? limit : 20;
        List<Standing> standings = matchService.getStandings(season, competition, lim);

        if (standings.isEmpty()) {
            return "No standings data found for the specified criteria.";
        }

        StringBuilder sb = new StringBuilder();
        String competitionStr = competition != null ? competition : "all competitions";
        String seasonStr = season != null ? String.valueOf(season) : "all seasons";
        sb.append(String.format("Standings: %s | Season: %s\n", competitionStr, seasonStr));
        sb.append("=".repeat(75)).append("\n");
        sb.append(String.format("%-4s %-30s %4s %4s %4s %4s %4s %4s %5s\n",
                "Pos", "Team", "MP", "W", "D", "L", "GF", "GA", "Pts"));
        sb.append("-".repeat(75)).append("\n");
        for (Standing s : standings) {
            TeamStats ts = s.getStats();
            sb.append(String.format("%-4d %-30s %4d %4d %4d %4d %4d %4d %5d\n",
                    s.getPosition(), ts.getTeam(), ts.getMatchesPlayed(),
                    ts.getWins(), ts.getDraws(), ts.getLosses(),
                    ts.getGoalsScored(), ts.getGoalsConceded(), ts.getPoints()));
        }
        return sb.toString();
    }

    /**
     * Get head-to-head record between two teams.
     */
    public String getHeadToHead(String team1, String team2, String competition, Integer season) {
        Map<String, Object> h2h = matchService.getHeadToHead(team1, team2, competition, season);

        StringBuilder sb = new StringBuilder();
        sb.append(String.format("Head-to-Head: %s vs %s\n", team1, team2));
        if (competition != null) sb.append(String.format("Competition: %s\n", competition));
        if (season != null) sb.append(String.format("Season: %d\n", season));
        sb.append("=".repeat(50)).append("\n");
        sb.append(String.format("Total matches: %d\n", h2h.get("total")));
        sb.append(String.format("%s wins: %d\n", team1, h2h.get("team1Wins")));
        sb.append(String.format("%s wins: %d\n", team2, h2h.get("team2Wins")));
        sb.append(String.format("Draws: %d\n", h2h.get("draws")));
        sb.append(String.format("Goals: %s %d - %d %s\n",
                team1, h2h.get("team1Goals"), h2h.get("team2Goals"), team2));
        sb.append("\nRecent matches:\n");
        Object recentObj = h2h.get("recentMatches");
        if (recentObj instanceof List) {
            List<?> recent = (List<?>) recentObj;
            for (Object obj : recent) {
                if (obj instanceof Match) {
                    Match m = (Match) obj;
                    String dateStr = m.getDate() != null ? m.getDate().toString() : "unknown";
                    sb.append(String.format("  [%s] %s %d-%d %s (%s)\n",
                            m.getCompetition(), m.getHomeTeam(), m.getHomeGoals(),
                            m.getAwayGoals(), m.getAwayTeam(), dateStr));
                }
            }
        }
        return sb.toString();
    }

    /**
     * Get statistics: biggest_wins, avg_goals, or home_record.
     */
    public String getStatistics(String statType, String competition, Integer season) {
        return matchService.getStatistics(statType, competition, season);
    }

    // ---- MCP Server Registration ----

    public void startMcpServer() {
        StdioServerTransportProvider transport = new StdioServerTransportProvider();

        String findMatchesSchema = "{" +
                "\"type\":\"object\"," +
                "\"properties\":{" +
                "\"team\":{\"type\":\"string\",\"description\":\"Team name (matches either home or away)\"}," +
                "\"homeTeam\":{\"type\":\"string\",\"description\":\"Home team name\"}," +
                "\"awayTeam\":{\"type\":\"string\",\"description\":\"Away team name\"}," +
                "\"competition\":{\"type\":\"string\",\"description\":\"Competition: brasileirao, copa_do_brasil, libertadores\"}," +
                "\"season\":{\"type\":\"integer\",\"description\":\"Season year\"}," +
                "\"dateFrom\":{\"type\":\"string\",\"description\":\"Start date (yyyy-MM-dd)\"}," +
                "\"dateTo\":{\"type\":\"string\",\"description\":\"End date (yyyy-MM-dd)\"}," +
                "\"limit\":{\"type\":\"integer\",\"description\":\"Max results (default 20)\"}" +
                "}" +
                "}";

        String getTeamStatsSchema = "{" +
                "\"type\":\"object\"," +
                "\"properties\":{" +
                "\"team\":{\"type\":\"string\",\"description\":\"Team name\"}," +
                "\"competition\":{\"type\":\"string\",\"description\":\"Competition name\"}," +
                "\"season\":{\"type\":\"integer\",\"description\":\"Season year\"}" +
                "}," +
                "\"required\":[\"team\"]" +
                "}";

        String findPlayersSchema = "{" +
                "\"type\":\"object\"," +
                "\"properties\":{" +
                "\"name\":{\"type\":\"string\",\"description\":\"Player name (partial match)\"}," +
                "\"nationality\":{\"type\":\"string\",\"description\":\"Player nationality\"}," +
                "\"club\":{\"type\":\"string\",\"description\":\"Club name\"}," +
                "\"position\":{\"type\":\"string\",\"description\":\"Player position (GK, CB, LB, etc.)\"}," +
                "\"minOverall\":{\"type\":\"integer\",\"description\":\"Minimum overall rating\"}," +
                "\"limit\":{\"type\":\"integer\",\"description\":\"Max results (default 20)\"}" +
                "}" +
                "}";

        String getStandingsSchema = "{" +
                "\"type\":\"object\"," +
                "\"properties\":{" +
                "\"season\":{\"type\":\"integer\",\"description\":\"Season year\"}," +
                "\"competition\":{\"type\":\"string\",\"description\":\"Competition name\"}," +
                "\"limit\":{\"type\":\"integer\",\"description\":\"Max teams to show (default 20)\"}" +
                "}" +
                "}";

        String getHeadToHeadSchema = "{" +
                "\"type\":\"object\"," +
                "\"properties\":{" +
                "\"team1\":{\"type\":\"string\",\"description\":\"First team\"}," +
                "\"team2\":{\"type\":\"string\",\"description\":\"Second team\"}," +
                "\"competition\":{\"type\":\"string\",\"description\":\"Filter by competition\"}," +
                "\"season\":{\"type\":\"integer\",\"description\":\"Filter by season\"}" +
                "}," +
                "\"required\":[\"team1\",\"team2\"]" +
                "}";

        String getStatisticsSchema = "{" +
                "\"type\":\"object\"," +
                "\"properties\":{" +
                "\"statType\":{\"type\":\"string\",\"description\":\"Type: biggest_wins, avg_goals, home_record\"}," +
                "\"competition\":{\"type\":\"string\",\"description\":\"Competition filter\"}," +
                "\"season\":{\"type\":\"integer\",\"description\":\"Season filter\"}" +
                "}," +
                "\"required\":[\"statType\"]" +
                "}";

        BrazilianSoccerMcpServer self = this;

        McpServerFeatures.SyncToolSpecification findMatchesTool = new McpServerFeatures.SyncToolSpecification(
                new McpSchema.Tool("findMatches", "Find soccer matches by team, competition, season, or date range",
                        findMatchesSchema),
                (exchange, args) -> {
                    String result = self.findMatches(
                            getStr(args, "team"), getStr(args, "homeTeam"), getStr(args, "awayTeam"),
                            getStr(args, "competition"), getInt(args, "season"),
                            getStr(args, "dateFrom"), getStr(args, "dateTo"), getInt(args, "limit"));
                    return new McpSchema.CallToolResult(result, false);
                }
        );

        McpServerFeatures.SyncToolSpecification getTeamStatsTool = new McpServerFeatures.SyncToolSpecification(
                new McpSchema.Tool("getTeamStats", "Get team statistics for a competition and season",
                        getTeamStatsSchema),
                (exchange, args) -> {
                    String result = self.getTeamStats(
                            getStr(args, "team"), getStr(args, "competition"), getInt(args, "season"));
                    return new McpSchema.CallToolResult(result, false);
                }
        );

        McpServerFeatures.SyncToolSpecification findPlayersTool = new McpServerFeatures.SyncToolSpecification(
                new McpSchema.Tool("findPlayers", "Find players by name, nationality, club, position, or rating",
                        findPlayersSchema),
                (exchange, args) -> {
                    String result = self.findPlayers(
                            getStr(args, "name"), getStr(args, "nationality"), getStr(args, "club"),
                            getStr(args, "position"), getInt(args, "minOverall"), getInt(args, "limit"));
                    return new McpSchema.CallToolResult(result, false);
                }
        );

        McpServerFeatures.SyncToolSpecification getStandingsTool = new McpServerFeatures.SyncToolSpecification(
                new McpSchema.Tool("getStandings", "Get league standings for a competition and season",
                        getStandingsSchema),
                (exchange, args) -> {
                    String result = self.getStandings(
                            getInt(args, "season"), getStr(args, "competition"), getInt(args, "limit"));
                    return new McpSchema.CallToolResult(result, false);
                }
        );

        McpServerFeatures.SyncToolSpecification getHeadToHeadTool = new McpServerFeatures.SyncToolSpecification(
                new McpSchema.Tool("getHeadToHead", "Get head-to-head record between two teams",
                        getHeadToHeadSchema),
                (exchange, args) -> {
                    String result = self.getHeadToHead(
                            getStr(args, "team1"), getStr(args, "team2"),
                            getStr(args, "competition"), getInt(args, "season"));
                    return new McpSchema.CallToolResult(result, false);
                }
        );

        McpServerFeatures.SyncToolSpecification getStatisticsTool = new McpServerFeatures.SyncToolSpecification(
                new McpSchema.Tool("getStatistics", "Get match statistics: biggest wins, avg goals, home record",
                        getStatisticsSchema),
                (exchange, args) -> {
                    String result = self.getStatistics(
                            getStr(args, "statType"), getStr(args, "competition"), getInt(args, "season"));
                    return new McpSchema.CallToolResult(result, false);
                }
        );

        McpServer.sync(transport)
                .serverInfo("Brazilian Soccer MCP", "1.0.0")
                .tools(findMatchesTool, getTeamStatsTool, findPlayersTool,
                       getStandingsTool, getHeadToHeadTool, getStatisticsTool)
                .build();
    }

    private static String getStr(Map<String, Object> args, String key) {
        Object val = args.get(key);
        return val != null ? val.toString() : null;
    }

    private static Integer getInt(Map<String, Object> args, String key) {
        Object val = args.get(key);
        if (val == null) return null;
        if (val instanceof Number) return ((Number) val).intValue();
        try {
            return Integer.parseInt(val.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static LocalDate parseDate(String dateStr) {
        if (dateStr == null || dateStr.isEmpty()) return null;
        try {
            return LocalDate.parse(dateStr, DATE_FMT);
        } catch (Exception e) {
            return null;
        }
    }

    public static void main(String[] args) {
        BrazilianSoccerMcpServer server = new BrazilianSoccerMcpServer();
        server.startMcpServer();
    }
}
