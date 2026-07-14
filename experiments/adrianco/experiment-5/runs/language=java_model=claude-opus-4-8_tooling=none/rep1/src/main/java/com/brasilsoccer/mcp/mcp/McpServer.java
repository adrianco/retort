/*
 * ============================================================================
 * McpServer - Model Context Protocol (JSON-RPC 2.0) server over stdio
 * ============================================================================
 * Context:
 *   Implements the MCP wire protocol directly (no SDK dependency) using
 *   newline-delimited JSON-RPC 2.0 messages on stdin/stdout, as used by the
 *   MCP stdio transport. It exposes the Brazilian soccer KnowledgeBase as a set
 *   of callable tools.
 *
 *   Supported protocol methods:
 *     - initialize                 handshake + capability advertisement
 *     - notifications/initialized  (notification, no reply)
 *     - tools/list                 enumerate the available tools + JSON schemas
 *     - tools/call                 invoke a tool and return text content
 *     - ping                       liveness check
 *
 *   Exposed tools (cover all 5 specification query categories):
 *     search_matches, head_to_head, team_record, search_players,
 *     standings, league_statistics, biggest_wins, data_summary
 *
 *   Logging goes to stderr only; stdout is reserved for protocol frames.
 *   The dispatch layer (handleRequest / callTool) is public so tests can drive
 *   it without spawning a process.
 * ============================================================================
 */
package com.brasilsoccer.mcp.mcp;

import com.brasilsoccer.mcp.data.KnowledgeBase;
import com.brasilsoccer.mcp.model.Match;
import com.brasilsoccer.mcp.query.MatchQuery;
import com.brasilsoccer.mcp.query.ResponseFormatter;
import com.brasilsoccer.mcp.query.Results;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Writer;
import java.time.LocalDate;
import java.util.List;

public final class McpServer {

    public static final String PROTOCOL_VERSION = "2024-11-05";
    public static final String SERVER_NAME = "brazilian-soccer-mcp";
    public static final String SERVER_VERSION = "1.0.0";

    private final KnowledgeBase kb;
    private final ObjectMapper mapper = new ObjectMapper();

    public McpServer(KnowledgeBase kb) {
        this.kb = kb;
    }

    // ----------------------------------------------------------------- stdio loop

    public void serve(BufferedReader in, Writer out) throws IOException {
        String line;
        while ((line = in.readLine()) != null) {
            if (line.isBlank()) {
                continue;
            }
            JsonNode request;
            try {
                request = mapper.readTree(line);
            } catch (Exception e) {
                writeMessage(out, parseError());
                continue;
            }
            ObjectNode response = handleRequest(request);
            if (response != null) {
                writeMessage(out, response);
            }
        }
    }

    private void writeMessage(Writer out, ObjectNode message) throws IOException {
        out.write(mapper.writeValueAsString(message));
        out.write("\n");
        out.flush();
    }

    // ----------------------------------------------------------------- dispatch

    /**
     * Handle a single JSON-RPC request node. Returns the response node, or null
     * for notifications (which must not be answered).
     */
    public ObjectNode handleRequest(JsonNode request) {
        String method = request.path("method").asText("");
        JsonNode idNode = request.get("id");
        boolean isNotification = idNode == null || idNode.isNull();

        // Notifications never get a reply.
        if (isNotification) {
            return null;
        }

        try {
            JsonNode params = request.path("params");
            ObjectNode result = switch (method) {
                case "initialize" -> initialize();
                case "tools/list" -> toolsList();
                case "tools/call" -> toolsCall(params);
                case "ping" -> mapper.createObjectNode();
                default -> null;
            };
            if (result == null) {
                return error(idNode, -32601, "Method not found: " + method);
            }
            return success(idNode, result);
        } catch (IllegalArgumentException e) {
            return error(idNode, -32602, e.getMessage());
        } catch (Exception e) {
            return error(idNode, -32603, "Internal error: " + e.getMessage());
        }
    }

    private ObjectNode initialize() {
        ObjectNode result = mapper.createObjectNode();
        result.put("protocolVersion", PROTOCOL_VERSION);
        ObjectNode caps = result.putObject("capabilities");
        caps.putObject("tools");
        ObjectNode info = result.putObject("serverInfo");
        info.put("name", SERVER_NAME);
        info.put("version", SERVER_VERSION);
        result.put("instructions",
                "Query Brazilian soccer matches, teams, players, competitions and statistics. "
                        + "Use search_matches, head_to_head, team_record, search_players, standings, "
                        + "league_statistics, biggest_wins and data_summary.");
        return result;
    }

    // ----------------------------------------------------------------- tools/list

    private ObjectNode toolsList() {
        ObjectNode result = mapper.createObjectNode();
        ArrayNode tools = result.putArray("tools");
        tools.add(ToolSchemas.searchMatches(mapper));
        tools.add(ToolSchemas.headToHead(mapper));
        tools.add(ToolSchemas.teamRecord(mapper));
        tools.add(ToolSchemas.searchPlayers(mapper));
        tools.add(ToolSchemas.standings(mapper));
        tools.add(ToolSchemas.leagueStatistics(mapper));
        tools.add(ToolSchemas.biggestWins(mapper));
        tools.add(ToolSchemas.dataSummary(mapper));
        return result;
    }

    // ----------------------------------------------------------------- tools/call

    private ObjectNode toolsCall(JsonNode params) {
        String name = params.path("name").asText("");
        JsonNode args = params.path("arguments");
        if (args.isMissingNode() || args.isNull()) {
            args = mapper.createObjectNode();
        }
        try {
            String text = callTool(name, args);
            return toolText(text, false);
        } catch (IllegalArgumentException e) {
            // Surface user/argument problems as tool errors, not protocol errors.
            return toolText("Error: " + e.getMessage(), true);
        }
    }

    /**
     * Execute a named tool with the given arguments and return rendered text.
     * Public for direct testing.
     */
    public String callTool(String name, JsonNode a) {
        return switch (name) {
            case "search_matches" -> doSearchMatches(a);
            case "head_to_head" -> doHeadToHead(a);
            case "team_record" -> doTeamRecord(a);
            case "search_players" -> doSearchPlayers(a);
            case "standings" -> doStandings(a);
            case "league_statistics" -> doLeagueStatistics(a);
            case "biggest_wins" -> doBiggestWins(a);
            case "data_summary" -> ResponseFormatter.summary(kb.summary());
            default -> throw new IllegalArgumentException("Unknown tool: " + name);
        };
    }

    // ----------------------------------------------------------------- tool impls

    private String doSearchMatches(JsonNode a) {
        MatchQuery q = new MatchQuery()
                .team(text(a, "team"))
                .team2(text(a, "opponent"))
                .competition(text(a, "competition"))
                .season(integer(a, "season"))
                .startDate(date(a, "start_date"))
                .endDate(date(a, "end_date"))
                .venue(venue(text(a, "venue")))
                .limit(intOr(a, "limit", 50));
        if (q.team == null && q.competition == null && q.season == null
                && q.startDate == null && q.endDate == null) {
            throw new IllegalArgumentException(
                    "Provide at least one of: team, competition, season, start_date, end_date.");
        }
        return ResponseFormatter.matchSearch(kb.searchMatches(q));
    }

    private String doHeadToHead(JsonNode a) {
        String t1 = required(a, "team1");
        String t2 = required(a, "team2");
        Results.HeadToHead h = kb.headToHead(t1, t2);
        if (h.total() == 0) {
            return "No matches found between " + t1 + " and " + t2 + " in the dataset.";
        }
        return ResponseFormatter.headToHead(h);
    }

    private String doTeamRecord(JsonNode a) {
        String team = required(a, "team");
        Results.TeamRecord r = kb.teamRecord(team, integer(a, "season"),
                text(a, "competition"), venue(text(a, "venue")));
        if (r.played() == 0) {
            return "No matches found for " + team + " with the given filters.";
        }
        return ResponseFormatter.teamRecord(r);
    }

    private String doSearchPlayers(JsonNode a) {
        if (text(a, "name") == null && text(a, "nationality") == null
                && text(a, "club") == null && text(a, "position") == null
                && integer(a, "min_overall") == null) {
            throw new IllegalArgumentException(
                    "Provide at least one of: name, nationality, club, position, min_overall.");
        }
        Results.PlayerSearch r = kb.searchPlayers(
                text(a, "name"), text(a, "nationality"), text(a, "club"),
                text(a, "position"), integer(a, "min_overall"),
                text(a, "sort_by"), intOr(a, "limit", 20));
        return ResponseFormatter.players(r, null);
    }

    private String doStandings(JsonNode a) {
        String competition = text(a, "competition");
        if (competition == null) {
            competition = "Brasileirao";
        }
        Integer season = integer(a, "season");
        if (season == null) {
            throw new IllegalArgumentException("'season' is required for standings.");
        }
        return ResponseFormatter.standings(kb.standings(competition, season));
    }

    private String doLeagueStatistics(JsonNode a) {
        Results.LeagueStats s = kb.leagueStats(text(a, "competition"), integer(a, "season"));
        return ResponseFormatter.leagueStats(s);
    }

    private String doBiggestWins(JsonNode a) {
        String competition = text(a, "competition");
        Integer season = integer(a, "season");
        List<Match> wins = kb.biggestWins(competition, season, intOr(a, "limit", 10));
        String label = (competition == null ? "all competitions" : competition)
                + (season == null ? "" : " " + season);
        return ResponseFormatter.biggestWins(wins, label);
    }

    // ----------------------------------------------------------------- arg helpers

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
            throw new IllegalArgumentException("'" + field + "' is required.");
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
        String s = n.asText().trim();
        if (s.isEmpty()) {
            return null;
        }
        try {
            return Integer.parseInt(s);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("'" + field + "' must be an integer.");
        }
    }

    private static int intOr(JsonNode a, String field, int fallback) {
        Integer v = integer(a, field);
        return v == null ? fallback : v;
    }

    private static LocalDate date(JsonNode a, String field) {
        String s = text(a, field);
        if (s == null) {
            return null;
        }
        try {
            return LocalDate.parse(s);
        } catch (Exception e) {
            throw new IllegalArgumentException("'" + field + "' must be an ISO date (YYYY-MM-DD).");
        }
    }

    private static MatchQuery.Venue venue(String s) {
        if (s == null) {
            return MatchQuery.Venue.ANY;
        }
        return switch (s.toLowerCase()) {
            case "home" -> MatchQuery.Venue.HOME;
            case "away" -> MatchQuery.Venue.AWAY;
            default -> MatchQuery.Venue.ANY;
        };
    }

    // ----------------------------------------------------------------- JSON-RPC plumbing

    private ObjectNode success(JsonNode id, ObjectNode result) {
        ObjectNode resp = baseResponse(id);
        resp.set("result", result);
        return resp;
    }

    private ObjectNode error(JsonNode id, int code, String message) {
        ObjectNode resp = baseResponse(id);
        ObjectNode err = resp.putObject("error");
        err.put("code", code);
        err.put("message", message);
        return resp;
    }

    private ObjectNode parseError() {
        ObjectNode resp = mapper.createObjectNode();
        resp.put("jsonrpc", "2.0");
        resp.putNull("id");
        ObjectNode err = resp.putObject("error");
        err.put("code", -32700);
        err.put("message", "Parse error");
        return resp;
    }

    private ObjectNode baseResponse(JsonNode id) {
        ObjectNode resp = mapper.createObjectNode();
        resp.put("jsonrpc", "2.0");
        if (id == null || id.isNull()) {
            resp.putNull("id");
        } else {
            resp.set("id", id);
        }
        return resp;
    }

    private ObjectNode toolText(String text, boolean isError) {
        ObjectNode result = mapper.createObjectNode();
        ArrayNode content = result.putArray("content");
        ObjectNode item = content.addObject();
        item.put("type", "text");
        item.put("text", text);
        result.put("isError", isError);
        return result;
    }
}
