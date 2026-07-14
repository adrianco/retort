package com.brazilsoccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Acceptance tests for the MCP protocol surface itself: an external client must be
 * able to perform the handshake, discover tools, and receive protocol-compliant
 * errors. Drives the server purely over JSON-RPC.
 */
class McpProtocolAcceptanceTest {

    @Test
    void handshake_reports_server_identity_and_tool_capability() {
        McpTestClient client = McpTestClient.bootAndInitialize();
        JsonNode init = client.initialize();

        assertEquals("2024-11-05", init.get("protocolVersion").asText());
        assertTrue(init.get("capabilities").has("tools"), "server must advertise tool capability");
        assertFalse(init.get("serverInfo").get("name").asText().isBlank(), "server must identify itself");
    }

    @Test
    void discovery_exposes_the_full_set_of_soccer_tools() {
        McpTestClient client = McpTestClient.bootAndInitialize();
        JsonNode tools = client.listTools().get("tools");

        Set<String> names = new HashSet<>();
        tools.forEach(t -> {
            names.add(t.get("name").asText());
            // Every tool must be self-describing for the LLM host.
            assertFalse(t.get("description").asText().isBlank());
            assertTrue(t.get("inputSchema").has("type"), "each tool needs a JSON input schema");
        });

        assertTrue(names.containsAll(Set.of(
                "find_matches", "head_to_head", "team_stats",
                "search_players", "competition_standings", "league_statistics")),
                "expected the soccer tool set, got: " + names);
    }

    @Test
    void calling_an_unknown_tool_yields_a_protocol_error() {
        McpTestClient client = McpTestClient.bootAndInitialize();
        JsonNode response = client.rawToolCall("teleport_player", Map.of());
        assertTrue(response.has("error"), "unknown tool must produce a JSON-RPC error");
        assertFalse(response.get("error").get("message").asText().isBlank());
    }
}
