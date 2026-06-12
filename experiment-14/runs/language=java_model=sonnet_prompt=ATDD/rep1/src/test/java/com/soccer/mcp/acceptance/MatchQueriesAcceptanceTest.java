package com.soccer.mcp.acceptance;

import com.soccer.mcp.BrazilianSoccerMcpServer;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Acceptance tests for match query functionality.
 * Tests exercise only the public MCP tool methods of BrazilianSoccerMcpServer.
 */
public class MatchQueriesAcceptanceTest {

    private static BrazilianSoccerMcpServer server;

    @BeforeAll
    static void setUp() {
        server = new BrazilianSoccerMcpServer();
    }

    @Test
    void findMatchesByHomeAndAwayTeam() {
        String result = server.findMatches(null, "Flamengo", "Fluminense", null, null, null, null, 10);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).contains("flamengo");
        assertThat(result.toLowerCase()).contains("fluminense");
        // Should contain goal scores
        assertThat(result).containsPattern("\\d+");
    }

    @Test
    void findMatchesByTeamOnEitherSide() {
        String result = server.findMatches("Corinthians", null, null, null, null, null, null, 20);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).contains("corinthians");
        // Should have multiple matches
        assertThat(result.split("\n").length).isGreaterThan(3);
    }

    @Test
    void findMatchesByCompetition() {
        String result = server.findMatches(null, null, null, "brasileirao", null, null, null, 10);
        assertThat(result).isNotEmpty();
        // Should contain match data
        assertThat(result).containsPattern("\\d+-\\d+");
    }

    @Test
    void findMatchesBySeason() {
        String result = server.findMatches(null, null, null, "brasileirao", 2019, null, null, 10);
        assertThat(result).isNotEmpty();
        assertThat(result).contains("2019");
    }

    @Test
    void findMatchesByDateRange() {
        String result = server.findMatches(null, null, null, null, null, "2019-01-01", "2019-12-31", 20);
        assertThat(result).isNotEmpty();
        assertThat(result).contains("2019");
    }

    @Test
    void findMatchesReturnsGoalScores() {
        String result = server.findMatches("Palmeiras", null, null, "brasileirao", 2022, null, null, 5);
        assertThat(result).isNotEmpty();
        // Should include score information (digits for goals)
        assertThat(result).containsPattern("\\d");
    }

    @Test
    void findMatchesWithLimitRespected() {
        String result = server.findMatches(null, null, null, "brasileirao", 2019, null, null, 5);
        assertThat(result).isNotEmpty();
        // Limit of 5 should give us at most 5 match lines
        long matchLines = java.util.Arrays.stream(result.split("\n"))
                .filter(line -> line.contains("-") && line.matches(".*\\d+.*"))
                .count();
        assertThat(matchLines).isLessThanOrEqualTo(5);
    }

    @Test
    void findMatchesForLibertadores() {
        String result = server.findMatches("Flamengo", null, null, "libertadores", null, null, null, 10);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).contains("flamengo");
    }

    @Test
    void findMatchesForCopaDoBrasil() {
        String result = server.findMatches("Flamengo", null, null, "copa", null, null, null, 10);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).contains("flamengo");
    }
}
