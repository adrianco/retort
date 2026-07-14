package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.data.TeamNameNormalizer;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for team name normalization.
 *
 * Feature: Team Name Normalization
 *   Scenario: Normalize team names with state suffixes
 *   Scenario: Match teams across different naming conventions
 */
@DisplayName("Team Name Normalizer Tests")
class TeamNameNormalizerTest {

    @Test
    @DisplayName("Scenario: Remove state suffix from Brasileirao team names")
    void testRemoveStateSuffix() {
        assertEquals("Palmeiras", TeamNameNormalizer.normalize("Palmeiras-SP"));
        assertEquals("Flamengo", TeamNameNormalizer.normalize("Flamengo-RJ"));
        assertEquals("Gremio", TeamNameNormalizer.normalize("Grêmio-RS"));
        assertEquals("Corinthians", TeamNameNormalizer.normalize("Corinthians-SP"));
    }

    @Test
    @DisplayName("Scenario: Normalize accent variations")
    void testNormalizeAccents() {
        assertEquals("Sao Paulo", TeamNameNormalizer.normalize("São Paulo-SP"));
        assertEquals("Sao Paulo", TeamNameNormalizer.normalize("São Paulo"));
        assertEquals("Atletico Mineiro", TeamNameNormalizer.normalize("Atlético-MG"));
        assertEquals("Vitoria", TeamNameNormalizer.normalize("Vitória-BA"));
    }

    @Test
    @DisplayName("Scenario: Match teams using partial name search")
    void testContainsTeam() {
        assertTrue(TeamNameNormalizer.containsTeam("Flamengo-RJ", "Flamengo"));
        assertTrue(TeamNameNormalizer.containsTeam("Palmeiras", "palmeiras"));
        assertTrue(TeamNameNormalizer.containsTeam("Sport Club Corinthians Paulista", "Corinthians"));
        assertFalse(TeamNameNormalizer.containsTeam("Flamengo", "Santos"));
    }

    @Test
    @DisplayName("Scenario: Match two team names that are same club")
    void testMatchesSameClub() {
        assertTrue(TeamNameNormalizer.matches("Flamengo-RJ", "Flamengo"));
        assertTrue(TeamNameNormalizer.matches("Palmeiras-SP", "Palmeiras"));
        assertFalse(TeamNameNormalizer.matches("Flamengo", "Santos"));
    }

    @Test
    @DisplayName("Scenario: Handle null and empty inputs gracefully")
    void testHandleNullAndEmpty() {
        assertNull(TeamNameNormalizer.normalize(null));
        assertFalse(TeamNameNormalizer.containsTeam(null, "Flamengo"));
        assertFalse(TeamNameNormalizer.containsTeam("Flamengo", null));
        assertFalse(TeamNameNormalizer.matches(null, "Flamengo"));
    }

    @Test
    @DisplayName("Scenario: Names without state suffix are returned unchanged if not in map")
    void testNoChange() {
        String result = TeamNameNormalizer.normalize("SomeUnknownTeam");
        assertEquals("SomeUnknownTeam", result);
    }

    @Test
    @DisplayName("Scenario: Normalize common Brazilian club abbreviations")
    void testAbbreviations() {
        // Test various known mappings
        assertEquals("Gremio", TeamNameNormalizer.normalize("Gremio-RS"));
        assertEquals("Internacional", TeamNameNormalizer.normalize("Internacional-RS"));
        assertEquals("Atletico Mineiro", TeamNameNormalizer.normalize("Atletico-MG"));
        assertEquals("Sport Recife", TeamNameNormalizer.normalize("Sport-PE"));
    }
}
