/*
 * ============================================================================
 * McpServerTest.java
 * ============================================================================
 * Context:
 *   BDD (Given/When/Then) coverage of the MCP protocol surface: the initialize
 *   handshake, tools/list catalogue, tools/call dispatch and error handling,
 *   plus an end-to-end stdio round-trip. Exercises SoccerTools formatting via
 *   the JSON-RPC layer so the whole server is validated together.
 * ============================================================================
 */
package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.server.McpServer;
import com.brazilsoccer.mcp.server.SoccerTools;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

class McpServerTest {

    private final ObjectMapper json = new ObjectMapper();

    private McpServer server() {
        return new McpServer(new SoccerTools(TestData.store()));
    }

    @Test
    @DisplayName("Given an initialize request, When handled, Then protocol version and capabilities are returned")
    void initializeHandshake() throws Exception {
        JsonNode req = json.readTree(
                "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}");

        ObjectNode resp = server().handle(req);

        assertEquals(McpServer.PROTOCOL_VERSION, resp.path("result").path("protocolVersion").asText());
        assertTrue(resp.path("result").path("capabilities").has("tools"));
        assertEquals(McpServer.SERVER_NAME, resp.path("result").path("serverInfo").path("name").asText());
    }

    @Test
    @DisplayName("Given a tools/list request, When handled, Then all seven tools are advertised with schemas")
    void toolsListed() throws Exception {
        JsonNode req = json.readTree(
                "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}");

        ObjectNode resp = server().handle(req);

        JsonNode tools = resp.path("result").path("tools");
        assertTrue(tools.isArray());
        Set<String> names = new HashSet<>();
        for (JsonNode t : tools) {
            names.add(t.path("name").asText());
            assertTrue(t.path("inputSchema").path("type").asText().equals("object"),
                    "each tool must declare an object input schema");
        }
        assertTrue(names.containsAll(Set.of(
                "search_matches", "team_record", "head_to_head", "search_players",
                "competition_standings", "league_stats", "top_scoring_teams")));
    }

    @Test
    @DisplayName("Given a tools/call for standings, When handled, Then the text mentions the champion")
    void toolsCallStandings() throws Exception {
        JsonNode req = json.readTree(
                "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":"
                        + "{\"name\":\"competition_standings\","
                        + "\"arguments\":{\"competition\":\"Brasileirão\",\"season\":2019}}}");

        ObjectNode resp = server().handle(req);

        JsonNode result = resp.path("result");
        assertFalse(result.path("isError").asBoolean());
        String text = result.path("content").get(0).path("text").asText();
        assertTrue(text.contains("Champion"), "standings output should label the champion");
        assertTrue(text.toLowerCase().contains("flamengo"));
    }

    @Test
    @DisplayName("Given a tools/call with a missing required arg, When handled, Then an isError result is returned")
    void toolsCallMissingArg() throws Exception {
        JsonNode req = json.readTree(
                "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":"
                        + "{\"name\":\"team_record\",\"arguments\":{}}}");

        ObjectNode resp = server().handle(req);

        assertTrue(resp.path("result").path("isError").asBoolean(),
                "missing required 'team' should produce an isError result");
    }

    @Test
    @DisplayName("Given an unknown method, When handled, Then a JSON-RPC method-not-found error is returned")
    void unknownMethod() throws Exception {
        JsonNode req = json.readTree(
                "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"does/notExist\"}");

        ObjectNode resp = server().handle(req);

        assertEquals(-32601, resp.path("error").path("code").asInt());
    }

    @Test
    @DisplayName("Given a notification, When handled, Then no response is produced")
    void notificationProducesNoResponse() throws Exception {
        JsonNode req = json.readTree(
                "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}");

        ObjectNode resp = server().handle(req);

        assertNull(resp, "notifications must not produce a response");
    }

    @Test
    @DisplayName("Given a stdio stream of requests, When served, Then a JSON response line is emitted per request")
    void stdioRoundTrip() throws Exception {
        String input =
                "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}\n"
                        + "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":"
                        + "{\"name\":\"search_players\",\"arguments\":{\"name\":\"Neymar\"}}}\n";
        ByteArrayInputStream in = new ByteArrayInputStream(input.getBytes(StandardCharsets.UTF_8));
        ByteArrayOutputStream out = new ByteArrayOutputStream();

        server().serve(in, out);

        String[] lines = out.toString(StandardCharsets.UTF_8).trim().split("\n");
        assertEquals(2, lines.length, "expected one response line per request");
        JsonNode second = json.readTree(lines[1]);
        assertTrue(second.path("result").path("content").get(0).path("text").asText().contains("Neymar"));
    }
}
