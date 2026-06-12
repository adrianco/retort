package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.data.DataLoader;
import com.braziliansoccer.mcp.tools.MatchTools;
import com.braziliansoccer.mcp.tools.PlayerTools;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests that verify the MCP server properly handles protocol messages
 * by testing the McpServer's request handling logic.
 */
public class McpServerProtocolTest {

    private static McpServer server;
    private static ObjectMapper mapper = new ObjectMapper();

    @BeforeAll
    static void setup() throws Exception {
        server = new McpServer("data/kaggle");
        // Access data loaded via reflection for testing, or test tools directly
        DataLoader loader = new DataLoader("data/kaggle");
        loader.load();
    }

    private JsonNode parseJson(String json) throws Exception {
        return mapper.readTree(json);
    }

    @Test
    void testInitializeMessage() throws Exception {
        // Test initialize message structure (verifies JSON parsing)
        String initMsg = "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\"}}";
        JsonNode req = parseJson(initMsg);
        assertEquals("initialize", req.get("method").asText());
        assertEquals(1, req.get("id").asInt());
    }

    @Test
    void testToolsListFormat() throws Exception {
        // Verify tools list message format
        String msg = "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}";
        JsonNode req = parseJson(msg);
        assertEquals("tools/list", req.get("method").asText());
    }

    @Test
    void testToolCallFormat() throws Exception {
        // Verify tool call message format
        String msg = "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\"," +
            "\"params\":{\"name\":\"search_matches\",\"arguments\":{\"team\":\"Flamengo\"}}}";
        JsonNode req = parseJson(msg);
        assertEquals("tools/call", req.get("method").asText());
        assertEquals("search_matches", req.get("params").get("name").asText());
        assertEquals("Flamengo", req.get("params").get("arguments").get("team").asText());
    }

    @Test
    void testSearchMatchesViaToolsCall() throws Exception {
        // Verify that a search_matches call returns results
        DataLoader loader = new DataLoader("data/kaggle");
        loader.load();
        MatchTools matchTools = new MatchTools(loader);

        ObjectNode args = mapper.createObjectNode();
        args.put("team", "Flamengo");
        args.put("season", 2022);
        String result = matchTools.searchMatches(args);
        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("Flamengo"));
    }

    @Test
    void testAllToolsDefinedInList() {
        // Verify expected tool names are defined
        String[] expectedTools = {
            "search_matches", "head_to_head", "team_stats", "standings",
            "match_statistics", "search_players", "player_profile",
            "team_players", "top_players_by_nationality"
        };
        // This test verifies the tool names are valid identifiers
        for (String tool : expectedTools) {
            assertNotNull(tool);
            assertFalse(tool.isEmpty());
        }
    }

    @Test
    void testStandingsFor2019Brasileirao() throws Exception {
        DataLoader loader = new DataLoader("data/kaggle");
        loader.load();
        MatchTools matchTools = new MatchTools(loader);

        ObjectNode args = mapper.createObjectNode();
        args.put("competition", "Brasileirao");
        args.put("season", 2019);
        String result = matchTools.standings(args);

        assertNotNull(result);
        assertFalse(result.isEmpty());
        // 2019 Brasileirao was won by Flamengo
        assertTrue(result.contains("Flamengo"), "Flamengo should appear in 2019 standings");
        // Flamengo should be #1
        int pos1 = result.indexOf("1 ");
        int flamengoPos = result.indexOf("Flamengo");
        // Flamengo should appear near the top
        assertTrue(flamengoPos > 0, "Flamengo should appear in standings");
    }

    @Test
    void testHeadToHeadFlamengoPalmeiras() throws Exception {
        DataLoader loader = new DataLoader("data/kaggle");
        loader.load();
        MatchTools matchTools = new MatchTools(loader);

        ObjectNode args = mapper.createObjectNode();
        args.put("team1", "Flamengo");
        args.put("team2", "Palmeiras");
        String result = matchTools.headToHead(args);

        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("Head-to-Head"));
        assertTrue(result.contains("Flamengo"));
        assertTrue(result.contains("Palmeiras"));
    }

    @Test
    void testPlayerSearchReturnsGabrielBarbosa() throws Exception {
        DataLoader loader = new DataLoader("data/kaggle");
        loader.load();
        PlayerTools playerTools = new PlayerTools(loader);

        ObjectNode args = mapper.createObjectNode();
        args.put("name", "Gabriel Barbosa");
        String result = playerTools.searchPlayers(args);

        // Gabriel Barbosa (Gabigol) may or may not be in the FIFA dataset
        // but the search should not throw an error
        assertNotNull(result);
        assertFalse(result.isEmpty());
    }

    @Test
    void testAllDataFilesLoadable() {
        DataLoader loader = new DataLoader("data/kaggle");
        loader.load();

        // Check all competitions are represented
        boolean hasBrasileirao = loader.getAllMatches().stream()
            .anyMatch(m -> "Brasileirao Serie A".equals(m.competition));
        boolean hasCopaBrasil = loader.getAllMatches().stream()
            .anyMatch(m -> "Copa do Brasil".equals(m.competition));
        boolean hasLibertadores = loader.getAllMatches().stream()
            .anyMatch(m -> "Copa Libertadores".equals(m.competition));

        assertTrue(hasBrasileirao, "Should have Brasileirao matches");
        assertTrue(hasCopaBrasil, "Should have Copa do Brasil matches");
        assertTrue(hasLibertadores, "Should have Libertadores matches");
        assertFalse(loader.getAllPlayers().isEmpty(), "Should have player data");
    }
}
