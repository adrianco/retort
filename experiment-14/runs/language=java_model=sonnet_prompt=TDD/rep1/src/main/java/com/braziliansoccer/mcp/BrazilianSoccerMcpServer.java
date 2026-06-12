package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.loader.MatchLoader;
import com.braziliansoccer.mcp.loader.PlayerLoader;
import com.braziliansoccer.mcp.model.Match;
import com.braziliansoccer.mcp.model.Player;
import com.braziliansoccer.mcp.service.MatchService;
import com.braziliansoccer.mcp.service.PlayerService;
import com.braziliansoccer.mcp.service.StatisticsService;

import io.modelcontextprotocol.server.McpServer;
import io.modelcontextprotocol.server.McpSyncServer;
import io.modelcontextprotocol.server.transport.StdioServerTransportProvider;
import io.modelcontextprotocol.json.McpJsonDefaults;
import io.modelcontextprotocol.json.McpJsonMapper;
import io.modelcontextprotocol.spec.McpSchema;

import java.util.*;
import java.util.stream.Collectors;

public class BrazilianSoccerMcpServer {

    private static final String DATA_DIR = "./data/kaggle/";

    public static void main(String[] args) throws Exception {
        // Load data
        System.err.println("Loading match data...");
        MatchLoader matchLoader = new MatchLoader(DATA_DIR);
        List<Match> allMatches = matchLoader.loadAll();
        System.err.println("Loaded " + allMatches.size() + " matches");

        System.err.println("Loading player data...");
        PlayerLoader playerLoader = new PlayerLoader(DATA_DIR);
        List<Player> allPlayers = playerLoader.loadAll();
        System.err.println("Loaded " + allPlayers.size() + " players");

        // Create services
        MatchService matchService = new MatchService(allMatches);
        PlayerService playerService = new PlayerService(allPlayers);
        StatisticsService statisticsService = new StatisticsService(allMatches);

        // Create JSON mapper
        McpJsonMapper jsonMapper = McpJsonDefaults.getMapper();

        // Create transport
        StdioServerTransportProvider transport = new StdioServerTransportProvider(jsonMapper);

        // Build MCP server with tools
        McpSyncServer server = McpServer.sync(transport)
            .serverInfo("brazilian-soccer-mcp", "1.0.0")
            .capabilities(McpSchema.ServerCapabilities.builder().tools(true).build())
            .toolCall(buildFindMatchesTool(), (exchange, request) -> {
                Map<String, Object> args2 = request.arguments();
                String team = getStr(args2, "team");
                String competition = getStr(args2, "competition");
                String seasonStr = getStr(args2, "season");

                List<Match> results;
                if (team != null && !team.isBlank()) {
                    results = matchService.findByTeam(team);
                } else {
                    results = allMatches;
                }
                if (competition != null && !competition.isBlank()) {
                    String comp = competition;
                    results = results.stream()
                        .filter(m -> m.competition().equalsIgnoreCase(comp))
                        .collect(Collectors.toList());
                }
                if (seasonStr != null && !seasonStr.isBlank()) {
                    try {
                        int season = Integer.parseInt(seasonStr.trim());
                        results = results.stream()
                            .filter(m -> m.season() == season)
                            .collect(Collectors.toList());
                    } catch (NumberFormatException ignored) {}
                }
                // Limit results
                int limit = 20;
                String limitStr = getStr(args2, "limit");
                if (limitStr != null && !limitStr.isBlank()) {
                    try { limit = Integer.parseInt(limitStr.trim()); } catch (NumberFormatException ignored) {}
                }
                List<Match> limited = results.stream().limit(limit).collect(Collectors.toList());
                String text = formatMatches(limited, results.size());
                return McpSchema.CallToolResult.builder().addTextContent(text).build();
            })
            .toolCall(buildGetTeamStatsTool(), (exchange, request) -> {
                Map<String, Object> args2 = request.arguments();
                String team = getStr(args2, "team");
                String competition = getStr(args2, "competition");
                String seasonStr = getStr(args2, "season");
                if (team == null || team.isBlank()) {
                    return McpSchema.CallToolResult.builder()
                        .addTextContent("Error: 'team' parameter is required")
                        .isError(true).build();
                }
                Integer season = null;
                if (seasonStr != null && !seasonStr.isBlank()) {
                    try { season = Integer.parseInt(seasonStr.trim()); } catch (NumberFormatException ignored) {}
                }
                StatisticsService.TeamRecord record = statisticsService.getTeamRecord(team, competition, season);
                int played = record.wins() + record.draws() + record.losses();
                int points = record.wins() * 3 + record.draws();
                String text = String.format(
                    "Team Statistics for %s%s%s:\n" +
                    "Played: %d | Won: %d | Drawn: %d | Lost: %d\n" +
                    "Goals For: %d | Goals Against: %d | Goal Difference: %d\n" +
                    "Points: %d",
                    team,
                    competition != null ? " in " + competition : "",
                    season != null ? " (" + season + ")" : "",
                    played, record.wins(), record.draws(), record.losses(),
                    record.goalsFor(), record.goalsAgainst(), record.goalsFor() - record.goalsAgainst(),
                    points
                );
                return McpSchema.CallToolResult.builder().addTextContent(text).build();
            })
            .toolCall(buildFindPlayersTool(), (exchange, request) -> {
                Map<String, Object> args2 = request.arguments();
                String name = getStr(args2, "name");
                String nationality = getStr(args2, "nationality");
                String club = getStr(args2, "club");
                String topStr = getStr(args2, "top");

                List<Player> results = allPlayers;
                if (name != null && !name.isBlank()) {
                    results = playerService.findByName(name);
                } else if (nationality != null && !nationality.isBlank()) {
                    results = playerService.findByNationality(nationality);
                } else if (club != null && !club.isBlank()) {
                    results = playerService.findByClub(club);
                } else if (topStr != null && !topStr.isBlank()) {
                    try {
                        int top = Integer.parseInt(topStr.trim());
                        results = playerService.getTopPlayers(top);
                    } catch (NumberFormatException ignored) {}
                }

                int limit = 20;
                String limitStr = getStr(args2, "limit");
                if (limitStr != null && !limitStr.isBlank()) {
                    try { limit = Integer.parseInt(limitStr.trim()); } catch (NumberFormatException ignored) {}
                }
                List<Player> limited = results.stream().limit(limit).collect(Collectors.toList());
                String text = formatPlayers(limited, results.size());
                return McpSchema.CallToolResult.builder().addTextContent(text).build();
            })
            .toolCall(buildGetHeadToHeadTool(), (exchange, request) -> {
                Map<String, Object> args2 = request.arguments();
                String team1 = getStr(args2, "team1");
                String team2 = getStr(args2, "team2");
                if (team1 == null || team1.isBlank() || team2 == null || team2.isBlank()) {
                    return McpSchema.CallToolResult.builder()
                        .addTextContent("Error: 'team1' and 'team2' parameters are required")
                        .isError(true).build();
                }
                StatisticsService.HeadToHead h2h = statisticsService.getHeadToHead(team1, team2);
                int total = h2h.team1Wins() + h2h.team2Wins() + h2h.draws();
                String text = String.format(
                    "Head-to-Head: %s vs %s\n" +
                    "Total matches: %d\n" +
                    "%s wins: %d\n" +
                    "%s wins: %d\n" +
                    "Draws: %d",
                    team1, team2, total,
                    team1, h2h.team1Wins(),
                    team2, h2h.team2Wins(),
                    h2h.draws()
                );
                return McpSchema.CallToolResult.builder().addTextContent(text).build();
            })
            .toolCall(buildGetStandingsTool(), (exchange, request) -> {
                Map<String, Object> args2 = request.arguments();
                String seasonStr = getStr(args2, "season");
                String competition = getStr(args2, "competition");
                if (seasonStr == null || seasonStr.isBlank()) {
                    return McpSchema.CallToolResult.builder()
                        .addTextContent("Error: 'season' parameter is required")
                        .isError(true).build();
                }
                int season;
                try {
                    season = Integer.parseInt(seasonStr.trim());
                } catch (NumberFormatException e) {
                    return McpSchema.CallToolResult.builder()
                        .addTextContent("Error: 'season' must be a number")
                        .isError(true).build();
                }
                String comp = (competition != null && !competition.isBlank()) ? competition : "Brasileirao";
                List<StatisticsService.StandingEntry> standings = statisticsService.getStandings(season, comp);
                if (standings.isEmpty()) {
                    return McpSchema.CallToolResult.builder()
                        .addTextContent("No standings data found for " + comp + " " + season).build();
                }
                StringBuilder sb = new StringBuilder();
                sb.append(String.format("Standings: %s %d\n", comp, season));
                sb.append(String.format("%-3s %-25s %3s %3s %3s %3s %3s %3s %3s\n",
                    "Pos", "Team", "Pts", "P", "W", "D", "L", "GF", "GA"));
                sb.append("-".repeat(60)).append("\n");
                int pos = 1;
                for (StatisticsService.StandingEntry e : standings) {
                    sb.append(String.format("%-3d %-25s %3d %3d %3d %3d %3d %3d %3d\n",
                        pos++, truncate(e.team(), 25), e.points(),
                        e.wins() + e.draws() + e.losses(),
                        e.wins(), e.draws(), e.losses(), e.goalsFor(), e.goalsAgainst()));
                }
                return McpSchema.CallToolResult.builder().addTextContent(sb.toString()).build();
            })
            .toolCall(buildGetBiggestWinsTool(), (exchange, request) -> {
                Map<String, Object> args2 = request.arguments();
                String limitStr = getStr(args2, "limit");
                String competition = getStr(args2, "competition");
                int limit = 10;
                if (limitStr != null && !limitStr.isBlank()) {
                    try { limit = Integer.parseInt(limitStr.trim()); } catch (NumberFormatException ignored) {}
                }
                List<Match> matches;
                if (competition != null && !competition.isBlank()) {
                    String comp = competition;
                    matches = allMatches.stream()
                        .filter(m -> m.competition().equalsIgnoreCase(comp))
                        .collect(Collectors.toList());
                    StatisticsService filteredStats = new StatisticsService(matches);
                    matches = filteredStats.getBiggestWins(limit);
                } else {
                    matches = statisticsService.getBiggestWins(limit);
                }
                String text = formatBiggestWins(matches);
                return McpSchema.CallToolResult.builder().addTextContent(text).build();
            })
            .build();

        System.err.println("Brazilian Soccer MCP Server started. Waiting for connections...");

        // Keep the server running until stdin is closed
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.err.println("Shutting down...");
            server.close();
        }));

        // Block the main thread - the transport reads from stdin in background threads
        Thread.currentThread().join();
    }

    private static McpSchema.Tool buildFindMatchesTool() {
        Map<String, Object> properties = new LinkedHashMap<>();
        properties.put("team", Map.of("type", "string", "description", "Team name to search for"));
        properties.put("competition", Map.of("type", "string", "description", "Competition name (Brasileirao, Copa do Brasil, Libertadores, BR-Football, Historico)"));
        properties.put("season", Map.of("type", "string", "description", "Season year (e.g. 2023)"));
        properties.put("limit", Map.of("type", "string", "description", "Maximum number of results to return (default 20)"));
        McpSchema.JsonSchema schema = new McpSchema.JsonSchema("object", properties, List.of(), false, null, null);
        return McpSchema.Tool.builder()
            .name("find_matches")
            .description("Find soccer matches by team, competition, and/or season. Returns match results from Brasileirao, Copa do Brasil, Libertadores, and historical data.")
            .inputSchema(schema)
            .build();
    }

    private static McpSchema.Tool buildGetTeamStatsTool() {
        Map<String, Object> properties = new LinkedHashMap<>();
        properties.put("team", Map.of("type", "string", "description", "Team name (required)"));
        properties.put("competition", Map.of("type", "string", "description", "Filter by competition (optional)"));
        properties.put("season", Map.of("type", "string", "description", "Filter by season year (optional)"));
        McpSchema.JsonSchema schema = new McpSchema.JsonSchema("object", properties, List.of("team"), false, null, null);
        return McpSchema.Tool.builder()
            .name("get_team_stats")
            .description("Get win/loss/draw statistics for a team, optionally filtered by competition and season.")
            .inputSchema(schema)
            .build();
    }

    private static McpSchema.Tool buildFindPlayersTool() {
        Map<String, Object> properties = new LinkedHashMap<>();
        properties.put("name", Map.of("type", "string", "description", "Player name to search for"));
        properties.put("nationality", Map.of("type", "string", "description", "Filter by nationality (e.g. Brazil)"));
        properties.put("club", Map.of("type", "string", "description", "Filter by club name"));
        properties.put("top", Map.of("type", "string", "description", "Return top N players by overall rating"));
        properties.put("limit", Map.of("type", "string", "description", "Maximum number of results (default 20)"));
        McpSchema.JsonSchema schema = new McpSchema.JsonSchema("object", properties, List.of(), false, null, null);
        return McpSchema.Tool.builder()
            .name("find_players")
            .description("Find FIFA player data by name, nationality, or club. Can also return top-rated players globally or by club.")
            .inputSchema(schema)
            .build();
    }

    private static McpSchema.Tool buildGetHeadToHeadTool() {
        Map<String, Object> properties = new LinkedHashMap<>();
        properties.put("team1", Map.of("type", "string", "description", "First team name (required)"));
        properties.put("team2", Map.of("type", "string", "description", "Second team name (required)"));
        McpSchema.JsonSchema schema = new McpSchema.JsonSchema("object", properties, List.of("team1", "team2"), false, null, null);
        return McpSchema.Tool.builder()
            .name("get_head_to_head")
            .description("Get head-to-head record between two teams across all competitions.")
            .inputSchema(schema)
            .build();
    }

    private static McpSchema.Tool buildGetStandingsTool() {
        Map<String, Object> properties = new LinkedHashMap<>();
        properties.put("season", Map.of("type", "string", "description", "Season year (required, e.g. 2023)"));
        properties.put("competition", Map.of("type", "string", "description", "Competition name (default: Brasileirao)"));
        McpSchema.JsonSchema schema = new McpSchema.JsonSchema("object", properties, List.of("season"), false, null, null);
        return McpSchema.Tool.builder()
            .name("get_standings")
            .description("Get league standings table for a given season and competition.")
            .inputSchema(schema)
            .build();
    }

    private static McpSchema.Tool buildGetBiggestWinsTool() {
        Map<String, Object> properties = new LinkedHashMap<>();
        properties.put("limit", Map.of("type", "string", "description", "Number of results to return (default 10)"));
        properties.put("competition", Map.of("type", "string", "description", "Filter by competition (optional)"));
        McpSchema.JsonSchema schema = new McpSchema.JsonSchema("object", properties, List.of(), false, null, null);
        return McpSchema.Tool.builder()
            .name("get_biggest_wins")
            .description("Get the matches with the largest goal differences (biggest wins/most lopsided results).")
            .inputSchema(schema)
            .build();
    }

    private static String getStr(Map<String, Object> args, String key) {
        Object v = args == null ? null : args.get(key);
        return v == null ? null : v.toString();
    }

    private static String formatMatches(List<Match> matches, int total) {
        if (matches.isEmpty()) return "No matches found.";
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("Found %d matches (showing %d):\n\n", total, matches.size()));
        for (Match m : matches) {
            sb.append(String.format("[%s] %s %s: %s %d - %d %s\n",
                m.competition(),
                m.season() > 0 ? String.valueOf(m.season()) : "",
                m.round() != null && !m.round().isBlank() ? "R" + m.round() : "",
                m.homeTeam(), m.homeGoals(), m.awayGoals(), m.awayTeam()));
        }
        return sb.toString();
    }

    private static String formatPlayers(List<Player> players, int total) {
        if (players.isEmpty()) return "No players found.";
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("Found %d players (showing %d):\n\n", total, players.size()));
        for (Player p : players) {
            sb.append(String.format("%s (%s, %d) - %s | %s | Overall: %d | Potential: %d\n",
                p.name(), p.nationality(), p.age(), p.club(), p.position(), p.overall(), p.potential()));
        }
        return sb.toString();
    }

    private static String formatBiggestWins(List<Match> matches) {
        if (matches.isEmpty()) return "No matches found.";
        StringBuilder sb = new StringBuilder();
        sb.append("Biggest wins by goal difference:\n\n");
        for (Match m : matches) {
            int diff = Math.abs(m.homeGoals() - m.awayGoals());
            String winner = m.homeGoals() > m.awayGoals() ? m.homeTeam() : m.awayTeam();
            sb.append(String.format("[%s %s] %s %d - %d %s (diff: %d, winner: %s)\n",
                m.competition(), m.season() > 0 ? String.valueOf(m.season()) : "",
                m.homeTeam(), m.homeGoals(), m.awayGoals(), m.awayTeam(), diff, winner));
        }
        return sb.toString();
    }

    private static String truncate(String s, int maxLen) {
        if (s == null) return "";
        return s.length() <= maxLen ? s : s.substring(0, maxLen - 3) + "...";
    }
}
