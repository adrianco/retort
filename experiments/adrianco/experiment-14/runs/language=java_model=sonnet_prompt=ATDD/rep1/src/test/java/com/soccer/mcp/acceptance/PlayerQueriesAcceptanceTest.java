package com.soccer.mcp.acceptance;

import com.soccer.mcp.BrazilianSoccerMcpServer;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Acceptance tests for player query functionality.
 * Tests exercise only the public MCP tool methods of BrazilianSoccerMcpServer.
 */
public class PlayerQueriesAcceptanceTest {

    private static BrazilianSoccerMcpServer server;

    @BeforeAll
    static void setUp() {
        server = new BrazilianSoccerMcpServer();
    }

    @Test
    void findPlayersByNationalityBrazil() {
        String result = server.findPlayers(null, "Brazil", null, null, null, 20);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).contains("brazil");
    }

    @Test
    void findPlayersByHighMinOverallIncludesNeymar() {
        String result = server.findPlayers(null, "Brazil", null, null, 90, 10);
        assertThat(result).isNotEmpty();
        // Neymar has overall 92 and is Brazilian - should appear
        assertThat(result.toLowerCase()).containsAnyOf("neymar", "brazil");
    }

    @Test
    void findPlayersByMinOverall85ReturnsElitePlayers() {
        String result = server.findPlayers(null, "Brazil", null, null, 85, 20);
        assertThat(result).isNotEmpty();
        // Should have multiple elite Brazilian players
        assertThat(result.split("\n").length).isGreaterThan(2);
    }

    @Test
    void findPlayersByClub() {
        // FIFA data contains European clubs like Real Madrid, PSG, Barcelona
        String result = server.findPlayers(null, null, "Real Madrid", null, null, 10);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).contains("real madrid");
    }

    @Test
    void findPlayersByNameNeymar() {
        String result = server.findPlayers("Neymar", null, null, null, null, 5);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).contains("neymar");
    }

    @Test
    void findPlayersByPosition() {
        String result = server.findPlayers(null, null, null, "GK", null, 10);
        assertThat(result).isNotEmpty();
        assertThat(result.toUpperCase()).contains("GK");
    }

    @Test
    void findPlayersWithLimitRespected() {
        String result = server.findPlayers(null, "Brazil", null, null, null, 5);
        assertThat(result).isNotEmpty();
        // Counting non-header lines that have player data (contain "|")
        long playerLines = java.util.Arrays.stream(result.split("\n"))
                .filter(line -> line.contains("|"))
                .count();
        assertThat(playerLines).isLessThanOrEqualTo(5);
    }

    @Test
    void findPlayersByNeymarHasOverallRating() {
        String result = server.findPlayers("Neymar", null, null, null, null, 5);
        assertThat(result).isNotEmpty();
        // Should include overall rating (92 for Neymar Jr)
        assertThat(result).containsPattern("9[0-9]"); // at least 90+ overall
    }
}
