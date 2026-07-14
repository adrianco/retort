package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.data.DataLoader;
import com.braziliansoccer.mcp.data.DataRepository;
import com.braziliansoccer.mcp.model.Match;
import com.braziliansoccer.mcp.model.Player;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for CSV data loading from all 6 datasets.
 *
 * BDD Scenarios:
 * Feature: Data Loading
 *   Scenario: All CSV files are loadable
 *     Given the data directory exists
 *     When I load each CSV file
 *     Then each file should return a non-empty list of records
 */
@DisplayName("Data Loading Tests")
class DataLoaderTest {

    private static final String DATA_DIR = "data/kaggle";
    private static DataLoader loader;

    @BeforeAll
    static void setUp() {
        loader = new DataLoader(DATA_DIR);
    }

    @Test
    @DisplayName("Scenario: Load Brasileirao matches - should return matches with required fields")
    void testLoadBrasileiraoMatches() throws IOException {
        // Given the data directory exists
        // When I load Brasileirao matches
        List<Match> matches = loader.loadBrasileiraoMatches();

        // Then I should receive a non-empty list
        assertFalse(matches.isEmpty(), "Brasileirao matches should not be empty");
        assertTrue(matches.size() > 100, "Should have many Brasileirao matches");

        // And each match should have required fields
        Match first = matches.get(0);
        assertNotNull(first.getHomeTeam(), "Home team should not be null");
        assertNotNull(first.getAwayTeam(), "Away team should not be null");
        assertEquals("Brasileirao Serie A", first.getCompetition());
        assertTrue(first.getSeason() > 2000, "Season should be a valid year");
    }

    @Test
    @DisplayName("Scenario: Load Copa do Brasil matches - should have round information")
    void testLoadCopaDoBrasilMatches() throws IOException {
        List<Match> matches = loader.loadCopaDoBrasilMatches();

        assertFalse(matches.isEmpty(), "Copa do Brasil matches should not be empty");
        assertEquals("Copa do Brasil", matches.get(0).getCompetition());

        // Check that rounds are present
        long matchesWithRound = matches.stream()
            .filter(m -> m.getRound() != null && !m.getRound().isBlank())
            .count();
        assertTrue(matchesWithRound > 0, "Some matches should have round information");
    }

    @Test
    @DisplayName("Scenario: Load Libertadores matches - should have stage information")
    void testLoadLibertadoresMatches() throws IOException {
        List<Match> matches = loader.loadLibertadoresMatches();

        assertFalse(matches.isEmpty(), "Libertadores matches should not be empty");
        assertEquals("Copa Libertadores", matches.get(0).getCompetition());

        // Check stage information
        long matchesWithStage = matches.stream()
            .filter(m -> m.getStage() != null && !m.getStage().isBlank())
            .count();
        assertTrue(matchesWithStage > 0, "Some matches should have stage information");
    }

    @Test
    @DisplayName("Scenario: Load extended match dataset - should have dates")
    void testLoadExtendedMatches() throws IOException {
        List<Match> matches = loader.loadExtendedMatches();

        assertFalse(matches.isEmpty(), "Extended match dataset should not be empty");
        assertTrue(matches.size() > 1000, "Extended dataset should have many matches");

        // Check date field
        long matchesWithDate = matches.stream()
            .filter(m -> m.getDatetime() != null && !m.getDatetime().isBlank())
            .count();
        assertTrue(matchesWithDate > matches.size() * 0.9, "Most matches should have dates");
    }

    @Test
    @DisplayName("Scenario: Load historical Brasileirao - dates converted from DD/MM/YYYY")
    void testLoadHistoricalMatches() throws IOException {
        List<Match> matches = loader.loadHistoricalMatches();

        assertFalse(matches.isEmpty(), "Historical matches should not be empty");
        assertTrue(matches.size() > 1000, "Historical dataset should have many matches");

        // Check date format conversion
        Match m = matches.stream()
            .filter(match -> match.getDatetime() != null)
            .findFirst()
            .orElse(null);
        assertNotNull(m, "Should find a match with datetime");
        // Date should be in YYYY-MM-DD format after conversion
        assertFalse(m.getDatetime().contains("/"),
            "Date should be converted from DD/MM/YYYY to YYYY-MM-DD: " + m.getDatetime());
    }

    @Test
    @DisplayName("Scenario: Load FIFA player data - Brazilian players should be present")
    void testLoadPlayers() throws IOException {
        List<Player> players = loader.loadPlayers();

        assertFalse(players.isEmpty(), "Player list should not be empty");
        assertTrue(players.size() > 1000, "Should have many players");

        // Check Brazilian players exist
        long brazilianPlayers = players.stream()
            .filter(p -> "Brazil".equals(p.getNationality()))
            .count();
        assertTrue(brazilianPlayers > 100, "Should have many Brazilian players");

        // Check required fields
        Player first = players.get(0);
        assertNotNull(first.getName(), "Player name should not be null");
        assertTrue(first.getOverall() > 0, "Overall rating should be positive");
    }

    @Test
    @DisplayName("Scenario: Data repository loads all datasets together")
    void testDataRepositoryLoadsAll() throws IOException {
        DataRepository repo = new DataRepository(DATA_DIR);
        repo.load();

        assertTrue(repo.isLoaded(), "Repository should be marked as loaded");
        assertTrue(repo.getAllMatches().size() > 5000, "Should have many combined matches");
        assertTrue(repo.getPlayers().size() > 1000, "Should have many players");
    }
}
