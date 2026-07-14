/*
 * ===========================================================================
 * Context: Brazilian Soccer MCP Server
 * File:    test/server/McpServerTest.java
 * Purpose: BDD tests for the MCP/JSON-RPC protocol layer: the initialize
 *          handshake, tools/list discovery and tools/call execution, driving
 *          the server through single request lines (the same path the stdio
 *          loop uses).
 * ===========================================================================
 */
package com.brazilsoccer.mcp.server;

import com.brazilsoccer.mcp.TestData;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: MCP protocol server")
class McpServerTest {

    private final ObjectMapper mapper = new ObjectMapper();
    private final McpServer server =
            new McpServer(new SoccerTools(TestData.queries()).tools());

    private JsonNode call(String request) throws Exception {
        return mapper.readTree(server.handle(request));
    }

    @Test
    @DisplayName("Scenario: initialize handshake advertises tools capability")
    void givenInitialize_whenHandled_thenServerInfoReturned() throws Exception {
        JsonNode resp = call("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\","
                + "\"params\":{\"protocolVersion\":\"2024-11-05\"}}");
        assertEquals("2.0", resp.get("jsonrpc").asText());
        assertEquals(1, resp.get("id").asInt());
        assertEquals(McpServer.SERVER_NAME,
                resp.get("result").get("serverInfo").get("name").asText());
        assertTrue(resp.get("result").get("capabilities").has("tools"));
    }

    @Test
    @DisplayName("Scenario: initialized notification yields no response")
    void givenInitializedNotification_whenHandled_thenNoReply() {
        assertNull(server.handle(
                "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}"));
    }

    @Test
    @DisplayName("Scenario: tools/list returns the catalogue with schemas")
    void givenToolsList_whenHandled_thenToolsHaveNameAndSchema() throws Exception {
        JsonNode resp = call("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}");
        JsonNode tools = resp.get("result").get("tools");
        assertTrue(tools.isArray() && tools.size() >= 10);
        JsonNode first = tools.get(0);
        assertTrue(first.has("name"));
        assertTrue(first.has("description"));
        assertEquals("object", first.get("inputSchema").get("type").asText());
    }

    @Test
    @DisplayName("Scenario: tools/call runs head_to_head and returns text content")
    void givenToolCall_whenHandled_thenTextContentReturned() throws Exception {
        String req = "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\","
                + "\"params\":{\"name\":\"head_to_head\","
                + "\"arguments\":{\"team_a\":\"Flamengo\",\"team_b\":\"Fluminense\"}}}";
        JsonNode resp = call(req);
        JsonNode result = resp.get("result");
        assertFalse(result.get("isError").asBoolean());
        String text = result.get("content").get(0).get("text").asText();
        assertTrue(text.toLowerCase().contains("head-to-head"));
        assertTrue(text.contains("Matches:"));
    }

    @Test
    @DisplayName("Scenario: tools/call for standings returns a champion line")
    void givenStandingsCall_whenHandled_thenChampionShown() throws Exception {
        String req = "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\","
                + "\"params\":{\"name\":\"standings\","
                + "\"arguments\":{\"season\":2019,\"competition\":\"Brasileirão\"}}}";
        JsonNode resp = call(req);
        String text = resp.get("result").get("content").get(0).get("text").asText();
        assertTrue(text.contains("Champion"));
        assertTrue(text.toLowerCase().contains("flamengo"));
    }

    @Test
    @DisplayName("Scenario: unknown tool reports a tool error, not a crash")
    void givenUnknownTool_whenCalled_thenErrorResult() throws Exception {
        String req = "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\","
                + "\"params\":{\"name\":\"does_not_exist\",\"arguments\":{}}}";
        JsonNode resp = call(req);
        assertTrue(resp.get("result").get("isError").asBoolean());
    }

    @Test
    @DisplayName("Scenario: unknown method returns JSON-RPC method-not-found")
    void givenUnknownMethod_whenHandled_thenMethodNotFound() throws Exception {
        JsonNode resp = call("{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"no/such\"}");
        assertEquals(-32601, resp.get("error").get("code").asInt());
    }
}
