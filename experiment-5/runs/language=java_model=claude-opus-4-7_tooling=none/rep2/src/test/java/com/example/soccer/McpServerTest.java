package com.example.soccer;

import com.example.soccer.data.DataStore;
import com.example.soccer.query.QueryService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.PrintWriter;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@DisplayName("Feature: MCP server protocol over stdio")
class McpServerTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private McpServer server;

    @BeforeAll
    void start() throws Exception {
        DataStore store = TestData.load();
        server = new McpServer(new QueryService(store));
    }

    private String runOne(String requestJson) throws Exception {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        PrintWriter pw = new PrintWriter(baos, true, StandardCharsets.UTF_8);
        server.run(new BufferedReader(new StringReader(requestJson + "\n")), pw);
        pw.flush();
        return baos.toString(StandardCharsets.UTF_8).trim();
    }

    @Test
    @DisplayName("Scenario: Given an initialize request, server returns protocol version and tools capability")
    void scenario_initialize() throws Exception {
        String req = "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}";
        JsonNode resp = MAPPER.readTree(runOne(req));
        assertEquals(1, resp.get("id").asInt());
        assertEquals(McpServer.PROTOCOL_VERSION, resp.get("result").get("protocolVersion").asText());
        assertTrue(resp.get("result").get("capabilities").has("tools"));
    }

    @Test
    @DisplayName("Scenario: Given tools/list, server returns the documented tool catalog")
    void scenario_toolsList() throws Exception {
        String req = "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}";
        JsonNode resp = MAPPER.readTree(runOne(req));
        JsonNode tools = resp.get("result").get("tools");
        assertNotNull(tools);
        assertTrue(tools.isArray() && tools.size() >= 7);
        // Verify the search_matches tool exists with expected schema fields
        boolean found = false;
        for (JsonNode t : tools) {
            if ("search_matches".equals(t.get("name").asText())) {
                found = true;
                assertTrue(t.get("inputSchema").get("properties").has("team_a"));
            }
        }
        assertTrue(found, "search_matches tool should be listed");
    }

    @Test
    @DisplayName("Scenario: Given tools/call search_matches, server returns formatted match text")
    void scenario_callSearchMatches() throws Exception {
        String req = "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\","
                + "\"params\":{\"name\":\"search_matches\",\"arguments\":"
                + "{\"team_a\":\"Flamengo\",\"team_b\":\"Fluminense\",\"limit\":5}}}";
        JsonNode resp = MAPPER.readTree(runOne(req));
        assertFalse(resp.has("error"));
        String text = resp.get("result").get("content").get(0).get("text").asText();
        assertTrue(text.toLowerCase().contains("flamengo") || text.toLowerCase().contains("fluminense"),
                "expected match listing, got: " + text);
    }

    @Test
    @DisplayName("Scenario: Given tools/call standings, server returns a Brasileirao table")
    void scenario_callStandings() throws Exception {
        String req = "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\","
                + "\"params\":{\"name\":\"standings\",\"arguments\":{\"season\":2019,\"limit\":5}}}";
        JsonNode resp = MAPPER.readTree(runOne(req));
        assertFalse(resp.has("error"));
        String text = resp.get("result").get("content").get(0).get("text").asText();
        assertTrue(text.contains("pts"));
        assertTrue(text.contains("1."));
    }

    @Test
    @DisplayName("Scenario: Given an unknown method, server returns JSON-RPC method-not-found")
    void scenario_unknownMethod() throws Exception {
        String req = "{\"jsonrpc\":\"2.0\",\"id\":99,\"method\":\"does/not/exist\"}";
        JsonNode resp = MAPPER.readTree(runOne(req));
        assertEquals(-32601, resp.get("error").get("code").asInt());
    }

    @Test
    @DisplayName("Scenario: Given a notification, server emits no response line")
    void scenario_notification() throws Exception {
        String req = "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}";
        String out = runOne(req);
        assertTrue(out.isEmpty(), "notifications should not produce a response, got: " + out);
    }

    @Test
    @DisplayName("Scenario: Given tools/call dataset_info, server reports loaded counts")
    void scenario_datasetInfo() throws Exception {
        String req = "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\","
                + "\"params\":{\"name\":\"dataset_info\",\"arguments\":{}}}";
        JsonNode resp = MAPPER.readTree(runOne(req));
        String text = resp.get("result").get("content").get(0).get("text").asText();
        assertTrue(text.contains("Total matches:"));
        assertTrue(text.contains("Total players:"));
    }
}
