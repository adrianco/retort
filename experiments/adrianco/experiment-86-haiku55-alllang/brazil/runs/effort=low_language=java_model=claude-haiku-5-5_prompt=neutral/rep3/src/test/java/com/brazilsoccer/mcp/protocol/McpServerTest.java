/*
 * Context block: Given/When/Then tests for the MCP JSON-RPC layer. Drives the server with raw
 * request lines against a small fixture database, checking the handshake, tool listing,
 * tool results, tool errors, and notification handling.
 */
package com.brazilsoccer.mcp.protocol;

import com.brazilsoccer.mcp.data.Competition;
import com.brazilsoccer.mcp.data.Match;
import com.brazilsoccer.mcp.data.SoccerDatabase;
import com.brazilsoccer.mcp.data.TeamName;
import com.brazilsoccer.mcp.tools.SoccerTools;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class McpServerTest {

    private final ObjectMapper mapper = new ObjectMapper();
    private McpServer server;

    @BeforeEach
    void setUp() {
        Match flaFlu = new Match(LocalDate.parse("2023-09-03"), Competition.BRASILEIRAO, 2023, "22",
                TeamName.parse("Flamengo-RJ"), TeamName.parse("Fluminense-RJ"), 2, 1);
        SoccerDatabase db = new SoccerDatabase(List.of(flaFlu), List.of());
        server = new McpServer(new SoccerTools(db, mapper), mapper);
    }

    private JsonNode call(String line) throws Exception {
        Optional<String> response = server.handleLine(line);
        assertTrue(response.isPresent(), "expected a response for: " + line);
        return mapper.readTree(response.get());
    }

    private String toolText(JsonNode response) {
        return response.at("/result/content/0/text").asText();
    }

    @Test
    @DisplayName("Given an initialize request, when handled, then the server reports tools capability and its name")
    void initialize() throws Exception {
        JsonNode r = call("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\"}}");

        assertEquals(1, r.get("id").asInt());
        assertEquals("2025-06-18", r.at("/result/protocolVersion").asText());
        assertTrue(r.at("/result/capabilities/tools").isObject());
        assertEquals("brazilian-soccer-mcp", r.at("/result/serverInfo/name").asText());
    }

    @Test
    @DisplayName("Given a notification, when received, then no response is written")
    void notificationGetsNoReply() {
        assertFalse(server.handleLine("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}").isPresent());
    }

    @Test
    @DisplayName("Given tools/list, when handled, then all six Brazilian soccer tools are described with input schemas")
    void toolList() throws Exception {
        JsonNode r = call("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}");

        List<String> names = new java.util.ArrayList<>();
        r.at("/result/tools").forEach(t -> names.add(t.get("name").asText()));
        assertEquals(List.of("search_matches", "team_stats", "head_to_head", "search_players",
                "competition_standings", "match_statistics"), names);
        assertEquals("object", r.at("/result/tools/0/inputSchema/type").asText());
    }

    @Test
    @DisplayName("Given a match search, when called, then the tool result contains the formatted match")
    void searchMatchesCall() throws Exception {
        JsonNode r = call("{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":"
                + "{\"name\":\"search_matches\",\"arguments\":{\"team\":\"Flamengo\",\"opponent\":\"Fluminense\"}}}");

        assertFalse(r.at("/result/isError").asBoolean());
        assertTrue(toolText(r).contains("2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A 2023, Round 22)"),
                toolText(r));
        assertTrue(toolText(r).contains("Head-to-head in dataset: Flamengo 1 wins, 0 draws, Fluminense 0 wins"),
                toolText(r));
    }

    @Test
    @DisplayName("Given a team record request, when called, then the record is formatted with the win rate")
    void teamStatsCall() throws Exception {
        JsonNode r = call("{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":"
                + "{\"name\":\"team_stats\",\"arguments\":{\"team\":\"Flamengo\",\"season\":2023}}}");

        assertTrue(toolText(r).contains("- Win rate: 100.0%"), toolText(r));
    }

    @Test
    @DisplayName("Given an unknown competition, when a tool is called, then the result is a tool error not a protocol error")
    void badArgumentIsToolError() throws Exception {
        JsonNode r = call("{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":"
                + "{\"name\":\"search_matches\",\"arguments\":{\"competition\":\"premier league\"}}}");

        assertTrue(r.at("/result/isError").asBoolean());
        assertTrue(toolText(r).contains("Unknown competition 'premier league'"), toolText(r));
        assertFalse(r.has("error"));
    }

    @Test
    @DisplayName("Given a bad date, when a tool is called, then the error names the expected format")
    void badDate() throws Exception {
        JsonNode r = call("{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"tools/call\",\"params\":"
                + "{\"name\":\"search_matches\",\"arguments\":{\"from\":\"03/09/2023\"}}}");

        assertTrue(r.at("/result/isError").asBoolean());
        assertTrue(toolText(r).contains("YYYY-MM-DD"));
    }

    @Test
    @DisplayName("Given an unknown tool name, when called, then a JSON-RPC invalid-params error is returned")
    void unknownTool() throws Exception {
        JsonNode r = call("{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"tools/call\",\"params\":{\"name\":\"nope\"}}");

        assertEquals(-32602, r.at("/error/code").asInt());
    }

    @Test
    @DisplayName("Given an unknown method, when called, then a method-not-found error is returned")
    void unknownMethod() throws Exception {
        JsonNode r = call("{\"jsonrpc\":\"2.0\",\"id\":8,\"method\":\"resources/list\"}");

        assertEquals(-32601, r.at("/error/code").asInt());
    }

    @Test
    @DisplayName("Given malformed JSON, when received, then a parse error is returned with a null id")
    void parseError() throws Exception {
        JsonNode r = call("{not json");

        assertEquals(-32700, r.at("/error/code").asInt());
        assertTrue(r.get("id").isNull());
    }

    @Test
    @DisplayName("Given a ping, when received, then an empty result is returned")
    void ping() throws Exception {
        JsonNode r = call("{\"jsonrpc\":\"2.0\",\"id\":\"abc\",\"method\":\"ping\"}");

        assertEquals("abc", r.get("id").asText());
        assertTrue(r.get("result").isObject());
    }
}
