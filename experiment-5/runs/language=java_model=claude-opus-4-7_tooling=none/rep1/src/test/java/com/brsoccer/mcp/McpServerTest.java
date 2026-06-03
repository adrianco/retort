package com.brsoccer.mcp;

import com.brsoccer.mcp.server.McpServer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: MCP JSON-RPC server")
class McpServerTest {

    private final ObjectMapper json = new ObjectMapper();

    @Nested
    @DisplayName("Scenario: Initialize handshake")
    class Initialize {
        @Test
        @DisplayName("Given an initialize request Then the server returns its capabilities and serverInfo")
        void initialize() throws Exception {
            McpServer server = new McpServer(TestData.get());
            JsonNode resp = json.readTree(server.handle(
                "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}"));
            assertEquals("2.0", resp.path("jsonrpc").asText());
            assertEquals(1, resp.path("id").asInt());
            assertTrue(resp.path("result").has("serverInfo"));
            assertTrue(resp.path("result").has("capabilities"));
        }
    }

    @Nested
    @DisplayName("Scenario: List tools")
    class ListTools {
        @Test
        @DisplayName("Given tools/list Then the response includes the expected tool catalog")
        void toolsList() throws Exception {
            McpServer server = new McpServer(TestData.get());
            JsonNode resp = json.readTree(server.handle(
                "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}"));
            JsonNode tools = resp.path("result").path("tools");
            assertTrue(tools.isArray() && tools.size() >= 10, "expected many tools");
            boolean found = false;
            for (JsonNode t : tools) {
                if ("find_matches_between_teams".equals(t.path("name").asText())) found = true;
            }
            assertTrue(found, "expected find_matches_between_teams tool");
        }
    }

    @Nested
    @DisplayName("Scenario: Call a tool")
    class CallTool {
        @Test
        @DisplayName("Given tools/call for find_matches_between_teams Then a text response is returned")
        void callMatchesBetween() throws Exception {
            McpServer server = new McpServer(TestData.get());
            String req = "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":"
                + "{\"name\":\"find_matches_between_teams\",\"arguments\":{\"team_a\":\"Flamengo\",\"team_b\":\"Fluminense\",\"limit\":3}}}";
            JsonNode resp = json.readTree(server.handle(req));
            assertNotNull(resp.path("result").path("content").get(0));
            assertEquals("text", resp.path("result").path("content").get(0).path("type").asText());
            String text = resp.path("result").path("content").get(0).path("text").asText();
            assertFalse(text.isEmpty());
            assertTrue(text.toLowerCase().contains("flamengo"));
        }

        @Test
        @DisplayName("Given tools/call with an unknown tool Then an error is returned in JSON-RPC envelope")
        void unknownTool() throws Exception {
            McpServer server = new McpServer(TestData.get());
            String req = "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":"
                + "{\"name\":\"does_not_exist\",\"arguments\":{}}}";
            JsonNode resp = json.readTree(server.handle(req));
            // either an error envelope, or an isError=true result
            boolean isError = resp.has("error")
                || resp.path("result").path("isError").asBoolean(false);
            assertTrue(isError, "expected error for unknown tool: " + resp);
        }
    }

    @Nested
    @DisplayName("Scenario: Notifications are silent")
    class Notifications {
        @Test
        @DisplayName("Given a notification (no id) Then the server returns no response")
        void noResponse() {
            McpServer server = new McpServer(TestData.get());
            String resp = server.handle(
                "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}");
            org.junit.jupiter.api.Assertions.assertNull(resp);
        }
    }
}
