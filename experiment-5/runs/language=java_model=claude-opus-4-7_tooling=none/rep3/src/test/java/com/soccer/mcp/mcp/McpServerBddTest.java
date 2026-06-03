package com.soccer.mcp.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.soccer.mcp.data.DataStore;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import java.nio.file.Paths;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@DisplayName("Feature: MCP JSON-RPC server")
class McpServerBddTest {

    private McpServer server;
    private final ObjectMapper mapper = new ObjectMapper();

    @BeforeAll
    void givenServerWithDataStore() throws Exception {
        DataStore store = DataStore.load(Paths.get("data", "kaggle"));
        server = new McpServer(store);
    }

    @Test
    @DisplayName("Scenario: initialize returns protocol version and capabilities")
    void whenIInitialize_thenIReceiveProtocolMetadata() throws Exception {
        JsonNode req = mapper.readTree("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\"}");
        JsonNode resp = server.handle(req);
        assertNotNull(resp);
        assertEquals("2.0", resp.path("jsonrpc").asText());
        assertEquals(1, resp.path("id").asInt());
        assertEquals("2024-11-05", resp.path("result").path("protocolVersion").asText());
        assertNotNull(resp.path("result").path("serverInfo").path("name").asText());
    }

    @Test
    @DisplayName("Scenario: tools/list lists all tools with schemas")
    void whenIListTools_thenIReceiveToolDefinitions() throws Exception {
        JsonNode req = mapper.readTree("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}");
        JsonNode resp = server.handle(req);
        JsonNode tools = resp.path("result").path("tools");
        assertTrue(tools.isArray());
        assertTrue(tools.size() >= 10, "expected at least 10 tools, got " + tools.size());
        for (JsonNode t : tools) {
            assertTrue(t.has("name"));
            assertTrue(t.has("inputSchema"));
        }
    }

    @Test
    @DisplayName("Scenario: tools/call head_to_head returns text content")
    void whenICallHeadToHead_thenIReceiveFormattedText() throws Exception {
        String body = "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\","
                + "\"params\":{\"name\":\"head_to_head\","
                + "\"arguments\":{\"team_a\":\"Flamengo\",\"team_b\":\"Fluminense\"}}}";
        JsonNode resp = server.handle(mapper.readTree(body));
        JsonNode content = resp.path("result").path("content");
        assertTrue(content.isArray());
        assertEquals("text", content.get(0).path("type").asText());
        String text = content.get(0).path("text").asText();
        assertTrue(text.contains("Flamengo"));
        assertTrue(text.contains("Fluminense"));
    }

    @Test
    @DisplayName("Scenario: unknown method returns method-not-found")
    void whenICallUnknownMethod_thenIReceiveJsonRpcError() throws Exception {
        JsonNode req = mapper.readTree("{\"jsonrpc\":\"2.0\",\"id\":9,\"method\":\"does/not/exist\"}");
        JsonNode resp = server.handle(req);
        assertEquals(-32601, resp.path("error").path("code").asInt());
    }

    @Test
    @DisplayName("Scenario: tools/call champion returns champion of Brasileirão 2019")
    void whenICallChampion_thenIReceiveFlamengo() throws Exception {
        String body = "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\","
                + "\"params\":{\"name\":\"champion\","
                + "\"arguments\":{\"competition\":\"Brasileirão\",\"season\":2019}}}";
        JsonNode resp = server.handle(mapper.readTree(body));
        String text = resp.path("result").path("content").get(0).path("text").asText();
        assertTrue(text.toLowerCase().contains("flamengo"), "got: " + text);
    }
}
