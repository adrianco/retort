package com.example.brsoccer.mcp;

import com.example.brsoccer.model.Match;
import com.example.brsoccer.query.SoccerDatabase;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class McpServerTest {

    private final ObjectMapper json = new ObjectMapper();
    private McpServer server;

    @BeforeEach
    void setUp() {
        List<Match> matches = List.of(
                new Match("Brasileirão", 2023, LocalDate.parse("2023-09-03"), "22",
                        "Flamengo", "Fluminense", 2, 1));
        server = new McpServer(new SoccerTools(new SoccerDatabase(matches, List.of())));
    }

    private JsonNode handle(String request) throws Exception {
        JsonNode response = server.handle(json.readTree(request));
        return response;
    }

    @Test
    void initializeReturnsServerInfoAndProtocolVersion() throws Exception {
        JsonNode r = handle("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}");
        assertEquals("2.0", r.get("jsonrpc").asText());
        assertEquals(1, r.get("id").asInt());
        assertTrue(r.get("result").has("protocolVersion"));
        assertTrue(r.get("result").get("serverInfo").has("name"));
        assertTrue(r.get("result").get("capabilities").has("tools"));
    }

    @Test
    void toolsListReturnsAllToolsWithSchemas() throws Exception {
        JsonNode r = handle("{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}");
        JsonNode toolsArray = r.get("result").get("tools");
        assertTrue(toolsArray.isArray());
        assertTrue(toolsArray.size() >= 6);
        JsonNode first = toolsArray.get(0);
        assertTrue(first.has("name"));
        assertTrue(first.has("description"));
        assertTrue(first.has("inputSchema"));
    }

    @Test
    void toolsCallReturnsTextContent() throws Exception {
        JsonNode r = handle("{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\","
                + "\"params\":{\"name\":\"find_matches\",\"arguments\":{\"team\":\"Flamengo\"}}}");
        JsonNode content = r.get("result").get("content");
        assertTrue(content.isArray());
        assertEquals("text", content.get(0).get("type").asText());
        assertTrue(content.get(0).get("text").asText().contains("Flamengo 2-1 Fluminense"));
        assertFalse(r.get("result").get("isError").asBoolean());
    }

    @Test
    void notificationProducesNoResponse() throws Exception {
        JsonNode r = handle("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}");
        assertNull(r);
    }

    @Test
    void unknownMethodReturnsJsonRpcError() throws Exception {
        JsonNode r = handle("{\"jsonrpc\":\"2.0\",\"id\":9,\"method\":\"no/such\"}");
        assertTrue(r.has("error"));
        assertEquals(-32601, r.get("error").get("code").asInt());
    }

    @Test
    void toolsCallWithUnknownToolReportsErrorContent() throws Exception {
        JsonNode r = handle("{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\","
                + "\"params\":{\"name\":\"bogus\",\"arguments\":{}}}");
        assertTrue(r.get("result").get("content").get(0).get("text").asText()
                .toLowerCase().contains("unknown tool"));
    }
}
