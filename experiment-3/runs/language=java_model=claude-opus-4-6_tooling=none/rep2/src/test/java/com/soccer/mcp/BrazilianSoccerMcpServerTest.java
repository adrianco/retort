package com.soccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.*;

import java.io.IOException;
import java.nio.file.*;

@DisplayName("Feature: MCP Server Protocol and Tool Integration")
class BrazilianSoccerMcpServerTest {

    private static BrazilianSoccerMcpServer server;
    private static ObjectMapper mapper;
    private static boolean dataAvailable;

    @BeforeAll
    static void setup() {
        mapper = new ObjectMapper();
        DataStore store = new DataStore();
        Path dataDir = Path.of("data/kaggle");
        dataAvailable = Files.exists(dataDir);
        if (dataAvailable) {
            try {
                store.loadAll("data/kaggle");
            } catch (IOException e) {
                dataAvailable = false;
            }
        }
        server = new BrazilianSoccerMcpServer(store);
    }

    private JsonNode request(String method, ObjectNode params) throws Exception {
        ObjectNode req = mapper.createObjectNode();
        req.put("jsonrpc", "2.0");
        req.put("id", 1);
        req.put("method", method);
        if (params != null) req.set("params", params);
        return server.handleRequest(req);
    }

    @Nested
    @DisplayName("Scenario: MCP protocol initialization")
    class ProtocolInit {
        @Test
        @DisplayName("Given an initialize request, server should return capabilities")
        void initialize() throws Exception {
            JsonNode response = request("initialize", null);
            assertNotNull(response);
            assertEquals("2.0", response.get("jsonrpc").asText());
            JsonNode result = response.get("result");
            assertNotNull(result);
            assertEquals("2024-11-05", result.get("protocolVersion").asText());
            assertNotNull(result.get("capabilities").get("tools"));
            assertEquals("brazilian-soccer-mcp", result.get("serverInfo").get("name").asText());
        }

        @Test
        @DisplayName("Given a ping request, server should respond")
        void ping() throws Exception {
            JsonNode response = request("ping", null);
            assertNotNull(response);
            assertNotNull(response.get("result"));
        }

        @Test
        @DisplayName("Given an unknown method, server should return error")
        void unknownMethod() throws Exception {
            JsonNode response = request("unknown/method", null);
            assertNotNull(response);
            assertNotNull(response.get("error"));
            assertEquals(-32601, response.get("error").get("code").asInt());
        }

        @Test
        @DisplayName("Given a notification, server should return null")
        void notification() throws Exception {
            JsonNode response = request("notifications/initialized", null);
            assertNull(response);
        }
    }

    @Nested
    @DisplayName("Scenario: Tools listing")
    class ToolsListing {
        @Test
        @DisplayName("Given a tools/list request, server should return all 6 tools")
        void listTools() throws Exception {
            JsonNode response = request("tools/list", null);
            JsonNode tools = response.get("result").get("tools");
            assertNotNull(tools);
            assertTrue(tools.isArray());
            assertEquals(6, tools.size(), "Should have 6 tools");

            var toolNames = new java.util.HashSet<String>();
            for (JsonNode tool : tools) {
                toolNames.add(tool.get("name").asText());
                assertNotNull(tool.get("description"), "Each tool should have a description");
                assertNotNull(tool.get("inputSchema"), "Each tool should have an input schema");
            }
            assertTrue(toolNames.contains("search_matches"));
            assertTrue(toolNames.contains("team_stats"));
            assertTrue(toolNames.contains("head_to_head"));
            assertTrue(toolNames.contains("search_players"));
            assertTrue(toolNames.contains("competition_standings"));
            assertTrue(toolNames.contains("biggest_wins"));
        }
    }

    @Nested
    @DisplayName("Scenario: Tool calls with real data")
    class ToolCalls {
        @Test
        @DisplayName("Given match data, search_matches tool returns formatted results")
        void searchMatches() throws Exception {
            assumeTrue(dataAvailable, "Data files not available");
            ObjectNode params = mapper.createObjectNode();
            params.put("name", "search_matches");
            ObjectNode args = mapper.createObjectNode();
            args.put("team", "Flamengo");
            args.put("season", "2019");
            params.set("arguments", args);

            JsonNode response = request("tools/call", params);
            JsonNode content = response.get("result").get("content");
            assertNotNull(content);
            assertTrue(content.isArray());
            String text = content.get(0).get("text").asText();
            assertTrue(text.contains("match"), "Response should mention matches");
        }

        @Test
        @DisplayName("Given match data, team_stats tool returns statistics")
        void teamStats() throws Exception {
            assumeTrue(dataAvailable, "Data files not available");
            ObjectNode params = mapper.createObjectNode();
            params.put("name", "team_stats");
            ObjectNode args = mapper.createObjectNode();
            args.put("team", "Corinthians");
            args.put("season", "2019");
            params.set("arguments", args);

            JsonNode response = request("tools/call", params);
            String text = response.get("result").get("content").get(0).get("text").asText();
            assertTrue(text.contains("Wins") || text.contains("wins"));
            assertTrue(text.contains("Losses") || text.contains("losses"));
        }

        @Test
        @DisplayName("Given match data, head_to_head tool compares two teams")
        void headToHead() throws Exception {
            assumeTrue(dataAvailable, "Data files not available");
            ObjectNode params = mapper.createObjectNode();
            params.put("name", "head_to_head");
            ObjectNode args = mapper.createObjectNode();
            args.put("team1", "Palmeiras");
            args.put("team2", "Santos");
            params.set("arguments", args);

            JsonNode response = request("tools/call", params);
            String text = response.get("result").get("content").get(0).get("text").asText();
            assertTrue(text.contains("Head-to-Head"));
            assertTrue(text.contains("wins"));
        }

        @Test
        @DisplayName("Given FIFA data, search_players tool finds players")
        void searchPlayers() throws Exception {
            assumeTrue(dataAvailable, "Data files not available");
            ObjectNode params = mapper.createObjectNode();
            params.put("name", "search_players");
            ObjectNode args = mapper.createObjectNode();
            args.put("nationality", "Brazil");
            args.put("min_rating", 85);
            params.set("arguments", args);

            JsonNode response = request("tools/call", params);
            String text = response.get("result").get("content").get(0).get("text").asText();
            assertTrue(text.contains("player"));
        }

        @Test
        @DisplayName("Given match data, competition_standings tool returns standings table")
        void competitionStandings() throws Exception {
            assumeTrue(dataAvailable, "Data files not available");
            ObjectNode params = mapper.createObjectNode();
            params.put("name", "competition_standings");
            ObjectNode args = mapper.createObjectNode();
            args.put("competition", "Brasileirao");
            args.put("season", "2019");
            params.set("arguments", args);

            JsonNode response = request("tools/call", params);
            String text = response.get("result").get("content").get(0).get("text").asText();
            assertTrue(text.contains("Standings"));
            assertTrue(text.contains("Pts"));
        }

        @Test
        @DisplayName("Given match data, biggest_wins tool returns sorted results")
        void biggestWins() throws Exception {
            assumeTrue(dataAvailable, "Data files not available");
            ObjectNode params = mapper.createObjectNode();
            params.put("name", "biggest_wins");
            ObjectNode args = mapper.createObjectNode();
            args.put("limit", 5);
            params.set("arguments", args);

            JsonNode response = request("tools/call", params);
            String text = response.get("result").get("content").get(0).get("text").asText();
            assertTrue(text.contains("goal difference"));
        }

        @Test
        @DisplayName("Given an unknown tool name, server returns error message in content")
        void unknownTool() throws Exception {
            ObjectNode params = mapper.createObjectNode();
            params.put("name", "nonexistent_tool");
            params.set("arguments", mapper.createObjectNode());

            JsonNode response = request("tools/call", params);
            String text = response.get("result").get("content").get(0).get("text").asText();
            assertTrue(text.contains("Unknown tool"));
        }

        @Test
        @DisplayName("Given team_stats with no team param, returns error message")
        void teamStatsNoTeam() throws Exception {
            ObjectNode params = mapper.createObjectNode();
            params.put("name", "team_stats");
            params.set("arguments", mapper.createObjectNode());

            JsonNode response = request("tools/call", params);
            String text = response.get("result").get("content").get(0).get("text").asText();
            assertTrue(text.contains("required"));
        }

        @Test
        @DisplayName("Given competition_standings with no season, returns error message")
        void standingsNoSeason() throws Exception {
            ObjectNode params = mapper.createObjectNode();
            params.put("name", "competition_standings");
            ObjectNode args = mapper.createObjectNode();
            args.put("competition", "Brasileirao");
            params.set("arguments", args);

            JsonNode response = request("tools/call", params);
            String text = response.get("result").get("content").get(0).get("text").asText();
            assertTrue(text.contains("required"));
        }
    }

    @Nested
    @DisplayName("Scenario: Resources and Prompts listing")
    class ResourcesAndPrompts {
        @Test
        @DisplayName("Given resources/list request, server returns empty list")
        void listResources() throws Exception {
            JsonNode response = request("resources/list", null);
            assertNotNull(response.get("result").get("resources"));
            assertEquals(0, response.get("result").get("resources").size());
        }

        @Test
        @DisplayName("Given prompts/list request, server returns empty list")
        void listPrompts() throws Exception {
            JsonNode response = request("prompts/list", null);
            assertNotNull(response.get("result").get("prompts"));
            assertEquals(0, response.get("result").get("prompts").size());
        }
    }
}
