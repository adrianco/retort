package com.brazilsoccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Locale;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** "Player Queries" capability — search by name, nationality, club and position. */
class PlayerQueryAcceptanceTest {

    private McpTestClient client;

    @BeforeEach
    void setUp() {
        client = McpTestClient.bootAndInitialize();
    }

    @Test
    void looks_up_a_player_by_name() {
        JsonNode result = client.callTool("search_players", Map.of("name", "Neymar"));

        assertTrue(result.get("count").asInt() > 0);
        JsonNode neymar = result.get("players").get(0);
        assertTrue(neymar.get("name").asText().toLowerCase(Locale.ROOT).contains("neymar"));
        assertEquals("Brazil", neymar.get("nationality").asText());
        assertTrue(neymar.get("overall").asInt() >= 85, "Neymar is an elite-rated player");
    }

    @Test
    void finds_brazilian_players_sorted_by_rating() {
        JsonNode result = client.callTool("search_players",
                Map.of("nationality", "Brazil", "limit", 50));

        assertTrue(result.get("count").asInt() > 100, "the dataset holds many Brazilian players");
        int previous = Integer.MAX_VALUE;
        for (JsonNode player : result.get("players")) {
            assertEquals("Brazil", player.get("nationality").asText(), "nationality filter must hold");
            int overall = player.get("overall").asInt();
            assertTrue(overall <= previous, "players must be ranked best-first");
            previous = overall;
        }
    }

    @Test
    void filters_players_by_club() {
        JsonNode result = client.callTool("search_players",
                Map.of("club", "Cruzeiro", "limit", 50));

        assertTrue(result.get("count").asInt() > 0, "Cruzeiro players appear in the FIFA dataset");
        for (JsonNode player : result.get("players")) {
            assertTrue(player.get("club").asText().toLowerCase(Locale.ROOT).contains("cruzeiro"),
                    "club filter must hold: " + player);
        }
    }

    @Test
    void filters_players_by_position() {
        JsonNode result = client.callTool("search_players",
                Map.of("nationality", "Brazil", "position", "GK", "limit", 50));

        assertTrue(result.get("count").asInt() > 0);
        for (JsonNode player : result.get("players")) {
            assertEquals("GK", player.get("position").asText());
        }
    }
}
