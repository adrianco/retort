/*
 * ============================================================================
 * TeamNamesTest - unit tests for name normalisation (BDD Given/When/Then)
 * ============================================================================
 * Context:
 *   Pure-function tests (no data load) for the normalisation rules that
 *   everything else depends on: stripping state suffixes for cross-dataset
 *   matching while keeping them for distinguishing same-base clubs, and folding
 *   Portuguese accents.
 * ============================================================================
 */
package com.brasilsoccer.mcp.util;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

@DisplayName("Feature: Team name normalisation")
class TeamNamesTest {

    @Test
    @DisplayName("Given variant spellings of one club, When base-keyed, Then they unify")
    void baseKeyUnifiesVariants() {
        assertEquals(TeamNames.baseKey("Palmeiras-SP"), TeamNames.baseKey("Palmeiras"));
        assertEquals(TeamNames.baseKey("Palmeiras"), TeamNames.baseKey("palmeiras"));
        assertEquals(TeamNames.baseKey("America - MG"), TeamNames.baseKey("America"));
    }

    @Test
    @DisplayName("Given two clubs sharing a base name, When full-keyed, Then they stay distinct")
    void fullKeyKeepsStateDistinct() {
        assertNotEquals(TeamNames.fullKey("Atletico-MG"), TeamNames.fullKey("Atletico-PR"));
        // ...but their base names collide, which is exactly why standings use full keys.
        assertEquals(TeamNames.baseKey("Atletico-MG"), TeamNames.baseKey("Atletico-PR"));
    }

    @Test
    @DisplayName("Given accented Portuguese text, When normalised, Then accents are folded")
    void normalisesAccents() {
        assertEquals("sao paulo", TeamNames.normalize("São Paulo"));
        assertEquals("gremio", TeamNames.normalize("Grêmio"));
        assertEquals("avai", TeamNames.normalize("Avaí"));
    }

    @Test
    @DisplayName("Given parentheticals and suffixes, When display-formatted, Then parens drop")
    void displayDropsParentheticals() {
        assertEquals("Nacional", TeamNames.displayFull("Nacional (URU)"));
        assertEquals("Boavista Sport Club - RJ",
                TeamNames.displayFull("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"));
    }
}
