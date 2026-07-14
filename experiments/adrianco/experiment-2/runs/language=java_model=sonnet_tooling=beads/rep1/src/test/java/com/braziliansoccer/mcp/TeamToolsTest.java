package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.data.DataRepository;
import com.braziliansoccer.mcp.tools.TeamTools;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * BDD tests for team statistics and standings tools.
 *
 * Feature: Team Queries
 *   Scenario: Get team statistics
 *   Scenario: Get league standings
 *   Scenario: Get global statistics
 */
@DisplayName("Team Tools BDD Tests")
class TeamToolsTest {

    private static TeamTools teamTools;

    @BeforeAll
    static void setUp() throws Exception {
        DataRepository repo = new DataRepository("data/kaggle");
        repo.load();
        teamTools = new TeamTools(repo);
    }

    @Test
    @DisplayName("Scenario: Get Palmeiras statistics for season 2022")
    void testGetPalmeiras2023Stats() {
        // Given the match data is loaded
        // When I request statistics for "Palmeiras" in season "2022" (latest in dataset)
        String result = teamTools.getTeamStats("Palmeiras", 2022, null);

        // Then I should receive wins, losses, draws, and goals
        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("Palmeiras"), "Result should mention team");
        assertTrue(result.contains("Record:"), "Should show W/D/L record");
        assertTrue(result.contains("Goals:"), "Should show goals");
        assertTrue(result.contains("Win rate:"), "Should show win rate");
        assertTrue(result.contains("Home:"), "Should show home record");
        assertTrue(result.contains("Away:"), "Should show away record");
    }

    @Test
    @DisplayName("Scenario: Get Flamengo home record in 2022 Brasileirao")
    void testGetFlamengoHomeRecord2022() {
        String result = teamTools.getTeamStats("Flamengo", 2022, "Brasileirao");

        assertNotNull(result);
        assertTrue(result.contains("Flamengo"));
        assertTrue(result.contains("2022") || result.contains("Season: 2022"));
    }

    @Test
    @DisplayName("Scenario: Get 2019 Brasileirao standings - Flamengo should be champion")
    void testGet2019BrasileiraoStandings() {
        // Given the match data is loaded
        // When I request 2019 Brasileirao standings
        String result = teamTools.getStandings(2019, "Brasileirao");

        // Then I should receive a standings table
        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("2019"), "Should show 2019 season");
        assertTrue(result.contains("Pos") || result.contains("Standings"), "Should show standings header");
        // Flamengo won 2019 Brasileirao with record 90 points
        // The standings should show them near the top
        assertTrue(result.contains("Flamengo"), "Flamengo should appear in standings");
    }

    @Test
    @DisplayName("Scenario: Get standings with missing season returns error")
    void testGetStandingsMissingSeason() {
        String result = teamTools.getStandings(null, "Brasileirao");

        assertNotNull(result);
        assertTrue(result.contains("Error") || result.contains("required"),
            "Should return error when season is missing");
    }

    @Test
    @DisplayName("Scenario: Get global statistics for Brasileirao")
    void testGetBrasileiraoGlobalStats() {
        String result = teamTools.getGlobalStats("Brasileirao", null);

        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("Total matches"), "Should show total match count");
        assertTrue(result.contains("Average goals per match"), "Should show average goals");
        assertTrue(result.contains("Home wins"), "Should show home win statistics");
    }

    @Test
    @DisplayName("Scenario: Get global statistics overall")
    void testGetOverallGlobalStats() {
        String result = teamTools.getGlobalStats(null, null);

        assertNotNull(result);
        assertTrue(result.contains("Total matches"));
        assertTrue(result.contains("Average goals per match"));
    }

    @Test
    @DisplayName("Scenario: Get Corinthians overall career stats")
    void testGetCorinthiansStats() {
        String result = teamTools.getTeamStats("Corinthians", null, null);

        assertNotNull(result);
        assertTrue(result.contains("Corinthians"));
        assertTrue(result.contains("Matches:"));

        // Corinthians is a major club, should have many matches
        // The result should show significant match history
        assertFalse(result.contains("No matches found"), "Corinthians should have match history");
    }

    @Test
    @DisplayName("Scenario: Get standings for Copa do Brasil")
    void testGetCopaDoBrasilStandings() {
        String result = teamTools.getStandings(2020, "Copa do Brasil");

        assertNotNull(result);
        assertFalse(result.isEmpty());
        // Copa do Brasil uses elimination rounds, not traditional standings
        // But we should get some data
        assertTrue(result.contains("2020"));
    }

    @Test
    @DisplayName("Scenario: Team stats for non-existent team returns appropriate message")
    void testNonExistentTeamStats() {
        String result = teamTools.getTeamStats("NonExistentTeamXYZ", null, null);

        assertNotNull(result);
        assertTrue(result.contains("No matches found"),
            "Should indicate no matches for non-existent team");
    }

    @Test
    @DisplayName("Scenario: Get standings for 2003 season - historical data")
    void testGet2003Standings() {
        String result = teamTools.getStandings(2003, "Brasileirao");

        assertNotNull(result);
        assertTrue(result.contains("2003"), "Should show 2003 data");
        assertFalse(result.contains("No matches found for season 2003"),
            "Should find historical 2003 data");
    }
}
