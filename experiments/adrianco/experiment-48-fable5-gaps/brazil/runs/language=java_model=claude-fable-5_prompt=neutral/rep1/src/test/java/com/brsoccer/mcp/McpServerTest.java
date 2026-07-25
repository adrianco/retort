package com.brsoccer.mcp;

import com.brsoccer.mcp.server.McpServer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** End-to-end MCP protocol tests over an in-memory stdio transport. */
class McpServerTest {

    private final ObjectMapper om = new ObjectMapper();

    private List<JsonNode> roundTrip(String... requests) throws Exception {
        String input = String.join("\n", requests) + "\n";
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        McpServer server = new McpServer(TestData.tools(),
            new ByteArrayInputStream(input.getBytes(StandardCharsets.UTF_8)), out);
        server.run();
        List<JsonNode> responses = new ArrayList<>();
        for (String line : out.toString(StandardCharsets.UTF_8).split("\n")) {
            if (!line.isBlank()) responses.add(om.readTree(line));
        }
        return responses;
    }

    @Test
    void initializeHandshake() throws Exception {
        var rs = roundTrip(
            "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"0\"}}}",
            "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}");
        assertEquals(1, rs.size(), "notification must not get a response");
        JsonNode r = rs.get(0).get("result");
        assertEquals("2024-11-05", r.get("protocolVersion").asText());
        assertEquals("brazilian-soccer-mcp", r.get("serverInfo").get("name").asText());
        assertNotNull(r.get("capabilities").get("tools"));
    }

    @Test
    void toolsListExposesAllTools() throws Exception {
        var rs = roundTrip("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}");
        JsonNode tools = rs.get(0).get("result").get("tools");
        assertEquals(9, tools.size());
        List<String> names = new ArrayList<>();
        tools.forEach(t -> {
            names.add(t.get("name").asText());
            assertNotNull(t.get("description"));
            assertEquals("object", t.get("inputSchema").get("type").asText());
        });
        assertTrue(names.containsAll(List.of("search_matches", "head_to_head", "team_stats",
            "league_standings", "search_players", "player_info", "competition_stats",
            "team_rankings", "list_competitions")));
    }

    @Test
    void toolsCallReturnsTextContent() throws Exception {
        var rs = roundTrip(
            "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"head_to_head\",\"arguments\":{\"team1\":\"Flamengo\",\"team2\":\"Fluminense\"}}}");
        JsonNode result = rs.get(0).get("result");
        assertFalse(result.get("isError").asBoolean());
        JsonNode content = result.get("content").get(0);
        assertEquals("text", content.get("type").asText());
        String text = content.get("text").asText();
        assertTrue(text.contains("Flamengo") && text.contains("Fluminense"));
        assertTrue(text.contains("wins"));
    }

    @Test
    void unknownToolIsAJsonRpcError() throws Exception {
        var rs = roundTrip(
            "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"no_such_tool\",\"arguments\":{}}}");
        assertEquals(-32602, rs.get(0).get("error").get("code").asInt());
    }

    @Test
    void missingRequiredArgumentIsAToolError() throws Exception {
        var rs = roundTrip(
            "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"head_to_head\",\"arguments\":{\"team1\":\"Flamengo\"}}}");
        JsonNode result = rs.get(0).get("result");
        assertTrue(result.get("isError").asBoolean());
        assertTrue(result.get("content").get(0).get("text").asText().contains("team2"));
    }

    @Test
    void unknownMethodAndParseErrors() throws Exception {
        var rs = roundTrip(
            "{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"bogus/method\"}",
            "this is not json",
            "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"ping\"}");
        assertEquals(3, rs.size());
        assertEquals(-32601, rs.get(0).get("error").get("code").asInt());
        assertEquals(-32700, rs.get(1).get("error").get("code").asInt());
        assertNotNull(rs.get(2).get("result"));
    }

    @Test
    void simpleLookupsRespondQuickly() throws Exception {
        // Success criterion: simple lookups < 2s, aggregates < 5s (data already loaded).
        long t0 = System.nanoTime();
        TestData.tools().call("search_matches", om.readTree("{\"team\":\"Flamengo\",\"opponent\":\"Corinthians\"}"));
        long simpleMs = (System.nanoTime() - t0) / 1_000_000;
        t0 = System.nanoTime();
        TestData.tools().call("league_standings", om.readTree("{\"season\":2019}"));
        TestData.tools().call("competition_stats", om.readTree("{\"competition\":\"Brasileirão\"}"));
        long aggMs = (System.nanoTime() - t0) / 1_000_000;
        assertTrue(simpleMs < 2000, "simple lookup took " + simpleMs + " ms");
        assertTrue(aggMs < 5000, "aggregate queries took " + aggMs + " ms");
    }
}
