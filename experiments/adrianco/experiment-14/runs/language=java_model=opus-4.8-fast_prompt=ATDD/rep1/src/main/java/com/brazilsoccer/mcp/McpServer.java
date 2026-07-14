package com.brazilsoccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Function;

/**
 * A minimal Model Context Protocol server speaking JSON-RPC 2.0. It implements the
 * handshake (initialize), tool discovery (tools/list) and invocation (tools/call),
 * exposing the Brazilian-soccer query tools to any MCP host.
 */
public final class McpServer {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String PROTOCOL_VERSION = "2024-11-05";
    private static final String SERVER_NAME = "brazilian-soccer-mcp";
    private static final String SERVER_VERSION = "1.0.0";

    private final Map<String, Tool> tools = new LinkedHashMap<>();

    public McpServer(SoccerService service) {
        registerTools(service);
    }

    /** Handles one JSON-RPC message; returns the response JSON, or null for notifications. */
    public String handle(String requestJson) {
        JsonNode request;
        try {
            request = MAPPER.readTree(requestJson);
        } catch (Exception e) {
            return toJson(errorResponse(null, -32700, "Parse error: " + e.getMessage()));
        }

        JsonNode idNode = request.get("id");
        String method = request.path("method").asText(null);
        boolean isNotification = idNode == null || idNode.isNull();

        if (method == null) {
            return isNotification ? null : toJson(errorResponse(idNode, -32600, "Invalid Request"));
        }

        try {
            switch (method) {
                case "initialize":
                    return toJson(success(idNode, initializeResult()));
                case "tools/list":
                    return toJson(success(idNode, toolsListResult()));
                case "tools/call":
                    return toJson(success(idNode, callToolResult(request.path("params"))));
                case "ping":
                    return toJson(success(idNode, MAPPER.createObjectNode()));
                default:
                    if (method.startsWith("notifications/")) {
                        return null; // fire-and-forget
                    }
                    return isNotification ? null
                            : toJson(errorResponse(idNode, -32601, "Method not found: " + method));
            }
        } catch (ToolNotFoundException e) {
            return toJson(errorResponse(idNode, -32602, e.getMessage()));
        } catch (Exception e) {
            return toJson(errorResponse(idNode, -32603, "Internal error: " + e.getMessage()));
        }
    }

    private JsonNode initializeResult() {
        ObjectNode result = MAPPER.createObjectNode();
        result.put("protocolVersion", PROTOCOL_VERSION);
        ObjectNode capabilities = result.putObject("capabilities");
        capabilities.putObject("tools");
        ObjectNode serverInfo = result.putObject("serverInfo");
        serverInfo.put("name", SERVER_NAME);
        serverInfo.put("version", SERVER_VERSION);
        return result;
    }

    private JsonNode toolsListResult() {
        ObjectNode result = MAPPER.createObjectNode();
        ArrayNode arr = result.putArray("tools");
        for (Tool tool : tools.values()) {
            ObjectNode node = arr.addObject();
            node.put("name", tool.name);
            node.put("description", tool.description);
            node.set("inputSchema", tool.inputSchema);
        }
        return result;
    }

    private JsonNode callToolResult(JsonNode params) {
        String name = params.path("name").asText(null);
        Tool tool = tools.get(name);
        if (tool == null) {
            throw new ToolNotFoundException("Unknown tool: " + name);
        }
        JsonNode arguments = params.get("arguments");
        JsonNode payload = tool.handler.apply(arguments == null ? MAPPER.createObjectNode() : arguments);

        ObjectNode result = MAPPER.createObjectNode();
        ArrayNode content = result.putArray("content");
        ObjectNode block = content.addObject();
        block.put("type", "text");
        block.put("text", toJson(payload));
        result.put("isError", false);
        return result;
    }

    // ---- tool registry -------------------------------------------------------

    private void registerTools(SoccerService service) {
        register("find_matches",
                "Find matches by team, opponent, competition, season and venue (home/away/any). "
                        + "Use 'team' with 'opponent' to list head-to-head fixtures.",
                schema(b -> {
                    b.prop("team", "string", "Team name, e.g. 'Flamengo' or 'Palmeiras-SP'");
                    b.prop("opponent", "string", "Restrict to matches against this opponent");
                    b.prop("competition", "string", "serie_a, copa_do_brasil, libertadores, serie_b, serie_c");
                    b.prop("season", "integer", "Season year, e.g. 2019");
                    b.prop("venue", "string", "home, away or any (applies to 'team')");
                    b.prop("limit", "integer", "Maximum matches to return (default 50)");
                }),
                service::toolFindMatches);

        register("head_to_head",
                "Head-to-head record between two teams: wins, draws and goals across all competitions.",
                schema(b -> {
                    b.prop("teamA", "string", "First team");
                    b.prop("teamB", "string", "Second team");
                    b.required("teamA", "teamB");
                }),
                service::toolHeadToHead);

        register("team_stats",
                "A team's record (matches, wins, draws, losses, goals, win rate), optionally filtered "
                        + "by season, competition and venue.",
                schema(b -> {
                    b.prop("team", "string", "Team name");
                    b.prop("season", "integer", "Season year");
                    b.prop("competition", "string", "Competition key");
                    b.prop("venue", "string", "home, away or all");
                    b.required("team");
                }),
                service::toolTeamStats);

        register("search_players",
                "Search FIFA players by name, nationality, club, position and minimum rating; "
                        + "results are ranked by overall rating.",
                schema(b -> {
                    b.prop("name", "string", "Full or partial player name");
                    b.prop("nationality", "string", "Nationality, e.g. 'Brazil'");
                    b.prop("club", "string", "Club name (partial match)");
                    b.prop("position", "string", "Position code, e.g. GK, ST, LW");
                    b.prop("minOverall", "integer", "Minimum FIFA overall rating");
                    b.prop("limit", "integer", "Maximum players to return (default 25)");
                }),
                service::toolSearchPlayers);

        register("competition_standings",
                "Final league standings for a competition and season, calculated from match results.",
                schema(b -> {
                    b.prop("competition", "string", "Competition key, e.g. serie_a");
                    b.prop("season", "integer", "Season year, e.g. 2019");
                    b.required("competition", "season");
                }),
                service::toolStandings);

        register("league_statistics",
                "Aggregate statistics: matches, goals per match, home/away win rates and biggest wins, "
                        + "optionally scoped to a competition and season.",
                schema(b -> {
                    b.prop("competition", "string", "Competition key");
                    b.prop("season", "integer", "Season year");
                }),
                service::toolLeagueStatistics);
    }

    private void register(String name, String description, ObjectNode schema,
                          Function<JsonNode, JsonNode> handler) {
        tools.put(name, new Tool(name, description, schema, handler));
    }

    private ObjectNode schema(java.util.function.Consumer<SchemaBuilder> spec) {
        SchemaBuilder builder = new SchemaBuilder();
        spec.accept(builder);
        return builder.build();
    }

    // ---- JSON-RPC envelope helpers ------------------------------------------

    private ObjectNode success(JsonNode id, JsonNode result) {
        ObjectNode response = MAPPER.createObjectNode();
        response.put("jsonrpc", "2.0");
        response.set("id", id == null ? null : id);
        response.set("result", result);
        return response;
    }

    private ObjectNode errorResponse(JsonNode id, int code, String message) {
        ObjectNode response = MAPPER.createObjectNode();
        response.put("jsonrpc", "2.0");
        response.set("id", id == null ? null : id);
        ObjectNode error = response.putObject("error");
        error.put("code", code);
        error.put("message", message);
        return response;
    }

    private static String toJson(JsonNode node) {
        try {
            return MAPPER.writeValueAsString(node);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    private static final class Tool {
        final String name;
        final String description;
        final ObjectNode inputSchema;
        final Function<JsonNode, JsonNode> handler;

        Tool(String name, String description, ObjectNode inputSchema, Function<JsonNode, JsonNode> handler) {
            this.name = name;
            this.description = description;
            this.inputSchema = inputSchema;
            this.handler = handler;
        }
    }

    private static final class ToolNotFoundException extends RuntimeException {
        ToolNotFoundException(String message) {
            super(message);
        }
    }

    /** Small helper for building JSON Schema objects for tool inputs. */
    private static final class SchemaBuilder {
        private final ObjectNode schema = MAPPER.createObjectNode();
        private final ObjectNode properties;
        private final ArrayNode required;

        SchemaBuilder() {
            schema.put("type", "object");
            properties = schema.putObject("properties");
            required = schema.putArray("required");
        }

        void prop(String name, String type, String description) {
            ObjectNode p = properties.putObject(name);
            p.put("type", type);
            p.put("description", description);
        }

        void required(String... names) {
            for (String name : names) {
                required.add(name);
            }
        }

        ObjectNode build() {
            if (required.isEmpty()) {
                schema.remove("required");
            }
            return schema;
        }
    }
}
