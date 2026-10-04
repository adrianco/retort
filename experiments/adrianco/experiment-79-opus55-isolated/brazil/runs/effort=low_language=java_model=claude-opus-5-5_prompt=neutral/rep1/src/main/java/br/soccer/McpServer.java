package br.soccer;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

/**
 * Model Context Protocol server over stdio (newline-delimited JSON-RPC 2.0) exposing the Brazilian
 * soccer queries as tools.
 */
public final class McpServer {
    private static final String PROTOCOL_VERSION = "2024-11-05";

    private record Tool(String name, String description, Map<String, Object> schema,
                        Function<Map<String, Object>, String> handler) {}

    private final QueryService q;
    private final Map<String, Tool> tools = new LinkedHashMap<>();

    public McpServer(QueryService q) {
        this.q = q;
        registerTools();
    }

    public static void main(String[] args) throws IOException {
        Path dir = args.length > 0 ? Path.of(args[0]) : DataStore.defaultDir();
        DataStore ds = DataStore.load(dir);
        System.err.println("brazilian-soccer-mcp: loaded " + ds.matches().size() + " matches and "
                + ds.players().size() + " players from " + dir.toAbsolutePath());
        new McpServer(new QueryService(ds)).serve(System.in, new PrintStream(System.out, true, StandardCharsets.UTF_8));
    }

    /** Reads one JSON-RPC message per line until end of input. */
    public void serve(InputStream in, PrintStream out) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        String line;
        while ((line = reader.readLine()) != null) {
            if (line.isBlank()) continue;
            String response = handle(line);
            if (response != null) {
                out.println(response);
                out.flush();
            }
        }
    }

    /** Handles one JSON-RPC message; returns the response JSON, or null for notifications. */
    public String handle(String message) {
        Object parsed;
        try {
            parsed = Json.parse(message);
        } catch (RuntimeException e) {
            return Json.write(error(null, -32700, "Parse error: " + e.getMessage()));
        }
        if (!(parsed instanceof Map<?, ?> raw)) {
            return Json.write(error(null, -32600, "Invalid request"));
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> req = (Map<String, Object>) raw;
        Object id = req.get("id");
        boolean notification = !req.containsKey("id");
        if (!(req.get("method") instanceof String method)) {
            return notification ? null : Json.write(error(id, -32600, "Invalid request"));
        }
        Map<String, Object> params = asMap(req.get("params"));
        try {
            Object result;
            switch (method) {
                case "initialize" -> result = initialize(params);
                case "ping" -> result = new LinkedHashMap<String, Object>();
                case "tools/list" -> result = Map.of("tools", toolList());
                case "tools/call" -> result = callTool(params);
                default -> {
                    if (notification) return null;
                    return Json.write(error(id, -32601, "Method not found: " + method));
                }
            }
            if (notification) return null;
            Map<String, Object> resp = new LinkedHashMap<>();
            resp.put("jsonrpc", "2.0");
            resp.put("id", id);
            resp.put("result", result);
            return Json.write(resp);
        } catch (IllegalArgumentException e) {
            return notification ? null : Json.write(error(id, -32602, e.getMessage()));
        } catch (RuntimeException e) {
            return notification ? null : Json.write(error(id, -32603, "Internal error: " + e));
        }
    }

    private static Map<String, Object> error(Object id, int code, String message) {
        Map<String, Object> err = new LinkedHashMap<>();
        err.put("code", code);
        err.put("message", message);
        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("jsonrpc", "2.0");
        resp.put("id", id);
        resp.put("error", err);
        return resp;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asMap(Object o) {
        return o instanceof Map<?, ?> m ? (Map<String, Object>) m : new LinkedHashMap<>();
    }

    private Map<String, Object> initialize(Map<String, Object> params) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("protocolVersion",
                params.get("protocolVersion") instanceof String v ? v : PROTOCOL_VERSION);
        result.put("capabilities", Map.of("tools", Map.of("listChanged", false)));
        result.put("serverInfo", Map.of("name", "brazilian-soccer-mcp", "version", "1.0.0"));
        result.put("instructions", "Query Brazilian soccer data: Brasileirão, Copa do Brasil and Libertadores"
                + " matches, standings and statistics, plus FIFA player data. Team names are accent- and"
                + " suffix-insensitive (\"Sao Paulo\", \"São Paulo-SP\" and \"São Paulo FC\" are the same club).");
        return result;
    }

    private List<Object> toolList() {
        List<Object> list = new ArrayList<>();
        for (Tool t : tools.values()) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("name", t.name());
            m.put("description", t.description());
            m.put("inputSchema", t.schema());
            list.add(m);
        }
        return list;
    }

    private Map<String, Object> callTool(Map<String, Object> params) {
        if (!(params.get("name") instanceof String name) || !tools.containsKey(name)) {
            throw new IllegalArgumentException("Unknown tool: " + params.get("name"));
        }
        String text;
        boolean isError = false;
        try {
            text = tools.get(name).handler().apply(asMap(params.get("arguments")));
        } catch (IllegalArgumentException e) {
            // Bad input is reported in-band so the calling model can correct itself.
            text = e.getMessage();
            isError = true;
        }
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("type", "text");
        content.put("text", text);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("content", List.of(content));
        result.put("isError", isError);
        return result;
    }

    // ---------------------------------------------------------------- argument helpers

    private static String str(Map<String, Object> a, String k) {
        Object v = a.get(k);
        if (v == null) return null;
        String s = v instanceof Double d && d == Math.rint(d) ? String.valueOf(d.longValue()) : v.toString();
        return s.isBlank() ? null : s;
    }

    private static Integer integer(Map<String, Object> a, String k) {
        Object v = a.get(k);
        if (v == null || v instanceof String s && s.isBlank()) return null;
        if (v instanceof Number n && n.doubleValue() == Math.rint(n.doubleValue())
                && Math.abs(n.doubleValue()) < 1e9) {
            return n.intValue();
        }
        if (v instanceof String s && s.trim().matches("-?\\d{1,9}")) return Integer.parseInt(s.trim());
        throw new IllegalArgumentException("Argument \"" + k + "\" must be an integer.");
    }

    private static Boolean bool(Map<String, Object> a, String k) {
        Object v = a.get(k);
        if (v == null) return null;
        if (v instanceof Boolean b) return b;
        if (v instanceof String s && (s.equalsIgnoreCase("true") || s.equalsIgnoreCase("false"))) {
            return Boolean.parseBoolean(s);
        }
        throw new IllegalArgumentException("Argument \"" + k + "\" must be a boolean.");
    }

    private static LocalDate date(Map<String, Object> a, String k) {
        String s = str(a, k);
        if (s == null) return null;
        LocalDate d = DataStore.parseDate(s);
        if (d == null) throw new IllegalArgumentException("Argument \"" + k + "\" must be a date (YYYY-MM-DD or DD/MM/YYYY).");
        return d;
    }

    /** Builds a JSON schema from "name:type:description" specs; names ending in '!' are required. */
    private static Map<String, Object> schema(String... props) {
        Map<String, Object> properties = new LinkedHashMap<>();
        List<String> required = new ArrayList<>();
        for (String p : props) {
            String[] parts = p.split(":", 3);
            String name = parts[0];
            if (name.endsWith("!")) {
                name = name.substring(0, name.length() - 1);
                required.add(name);
            }
            Map<String, Object> prop = new LinkedHashMap<>();
            prop.put("type", parts[1]);
            prop.put("description", parts[2]);
            properties.put(name, prop);
        }
        Map<String, Object> s = new LinkedHashMap<>();
        s.put("type", "object");
        s.put("properties", properties);
        if (!required.isEmpty()) s.put("required", required);
        return s;
    }

    private void tool(String name, String description, Map<String, Object> schema,
                      Function<Map<String, Object>, String> handler) {
        tools.put(name, new Tool(name, description, schema, handler));
    }

    private static final String COMP = "competition:string:Competition: Brasileirão (Serie A), Serie B, Serie C,"
            + " Copa do Brasil or Libertadores. Omit for all.";
    private static final String SEASON = "season:integer:Season year, e.g. 2019";
    private static final String LIMIT = "limit:integer:Maximum number of rows to return";

    private void registerTools() {
        tool("search_matches",
                "Find matches by team, opponent, venue, competition, season, date range or stage. Most recent"
                        + " first, so limit=1 answers \"when did X last play Y\". With team and opponent it also"
                        + " returns the head-to-head tally.",
                schema("team:string:Team name (any spelling variant)",
                        "opponent:string:Second team, to find matches between the two",
                        "venue:string:home, away or either - where 'team' played", COMP, SEASON,
                        "date_from:string:Earliest date, YYYY-MM-DD", "date_to:string:Latest date, YYYY-MM-DD",
                        "stage:string:Stage or round, e.g. final, semifinals, quarterfinals, round of 16,"
                                + " group stage, or a round number",
                        LIMIT),
                a -> q.searchMatches(new QueryService.Filter().team(str(a, "team")).opponent(str(a, "opponent"))
                        .venue(str(a, "venue")).competition(str(a, "competition")).season(integer(a, "season"))
                        .from(date(a, "date_from")).to(date(a, "date_to")).stage(str(a, "stage")),
                        integer(a, "limit")));
        tool("head_to_head", "Compare two teams head-to-head: wins, draws, goals, home/away split, recent meetings.",
                schema("team_a!:string:First team", "team_b!:string:Second team", COMP, SEASON),
                a -> q.headToHead(str(a, "team_a"), str(a, "team_b"), str(a, "competition"), integer(a, "season")));
        tool("team_stats",
                "A team's record: matches, wins, draws, losses, goals, win rate, home/away split and breakdown"
                        + " by competition (which also shows every competition the team has played in).",
                schema("team!:string:Team name", SEASON, COMP, "venue:string:home, away or either"),
                a -> q.teamStats(str(a, "team"), integer(a, "season"), str(a, "competition"), str(a, "venue")));
        tool("standings",
                "League table for a season calculated from match results, with champion and relegated teams"
                        + " for complete Serie A seasons.",
                schema("season!:integer:Season year, e.g. 2019", "competition:string:Serie A (default), Serie B or Serie C"),
                a -> q.standings(integer(a, "season"), str(a, "competition")));
        tool("team_rankings",
                "Rank teams by a metric, e.g. best home record, best away record, most goals scored in a season.",
                schema("metric:string:win_rate (default), points, points_per_match, wins, goals_for,"
                                + " goals_against or goal_difference",
                        "venue:string:home, away or all (default)", COMP, SEASON,
                        "min_matches:integer:Ignore teams with fewer matches (default 20, or 5 when a season is given)",
                        LIMIT),
                a -> q.teamRankings(str(a, "metric"), str(a, "venue"), str(a, "competition"), integer(a, "season"),
                        integer(a, "min_matches"), integer(a, "limit")));
        tool("match_statistics",
                "Aggregate statistics: average goals per match, home win / draw / away win rates, corners and shots.",
                schema(COMP, SEASON),
                a -> q.matchStatistics(str(a, "competition"), integer(a, "season")));
        tool("biggest_wins", "Matches with the largest winning margins.",
                schema(COMP, SEASON, "team:string:Only matches involving this team", LIMIT),
                a -> q.biggestWins(str(a, "competition"), integer(a, "season"), str(a, "team"), integer(a, "limit")));
        tool("compare_seasons", "Compare aggregate statistics of two seasons of a competition.",
                schema("season_a!:integer:First season year", "season_b!:integer:Second season year",
                        "competition:string:Competition (default Serie A)"),
                a -> q.compareSeasons(integer(a, "season_a"), integer(a, "season_b"), str(a, "competition")));
        tool("derbies", "Matches between traditional rivals (Fla-Flu, Derby Paulista, Gre-Nal, ...).",
                schema(SEASON, COMP, "team:string:Only derbies involving this team", LIMIT),
                a -> q.derbies(integer(a, "season"), str(a, "competition"), str(a, "team"), integer(a, "limit")));
        tool("knockout_stages",
                "Knockout bracket of a cup season: every tie by stage with aggregate scores.",
                schema("season!:integer:Season year, e.g. 2018", "competition:string:Libertadores (default) or Copa do Brasil"),
                a -> q.knockoutStages(str(a, "competition"), integer(a, "season")));
        tool("search_players",
                "Search the FIFA player database by name, nationality, club and position; highest rated first.",
                schema("name:string:Full or partial player name", "nationality:string:Country, e.g. Brazil",
                        "club:string:Full or partial club name",
                        "position:string:FIFA position code (ST, GK, CAM, ...) or a group: forward, midfielder,"
                                + " defender, goalkeeper",
                        "min_overall:integer:Minimum overall rating", LIMIT),
                a -> q.searchPlayers(str(a, "name"), str(a, "nationality"), str(a, "club"), str(a, "position"),
                        integer(a, "min_overall"), integer(a, "limit")));
        tool("player_details", "Full profile of one player: ratings, club, position, physical and skill attributes.",
                schema("name!:string:Player name"),
                a -> q.playerDetails(str(a, "name")));
        tool("players_by_club", "Count and average rating of players of a nationality, grouped by club.",
                schema("nationality:string:Country (default Brazil)",
                        "brazilian_clubs_only:boolean:Only clubs from Brazil (default true)", LIMIT),
                a -> q.playersByClub(str(a, "nationality"), bool(a, "brazilian_clubs_only"), integer(a, "limit")));
        tool("club_profile",
                "Cross-dataset view of a club: all-time match record by competition plus its FIFA squad.",
                schema("team!:string:Team name"),
                a -> q.clubProfile(str(a, "team")));
        tool("dataset_info", "Which files are loaded, how many rows, and which competitions and seasons are covered.",
                schema(),
                a -> q.datasetInfo());
    }
}
