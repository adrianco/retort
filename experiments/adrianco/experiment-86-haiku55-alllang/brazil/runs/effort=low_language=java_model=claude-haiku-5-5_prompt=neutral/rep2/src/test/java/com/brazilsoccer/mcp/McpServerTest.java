package com.brazilsoccer.mcp;

import com.brazilsoccer.TestFixtures;
import com.brazilsoccer.query.SoccerQueries;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class McpServerTest {

    private final ObjectMapper mapper = new ObjectMapper();
    private McpServer server;

    @BeforeEach
    void setUp() {
        SoccerQueries queries = new SoccerQueries(TestFixtures.smallRepository());
        server = new McpServer(new SoccerTools(queries, mapper), mapper);
    }

    @Test
    @DisplayName("Scenario: the client initializes and the server advertises the tools capability")
    void givenInitializeRequest_whenHandled_thenServerInfoAndToolsCapabilityAreReturned() throws IOException {
        // Given an initialize request
        // When it is handled
        JsonNode response = server.handleLine(
                "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}");

        // Then the response names the server and advertises tools
        assertEquals("brazilian-soccer-mcp", response.at("/result/serverInfo/name").asText());
        assertFalse(response.at("/result/capabilities/tools").isMissingNode());
        assertEquals(McpServer.PROTOCOL_VERSION, response.at("/result/protocolVersion").asText());
    }

    @Test
    @DisplayName("Scenario: notifications receive no reply")
    void givenNotification_whenHandled_thenNothingIsReturned() {
        // Given the initialized notification, which has no id
        // When it is handled
        JsonNode response = server.handleLine("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}");

        // Then no response is sent
        assertNull(response);
    }

    @Test
    @DisplayName("Scenario: tools/list exposes all seven query tools with input schemas")
    void givenToolsList_whenRequested_thenAllSevenToolsAreListed() {
        // Given a client asking for the tool list
        // When tools/list is handled
        JsonNode tools = server.handleLine("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}")
                .at("/result/tools");

        // Then each tool has a name, description and object schema
        assertEquals(7, tools.size());
        for (JsonNode tool : tools) {
            assertTrue(tool.hasNonNull("name"));
            assertTrue(tool.hasNonNull("description"));
            assertEquals("object", tool.at("/inputSchema/type").asText());
        }
    }

    @Test
    @DisplayName("Scenario: a tool call returns formatted text for the model")
    void givenMatchSearch_whenCalled_thenTextContentDescribesTheMatch() {
        // Given a search for Flamengo vs Fluminense
        String request = """
                {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches",
                 "arguments":{"team":"Flamengo","opponent":"Fluminense","season":2023}}}""";

        // When the tool is called
        JsonNode result = server.handleLine(request).get("result");

        // Then the text lists the 2023 meetings with scores and competition
        String text = result.at("/content/0/text").asText();
        assertEquals("text", result.at("/content/0/type").asText());
        assertTrue(text.contains("2023-09-03: Flamengo-RJ 2-1 Fluminense-RJ (Brasileirão Série A)"), text);
        assertTrue(result.path("isError").isMissingNode());
    }

    @Test
    @DisplayName("Scenario: invalid tool arguments are reported as a tool error, not a protocol error")
    void givenBadArguments_whenCalled_thenIsErrorIsSetInResult() {
        // Given a date filter in an unsupported format
        String request = """
                {"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search_matches",
                 "arguments":{"team":"Flamengo","from":"next tuesday"}}}""";

        // When the tool is called
        JsonNode response = server.handleLine(request);

        // Then the result is flagged as an error with an explanation the model can act on
        assertTrue(response.at("/result/isError").asBoolean());
        assertTrue(response.at("/result/content/0/text").asText().contains("from must be"));
        assertNull(response.get("error"));
    }

    @Test
    @DisplayName("Scenario: an unknown tool name is reported as a tool error")
    void givenUnknownTool_whenCalled_thenToolErrorIsReturned() {
        // Given a tool name the server does not know
        String request = """
                {"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"nope","arguments":{}}}""";

        // When it is called
        JsonNode response = server.handleLine(request);

        // Then the error names the tool
        assertTrue(response.at("/result/isError").asBoolean());
        assertTrue(response.at("/result/content/0/text").asText().contains("Unknown tool: nope"));
    }

    @Test
    @DisplayName("Scenario: an unknown method returns a JSON-RPC method-not-found error")
    void givenUnknownMethod_whenHandled_thenMethodNotFoundIsReturned() {
        // Given a method the server does not implement
        // When it is handled
        JsonNode response = server.handleLine("{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"resources/list\"}");

        // Then a -32601 error comes back
        assertEquals(McpServer.METHOD_NOT_FOUND, response.at("/error/code").asInt());
    }

    @Test
    @DisplayName("Scenario: malformed JSON returns a parse error")
    void givenMalformedJson_whenHandled_thenParseErrorIsReturned() {
        // Given a line that is not JSON
        // When it is handled
        JsonNode response = server.handleLine("{not json");

        // Then a parse error comes back
        assertEquals(-32700, response.at("/error/code").asInt());
    }

    @Test
    @DisplayName("Scenario: a full stdio session writes one reply per request and skips notifications")
    void givenStdioSession_whenServed_thenRepliesAreWrittenLineByLine() throws IOException {
        // Given three requests and one notification on stdin
        String input = """
                {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
                {"jsonrpc":"2.0","method":"notifications/initialized"}

                {"jsonrpc":"2.0","id":2,"method":"ping"}
                """;
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        PrintStream out = new PrintStream(bytes, true, StandardCharsets.UTF_8);

        // When the session is served
        server.serve(new BufferedReader(new InputStreamReader(
                new ByteArrayInputStream(input.getBytes(StandardCharsets.UTF_8)), StandardCharsets.UTF_8)), out);

        // Then two reply lines are written
        String[] lines = bytes.toString(StandardCharsets.UTF_8).split("\n");
        assertEquals(2, lines.length);
        assertEquals(1, mapper.readTree(lines[0]).get("id").asInt());
        assertEquals(2, mapper.readTree(lines[1]).get("id").asInt());
    }
}
