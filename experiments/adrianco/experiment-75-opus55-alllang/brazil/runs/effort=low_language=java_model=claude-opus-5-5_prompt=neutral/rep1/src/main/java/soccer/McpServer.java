package soccer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.Function;

/** MCP server over stdio (newline-delimited JSON-RPC 2.0). */
public final class McpServer {
    private static final ObjectMapper JSON = new ObjectMapper();
    private final SoccerService svc;
    private final Map<String, Tool> tools = new LinkedHashMap<>();

    record Tool(String name, String description, ObjectNode schema, Function<JsonNode, String> handler) {}

    public McpServer(SoccerService svc) {
        this.svc = svc;
        register();
    }

    public static void main(String[] args) throws IOException {
        DataStore data = DataStore.load(args.length > 0 ? java.nio.file.Path.of(args[0]) : DataStore.defaultDir());
        new McpServer(new SoccerService(data)).run(System.in, System.out);
    }

    public void run(InputStream in, OutputStream out) throws IOException {
        BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        PrintStream w = new PrintStream(out, true, StandardCharsets.UTF_8);
        String line;
        while ((line = r.readLine()) != null) {
            if (line.isBlank()) continue;
            JsonNode resp = handle(line);
            if (resp != null) w.println(JSON.writeValueAsString(resp));
        }
    }

    /** Handle one JSON-RPC message; returns null for notifications. */
    public JsonNode handle(String message) {
        JsonNode req;
        try { req = JSON.readTree(message); } catch (IOException e) { return error(null, -32700, "Parse error"); }
        JsonNode id = req.get("id");
        String method = req.path("method").asText();
        if (id == null || id.isNull()) return null;
        try {
            ObjectNode result = JSON.createObjectNode();
            switch (method) {
                case "initialize" -> {
                    result.put("protocolVersion", req.path("params").path("protocolVersion").asText("2024-11-05"));
                    result.putObject("capabilities").putObject("tools");
                    result.putObject("serverInfo").put("name", "brazilian-soccer").put("version", "1.0");
                }
                case "ping" -> {}
                case "tools/list" -> {
                    ArrayNode arr = result.putArray("tools");
                    for (Tool t : tools.values())
                        arr.addObject().put("name", t.name()).put("description", t.description()).set("inputSchema", t.schema());
                }
                case "tools/call" -> {
                    String name = req.path("params").path("name").asText();
                    Tool t = tools.get(name);
                    if (t == null) return error(id, -32602, "Unknown tool: " + name);
                    String text;
                    boolean isError = false;
                    try { text = t.handler().apply(req.path("params").path("arguments")); }
                    catch (RuntimeException e) { text = "Error: " + e.getMessage(); isError = true; }
                    result.putArray("content").addObject().put("type", "text").put("text", text);
                    result.put("isError", isError);
                }
                default -> { return error(id, -32601, "Method not found: " + method); }
            }
            ObjectNode resp = JSON.createObjectNode().put("jsonrpc", "2.0");
            resp.set("id", id);
            resp.set("result", result);
            return resp;
        } catch (RuntimeException e) {
            return error(id, -32603, e.getMessage());
        }
    }

    private static ObjectNode error(JsonNode id, int code, String msg) {
        ObjectNode resp = JSON.createObjectNode().put("jsonrpc", "2.0");
        resp.set("id", id);
        resp.putObject("error").put("code", code).put("message", msg);
        return resp;
    }

    public Set<String> toolNames() { return tools.keySet(); }

    // ---------------- tool registration ----------------
    private static String s(JsonNode a, String k) { JsonNode n = a.get(k); return n == null || n.isNull() ? null : n.asText(); }
    private static Integer i(JsonNode a, String k) { JsonNode n = a.get(k); return n == null || n.isNull() || n.asText().isBlank() ? null : n.asInt(); }
    private static String req(JsonNode a, String k) {
        String v = s(a, k);
        if (v == null || v.isBlank()) throw new IllegalArgumentException("Missing required argument: " + k);
        return v;
    }

    private void add(String name, String desc, String[][] props, String[] required, Function<JsonNode, String> h) {
        ObjectNode schema = JSON.createObjectNode().put("type", "object");
        ObjectNode p = schema.putObject("properties");
        for (String[] prop : props) p.putObject(prop[0]).put("type", prop[1]).put("description", prop[2]);
        ArrayNode reqd = schema.putArray("required");
        for (String r : required) reqd.add(r);
        tools.put(name, new Tool(name, desc, schema, h));
    }

    private static final String[] TEAM = {"team", "string", "Team name (accents/state suffix optional, e.g. 'Flamengo', 'São Paulo')"};
    private static final String[] COMP = {"competition", "string", "Brasileirão | Copa do Brasil | Libertadores | Serie B | Serie C"};
    private static final String[] SEASON = {"season", "integer", "Season year"};
    private static final String[] LIMIT = {"limit", "integer", "Max results"};
    private static final String[] VENUE = {"venue", "string", "home | away | all"};

    private void register() {
        add("search_matches", "Find matches by team, opponent, competition, season, date range and venue.",
                new String[][]{TEAM, {"opponent", "string", "Opponent team"}, COMP, SEASON,
                        {"date_from", "string", "Start date (YYYY-MM-DD or DD/MM/YYYY)"}, {"date_to", "string", "End date"}, VENUE, LIMIT},
                new String[0], a -> svc.searchMatches(s(a, "team"), s(a, "opponent"), s(a, "competition"), i(a, "season"),
                        s(a, "date_from"), s(a, "date_to"), s(a, "venue"), i(a, "limit")));
        add("last_match", "Most recent match between two teams, with score.",
                new String[][]{TEAM, {"opponent", "string", "Opponent team"}}, new String[]{"team", "opponent"},
                a -> svc.lastMatch(req(a, "team"), req(a, "opponent")));
        add("head_to_head", "Head-to-head record between two teams.",
                new String[][]{{"team_a", "string", "First team"}, {"team_b", "string", "Second team"}, COMP},
                new String[]{"team_a", "team_b"}, a -> svc.headToHead(req(a, "team_a"), req(a, "team_b"), s(a, "competition")));
        add("team_stats", "Win/draw/loss record and goals for a team, optionally by season, competition and venue.",
                new String[][]{TEAM, SEASON, COMP, VENUE}, new String[]{"team"},
                a -> svc.teamStats(req(a, "team"), i(a, "season"), s(a, "competition"), s(a, "venue")));
        add("team_competitions", "List competitions and seasons a team appears in.",
                new String[][]{TEAM}, new String[]{"team"}, a -> svc.teamCompetitions(req(a, "team")));
        add("standings", "League table for a season calculated from match results.",
                new String[][]{SEASON, COMP, {"top", "integer", "Only show top N"}}, new String[]{"season"},
                a -> svc.standings(i(a, "season"), s(a, "competition"), i(a, "top")));
        add("champion", "Who won a competition in a season (calculated).",
                new String[][]{SEASON, COMP}, new String[]{"season"}, a -> svc.champion(i(a, "season"), s(a, "competition")));
        add("relegated", "Teams relegated from the Brasileirão in a season (bottom 4, calculated).",
                new String[][]{SEASON}, new String[]{"season"}, a -> svc.relegated(i(a, "season")));
        add("finals", "List cup finals (Copa do Brasil or Libertadores).",
                new String[][]{COMP}, new String[0], a -> svc.finals(s(a, "competition")));
        add("bracket", "Knockout-stage matches for a cup competition season.",
                new String[][]{COMP, SEASON}, new String[]{"competition", "season"},
                a -> svc.bracket(req(a, "competition"), i(a, "season")));
        add("derbies", "Traditional rivalry matches (Fla-Flu, Grenal, Derby Paulista...).",
                new String[][]{SEASON, COMP}, new String[0], a -> svc.derbies(i(a, "season"), s(a, "competition")));
        add("top_scoring_teams", "Teams ranked by goals scored.",
                new String[][]{SEASON, COMP, LIMIT}, new String[0],
                a -> svc.topScoringTeams(i(a, "season"), s(a, "competition"), i(a, "limit")));
        add("competition_stats", "Average goals per match, home/away/draw rates.",
                new String[][]{COMP, SEASON}, new String[0], a -> svc.competitionStats(s(a, "competition"), i(a, "season")));
        add("biggest_wins", "Largest margins of victory.",
                new String[][]{COMP, SEASON, LIMIT}, new String[0],
                a -> svc.biggestWins(s(a, "competition"), i(a, "season"), i(a, "limit")));
        add("best_records", "Teams ranked by win rate (overall, home or away).",
                new String[][]{COMP, SEASON, VENUE, {"min_matches", "integer", "Minimum matches"}, LIMIT}, new String[0],
                a -> svc.bestRecords(s(a, "competition"), i(a, "season"), s(a, "venue"), i(a, "min_matches"), i(a, "limit")));
        add("compare_seasons", "Compare aggregate statistics across seasons.",
                new String[][]{COMP, {"seasons", "string", "Comma-separated years, e.g. '2018,2019'"}}, new String[]{"seasons"},
                a -> svc.compareSeasons(s(a, "competition"), Arrays.stream(req(a, "seasons").split(","))
                        .map(String::trim).map(Integer::parseInt).toList()));
        add("search_players", "Search FIFA players by name, nationality, club, position (or group: forward/midfielder/defender/goalkeeper) and rating.",
                new String[][]{{"name", "string", "Name substring"}, {"nationality", "string", "e.g. Brazil"},
                        {"club", "string", "Club substring"}, {"position", "string", "Position code or group"},
                        {"min_overall", "integer", "Minimum overall rating"}, LIMIT}, new String[0],
                a -> svc.searchPlayers(s(a, "name"), s(a, "nationality"), s(a, "club"), s(a, "position"), i(a, "min_overall"), i(a, "limit")));
        add("players_by_club", "Count and average rating of players of a nationality per club.",
                new String[][]{{"nationality", "string", "Default Brazil"}, LIMIT}, new String[0],
                a -> svc.playersByClub(s(a, "nationality"), i(a, "limit")));
        add("club_profile", "Cross-dataset profile: FIFA players at a club plus its match record.",
                new String[][]{{"club", "string", "Club name"}}, new String[]{"club"}, a -> svc.clubProfile(req(a, "club")));
        add("dataset_info", "Describe the loaded datasets.", new String[0][], new String[0], a -> svc.datasetInfo());
    }
}
