package br.soccer.mcp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.soccer.data.DataLoader;
import br.soccer.data.Dataset;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.StringReader;
import java.io.StringWriter;
import java.io.PrintWriter;
import java.nio.file.Path;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

class McpServerTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final McpServer SERVER = new McpServer(new SoccerTools(load()));

    private static Dataset load() {
        try {
            return DataLoader.load(Path.of("data/kaggle"));
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    private static JsonNode send(String message) throws IOException {
        return SERVER.handle(message);
    }

    @Nested
    @DisplayName("Feature: MCP handshake")
    class Handshake {

        @Test
        @DisplayName("Scenario: Initialize advertises the tools capability")
        void initialize() throws IOException {
            JsonNode reply = send("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}");

            assertEquals("2.0", reply.get("jsonrpc").asText());
            assertEquals(1, reply.get("id").asInt());
            assertEquals(McpServer.PROTOCOL_VERSION, reply.at("/result/protocolVersion").asText());
            assertTrue(reply.at("/result/capabilities/tools").isObject());
        }

        @Test
        @DisplayName("Scenario: Notifications receive no reply")
        void notificationsAreSilent() throws IOException {
            assertNull(send("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}"));
        }

        @Test
        @DisplayName("Scenario: Ping answers with an empty result")
        void ping() throws IOException {
            JsonNode reply = send("{\"jsonrpc\":\"2.0\",\"id\":\"abc\",\"method\":\"ping\"}");

            assertEquals("abc", reply.get("id").asText());
            assertTrue(reply.get("result").isObject());
        }
    }

    @Nested
    @DisplayName("Feature: Tool discovery and invocation")
    class ToolsOverTheWire {

        @Test
        @DisplayName("Scenario: tools/list describes every query tool")
        void listsTools() throws IOException {
            JsonNode tools = send("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}").at("/result/tools");

            assertEquals(7, tools.size());
            assertEquals("search_matches", tools.get(0).get("name").asText());
        }

        @Test
        @DisplayName("Scenario: tools/call returns text content")
        void callsTool() throws IOException {
            JsonNode reply = send("{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":"
                    + "{\"name\":\"find_players\",\"arguments\":{\"name\":\"Messi\",\"limit\":1}}}");

            assertFalse(reply.at("/result/isError").asBoolean());
            assertEquals("text", reply.at("/result/content/0/type").asText());
            assertTrue(reply.at("/result/content/0/text").asText().contains("L. Messi"));
        }

        @Test
        @DisplayName("Scenario: Invalid arguments come back as a tool error the model can read")
        void toolErrorIsReportedInResult() throws IOException {
            JsonNode reply = send("{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":"
                    + "{\"name\":\"standings\",\"arguments\":{}}}");

            assertTrue(reply.at("/result/isError").asBoolean());
            assertTrue(reply.at("/result/content/0/text").asText().contains("season"));
        }

        @Test
        @DisplayName("Scenario: Unknown tools are a protocol error")
        void unknownToolIsProtocolError() throws IOException {
            JsonNode reply = send("{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":"
                    + "{\"name\":\"nope\"}}");

            assertEquals(-32602, reply.at("/error/code").asInt());
        }
    }

    @Nested
    @DisplayName("Feature: Robustness")
    class Robustness {

        @Test
        @DisplayName("Scenario: Unknown methods get method-not-found")
        void unknownMethod() throws IOException {
            assertEquals(-32601, send("{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"resources/list\"}")
                    .at("/error/code").asInt());
        }

        @Test
        @DisplayName("Scenario: Malformed JSON gets a parse error")
        void malformedJson() throws IOException {
            assertEquals(-32700, send("{not json").at("/error/code").asInt());
        }

        @Test
        @DisplayName("Scenario: serve() answers each request on its own line")
        void serveLoop() throws IOException {
            String input = "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}\n\n"
                    + "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}\n"
                    + "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"ping\"}\n";
            StringWriter out = new StringWriter();

            SERVER.serve(new BufferedReader(new StringReader(input)), new PrintWriter(out));

            String[] lines = out.toString().strip().split("\n");
            assertEquals(2, lines.length);
            assertEquals(2, JSON.readTree(lines[1]).get("id").asInt());
        }
    }
}
