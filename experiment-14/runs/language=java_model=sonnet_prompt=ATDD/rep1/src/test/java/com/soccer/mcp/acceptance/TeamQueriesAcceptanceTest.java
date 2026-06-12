package com.soccer.mcp.acceptance;

import com.soccer.mcp.BrazilianSoccerMcpServer;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Acceptance tests for team stats query functionality.
 * Tests exercise only the public MCP tool methods of BrazilianSoccerMcpServer.
 */
public class TeamQueriesAcceptanceTest {

    private static BrazilianSoccerMcpServer server;

    @BeforeAll
    static void setUp() {
        server = new BrazilianSoccerMcpServer();
    }

    @Test
    void getTeamStatsReturnsWinDrawLoss() {
        String result = server.getTeamStats("Corinthians", "brasileirao", 2022);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).containsAnyOf("win", "drew", "draw", "loss", "lost", "vitória", "empate", "derrota");
    }

    @Test
    void getTeamStatsCorinthians2022HasRoughly38Matches() {
        String result = server.getTeamStats("Corinthians", "brasileirao", 2022);
        assertThat(result).isNotEmpty();
        // Corinthians plays 38 matches in Brasileirao - extract total games
        // The result should mention wins + draws + losses summing near 38
        assertThat(result).containsPattern("\\d+");
        // Parse wins, draws, losses from result - they should sum to ~38
        int wins = extractNumber(result, "win");
        int draws = extractNumber(result, "draw");
        int losses = extractNumber(result, "loss");
        int total = wins + draws + losses;
        assertThat(total).isBetween(35, 40); // allow some tolerance
    }

    @Test
    void getTeamStatsIncludesGoals() {
        String result = server.getTeamStats("Flamengo", "brasileirao", 2019);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).containsAnyOf("goal", "gol", "scored", "conceded");
    }

    @Test
    void getTeamStatsFlamengoDominantIn2019() {
        String result = server.getTeamStats("Flamengo", "brasileirao", 2019);
        assertThat(result).isNotEmpty();
        // Flamengo won the 2019 Brasileirao with many wins
        int wins = extractNumber(result, "win");
        assertThat(wins).isGreaterThan(20); // Flamengo had ~28 wins in 2019
    }

    @Test
    void getTeamStatsWithoutSeasonReturnsCombined() {
        String result = server.getTeamStats("Palmeiras", "brasileirao", null);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).contains("palmeiras");
    }

    @Test
    void getTeamStatsContainsTeamName() {
        String result = server.getTeamStats("Santos", "brasileirao", 2021);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).contains("santos");
    }

    private int extractNumber(String text, String keyword) {
        String lower = text.toLowerCase();
        int idx = lower.indexOf(keyword);
        if (idx < 0) return 0;
        // Look for digits AFTER the keyword (within 20 chars after)
        String window = text.substring(idx, Math.min(text.length(), idx + 20));
        java.util.regex.Matcher m = java.util.regex.Pattern.compile("\\d+").matcher(window);
        if (m.find()) {
            return Integer.parseInt(m.group());
        }
        return 0;
    }
}
