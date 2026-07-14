package com.soccer.mcp.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.soccer.mcp.data.DataStore;
import com.soccer.mcp.model.Match;
import com.soccer.mcp.model.Player;
import com.soccer.mcp.query.HeadToHead;
import com.soccer.mcp.query.QueryService;
import com.soccer.mcp.query.TeamStats;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.List;

/**
 * Minimal MCP server: JSON-RPC 2.0 over stdio.
 * Supports: initialize, tools/list, tools/call.
 */
public final class McpServer {

    private static final String PROTOCOL_VERSION = "2024-11-05";

    private final QueryService query;
    private final DataStore store;
    private final ObjectMapper json = new ObjectMapper();

    public McpServer(DataStore store) {
        this.store = store;
        this.query = new QueryService(store);
    }

    public void run(InputStream in, PrintWriter out) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        String line;
        while ((line = reader.readLine()) != null) {
            String trimmed = line.trim();
            if (trimmed.isEmpty()) continue;
            try {
                JsonNode req = json.readTree(trimmed);
                JsonNode response = handle(req);
                if (response != null) {
                    out.println(json.writeValueAsString(response));
                    out.flush();
                }
            } catch (Exception e) {
                ObjectNode err = json.createObjectNode();
                err.put("jsonrpc", "2.0");
                err.putNull("id");
                ObjectNode errBody = err.putObject("error");
                errBody.put("code", -32700);
                errBody.put("message", "Parse error: " + e.getMessage());
                out.println(json.writeValueAsString(err));
                out.flush();
            }
        }
    }

    public JsonNode handle(JsonNode req) {
        String method = req.path("method").asText("");
        JsonNode id = req.get("id");
        JsonNode params = req.path("params");

        try {
            switch (method) {
                case "initialize":
                    return success(id, initialize());
                case "initialized":
                case "notifications/initialized":
                    return null; // notification, no reply
                case "tools/list":
                    return success(id, toolsList());
                case "tools/call":
                    return success(id, toolsCall(params));
                case "ping":
                    return success(id, json.createObjectNode());
                default:
                    return error(id, -32601, "Method not found: " + method);
            }
        } catch (IllegalArgumentException ex) {
            return error(id, -32602, "Invalid params: " + ex.getMessage());
        } catch (Exception ex) {
            return error(id, -32603, "Internal error: " + ex.getMessage());
        }
    }

    private ObjectNode initialize() {
        ObjectNode result = json.createObjectNode();
        result.put("protocolVersion", PROTOCOL_VERSION);
        ObjectNode capabilities = result.putObject("capabilities");
        capabilities.putObject("tools");
        ObjectNode info = result.putObject("serverInfo");
        info.put("name", "brazilian-soccer-mcp");
        info.put("version", "1.0.0");
        return result;
    }

    private ObjectNode toolsList() {
        ObjectNode result = json.createObjectNode();
        ArrayNode tools = result.putArray("tools");
        tools.add(tool("find_matches",
                "Find matches by optional team, competition, season, and date range",
                schemaProps(
                        prop("team", "string", "Team name (any team plays in match)", false),
                        prop("competition", "string", "Competition substring (e.g. 'Brasileirão')", false),
                        prop("season", "integer", "Season year", false),
                        prop("from", "string", "ISO date YYYY-MM-DD (inclusive)", false),
                        prop("to", "string", "ISO date YYYY-MM-DD (inclusive)", false),
                        prop("limit", "integer", "Max number of matches to return", false)
                )));
        tools.add(tool("matches_between",
                "Find all matches between two teams",
                schemaProps(
                        prop("team_a", "string", "First team", true),
                        prop("team_b", "string", "Second team", true)
                )));
        tools.add(tool("team_stats",
                "Aggregate statistics for a team",
                schemaProps(
                        prop("team", "string", "Team name", true),
                        prop("season", "integer", "Filter by season", false),
                        prop("competition", "string", "Competition substring", false),
                        prop("venue", "string", "'home', 'away', or omit for both", false)
                )));
        tools.add(tool("head_to_head",
                "Head-to-head record between two teams",
                schemaProps(
                        prop("team_a", "string", "First team", true),
                        prop("team_b", "string", "Second team", true)
                )));
        tools.add(tool("standings",
                "Calculate season standings for a competition",
                schemaProps(
                        prop("competition", "string", "Competition substring", true),
                        prop("season", "integer", "Season year", true)
                )));
        tools.add(tool("champion",
                "Champion of a competition for a season (top of standings)",
                schemaProps(
                        prop("competition", "string", "Competition substring", true),
                        prop("season", "integer", "Season year", true)
                )));
        tools.add(tool("find_players",
                "Search players by name, nationality, club or position",
                schemaProps(
                        prop("name", "string", "Substring match on name", false),
                        prop("nationality", "string", "Exact nationality (e.g. 'Brazil')", false),
                        prop("club", "string", "Substring match on club", false),
                        prop("position", "string", "Position code (e.g. 'ST','GK','CB')", false),
                        prop("min_overall", "integer", "Minimum FIFA overall", false),
                        prop("limit", "integer", "Max players to return", false)
                )));
        tools.add(tool("top_brazilian_players",
                "Top-rated Brazilian players by FIFA Overall",
                schemaProps(
                        prop("limit", "integer", "Max players (default 10)", false)
                )));
        tools.add(tool("biggest_wins",
                "Largest goal-margin victories in the dataset",
                schemaProps(
                        prop("limit", "integer", "How many to return (default 10)", false)
                )));
        tools.add(tool("competition_stats",
                "Average goals per match and home win rate for a competition",
                schemaProps(
                        prop("competition", "string", "Competition substring (omit for all)", false)
                )));
        return result;
    }

    private ObjectNode tool(String name, String description, ObjectNode inputSchema) {
        ObjectNode t = json.createObjectNode();
        t.put("name", name);
        t.put("description", description);
        t.set("inputSchema", inputSchema);
        return t;
    }

    private ObjectNode prop(String name, String type, String description, boolean required) {
        ObjectNode p = json.createObjectNode();
        p.put("name", name);
        p.put("type", type);
        p.put("description", description);
        p.put("required", required);
        return p;
    }

    private ObjectNode schemaProps(ObjectNode... props) {
        ObjectNode schema = json.createObjectNode();
        schema.put("type", "object");
        ObjectNode properties = schema.putObject("properties");
        ArrayNode required = json.createArrayNode();
        for (ObjectNode p : props) {
            String name = p.get("name").asText();
            ObjectNode propSchema = properties.putObject(name);
            propSchema.put("type", p.get("type").asText());
            propSchema.put("description", p.get("description").asText());
            if (p.get("required").asBoolean()) required.add(name);
        }
        if (required.size() > 0) schema.set("required", required);
        return schema;
    }

    private ObjectNode toolsCall(JsonNode params) {
        String name = params.path("name").asText("");
        JsonNode args = params.path("arguments");
        String text = switch (name) {
            case "find_matches" -> formatMatches(query.findMatches(
                    optStr(args, "team"),
                    optStr(args, "competition"),
                    optInt(args, "season"),
                    optDate(args, "from"),
                    optDate(args, "to")
            ), optIntOr(args, "limit", 50));
            case "matches_between" -> formatMatchesBetween(
                    requireStr(args, "team_a"),
                    requireStr(args, "team_b"));
            case "team_stats" -> formatTeamStats(query.teamStats(
                    requireStr(args, "team"),
                    optInt(args, "season"),
                    optStr(args, "competition"),
                    optStr(args, "venue")));
            case "head_to_head" -> formatHeadToHead(query.headToHead(
                    requireStr(args, "team_a"),
                    requireStr(args, "team_b")));
            case "standings" -> formatStandings(query.standings(
                    requireStr(args, "competition"),
                    requireInt(args, "season")), requireStr(args, "competition"),
                    requireInt(args, "season"));
            case "champion" -> {
                TeamStats champ = query.champion(
                        requireStr(args, "competition"),
                        requireInt(args, "season"));
                yield champ == null
                        ? "No data found"
                        : "Champion: " + champ.team() + " — " + champ.points() + " pts (" +
                          champ.wins() + "W, " + champ.draws() + "D, " + champ.losses() + "L)";
            }
            case "find_players" -> formatPlayers(filterPlayers(args), optIntOr(args, "limit", 25));
            case "top_brazilian_players" -> formatPlayers(
                    query.topRatedBrazilianPlayers(optIntOr(args, "limit", 10)),
                    optIntOr(args, "limit", 10));
            case "biggest_wins" -> formatMatches(
                    query.biggestWins(optIntOr(args, "limit", 10)),
                    optIntOr(args, "limit", 10));
            case "competition_stats" -> {
                String c = optStr(args, "competition");
                double avg = query.averageGoalsPerMatch(c);
                double hwr = query.homeWinRate(c);
                yield String.format("Competition: %s%nAverage goals per match: %.2f%nHome win rate: %.1f%%",
                        c == null ? "all" : c, avg, hwr * 100);
            }
            default -> throw new IllegalArgumentException("Unknown tool: " + name);
        };

        ObjectNode result = json.createObjectNode();
        ArrayNode content = result.putArray("content");
        ObjectNode item = content.addObject();
        item.put("type", "text");
        item.put("text", text);
        return result;
    }

    private List<Player> filterPlayers(JsonNode args) {
        String name = optStr(args, "name");
        String nationality = optStr(args, "nationality");
        String club = optStr(args, "club");
        String position = optStr(args, "position");
        Integer minOverall = optInt(args, "min_overall");

        return store.players().stream()
                .filter(p -> {
                    if (name != null) {
                        if (p.name() == null) return false;
                        String lower = p.name().toLowerCase();
                        if (!lower.contains(name.toLowerCase())) return false;
                    }
                    if (nationality != null) {
                        if (p.nationality() == null
                                || !p.nationality().equalsIgnoreCase(nationality)) return false;
                    }
                    if (club != null) {
                        if (p.club() == null) return false;
                        if (!p.club().toLowerCase().contains(club.toLowerCase())) return false;
                    }
                    if (position != null) {
                        if (p.position() == null
                                || !p.position().equalsIgnoreCase(position)) return false;
                    }
                    if (minOverall != null) {
                        if (p.overall() == null || p.overall() < minOverall) return false;
                    }
                    return true;
                })
                .sorted((a, b) -> {
                    Integer ao = a.overall(), bo = b.overall();
                    if (ao == null && bo == null) return 0;
                    if (ao == null) return 1;
                    if (bo == null) return -1;
                    return bo - ao;
                })
                .toList();
    }

    // --- Formatters ---

    private String formatMatches(List<Match> matches, int limit) {
        if (matches.isEmpty()) return "No matches found";
        StringBuilder sb = new StringBuilder();
        sb.append("Matches found: ").append(matches.size()).append('\n');
        int n = Math.min(limit, matches.size());
        for (int i = 0; i < n; i++) {
            Match m = matches.get(i);
            sb.append(formatMatchLine(m)).append('\n');
        }
        if (matches.size() > n) {
            sb.append("... (").append(matches.size() - n).append(" more)");
        }
        return sb.toString();
    }

    private String formatMatchLine(Match m) {
        String date = m.date() == null ? "(unknown)" : m.date().toString();
        return String.format("%s: %s %d-%d %s [%s%s]",
                date, m.homeTeam(), m.homeGoals(), m.awayGoals(), m.awayTeam(),
                m.competition() == null ? "" : m.competition(),
                m.round() == null || m.round().isEmpty() ? "" : " R" + m.round());
    }

    private String formatMatchesBetween(String a, String b) {
        HeadToHead h2h = query.headToHead(a, b);
        StringBuilder sb = new StringBuilder();
        sb.append(a).append(" vs ").append(b).append(":\n");
        for (Match m : h2h.matches()) {
            sb.append("- ").append(formatMatchLine(m)).append('\n');
        }
        sb.append(String.format("Head-to-head: %s %d wins, %s %d wins, %d draws (goals: %d-%d)",
                a, h2h.teamAWins(), b, h2h.teamBWins(), h2h.draws(),
                h2h.teamAGoals(), h2h.teamBGoals()));
        return sb.toString();
    }

    private String formatTeamStats(TeamStats s) {
        return String.format(
                "%s — Played: %d, Wins: %d, Draws: %d, Losses: %d, GF: %d, GA: %d, Points: %d, Win rate: %.1f%%",
                s.team(), s.played(), s.wins(), s.draws(), s.losses(),
                s.goalsFor(), s.goalsAgainst(), s.points(), s.winRate() * 100);
    }

    private String formatHeadToHead(HeadToHead h) {
        return String.format(
                "%s vs %s — Matches: %d | %s wins: %d | %s wins: %d | Draws: %d | Goals: %d-%d",
                h.teamA(), h.teamB(), h.totalMatches(), h.teamA(), h.teamAWins(),
                h.teamB(), h.teamBWins(), h.draws(), h.teamAGoals(), h.teamBGoals());
    }

    private String formatStandings(List<TeamStats> standings, String competition, int season) {
        if (standings.isEmpty()) return "No data for " + competition + " " + season;
        StringBuilder sb = new StringBuilder();
        sb.append(season).append(" ").append(competition).append(" standings:\n");
        int rank = 1;
        for (TeamStats s : standings) {
            sb.append(String.format("%2d. %-25s %3d pts (%2dW %2dD %2dL) GF:%-3d GA:%-3d GD:%+d%n",
                    rank++, s.team(), s.points(), s.wins(), s.draws(), s.losses(),
                    s.goalsFor(), s.goalsAgainst(), s.goalDifference()));
        }
        return sb.toString();
    }

    private String formatPlayers(List<Player> players, int limit) {
        if (players.isEmpty()) return "No players found";
        StringBuilder sb = new StringBuilder();
        sb.append("Players found: ").append(players.size()).append('\n');
        int n = Math.min(limit, players.size());
        int rank = 1;
        for (int i = 0; i < n; i++) {
            Player p = players.get(i);
            sb.append(String.format("%2d. %s — Overall: %s, Position: %s, Club: %s, Nat: %s%n",
                    rank++, p.name(),
                    p.overall() == null ? "?" : p.overall().toString(),
                    p.position() == null ? "?" : p.position(),
                    p.club() == null ? "?" : p.club(),
                    p.nationality() == null ? "?" : p.nationality()));
        }
        if (players.size() > n) {
            sb.append("... (").append(players.size() - n).append(" more)");
        }
        return sb.toString();
    }

    // --- Helpers ---

    private ObjectNode success(JsonNode id, JsonNode result) {
        ObjectNode resp = json.createObjectNode();
        resp.put("jsonrpc", "2.0");
        if (id != null) resp.set("id", id);
        else resp.putNull("id");
        resp.set("result", result);
        return resp;
    }

    private ObjectNode error(JsonNode id, int code, String message) {
        ObjectNode resp = json.createObjectNode();
        resp.put("jsonrpc", "2.0");
        if (id != null) resp.set("id", id);
        else resp.putNull("id");
        ObjectNode err = resp.putObject("error");
        err.put("code", code);
        err.put("message", message);
        return resp;
    }

    private String optStr(JsonNode args, String name) {
        JsonNode n = args.get(name);
        if (n == null || n.isNull()) return null;
        String s = n.asText();
        return s.isEmpty() ? null : s;
    }

    private String requireStr(JsonNode args, String name) {
        String s = optStr(args, name);
        if (s == null) throw new IllegalArgumentException("Missing required argument: " + name);
        return s;
    }

    private Integer optInt(JsonNode args, String name) {
        JsonNode n = args.get(name);
        if (n == null || n.isNull()) return null;
        if (n.isNumber()) return n.asInt();
        try { return Integer.parseInt(n.asText().trim()); }
        catch (NumberFormatException e) { return null; }
    }

    private int requireInt(JsonNode args, String name) {
        Integer i = optInt(args, name);
        if (i == null) throw new IllegalArgumentException("Missing required argument: " + name);
        return i;
    }

    private int optIntOr(JsonNode args, String name, int defaultValue) {
        Integer i = optInt(args, name);
        return i == null ? defaultValue : i;
    }

    private LocalDate optDate(JsonNode args, String name) {
        String s = optStr(args, name);
        if (s == null) return null;
        try { return LocalDate.parse(s); }
        catch (Exception e) { throw new IllegalArgumentException("Invalid date: " + s); }
    }
}
