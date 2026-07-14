/*
 * ============================================================================
 * TeamNamesTest.java
 * ============================================================================
 * Context:
 *   Unit coverage for the team-name normalization rules, including the critical
 *   requirement that distinct clubs sharing a base name (Atlético-MG vs
 *   Atlético-PR) must NOT collapse to the same key, while accent and suffix
 *   variations of the SAME query still match via substring logic.
 * ============================================================================
 */
package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.data.TeamNames;
import com.brazilsoccer.mcp.query.MatchService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class TeamNamesTest {

    @Test
    @DisplayName("Given accented names, When keyed, Then accents are removed")
    void accentsRemoved() {
        assertEquals("saopaulosp", TeamNames.key("São Paulo-SP"));
        assertEquals("gremio", TeamNames.key("Grêmio"));
        assertEquals("avaisc", TeamNames.key("Avaí-SC"));
    }

    @Test
    @DisplayName("Given quoted raw names, When displayed, Then quotes are stripped but suffix kept")
    void displayStripsQuotesKeepsSuffix() {
        assertEquals("Palmeiras-SP", TeamNames.display("\"Palmeiras-SP\""));
        assertEquals("Flamengo-RJ", TeamNames.display("Flamengo-RJ"));
    }

    @Test
    @DisplayName("Given sibling clubs, When keyed, Then they stay distinct")
    void siblingClubsStayDistinct() {
        // Atlético Mineiro / Goianiense / Paranaense must not merge.
        assertNotEquals(TeamNames.key("Atlético-MG"), TeamNames.key("Atlético-GO"));
        assertNotEquals(TeamNames.key("Atlético-MG"), TeamNames.key("Atlético-PR"));
        assertNotEquals(TeamNames.key("América-MG"), TeamNames.key("América-RN"));
    }

    @Test
    @DisplayName("Given a base-name query, When matched, Then it finds the suffixed key")
    void baseNameQueryMatchesSuffixedKey() {
        // "Flamengo" should match "flamengorj" via substring matching.
        assertTrue(MatchService.keyMatches(TeamNames.key("Flamengo-RJ"), TeamNames.key("Flamengo")));
        // "Sao Paulo" (no accent) should match "São Paulo-SP".
        assertTrue(MatchService.keyMatches(TeamNames.key("São Paulo-SP"), TeamNames.key("Sao Paulo")));
        // But a wrong team should not match.
        assertFalse(MatchService.keyMatches(TeamNames.key("Santos"), TeamNames.key("Flamengo")));
    }
}
