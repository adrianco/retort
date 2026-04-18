package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.data.DataRepository;
import com.braziliansoccer.mcp.tools.MatchTools;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * BDD tests for match query tools.
 *
 * Feature: Match Queries
 *   Scenario: Find matches between two teams
 *   Scenario: Search matches by team name
 *   Scenario: Search matches by season
 *   Scenario: Search matches by competition
 *   Scenario: Get biggest wins
 */
@DisplayName("Match Tools BDD Tests")
class MatchToolsTest {

    private static MatchTools matchTools;

    @BeforeAll
    static void setUp() throws Exception {
        DataRepository repo = new DataRepository("data/kaggle");
        repo.load();
        matchTools = new MatchTools(repo);
    }

    @Test
    @DisplayName("Scenario: Find matches between Flamengo and Fluminense")
    void testHeadToHeadFlamengoFluminense() {
        // Given the match data is loaded
        // When I search for matches between "Flamengo" and "Fluminense"
        String result = matchTools.headToHead("Flamengo", "Fluminense", null, null);

        // Then I should receive a list of matches
        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("Flamengo"), "Result should mention Flamengo");
        assertTrue(result.contains("Fluminense"), "Result should mention Fluminense");
        // And should include head-to-head statistics
        assertTrue(result.contains("wins") || result.contains("Total matches"),
            "Result should include win statistics");
    }

    @Test
    @DisplayName("Scenario: Search Palmeiras matches in 2022")
    void testSearchPalmeiras2023() {
        // Given the match data is loaded
        // When I search for Palmeiras matches in 2022 (latest season in dataset)
        String result = matchTools.searchMatches("Palmeiras", 2022, null, null, null, null);

        // Then I should receive matches
        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("Palmeiras"), "Result should include Palmeiras matches");
    }

    @Test
    @DisplayName("Scenario: Find all Brasileirao matches")
    void testSearchBrasileiraoMatches() {
        // Given the match data is loaded
        // When I search for Brasileirao competition matches
        String result = matchTools.searchMatches(null, null, "Brasileirao", null, null, 10);

        // Then I should receive matches from Brasileirao
        assertNotNull(result);
        assertTrue(result.contains("Found") && result.contains("matches"),
            "Result should show match count");
        assertTrue(result.contains("Brasileirao"), "Should mention competition");
    }

    @Test
    @DisplayName("Scenario: Find Copa Libertadores matches")
    void testSearchLibertadoresMatches() {
        String result = matchTools.searchMatches(null, null, "Libertadores", null, null, 20);

        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("Libertadores"), "Should contain Libertadores matches");
    }

    @Test
    @DisplayName("Scenario: Get biggest victories in the dataset")
    void testGetBiggestWins() {
        // When I request biggest wins
        String result = matchTools.getBiggestWins(null, null, 10);

        // Then I should receive a ranked list
        assertNotNull(result);
        assertTrue(result.contains("Biggest victories"), "Should show biggest victories header");
        assertTrue(result.contains("1."), "Should have ranked entries");
    }

    @Test
    @DisplayName("Scenario: Search matches by date range")
    void testSearchByDateRange() {
        String result = matchTools.searchMatches(null, null, null, "2019-01-01", "2019-12-31", 50);

        assertNotNull(result);
        assertFalse(result.isEmpty());
        // Should find matches in 2019
        assertTrue(result.contains("2019"), "Should find matches in 2019");
    }

    @Test
    @DisplayName("Scenario: Head-to-head for Corinthians vs Palmeiras classic derby")
    void testCorinthiansPalmeirasH2H() {
        String result = matchTools.headToHead("Corinthians", "Palmeiras", null, null);

        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("Total matches"), "Should show total match count");
        // This is a famous derby, should have many matches
        assertFalse(result.contains("No matches found"), "Should find derby matches");
    }

    @Test
    @DisplayName("Scenario: Search with no filters returns results")
    void testSearchWithNoFilters() {
        String result = matchTools.searchMatches(null, null, null, null, null, 10);

        assertNotNull(result);
        assertTrue(result.contains("Found"), "Should return some results");
    }

    @Test
    @DisplayName("Scenario: Search for nonexistent team returns empty result message")
    void testSearchNonexistentTeam() {
        String result = matchTools.searchMatches("NonexistentTeamXYZ123", null, null, null, null, null);

        assertNotNull(result);
        assertTrue(result.contains("Found 0 matches") || result.contains("No matches"),
            "Should indicate no matches found");
    }

    @Test
    @DisplayName("Scenario: Head-to-head with required parameters missing returns error")
    void testHeadToHeadMissingParams() {
        String result = matchTools.headToHead(null, "Flamengo", null, null);

        assertNotNull(result);
        assertTrue(result.contains("Error") || result.contains("required"),
            "Should return error when team1 is missing");
    }
}
