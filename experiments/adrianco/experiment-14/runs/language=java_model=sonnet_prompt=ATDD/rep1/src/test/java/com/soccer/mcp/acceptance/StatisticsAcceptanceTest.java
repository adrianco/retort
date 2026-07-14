package com.soccer.mcp.acceptance;

import com.soccer.mcp.BrazilianSoccerMcpServer;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Acceptance tests for statistics and head-to-head queries.
 * Tests exercise only the public MCP tool methods of BrazilianSoccerMcpServer.
 */
public class StatisticsAcceptanceTest {

    private static BrazilianSoccerMcpServer server;

    @BeforeAll
    static void setUp() {
        server = new BrazilianSoccerMcpServer();
    }

    @Test
    void getHeadToHeadFlamengVsFluminense() {
        String result = server.getHeadToHead("Flamengo", "Fluminense", null, null);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).contains("flamengo");
        assertThat(result.toLowerCase()).contains("fluminense");
    }

    @Test
    void getHeadToHeadContainsWinRecord() {
        String result = server.getHeadToHead("Flamengo", "Fluminense", null, null);
        assertThat(result).isNotEmpty();
        // Should include win/draw/loss info
        assertThat(result.toLowerCase()).containsAnyOf("win", "draw", "loss", "won", "total");
    }

    @Test
    void getHeadToHeadHasMatchCount() {
        String result = server.getHeadToHead("Corinthians", "Palmeiras", null, null);
        assertThat(result).isNotEmpty();
        assertThat(result).containsPattern("\\d+");
        // Both teams should be mentioned
        assertThat(result.toLowerCase()).contains("corinthians");
        assertThat(result.toLowerCase()).contains("palmeiras");
    }

    @Test
    void getHeadToHeadFilteredByCompetition() {
        String result = server.getHeadToHead("Flamengo", "Fluminense", "brasileirao", null);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).containsAnyOf("flamengo", "fluminense");
    }

    @Test
    void getStatisticsBiggestWins() {
        String result = server.getStatistics("biggest_wins", "brasileirao", null);
        assertThat(result).isNotEmpty();
        // Biggest wins should show matches with large goal margins
        assertThat(result).containsPattern("\\d+");
    }

    @Test
    void getStatisticsAvgGoals() {
        String result = server.getStatistics("avg_goals", "brasileirao", null);
        assertThat(result).isNotEmpty();
        // Average goals should contain a decimal number
        assertThat(result).containsPattern("\\d+\\.\\d+");
    }

    @Test
    void getStatisticsHomeRecord() {
        String result = server.getStatistics("home_record", "brasileirao", null);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).containsAnyOf("home", "win", "rate", "%");
    }

    @Test
    void getStatisticsBiggestWinsShowsHighScores() {
        String result = server.getStatistics("biggest_wins", "brasileirao", 2019);
        assertThat(result).isNotEmpty();
        // Should contain high-scoring matches (margins >= 4)
        assertThat(result).containsPattern("[4-9]|[1-9]\\d");
    }

    @Test
    void getStatisticsAvgGoalsPerSeason() {
        String result = server.getStatistics("avg_goals", "brasileirao", 2022);
        assertThat(result).isNotEmpty();
        assertThat(result).contains("2022");
    }
}
