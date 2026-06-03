/*
 * ============================================================================
 * McpServerTest - BDD scenarios for the MCP JSON-RPC protocol layer
 * ============================================================================
 * Context:
 *   Drives the server through the protocol surface an MCP client uses:
 *   initialize handshake, tools/list discovery, tools/call invocation, handling
 *   of notifications (no reply), unknown methods and bad arguments. Confirms the
 *   wiring from JSON request to rendered text answer end-to-end.
 * ============================================================================
 */
package com.brasilsoccer.mcp;

import com.brasilsoccer.mcp.mcp.McpServer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: MCP protocol server")
class McpServerTest {

    private final ObjectMapper mapper = new ObjectMapper();
    private final McpServer server = new McpServer(TestData.kb());

    private JsonNode request(String json) throws Exception {
        return mapper.readTree(json);
    }

    @Test
    @DisplayName("Given an initialize request, When handled, Then capabilities are advertised")
    void initialize() throws Exception {
        ObjectNode resp = server.handleRequest(request(
                "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}"));
        assertEquals("2.0", resp.get("jsonrpc").asText());
        assertEquals(1, resp.get("id").asInt());
        JsonNode result = resp.get("result");
        assertTrue(result.has("protocolVersion"));
        assertEquals("brazilian-soccer-mcp", result.get("serverInfo").get("name").asText());
        assertTrue(result.get("capabilities").has("tools"));
    }

    @Test
    @DisplayName("Given tools/list, When handled, Then all eight tools are described")
    void toolsList() throws Exception {
        ObjectNode resp = server.handleRequest(request(
                "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}"));
        JsonNode tools = resp.get("result").get("tools");
        assertEquals(8, tools.size());
        for (JsonNode t : tools) {
            assertTrue(t.has("name"));
            assertTrue(t.has("description"));
            assertEquals("object", t.get("inputSchema").get("type").asText());
        }
    }

    @Test
    @DisplayName("Given a notification (no id), When handled, Then there is no reply")
    void notificationsAreSilent() throws Exception {
        ObjectNode resp = server.handleRequest(request(
                "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}"));
        assertNull(resp, "notifications must not be answered");
    }

    @Test
    @DisplayName("Given tools/call search_matches, When invoked, Then text content is returned")
    void callSearchMatches() throws Exception {
        ObjectNode resp = server.handleRequest(request(
                "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":"
                        + "{\"name\":\"search_matches\",\"arguments\":"
                        + "{\"team\":\"Flamengo\",\"opponent\":\"Fluminense\",\"limit\":5}}}"));
        JsonNode result = resp.get("result");
        assertFalse(result.get("isError").asBoolean());
        String text = result.get("content").get(0).get("text").asText();
        assertTrue(text.toLowerCase().contains("flamengo"));
        assertTrue(text.toLowerCase().contains("head-to-head"));
    }

    @Test
    @DisplayName("Given tools/call standings, When invoked, Then a league table is rendered")
    void callStandings() throws Exception {
        ObjectNode resp = server.handleRequest(request(
                "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":"
                        + "{\"name\":\"standings\",\"arguments\":{\"competition\":\"Brasileirao\",\"season\":2019}}}"));
        String text = resp.get("result").get("content").get(0).get("text").asText();
        assertTrue(text.contains("Standings"));
        assertTrue(text.toLowerCase().contains("flamengo"));
    }

    @Test
    @DisplayName("Given an unknown method, When handled, Then a JSON-RPC error is returned")
    void unknownMethod() throws Exception {
        ObjectNode resp = server.handleRequest(request(
                "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"does/not/exist\"}"));
        assertTrue(resp.has("error"));
        assertEquals(-32601, resp.get("error").get("code").asInt());
    }

    @Test
    @DisplayName("Given a tool call missing required args, When invoked, Then an isError result")
    void missingArgsIsToolError() throws Exception {
        ObjectNode resp = server.handleRequest(request(
                "{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"tools/call\",\"params\":"
                        + "{\"name\":\"head_to_head\",\"arguments\":{\"team1\":\"Santos\"}}}"));
        JsonNode result = resp.get("result");
        assertTrue(result.get("isError").asBoolean());
        assertTrue(result.get("content").get(0).get("text").asText().toLowerCase().contains("team2"));
    }

    @Test
    @DisplayName("Given search_players for Brazilians, When invoked via protocol, Then names appear")
    void callSearchPlayers() throws Exception {
        ObjectNode resp = server.handleRequest(request(
                "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"tools/call\",\"params\":"
                        + "{\"name\":\"search_players\",\"arguments\":{\"nationality\":\"Brazil\",\"limit\":5}}}"));
        String text = resp.get("result").get("content").get(0).get("text").asText();
        assertTrue(text.contains("Overall"));
    }
}
