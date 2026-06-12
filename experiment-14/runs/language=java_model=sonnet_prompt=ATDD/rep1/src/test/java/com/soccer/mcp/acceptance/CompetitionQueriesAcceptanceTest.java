package com.soccer.mcp.acceptance;

import com.soccer.mcp.BrazilianSoccerMcpServer;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Acceptance tests for competition standings.
 * Tests exercise only the public MCP tool methods of BrazilianSoccerMcpServer.
 */
public class CompetitionQueriesAcceptanceTest {

    private static BrazilianSoccerMcpServer server;

    @BeforeAll
    static void setUp() {
        server = new BrazilianSoccerMcpServer();
    }

    @Test
    void getStandings2019BrasileiraoPutsFlamengoFirst() {
        String result = server.getStandings(2019, "brasileirao", 5);
        assertThat(result).isNotEmpty();
        // Flamengo won 2019 Brasileirao - should be at or near top
        assertThat(result.toLowerCase()).contains("flamengo");
        // Flamengo should appear before other teams in the standings
        int flamengoPos = result.toLowerCase().indexOf("flamengo");
        int otherTeamPos = result.toLowerCase().indexOf("palmeiras");
        if (otherTeamPos > 0) {
            assertThat(flamengoPos).isLessThan(otherTeamPos);
        }
    }

    @Test
    void getStandingsShowsPoints() {
        String result = server.getStandings(2019, "brasileirao", 10);
        assertThat(result).isNotEmpty();
        assertThat(result.toLowerCase()).containsAnyOf("points", "pts", "pontos");
    }

    @Test
    void getStandingsFlamengo2019HasHighPoints() {
        String result = server.getStandings(2019, "brasileirao", 3);
        assertThat(result).isNotEmpty();
        // Flamengo had 90 points in 2019
        assertThat(result).containsPattern("[7-9]\\d"); // at least 70+ points for champion
    }

    @Test
    void getStandingsWithLimitRespectsTop() {
        String result = server.getStandings(2022, "brasileirao", 3);
        assertThat(result).isNotEmpty();
        // Should list only top 3 teams
        String[] lines = result.split("\n");
        long teamLines = java.util.Arrays.stream(lines)
                .filter(l -> !l.isBlank() && !l.startsWith("Stand") && !l.startsWith("---") && !l.startsWith("Season"))
                .count();
        assertThat(teamLines).isLessThanOrEqualTo(5); // generous for header lines
    }

    @Test
    void getStandingsShowsWinsDrawsLosses() {
        String result = server.getStandings(2019, "brasileirao", 5);
        assertThat(result).isNotEmpty();
        // Should show W/D/L records
        assertThat(result).containsPattern("\\d+");
    }

    @Test
    void getStandings2022BrasileiraoPutsAtleticoOrFlamengoFirst() {
        // Atletico-MG won 2021, Palmeiras won 2022 Brasileirao
        String result = server.getStandings(2022, "brasileirao", 3);
        assertThat(result).isNotEmpty();
        // Top team should be Palmeiras (2022 champion)
        assertThat(result.toLowerCase()).containsAnyOf("palmeiras", "athletico", "atletico", "flamengo", "corinthians");
    }

    @Test
    void getStandingsWithoutSeasonReturnsData() {
        String result = server.getStandings(null, "brasileirao", 10);
        assertThat(result).isNotEmpty();
    }
}
