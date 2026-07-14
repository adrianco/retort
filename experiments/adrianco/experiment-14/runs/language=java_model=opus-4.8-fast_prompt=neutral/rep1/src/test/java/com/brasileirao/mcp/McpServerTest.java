/*
 * ============================================================================
 *  Brazilian Soccer MCP Server - Tests
 * ----------------------------------------------------------------------------
 *  File    : McpServerTest.java
 *  Purpose : Verify the MCP JSON-RPC protocol surface and tool dispatch.
 *  Context : Drives McpServer.handleMessage() and Tools.callTool() directly
 *            (no pipes) to confirm the handshake, tools/list, tools/call,
 *            notification handling and error envelopes behave per JSON-RPC 2.0,
 *            and that representative natural-language questions are answered.
 * ============================================================================
 */
package com.brasileirao.mcp;

import com.brasileirao.mcp.server.McpServer;
import com.brasileirao.mcp.server.Tools;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class McpServerTest {

    private static final ObjectMapper M = new ObjectMapper();

    private final Tools tools = new Tools(TestData.query());
    private final McpServer server = new McpServer(tools, "brazilian-soccer-mcp", "1.0.0");

    private JsonNode rpc(String json) {
        try {
            return server.handleMessage(M.readTree(json));
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Test
    void initializeReturnsProtocolAndServerInfo() {
        JsonNode r = rpc("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}");
        assertEquals("2.0", r.path("jsonrpc").asText());
        assertEquals(1, r.path("id").asInt());
        assertEquals("2024-11-05", r.path("result").path("protocolVersion").asText());
        assertEquals("brazilian-soccer-mcp", r.path("result").path("serverInfo").path("name").asText());
        assertTrue(r.path("result").path("capabilities").has("tools"));
    }

    @Test
    void notificationsGetNoResponse() {
        assertNull(rpc("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}"));
    }

    @Test
    void toolsListAdvertisesAllTools() {
        JsonNode r = rpc("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}");
        JsonNode toolsArr = r.path("result").path("tools");
        assertTrue(toolsArr.isArray());
        assertEquals(9, toolsArr.size());
        boolean hasStandings = false;
        for (JsonNode t : toolsArr) {
            assertTrue(t.has("name"));
            assertTrue(t.has("description"));
            assertEquals("object", t.path("inputSchema").path("type").asText());
            if (t.path("name").asText().equals("standings")) {
                hasStandings = true;
            }
        }
        assertTrue(hasStandings);
    }

    @Test
    void toolsCallStandingsReturnsText() {
        String req = "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{"
                + "\"name\":\"standings\",\"arguments\":{\"competition\":\"Brasileirão Série A\",\"season\":2019}}}";
        JsonNode r = rpc(req);
        JsonNode content = r.path("result").path("content");
        assertTrue(content.isArray());
        String text = content.get(0).path("text").asText();
        assertEquals("text", content.get(0).path("type").asText());
        assertTrue(text.contains("Flamengo"));
        assertTrue(text.contains("90 pts"));
        assertFalse(r.path("result").path("isError").asBoolean());
    }

    @Test
    void unknownMethodYieldsError() {
        JsonNode r = rpc("{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"does/not/exist\"}");
        assertEquals(-32601, r.path("error").path("code").asInt());
    }

    @Test
    void missingRequiredArgIsToolError() {
        String req = "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{"
                + "\"name\":\"head_to_head\",\"arguments\":{\"team_a\":\"Flamengo\"}}}";
        JsonNode r = rpc(req);
        assertTrue(r.path("result").path("isError").asBoolean());
        assertTrue(r.path("result").path("content").get(0).path("text").asText().contains("team_b"));
    }

    @Test
    void naturalLanguageQuestionsAnswered() {
        // "Who is Gabriel Jesus?" -> player search by name
        assertTrue(tools.callTool("search_players", obj("{\"name\":\"Gabriel Jesus\"}"))
                .toLowerCase().contains("gabriel jesus"));
        // "What competitions are available?"
        assertTrue(tools.callTool("list_competitions", null).contains("Copa do Brasil"));
        // "Average goals per match in the Brasileirão"
        assertTrue(tools.callTool("match_statistics", obj("{\"competition\":\"Brasileirão\"}"))
                .contains("Average goals per match"));
    }

    private ObjectNode obj(String json) {
        try {
            return (ObjectNode) M.readTree(json);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Test
    void resultEnvelopeAlwaysWellFormed() {
        JsonNode r = rpc("{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"ping\"}");
        assertNotNull(r);
        assertEquals("2.0", r.path("jsonrpc").asText());
        assertTrue(r.has("result"));
    }
}
