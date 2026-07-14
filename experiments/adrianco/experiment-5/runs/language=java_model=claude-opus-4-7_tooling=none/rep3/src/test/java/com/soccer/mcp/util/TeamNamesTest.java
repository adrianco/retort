package com.soccer.mcp.util;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TeamNamesTest {

    @Test
    void givenNameWithStateSuffix_whenNormalized_thenSuffixStripped() {
        assertEquals("palmeiras", TeamNames.normalize("Palmeiras-SP"));
        assertEquals("flamengo", TeamNames.normalize("Flamengo-RJ"));
    }

    @Test
    void givenAccentedName_whenNormalized_thenAccentsStripped() {
        assertEquals("sao paulo", TeamNames.normalize("São Paulo"));
        assertEquals("gremio", TeamNames.normalize("Grêmio"));
    }

    @Test
    void givenLongFormCorinthiansName_whenNormalized_thenAliasedToShortForm() {
        assertEquals("corinthians", TeamNames.normalize("Sport Club Corinthians Paulista"));
    }

    @Test
    void givenCountrySuffixInParens_whenNormalized_thenParenStripped() {
        assertEquals("nacional", TeamNames.normalize("Nacional (URU)"));
    }

    @Test
    void givenDifferentSpellingsOfSamteTeam_whenMatched_thenTrue() {
        assertTrue(TeamNames.matches("Palmeiras-SP", "Palmeiras"));
        assertTrue(TeamNames.matches("São Paulo", "Sao Paulo"));
    }
}
