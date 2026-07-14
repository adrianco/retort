package com.example.soccer;

import com.example.soccer.data.DataStore;
import com.example.soccer.data.Match;
import com.example.soccer.data.Player;
import com.example.soccer.format.Formatter;
import com.example.soccer.query.QueryService;
import com.example.soccer.query.TeamRecord;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

public final class McpServer {

    public static final String PROTOCOL_VERSION = "2024-11-05";
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final QueryService queries;

    public McpServer(QueryService queries) {
        this.queries = queries;
    }

    public static void main(String[] args) throws IOException {
        Path dataDir = Paths.get(System.getProperty("soccer.data.dir",
                System.getenv().getOrDefault("SOCCER_DATA_DIR", "data/kaggle")));
        DataStore store = new DataStore(dataDir);
        long t0 = System.currentTimeMillis();
        store.loadAll();
        long t1 = System.currentTimeMillis();
        System.err.println("[mcp] loaded " + store.matches().size() + " matches and "
                + store.players().size() + " players in " + (t1 - t0) + " ms");
        QueryService qs = new QueryService(store);
        new McpServer(qs).run(new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8)),
                new PrintWriter(new java.io.OutputStreamWriter(System.out, StandardCharsets.UTF_8), true));
    }

    public void run(BufferedReader in, PrintWriter out) throws IOException {
        String line;
        while ((line = in.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty()) continue;
            JsonNode req;
            try {
                req = MAPPER.readTree(line);
            } catch (Exception e) {
                writeError(out, null, -32700, "Parse error: " + e.getMessage());
                continue;
            }
            handleRequest(req, out);
        }
    }

    public void handleRequest(JsonNode req, PrintWriter out) {
        JsonNode idNode = req.get("id");
        String method = req.hasNonNull("method") ? req.get("method").asText() : null;
        JsonNode params = req.get("params");
        if (method == null) {
            writeError(out, idNode, -32600, "Missing method");
            return;
        }
        try {
            switch (method) {
                case "initialize" -> writeResult(out, idNode, buildInitializeResult());
                case "notifications/initialized", "notifications/cancelled" -> {
                    // no response for notifications
                }
                case "ping" -> writeResult(out, idNode, MAPPER.createObjectNode());
                case "tools/list" -> writeResult(out, idNode, buildToolsList());
                case "tools/call" -> writeResult(out, idNode, callTool(params));
                default -> writeError(out, idNode, -32601, "Method not found: " + method);
            }
        } catch (IllegalArgumentException e) {
            writeError(out, idNode, -32602, e.getMessage());
        } catch (Exception e) {
            writeError(out, idNode, -32603, "Internal error: " + e.getMessage());
        }
    }

    private ObjectNode buildInitializeResult() {
        ObjectNode result = MAPPER.createObjectNode();
        result.put("protocolVersion", PROTOCOL_VERSION);
        ObjectNode caps = result.putObject("capabilities");
        caps.putObject("tools");
        ObjectNode info = result.putObject("serverInfo");
        info.put("name", "brazilian-soccer-mcp");
        info.put("version", "1.0.0");
        return result;
    }

    public ObjectNode buildToolsList() {
        ObjectNode result = MAPPER.createObjectNode();
        ArrayNode tools = result.putArray("tools");
        tools.add(tool("search_matches",
                "Search matches by team(s), date range, competition, and/or season.",
                Map.of(
                        "team_a", "string - team name (matches in any competition/venue)",
                        "team_b", "string - second team for head-to-head match listing",
                        "season", "integer - season year filter",
                        "competition", "string - competition substring (e.g. 'Brasileirão', 'Libertadores')",
                        "date_from", "string - ISO date (yyyy-MM-dd) inclusive lower bound",
                        "date_to", "string - ISO date (yyyy-MM-dd) inclusive upper bound",
                        "venue", "string - 'home' / 'away' / 'either' (default either) for team_a only",
                        "limit", "integer - max matches to render (default 50)"
                )));
        tools.add(tool("team_stats",
                "Return wins/draws/losses/goals for a team optionally filtered by season, competition, venue.",
                Map.of(
                        "team", "string - team name (required)",
                        "season", "integer - season year",
                        "competition", "string - competition substring",
                        "venue", "string - 'home' / 'away' / 'either' (default either)"
                )));
        tools.add(tool("head_to_head",
                "Return head-to-head stats between two teams.",
                Map.of(
                        "team_a", "string - first team (required)",
                        "team_b", "string - second team (required)",
                        "season", "integer - season year",
                        "competition", "string - competition substring",
                        "limit", "integer - max matches to render (default 20)"
                )));
        tools.add(tool("standings",
                "Compute final standings from match results (default: Brasileirão).",
                Map.of(
                        "season", "integer - season year (required)",
                        "competition", "string - competition substring (default Brasileirão)",
                        "limit", "integer - max rows (default 30)"
                )));
        tools.add(tool("biggest_wins",
                "Return the matches with the largest goal margin.",
                Map.of(
                        "competition", "string - competition substring filter",
                        "min_margin", "integer - minimum goal difference",
                        "limit", "integer - max results (default 10)"
                )));
        tools.add(tool("match_stats",
                "Aggregate stats: number of matches, avg goals/match, home/away win rates.",
                Map.of(
                        "season", "integer - season year",
                        "competition", "string - competition substring"
                )));
        tools.add(tool("search_players",
                "Search FIFA player database by name, nationality, club, position.",
                Map.of(
                        "name", "string - substring of player name",
                        "nationality", "string - nationality (e.g. 'Brazil')",
                        "club", "string - substring of club name",
                        "position", "string - position code (e.g. 'GK', 'ST')",
                        "min_overall", "integer - minimum FIFA overall rating",
                        "limit", "integer - max players (default 25)"
                )));
        tools.add(tool("dataset_info",
                "Return counts of matches and players loaded per competition.",
                Map.of()));
        return result;
    }

    private ObjectNode tool(String name, String description, Map<String, String> properties) {
        ObjectNode tool = MAPPER.createObjectNode();
        tool.put("name", name);
        tool.put("description", description);
        ObjectNode schema = tool.putObject("inputSchema");
        schema.put("type", "object");
        ObjectNode props = schema.putObject("properties");
        for (Map.Entry<String, String> e : properties.entrySet()) {
            ObjectNode prop = props.putObject(e.getKey());
            prop.put("description", e.getValue());
            prop.put("type", inferType(e.getValue()));
        }
        schema.putArray("required");
        return tool;
    }

    private static String inferType(String description) {
        if (description.startsWith("integer")) return "integer";
        if (description.startsWith("number")) return "number";
        if (description.startsWith("boolean")) return "boolean";
        return "string";
    }

    public ObjectNode callTool(JsonNode params) {
        if (params == null || !params.hasNonNull("name")) {
            throw new IllegalArgumentException("Missing tool name");
        }
        String name = params.get("name").asText();
        JsonNode args = params.has("arguments") ? params.get("arguments") : MAPPER.createObjectNode();
        String text = switch (name) {
            case "search_matches" -> doSearchMatches(args);
            case "team_stats" -> doTeamStats(args);
            case "head_to_head" -> doHeadToHead(args);
            case "standings" -> doStandings(args);
            case "biggest_wins" -> doBiggestWins(args);
            case "match_stats" -> doMatchStats(args);
            case "search_players" -> doSearchPlayers(args);
            case "dataset_info" -> doDatasetInfo();
            default -> throw new IllegalArgumentException("Unknown tool: " + name);
        };
        return contentResult(text);
    }

    private String doSearchMatches(JsonNode args) {
        String teamA = optString(args, "team_a");
        String teamB = optString(args, "team_b");
        Integer season = optInt(args, "season");
        String competition = optString(args, "competition");
        LocalDate from = optDate(args, "date_from");
        LocalDate to = optDate(args, "date_to");
        String venue = optString(args, "venue");
        int limit = optIntOr(args, "limit", 50);
        List<Match> matches = queries.searchMatches(teamA, teamB, season, competition, from, to, venue);
        return Formatter.formatMatches(matches, limit);
    }

    private String doTeamStats(JsonNode args) {
        String team = requireString(args, "team");
        Integer season = optInt(args, "season");
        String competition = optString(args, "competition");
        String venue = optString(args, "venue");
        TeamRecord rec = queries.teamRecord(team, season, competition, venue);
        StringBuilder label = new StringBuilder(team);
        if (venue != null) label.append(' ').append(venue);
        label.append(" record");
        if (season != null) label.append(" in ").append(season);
        if (competition != null) label.append(" (").append(competition).append(')');
        return Formatter.formatTeamRecord(label.toString(), rec);
    }

    private String doHeadToHead(JsonNode args) {
        String a = requireString(args, "team_a");
        String b = requireString(args, "team_b");
        Integer season = optInt(args, "season");
        String competition = optString(args, "competition");
        int limit = optIntOr(args, "limit", 20);
        QueryService.HeadToHead h = queries.headToHead(a, b, season, competition);
        return Formatter.formatHeadToHead(h, limit);
    }

    private String doStandings(JsonNode args) {
        Integer season = optInt(args, "season");
        if (season == null) throw new IllegalArgumentException("standings requires 'season'");
        String competition = optString(args, "competition");
        int limit = optIntOr(args, "limit", 30);
        List<QueryService.Standing> rows = queries.standings(season, competition);
        return Formatter.formatStandings(rows, limit);
    }

    private String doBiggestWins(JsonNode args) {
        String competition = optString(args, "competition");
        Integer minMargin = optInt(args, "min_margin");
        int limit = optIntOr(args, "limit", 10);
        List<Match> matches = queries.biggestWins(competition, minMargin, limit);
        return Formatter.formatMatches(matches, limit);
    }

    private String doMatchStats(JsonNode args) {
        Integer season = optInt(args, "season");
        String competition = optString(args, "competition");
        Map<String, Object> stats = queries.matchStats(season, competition);
        return Formatter.formatStats(stats);
    }

    private String doSearchPlayers(JsonNode args) {
        String name = optString(args, "name");
        String nationality = optString(args, "nationality");
        String club = optString(args, "club");
        String position = optString(args, "position");
        Integer minOverall = optInt(args, "min_overall");
        int limit = optIntOr(args, "limit", 25);
        List<Player> players = queries.searchPlayers(name, nationality, club, position, minOverall, limit);
        return Formatter.formatPlayers(players, limit);
    }

    private String doDatasetInfo() {
        StringBuilder sb = new StringBuilder();
        sb.append("Total matches: ").append(queries.store().matches().size()).append('\n');
        sb.append("Total players: ").append(queries.store().players().size()).append('\n');
        sb.append("By competition:\n");
        for (Map.Entry<String, Long> e : queries.competitionCounts().entrySet()) {
            sb.append("- ").append(e.getKey()).append(": ").append(e.getValue()).append('\n');
        }
        return sb.toString();
    }

    private ObjectNode contentResult(String text) {
        ObjectNode result = MAPPER.createObjectNode();
        ArrayNode content = result.putArray("content");
        ObjectNode item = content.addObject();
        item.put("type", "text");
        item.put("text", text);
        result.put("isError", false);
        return result;
    }

    private static String requireString(JsonNode args, String key) {
        if (args == null || !args.hasNonNull(key)) {
            throw new IllegalArgumentException("Missing required argument: " + key);
        }
        String v = args.get(key).asText().trim();
        if (v.isEmpty()) throw new IllegalArgumentException("Missing required argument: " + key);
        return v;
    }

    private static String optString(JsonNode args, String key) {
        if (args == null || !args.hasNonNull(key)) return null;
        String v = args.get(key).asText().trim();
        return v.isEmpty() ? null : v;
    }

    private static Integer optInt(JsonNode args, String key) {
        if (args == null || !args.hasNonNull(key)) return null;
        JsonNode n = args.get(key);
        if (n.isNumber()) return n.asInt();
        try {
            return Integer.parseInt(n.asText().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static int optIntOr(JsonNode args, String key, int fallback) {
        Integer v = optInt(args, key);
        return v == null ? fallback : v;
    }

    private static LocalDate optDate(JsonNode args, String key) {
        String s = optString(args, key);
        if (s == null) return null;
        try {
            return LocalDate.parse(s);
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid date for " + key + ": " + s);
        }
    }

    private void writeResult(PrintWriter out, JsonNode id, Object result) {
        ObjectNode msg = MAPPER.createObjectNode();
        msg.put("jsonrpc", "2.0");
        if (id != null) msg.set("id", id);
        msg.set("result", MAPPER.valueToTree(result));
        out.println(msg);
        out.flush();
    }

    private void writeError(PrintWriter out, JsonNode id, int code, String message) {
        ObjectNode msg = MAPPER.createObjectNode();
        msg.put("jsonrpc", "2.0");
        if (id != null) msg.set("id", id);
        ObjectNode err = msg.putObject("error");
        err.put("code", code);
        err.put("message", message);
        out.println(msg);
        out.flush();
    }
}
