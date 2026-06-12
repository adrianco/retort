package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.data.DataLoader;
import com.braziliansoccer.mcp.tools.MatchTools;
import com.braziliansoccer.mcp.tools.PlayerTools;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.logging.*;

/**
 * MCP Server implementing JSON-RPC 2.0 over stdio.
 * Provides tools for querying Brazilian soccer data.
 */
public class McpServer {

    private static final Logger log = Logger.getLogger(McpServer.class.getName());
    private final ObjectMapper mapper = new ObjectMapper();
    private DataLoader dataLoader;
    private MatchTools matchTools;
    private PlayerTools playerTools;

    public McpServer(String dataDir) {
        this.dataLoader = new DataLoader(dataDir);
    }

    public void run() throws IOException {
        // Load data on startup
        dataLoader.load();
        matchTools = new MatchTools(dataLoader);
        playerTools = new PlayerTools(dataLoader);

        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        PrintWriter writer = new PrintWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8), true);

        String line;
        while ((line = reader.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty()) continue;
            try {
                JsonNode request = mapper.readTree(line);
                String response = handleRequest(request);
                if (response != null) {
                    writer.println(response);
                }
            } catch (Exception e) {
                writer.println(errorResponse(null, -32700, "Parse error: " + e.getMessage()));
            }
        }
    }

    private String handleRequest(JsonNode req) throws Exception {
        JsonNode idNode = req.get("id");
        String method = req.has("method") ? req.get("method").asText() : "";
        JsonNode params = req.get("params");

        return switch (method) {
            case "initialize" -> handleInitialize(idNode, params);
            case "initialized" -> null; // notification, no response
            case "tools/list" -> handleToolsList(idNode);
            case "tools/call" -> handleToolCall(idNode, params);
            case "ping" -> successResponse(idNode, mapper.createObjectNode());
            default -> errorResponse(idNode, -32601, "Method not found: " + method);
        };
    }

    private String handleInitialize(JsonNode id, JsonNode params) throws Exception {
        ObjectNode result = mapper.createObjectNode();
        result.put("protocolVersion", "2024-11-05");
        ObjectNode serverInfo = mapper.createObjectNode();
        serverInfo.put("name", "brazilian-soccer-mcp");
        serverInfo.put("version", "1.0.0");
        result.set("serverInfo", serverInfo);
        ObjectNode capabilities = mapper.createObjectNode();
        capabilities.set("tools", mapper.createObjectNode());
        result.set("capabilities", capabilities);
        return successResponse(id, result);
    }

    private String handleToolsList(JsonNode id) throws Exception {
        ArrayNode tools = mapper.createArrayNode();

        tools.add(makeTool("search_matches",
            "Search for soccer matches by team, competition, season, and/or date range. " +
            "Supports all competitions: Brasileirao Serie A, Copa do Brasil, Copa Libertadores.",
            makeSchema(new String[][]{
                {"team", "string", "Team name to search (partial match supported)"},
                {"team2", "string", "Second team for specific matchup"},
                {"competition", "string", "Competition name (Brasileirao, Copa do Brasil, Libertadores)"},
                {"season", "integer", "Season year (e.g. 2023)"},
                {"start_date", "string", "Start date filter (YYYY-MM-DD)"},
                {"end_date", "string", "End date filter (YYYY-MM-DD)"},
                {"limit", "integer", "Max results to return (default 20)"}
            }, new String[]{})));

        tools.add(makeTool("head_to_head",
            "Get head-to-head statistics and match history between two teams.",
            makeSchema(new String[][]{
                {"team1", "string", "First team name"},
                {"team2", "string", "Second team name"},
                {"competition", "string", "Filter by competition (optional)"},
                {"season", "integer", "Filter by season year (optional)"}
            }, new String[]{"team1", "team2"})));

        tools.add(makeTool("team_stats",
            "Get comprehensive statistics for a team including wins, losses, goals, and performance by competition.",
            makeSchema(new String[][]{
                {"team", "string", "Team name"},
                {"competition", "string", "Filter by competition (optional)"},
                {"season", "integer", "Filter by season year (optional)"}
            }, new String[]{"team"})));

        tools.add(makeTool("standings",
            "Calculate league standings for a competition and season based on match results.",
            makeSchema(new String[][]{
                {"competition", "string", "Competition name (e.g. Brasileirao Serie A)"},
                {"season", "integer", "Season year (e.g. 2019)"}
            }, new String[]{"competition", "season"})));

        tools.add(makeTool("match_statistics",
            "Get aggregate statistics: biggest wins, goals averages, home/away analysis.",
            makeSchema(new String[][]{
                {"competition", "string", "Filter by competition (optional)"},
                {"season", "integer", "Filter by season year (optional)"},
                {"stat_type", "string", "Type of stats: biggest_wins, goals_avg, home_away (optional)"}
            }, new String[]{})));

        tools.add(makeTool("search_players",
            "Search FIFA player data by name, nationality, club, or position.",
            makeSchema(new String[][]{
                {"name", "string", "Player name (partial match)"},
                {"nationality", "string", "Player nationality (e.g. Brazil)"},
                {"club", "string", "Club name (partial match)"},
                {"position", "string", "Playing position (e.g. ST, GK, CAM)"},
                {"min_overall", "integer", "Minimum overall rating"},
                {"max_results", "integer", "Maximum results to return (default 20)"},
                {"sort_by", "string", "Sort by: overall (default) or name"}
            }, new String[]{})));

        tools.add(makeTool("player_profile",
            "Get detailed profile for a player including all FIFA attributes.",
            makeSchema(new String[][]{
                {"name", "string", "Player name to look up"}
            }, new String[]{"name"})));

        tools.add(makeTool("team_players",
            "Get all players in FIFA dataset for a specific club, grouped by position.",
            makeSchema(new String[][]{
                {"club", "string", "Club name"},
                {"min_overall", "integer", "Minimum overall rating filter (optional)"}
            }, new String[]{"club"})));

        tools.add(makeTool("top_players_by_nationality",
            "Get top-rated players from a specific nationality.",
            makeSchema(new String[][]{
                {"nationality", "string", "Nationality (e.g. Brazil, Argentina)"},
                {"limit", "integer", "Number of players to return (default 20)"}
            }, new String[]{"nationality"})));

        ObjectNode result = mapper.createObjectNode();
        result.set("tools", tools);
        return successResponse(id, result);
    }

    private String handleToolCall(JsonNode id, JsonNode params) throws Exception {
        if (params == null || !params.has("name")) {
            return errorResponse(id, -32602, "Missing tool name");
        }
        String toolName = params.get("name").asText();
        JsonNode args = params.has("arguments") ? params.get("arguments") : mapper.createObjectNode();

        try {
            String result = switch (toolName) {
                case "search_matches" -> matchTools.searchMatches(args);
                case "head_to_head" -> matchTools.headToHead(args);
                case "team_stats" -> matchTools.teamStats(args);
                case "standings" -> matchTools.standings(args);
                case "match_statistics" -> matchTools.matchStatistics(args);
                case "search_players" -> playerTools.searchPlayers(args);
                case "player_profile" -> playerTools.playerProfile(args);
                case "team_players" -> playerTools.teamPlayers(args);
                case "top_players_by_nationality" -> playerTools.topPlayersByNationality(args);
                default -> "Unknown tool: " + toolName;
            };

            ObjectNode response = mapper.createObjectNode();
            ArrayNode content = mapper.createArrayNode();
            ObjectNode textContent = mapper.createObjectNode();
            textContent.put("type", "text");
            textContent.put("text", result);
            content.add(textContent);
            response.set("content", content);
            response.put("isError", false);
            return successResponse(id, response);

        } catch (Exception e) {
            ObjectNode response = mapper.createObjectNode();
            ArrayNode content = mapper.createArrayNode();
            ObjectNode textContent = mapper.createObjectNode();
            textContent.put("type", "text");
            textContent.put("text", "Error executing tool " + toolName + ": " + e.getMessage());
            content.add(textContent);
            response.set("content", content);
            response.put("isError", true);
            return successResponse(id, response);
        }
    }

    private ObjectNode makeTool(String name, String description, ObjectNode inputSchema) {
        ObjectNode tool = mapper.createObjectNode();
        tool.put("name", name);
        tool.put("description", description);
        tool.set("inputSchema", inputSchema);
        return tool;
    }

    private ObjectNode makeSchema(String[][] properties, String[] required) {
        ObjectNode schema = mapper.createObjectNode();
        schema.put("type", "object");
        ObjectNode props = mapper.createObjectNode();
        for (String[] prop : properties) {
            ObjectNode p = mapper.createObjectNode();
            p.put("type", prop[1]);
            p.put("description", prop[2]);
            props.set(prop[0], p);
        }
        schema.set("properties", props);
        ArrayNode req = mapper.createArrayNode();
        for (String r : required) req.add(r);
        schema.set("required", req);
        return schema;
    }

    private String successResponse(JsonNode id, JsonNode result) throws Exception {
        ObjectNode response = mapper.createObjectNode();
        response.put("jsonrpc", "2.0");
        if (id != null) response.set("id", id);
        response.set("result", result);
        return mapper.writeValueAsString(response);
    }

    private String errorResponse(JsonNode id, int code, String message) {
        try {
            ObjectNode response = mapper.createObjectNode();
            response.put("jsonrpc", "2.0");
            if (id != null) response.set("id", id);
            ObjectNode error = mapper.createObjectNode();
            error.put("code", code);
            error.put("message", message);
            response.set("error", error);
            return mapper.writeValueAsString(response);
        } catch (Exception e) {
            return "{\"jsonrpc\":\"2.0\",\"error\":{\"code\":-32603,\"message\":\"Internal error\"}}";
        }
    }

    public static void main(String[] args) {
        // Configure logging to stderr so it doesn't interfere with MCP protocol on stdout
        LogManager.getLogManager().reset();
        Logger root = Logger.getLogger("");
        Handler handler = new StreamHandler(System.err, new SimpleFormatter());
        handler.setLevel(Level.WARNING);
        root.addHandler(handler);
        root.setLevel(Level.WARNING);

        String dataDir = args.length > 0 ? args[0] : "data/kaggle";
        try {
            new McpServer(dataDir).run();
        } catch (IOException e) {
            System.err.println("Fatal error: " + e.getMessage());
            System.exit(1);
        }
    }
}
