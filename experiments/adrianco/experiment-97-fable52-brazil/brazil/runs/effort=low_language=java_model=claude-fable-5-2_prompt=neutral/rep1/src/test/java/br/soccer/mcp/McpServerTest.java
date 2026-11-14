package br.soccer.mcp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

@DisplayName("Feature: MCP protocol over stdio")
class McpServerTest {
    private static final ObjectMapper JSON = new ObjectMapper();
    private final McpServer server = new McpServer(TestData.TOOLS);

    private JsonNode rpc(String json) throws Exception {
        String out = server.handleLine(json);
        return out == null ? null : JSON.readTree(out);
    }

    private JsonNode call(String tool, String argsJson) throws Exception {
        ObjectNode req = JSON.createObjectNode();
        req.put("jsonrpc", "2.0");
        req.put("id", 7);
        req.put("method", "tools/call");
        ObjectNode p = req.putObject("params");
        p.put("name", tool);
        p.set("arguments", JSON.readTree(argsJson));
        JsonNode res = rpc(req.toString());
        assertEquals(7, res.get("id").asInt());
        return res.get("result");
    }

    private static String text(JsonNode result) {
        assertEquals("text", result.get("content").get(0).get("type").asText());
        return result.get("content").get(0).get("text").asText();
    }

    @Test
    @DisplayName("Scenario: initialize handshake")
    void initialize() throws Exception {
        JsonNode res = rpc("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\","
                + "\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1\"}}}");
        assertEquals("2.0", res.get("jsonrpc").asText());
        assertEquals("2024-11-05", res.get("result").get("protocolVersion").asText());
        assertEquals(McpServer.SERVER_NAME, res.get("result").get("serverInfo").get("name").asText());
        assertTrue(res.get("result").get("capabilities").has("tools"));
        // unknown protocol version -> server answers with one it supports
        JsonNode other = rpc("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"1999-01-01\"}}");
        assertEquals("2025-06-18", other.get("result").get("protocolVersion").asText());
    }

    @Test
    @DisplayName("Scenario: notifications get no response; ping does")
    void notificationsAndPing() throws Exception {
        assertNull(rpc("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}"));
        assertNull(rpc("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/cancelled\",\"params\":{}}"));
        JsonNode pong = rpc("{\"jsonrpc\":\"2.0\",\"id\":\"abc\",\"method\":\"ping\"}");
        assertEquals("abc", pong.get("id").asText());
        assertTrue(pong.get("result").isObject());
    }

    @Test
    @DisplayName("Scenario: tools/list publishes every tool with a JSON schema")
    void toolsList() throws Exception {
        JsonNode tools = rpc("{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/list\"}").get("result").get("tools");
        List<String> names = new ArrayList<>();
        for (JsonNode t : tools) {
            names.add(t.get("name").asText());
            assertFalse(t.get("description").asText().isBlank());
            assertEquals("object", t.get("inputSchema").get("type").asText());
            assertTrue(t.get("inputSchema").get("properties").isObject());
        }
        assertEquals(List.of("find_matches", "head_to_head", "team_stats", "team_profile", "team_rankings", "standings",
                "competition_bracket", "match_statistics", "compare_seasons", "biggest_wins", "derbies", "search_players",
                "player_details", "players_by_club", "dataset_info"), names);
    }

    @Test
    @DisplayName("Scenario: tools/call returns formatted text")
    void toolsCall() throws Exception {
        JsonNode r = call("find_matches", "{\"team\":\"Flamengo\",\"opponent\":\"Fluminense\",\"limit\":3}");
        assertFalse(r.get("isError").asBoolean());
        assertTrue(text(r).contains("Head-to-head in dataset"));
        assertTrue(text(call("standings", "{\"season\":\"2019\"}")).contains("1. Flamengo - 90 pts"), "numeric strings are accepted");
        assertTrue(text(call("dataset_info", "{}")).contains("fifa_data.csv: 18207 players"));
        assertTrue(text(call("find_matches", "{\"team\":\"Grêmio\",\"date_from\":\"01/01/2019\",\"date_to\":\"2019-12-31\","
                + "\"competition\":\"Libertadores\"}")).contains("Copa Libertadores 2019"));
    }

    @Test
    @DisplayName("Scenario: every tool answers with default-ish arguments")
    void everyToolRuns() throws Exception {
        String[][] calls = {
            {"find_matches", "{\"season\":2021,\"competition\":\"Serie B\"}"},
            {"head_to_head", "{\"team_a\":\"Grêmio\",\"team_b\":\"Internacional\"}"},
            {"team_stats", "{\"team\":\"Bahia\"}"}, {"team_profile", "{\"team\":\"Santos\"}"},
            {"team_rankings", "{}"}, {"standings", "{\"season\":2012}"},
            {"competition_bracket", "{\"season\":2021,\"include_group_stage\":true}"},
            {"match_statistics", "{}"}, {"compare_seasons", "{\"season_a\":2010,\"season_b\":2022}"},
            {"biggest_wins", "{\"team\":\"Santos\"}"}, {"derbies", "{}"}, {"search_players", "{\"position\":\"GK\",\"min_overall\":85}"},
            {"player_details", "{\"name\":\"Alisson\"}"}, {"players_by_club", "{}"}, {"dataset_info", "{}"},
        };
        for (String[] c : calls) {
            JsonNode r = call(c[0], c[1]);
            assertFalse(r.get("isError").asBoolean(), c[0] + ": " + text(r));
            assertFalse(text(r).isBlank(), c[0]);
        }
    }

    @Test
    @DisplayName("Scenario: bad tool arguments come back as tool errors the model can read")
    void toolErrors() throws Exception {
        JsonNode r = call("team_stats", "{\"team\":\"Nonexistent United\"}");
        assertTrue(r.get("isError").asBoolean());
        assertTrue(text(r).startsWith("Error: No team matching"));
        assertTrue(call("standings", "{\"season\":\"twenty\"}").get("isError").asBoolean());
        assertTrue(call("standings", "{}").get("isError").asBoolean());
        assertTrue(call("find_matches", "{\"date_from\":\"yesterday\"}").get("isError").asBoolean());
        assertTrue(call("find_matches", "{\"limit\":-1}").get("isError").asBoolean());
        assertTrue(call("search_players", "{\"brazilian_clubs_only\":\"maybe\"}").get("isError").asBoolean());
    }

    @Test
    @DisplayName("Scenario: protocol errors use JSON-RPC error codes")
    void protocolErrors() throws Exception {
        assertEquals(-32700, rpc("{not json").get("error").get("code").asInt());
        assertEquals(-32600, rpc("[1,2]").get("error").get("code").asInt());
        assertEquals(-32601, rpc("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"resources/list\"}").get("error").get("code").asInt());
        assertEquals(-32602, rpc("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"nope\"}}")
                .get("error").get("code").asInt());
        assertEquals(-32602, rpc("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{}}").get("error").get("code").asInt());
        assertEquals(-32602, rpc("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"dataset_info\","
                + "\"arguments\":[1]}}").get("error").get("code").asInt());
    }

    @Test
    @DisplayName("Scenario: a full stdio session writes one UTF-8 JSON line per request")
    void stdioSession() throws Exception {
        String input = "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}\n"
                + "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}\n\n"
                + "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"team_stats\",\"arguments\":"
                + "{\"team\":\"São Paulo\",\"season\":2019}}}\n";
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        server.serve(new ByteArrayInputStream(input.getBytes(StandardCharsets.UTF_8)), out);
        String[] lines = out.toString(StandardCharsets.UTF_8).split("\n");
        assertEquals(2, lines.length);
        assertEquals(1, JSON.readTree(lines[0]).get("id").asInt());
        assertTrue(text(JSON.readTree(lines[1]).get("result")).startsWith("São Paulo record"));
    }
}
