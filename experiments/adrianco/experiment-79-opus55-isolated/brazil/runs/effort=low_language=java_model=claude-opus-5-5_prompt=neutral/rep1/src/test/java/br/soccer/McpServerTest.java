package br.soccer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("Feature: MCP protocol")
@SuppressWarnings("unchecked")
class McpServerTest {
    private final McpServer server = new McpServer(TestData.QUERIES);

    private Map<String, Object> rpc(String json) {
        return (Map<String, Object>) Json.parse(server.handle(json));
    }

    /** Calls a tool and returns its result object. */
    private Map<String, Object> call(String tool, Map<String, Object> args) {
        Map<String, Object> params = new LinkedHashMap<>();
        params.put("name", tool);
        params.put("arguments", args);
        Map<String, Object> req = new LinkedHashMap<>();
        req.put("jsonrpc", "2.0");
        req.put("id", 7);
        req.put("method", "tools/call");
        req.put("params", params);
        Map<String, Object> resp = rpc(Json.write(req));
        assertEquals(7L, resp.get("id"));
        assertNotNull(resp.get("result"), () -> "no result: " + resp);
        return (Map<String, Object>) resp.get("result");
    }

    private static String text(Map<String, Object> result) {
        return (String) ((Map<String, Object>) ((List<Object>) result.get("content")).get(0)).get("text");
    }

    @Test
    @DisplayName("Scenario: initialize handshake")
    void initialize() {
        Map<String, Object> resp = rpc("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":"
                + "{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"t\",\"version\":\"1\"}}}");
        Map<String, Object> result = (Map<String, Object>) resp.get("result");
        assertEquals("2024-11-05", result.get("protocolVersion"));
        assertTrue(((Map<String, Object>) result.get("capabilities")).containsKey("tools"));
        assertEquals("brazilian-soccer-mcp", ((Map<String, Object>) result.get("serverInfo")).get("name"));
        assertNull(server.handle("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}"));
    }

    @Test
    @DisplayName("Scenario: tools/list advertises every tool with an input schema")
    void toolsList() {
        Map<String, Object> resp = rpc("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}");
        List<Object> tools = (List<Object>) ((Map<String, Object>) resp.get("result")).get("tools");
        assertEquals(15, tools.size());
        for (Object o : tools) {
            Map<String, Object> t = (Map<String, Object>) o;
            assertFalse(((String) t.get("description")).isEmpty());
            assertEquals("object", ((Map<String, Object>) t.get("inputSchema")).get("type"));
        }
    }

    @Test
    @DisplayName("Scenario: errors follow JSON-RPC and MCP conventions")
    void errors() {
        assertEquals(-32700L, ((Map<String, Object>) rpc("{not json").get("error")).get("code"));
        assertEquals(-32601L, ((Map<String, Object>) rpc("{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"nope\"}")
                .get("error")).get("code"));
        assertEquals(-32602L, ((Map<String, Object>) rpc("{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\","
                + "\"params\":{\"name\":\"nope\"}}").get("error")).get("code"));
        // Bad tool input is reported in-band with isError so the model can retry.
        Map<String, Object> r = call("team_stats", Map.of("team", "Nonexistent United"));
        assertEquals(true, r.get("isError"));
        assertTrue(text(r).contains("No team found"));
        r = call("standings", Map.of("season", "twenty"));
        assertEquals(true, r.get("isError"));
        r = call("search_matches", Map.of("date_from", "yesterday"));
        assertEquals(true, r.get("isError"));
    }

    @Test
    @DisplayName("Scenario: serve() answers newline-delimited requests over streams in UTF-8")
    void stdio() throws Exception {
        String input = "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}\n\n"
                + "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}\n"
                + "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"team_stats\","
                + "\"arguments\":{\"team\":\"Grêmio\",\"season\":2019}}}\n";
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        server.serve(new ByteArrayInputStream(input.getBytes(StandardCharsets.UTF_8)),
                new PrintStream(out, true, StandardCharsets.UTF_8));
        String[] lines = out.toString(StandardCharsets.UTF_8).strip().split("\n");
        assertEquals(2, lines.length);
        assertTrue(lines[1].contains("Grêmio record (2019 all competitions)"), lines[1]);
    }

    /** The specification's sample questions, each mapped to the tool call an LLM would make. */
    @Test
    @DisplayName("Scenario: at least 20 sample questions are answerable through tools")
    void sampleQuestions() {
        Object[][] cases = {
            {"Show me all Flamengo vs Fluminense matches", "search_matches",
                Map.of("team", "Flamengo", "opponent", "Fluminense"), "Head-to-head in dataset"},
            {"What matches did Palmeiras play in 2023?", "search_matches",
                Map.of("team", "Palmeiras", "season", 2023), "Palmeiras"},
            {"Find all Copa do Brasil finals", "search_matches",
                Map.of("competition", "Copa do Brasil", "stage", "final"), "final"},
            {"What is Corinthians' home record in 2022?", "team_stats",
                Map.of("team", "Corinthians", "season", 2022, "venue", "home", "competition", "Brasileirão"), "Win rate"},
            {"Which team scored the most goals in Serie A 2023?", "team_rankings",
                Map.of("metric", "goals_for", "competition", "Serie A", "season", 2023), "1. "},
            {"Compare Palmeiras and Santos head-to-head", "head_to_head",
                Map.of("team_a", "Palmeiras", "team_b", "Santos"), "Palmeiras vs Santos"},
            {"Find all Brazilian players in the dataset", "search_players",
                Map.of("nationality", "Brazil"), "Neymar Jr"},
            {"Who are the highest-rated players at Santos?", "search_players",
                Map.of("club", "Santos", "limit", 5), "Club: Santos"},
            {"Show me all forwards from Grêmio", "search_players",
                Map.of("club", "Grêmio", "position", "forward"), "Club: Grêmio"},
            {"Who won the 2019 Brasileirão?", "standings", Map.of("season", 2019), "1. Flamengo - 90 pts"},
            {"Show the 2018 Copa Libertadores bracket", "knockout_stages",
                Map.of("season", 2018, "competition", "Libertadores"), "Semifinals"},
            {"Which teams were relegated in 2020?", "standings", Map.of("season", 2020), "Relegated"},
            {"What's the average goals per match in the Brasileirão?", "match_statistics",
                Map.of("competition", "Brasileirão"), "Average goals per match"},
            {"Which team has the best away record?", "team_rankings",
                Map.of("venue", "away", "competition", "Serie A"), "away matches"},
            {"Show me the biggest wins in the dataset", "biggest_wins", Map.of(), "Biggest victories"},
            {"When did Flamengo last play Corinthians?", "search_matches",
                Map.of("team", "Flamengo", "opponent", "Corinthians", "limit", 1), "Corinthians"},
            {"Who is Neymar?", "player_details", Map.of("name", "Neymar"), "Overall: 92"},
            {"Which players play for Fluminense?", "search_players", Map.of("club", "Fluminense"), "Club: Fluminense"},
            {"Show me all derbies in 2023", "derbies", Map.of("season", 2023), "Fla-Flu"},
            {"What competitions has Palmeiras played in?", "team_stats", Map.of("team", "Palmeiras"), "By competition"},
            {"Which team has the best home record?", "team_rankings",
                Map.of("venue", "home", "competition", "Serie A"), "home matches"},
            {"Who are the top Brazilian players?", "search_players",
                Map.of("nationality", "Brazil", "limit", 10), "1. Neymar Jr"},
            {"Compare the 2018 and 2019 seasons", "compare_seasons",
                Map.of("season_a", 2018, "season_b", 2019), "Season comparison"},
            {"Brazilian players at Brazilian clubs", "players_by_club", Map.of(), "avg rating"},
            {"Tell me about Santos and its squad", "club_profile", Map.of("team", "Santos"), "FIFA squad for Santos"},
            {"What data is available?", "dataset_info", Map.of(), "fifa_data.csv"},
        };
        assertTrue(cases.length >= 20);
        for (Object[] c : cases) {
            long t0 = System.nanoTime();
            Map<String, Object> r = call((String) c[1], (Map<String, Object>) c[2]);
            long ms = (System.nanoTime() - t0) / 1_000_000;
            assertEquals(false, r.get("isError"), c[0] + " -> " + text(r));
            assertTrue(text(r).contains((String) c[3]), c[0] + " -> " + text(r));
            assertTrue(ms < 2000, c[0] + " took " + ms + " ms");
        }
    }
}
