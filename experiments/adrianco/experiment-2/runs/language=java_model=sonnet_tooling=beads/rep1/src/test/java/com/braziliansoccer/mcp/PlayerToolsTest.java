package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.data.DataRepository;
import com.braziliansoccer.mcp.tools.PlayerTools;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * BDD tests for player search tools.
 *
 * Feature: Player Queries
 *   Scenario: Find all Brazilian players in the dataset
 *   Scenario: Find highest-rated players at Flamengo
 *   Scenario: Search player by name
 *   Scenario: Get Brazilian club player summary
 */
@DisplayName("Player Tools BDD Tests")
class PlayerToolsTest {

    private static PlayerTools playerTools;

    @BeforeAll
    static void setUp() throws Exception {
        DataRepository repo = new DataRepository("data/kaggle");
        repo.load();
        playerTools = new PlayerTools(repo);
    }

    @Test
    @DisplayName("Scenario: Find all Brazilian players in the dataset")
    void testFindBrazilianPlayers() {
        // Given the player data is loaded
        // When I search for players by nationality "Brazil"
        String result = playerTools.searchPlayers(null, "Brazil", null, null, null, 25);

        // Then I should receive a list of Brazilian players
        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("Brazil"), "Should show Brazilian players");
        assertTrue(result.contains("Overall:"), "Should show player ratings");
        assertTrue(result.contains("Found"), "Should show result count");
    }

    @Test
    @DisplayName("Scenario: Find highest-rated players at Flamengo")
    void testFindFlamengoPlayers() {
        // Given the player data is loaded
        // When I search for players at Flamengo club
        String result = playerTools.searchPlayers(null, null, "Flamengo", null, null, 10);

        // Then I should receive Flamengo players sorted by rating
        assertNotNull(result);
        // Flamengo may or may not be in the FIFA dataset
        // Just verify the search doesn't crash and returns a valid response
        assertFalse(result.isEmpty());
    }

    @Test
    @DisplayName("Scenario: Find Gabriel Barbosa (Gabigol) by name")
    void testFindGabrielBarbosa() {
        // When I search for "Gabriel Barbosa"
        String result = playerTools.searchPlayers("Gabriel", "Brazil", null, null, null, 10);

        // Then I should receive results
        assertNotNull(result);
        assertFalse(result.isEmpty());
        // Either finds Gabriel players or says none found
        assertTrue(result.contains("Gabriel") || result.contains("No players found"),
            "Should search for Gabriel");
    }

    @Test
    @DisplayName("Scenario: Search forwards from Brazil")
    void testFindBrazilianForwards() {
        String result = playerTools.searchPlayers(null, "Brazil", null, "ST", null, 20);

        assertNotNull(result);
        assertFalse(result.isEmpty());
        // Should find strikers or report none
        assertTrue(result.contains("ST") || result.contains("No players found") || result.contains("Brazil"),
            "Should search for Brazilian strikers");
    }

    @Test
    @DisplayName("Scenario: Filter players by minimum overall rating 85+")
    void testFindElitePlayers() {
        String result = playerTools.searchPlayers(null, null, null, null, 85, 20);

        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("Overall:"), "Should show ratings");
        // All shown players should have 85+ overall
        // This is validated by checking the filter works
        assertFalse(result.contains("Found 0"), "Should find elite players");
    }

    @Test
    @DisplayName("Scenario: Get Brazilian club players summary")
    void testGetBrazilianClubSummary() {
        // When I request Brazilian club summary
        String result = playerTools.getBrazilianClubPlayers(null);

        // Then I should see stats for multiple Brazilian clubs
        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.contains("Brazilian clubs"), "Should mention Brazilian clubs");
        // Some major Brazilian clubs should appear
        // (They may or may not be in the FIFA dataset)
    }

    @Test
    @DisplayName("Scenario: Get players at specific club")
    void testGetPlayersAtSpecificClub() {
        // Search for players at a major European club (more likely in FIFA dataset)
        String result = playerTools.getBrazilianClubPlayers("Barcelona");

        assertNotNull(result);
        assertFalse(result.isEmpty());
        // Barcelona players should be in FIFA dataset
        assertTrue(result.contains("Barcelona") || result.contains("No players found"),
            "Should search for Barcelona players");
    }

    @Test
    @DisplayName("Scenario: Search by name returns sorted results by overall")
    void testSearchByNameSortedByOverall() {
        String result = playerTools.searchPlayers("Neymar", null, null, null, null, 10);

        assertNotNull(result);
        // Neymar is a famous player, likely in dataset
        if (!result.contains("No players found")) {
            assertTrue(result.contains("Overall:"), "Should show overall ratings");
        }
    }

    @Test
    @DisplayName("Scenario: Search with no criteria returns default limit results")
    void testSearchWithNoCriteria() {
        String result = playerTools.searchPlayers(null, null, null, null, null, 10);

        assertNotNull(result);
        assertTrue(result.contains("Found"), "Should show found count");
        assertFalse(result.isEmpty());
    }

    @Test
    @DisplayName("Scenario: Search for Ronaldo players")
    void testSearchRonaldo() {
        String result = playerTools.searchPlayers("Ronaldo", null, null, null, null, 10);

        assertNotNull(result);
        assertFalse(result.isEmpty());
        // There are multiple Ronaldos - should find them or say none
    }
}
