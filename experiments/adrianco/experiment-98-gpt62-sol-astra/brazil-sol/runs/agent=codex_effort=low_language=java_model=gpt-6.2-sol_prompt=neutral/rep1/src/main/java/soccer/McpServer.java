package soccer;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.*;
import java.util.function.Function;

public final class McpServer {
    private static final ObjectMapper JSON = new ObjectMapper().enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    private static final Set<String> PROTOCOLS = Set.of("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05");
    private final Map<String, Tool> tools = new LinkedHashMap<>();
    private String version = "2025-06-18";

    private record Tool(String name, String description, Map<String, Object> inputSchema,
                        Function<JsonNode, SoccerTools.Answer> execute) {
        Map<String, Object> definition() {
            return Map.of("name", name, "description", description, "inputSchema", inputSchema,
                    "annotations", Map.of("readOnlyHint", true, "openWorldHint", false));
        }
    }

    McpServer(SoccerData data) {
        SoccerTools queries = new SoccerTools(data);
        Map<String, Map<String, Object>> filters = new LinkedHashMap<>();
        filters.put("team", string("Club involved in the fixture"));
        filters.put("opponent", string("Second club in a fixture with team"));
        filters.put("venue", choices("Venue relative to team, or to each ranked team", "home", "away", "either"));
        filters.put("home", string("Home club"));
        filters.put("away", string("Away club"));
        filters.put("competition", string("Brasileirão (Série A), Série B, Série C, Copa do Brasil, or Libertadores"));
        filters.put("season", number("Competition season year", 1, 9999));
        filters.put("fromSeason", number("First season to include", 1, 9999));
        filters.put("toSeason", number("Last season to include", 1, 9999));
        filters.put("from", string("First fixture date, inclusive, in YYYY-MM-DD or DD/MM/YYYY"));
        filters.put("to", string("Last fixture date, inclusive, in YYYY-MM-DD or DD/MM/YYYY"));
        filters.put("stage", string("Exact round or stage, such as Round 22, group stage, semifinals, or final"));
        filters.put("derby", Map.of("type", "boolean", "description", "Restrict to known Brazilian rivalries"));
        filters.put("playedOnly", Map.of("type", "boolean", "description", "Require a recorded score"));
        filters.put("source", choices("Read one CSV directly. Omit for merged fixtures.", data.bySource.keySet().toArray(String[]::new)));
        Map<String, Map<String, Object>> pagination = Map.of(
                "limit", number("Page size, default 20", 1, 200),
                "offset", number("Zero-based offset, default 0. Use nextOffset for the next page.", 0, Integer.MAX_VALUE));
        Map<String, Map<String, Object>> playerFilters = Map.of(
                "name", string("Player name or substring, using the FIFA snapshot spelling"),
                "club", string("Club in the FIFA snapshot"),
                "nationality", string("FIFA nationality, such as Brazil"),
                "position", string("FIFA position code or forward, midfielder, defender, goalkeeper"));

        register("search_matches", "Find historical results and fixtures, most recent first. Use limit 1 for the latest fixture, "
                + "stage final for finals, or competition plus season for a cup bracket organized by each fixture's stage.",
                queries::searchMatches, List.of(), filters, pagination);
        register("head_to_head", "Compare two clubs' win, draw, loss and goal totals and list their fixtures.",
                queries::headToHead, List.of("team", "opponent"), filters, pagination);
        register("team_record", "Get W/D/L, goals and win rates for a club, split by venue and competition or season.",
                queries::teamRecord, List.of("team"), filters, Map.of("groupBy", choices("Grouping", "season", "competition")));
        register("search_players", "Find players in the FIFA snapshot, highest overall rating first. "
                + "Returns ratings, positions, club, nationality and recorded player attributes.",
                queries::players, List.of(), playerFilters, pagination);
        register("club_profile", "Combine club match records with its FIFA snapshot roster using the same club identity. "
                + "Match season filters apply to fixtures.",
                queries::clubProfile, List.of("team"), filters, pagination, Map.of(
                    "nationality", playerFilters.get("nationality"), "position", playerFilters.get("position")));
        register("standings", "Calculate a season's league table from scores and show bottom positions when coverage permits. "
                + "Defaults to Série A. Administrative adjustments and player scorers are unavailable.",
                queries::standings, List.of("season"), Map.of("season", filters.get("season"),
                    "competition", string("Brasileirão (Série A) or Série B"),
                    "source", filters.get("source")));
        register("team_rankings", "Rank clubs by goals scored, wins, points or win rate. "
                + "Use venue and minimumMatches for home or away comparisons.",
                queries::rankings, List.of(), filters, pagination, Map.of(
                    "metric", choices("Ranking metric", "goals", "wins", "points", "winRate"),
                    "minimumMatches", number("Minimum scored fixtures per club, default 1", 1, Integer.MAX_VALUE)));
        register("match_statistics", "Calculate average goals and home/away win rates, compare seasons, or find biggest wins.",
                queries::statistics, List.of(), filters, pagination,
                Map.of("mode", choices("Analysis", "summary", "bySeason", "biggestWins")));
    }

    @SafeVarargs
    private void register(String name, String description, Function<JsonNode, SoccerTools.Answer> execute,
                          List<String> required, Map<String, Map<String, Object>>... groups) {
        Map<String, Map<String, Object>> properties = new TreeMap<>();
        for (var group : groups) {
            properties.putAll(group);
        }
        tools.put(name, new Tool(name, description,
                Map.of("type", "object", "properties", properties, "required", required, "additionalProperties", false),
                execute));
    }

    private static Map<String, Object> string(String description) {
        return Map.of("type", "string", "description", description, "minLength", 1);
    }

    private static Map<String, Object> choices(String description, String... values) {
        return Map.of("type", "string", "description", description, "enum", List.of(values));
    }

    private static Map<String, Object> number(String description, int min, int max) {
        return Map.of("type", "integer", "description", description, "minimum", min, "maximum", max);
    }

    public static void main(String[] args) throws IOException {
        if (args.length > 1) {
            System.err.println("Usage: java -jar brazilian-soccer-mcp.jar [data-directory]");
            System.exit(2);
        }
        Path root = Path.of(args.length == 1 ? args[0] : "data/kaggle");
        McpServer server = new McpServer(new SoccerData(root));
        try (var input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
             var output = new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8))) {
            server.serve(input, output);
        }
    }

    void serve(BufferedReader input, BufferedWriter output) throws IOException {
        String line;
        while ((line = input.readLine()) != null) {
            JsonNode response;
            try {
                response = dispatch(JSON.readTree(line));
            } catch (JsonProcessingException exception) {
                response = error(null, -32700, "Parse error");
            }
            if (response != null) {
                output.write(JSON.writeValueAsString(response));
                output.newLine();
                output.flush();
            }
        }
    }

    JsonNode dispatch(JsonNode request) {
        if (request == null || !request.isObject()) {
            return error(null, -32600, "Invalid request");
        }
        JsonNode id = request.get("id");
        if (!"2.0".equals(request.path("jsonrpc").asText()) || !request.path("method").isTextual()
                || (id != null && !id.isTextual() && !id.isNumber())) {
            return error(null, -32600, "Invalid request");
        }
        if (id == null) {
            return null;
        }
        JsonNode params = request.path("params");
        if (!params.isMissingNode() && !params.isObject()) {
            return error(id, -32602, "params must be an object");
        }
        try {
            Object result = switch (request.path("method").textValue()) {
                case "initialize" -> initialize(params);
                case "ping" -> Map.of();
                case "tools/list" -> Map.of("tools", tools.values().stream().map(Tool::definition).toList());
                case "tools/call" -> call(params);
                default -> null;
            };
            if (result == null) {
                return error(id, -32601, "Method not found");
            }
            return envelope(id).set("result", JSON.valueToTree(result));
        } catch (IllegalArgumentException exception) {
            return error(id, -32602, exception.getMessage());
        } catch (RuntimeException exception) {
            exception.printStackTrace(System.err);
            return error(id, -32603, "Internal error");
        }
    }

    private Map<String, Object> initialize(JsonNode params) {
        String requested = params.path("protocolVersion").asText();
        if (requested.isBlank()) {
            throw new IllegalArgumentException("Supply protocolVersion.");
        }
        version = PROTOCOLS.contains(requested) ? requested : "2025-11-25";
        return Map.of("protocolVersion", version, "capabilities", Map.of("tools", Map.of()),
                "serverInfo", Map.of("name", "brazilian-soccer-mcp", "version", "1.0.0"),
                "instructions", "Answer Brazilian soccer questions using local match results and a historical FIFA snapshot. "
                        + "Use source to inspect individual datasets. Player goal events are unavailable.");
    }

    private Object call(JsonNode params) {
        String name = params.path("name").asText();
        Tool tool = tools.get(name);
        if (tool == null) {
            throw new IllegalArgumentException("Unknown tool: " + name);
        }
        JsonNode arguments = params.has("arguments") ? params.get("arguments") : JSON.createObjectNode();
        validate(tool, arguments);
        try {
            SoccerTools.Answer answer = tool.execute.apply(arguments);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("content", List.of(Map.of("type", "text", "text", answer.text())));
            if (version.compareTo("2025-06-18") >= 0) {
                result.put("structuredContent", answer.data());
            } else {
                result.put("content", List.of(Map.of("type", "text", "text", answer.text()),
                        Map.of("type", "text", "text", JSON.writeValueAsString(answer.data()))));
            }
            return result;
        } catch (IllegalArgumentException exception) {
            return Map.of("content", List.of(Map.of("type", "text", "text", exception.getMessage())), "isError", true);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException(exception);
        }
    }

    private static void validate(Tool tool, JsonNode args) {
        if (!args.isObject()) {
            throw new IllegalArgumentException("arguments must be an object");
        }
        JsonNode schema = JSON.valueToTree(tool.inputSchema);
        for (JsonNode required : schema.path("required")) {
            if (!args.has(required.textValue())) {
                throw new IllegalArgumentException("Supply " + required.textValue());
            }
        }
        args.properties().forEach(field -> {
            String key = field.getKey();
            JsonNode value = field.getValue();
            JsonNode property = schema.path("properties").path(key);
            boolean valid = switch (property.path("type").asText()) {
                case "string" -> value.isTextual() && !value.textValue().isBlank()
                        && (!property.has("enum") || allowedChoice(property.get("enum"), value));
                case "integer" -> value.isIntegralNumber() && value.canConvertToInt()
                        && value.intValue() >= property.path("minimum").intValue()
                        && value.intValue() <= property.path("maximum").intValue();
                case "boolean" -> value.isBoolean();
                default -> throw new IllegalArgumentException("Unknown argument: " + key);
            };
            if (!valid) {
                throw new IllegalArgumentException("Invalid value for " + key);
            }
        });
    }

    private static boolean allowedChoice(JsonNode choices, JsonNode value) {
        for (JsonNode choice : choices) {
            if (choice.equals(value)) {
                return true;
            }
        }
        return false;
    }

    private static ObjectNode envelope(JsonNode id) {
        var response = JSON.createObjectNode().put("jsonrpc", "2.0");
        response.set("id", id);
        return response;
    }

    private static JsonNode error(JsonNode id, int code, String message) {
        ObjectNode response = envelope(id);
        response.putObject("error").put("code", code).put("message", message);
        return response;
    }
}
