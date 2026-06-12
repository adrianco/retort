package com.example.brsoccer.model;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class TeamNamesTest {

    @Test
    void stripsTrailingStateSuffixWithHyphen() {
        assertEquals("Palmeiras", TeamNames.displayName("Palmeiras-SP"));
        assertEquals("Flamengo", TeamNames.displayName("Flamengo-RJ"));
    }

    @Test
    void stripsTrailingCountrySuffixWithHyphen() {
        assertEquals("Barcelona", TeamNames.displayName("Barcelona-EQU"));
    }

    @Test
    void stripsSpacedHyphenStateSuffix() {
        assertEquals("América", TeamNames.displayName("América - MG"));
    }

    @Test
    void stripsParentheticalCountryCode() {
        assertEquals("Nacional", TeamNames.displayName("Nacional (URU)"));
    }

    @Test
    void leavesPlainNameUnchanged() {
        assertEquals("Santos", TeamNames.displayName("Santos"));
    }

    @Test
    void canonicalKeyIsLowercaseAndAccentInsensitive() {
        assertEquals(TeamNames.canonicalKey("São Paulo"), TeamNames.canonicalKey("Sao Paulo"));
        assertEquals(TeamNames.canonicalKey("Grêmio"), TeamNames.canonicalKey("Gremio"));
    }

    @Test
    void canonicalKeyIgnoresStateSuffix() {
        assertEquals(TeamNames.canonicalKey("Palmeiras"), TeamNames.canonicalKey("Palmeiras-SP"));
        assertEquals(TeamNames.canonicalKey("Flamengo"), TeamNames.canonicalKey("Flamengo - RJ"));
    }

    @Test
    void canonicalKeyCollapsesWhitespace() {
        assertEquals(TeamNames.canonicalKey("Sao  Paulo"), TeamNames.canonicalKey("Sao Paulo"));
    }

    @Test
    void keepsDistinctClubsThatShareABaseNameButDifferInState() {
        // Atlético Mineiro, Paranaense and Goianiense are three different clubs.
        assertNotEquals(TeamNames.canonicalKey("Atletico-MG"), TeamNames.canonicalKey("Atletico-PR"));
        assertNotEquals(TeamNames.canonicalKey("Atletico-MG"), TeamNames.canonicalKey("Atletico-GO"));
        assertNotEquals(TeamNames.canonicalKey("America-MG"), TeamNames.canonicalKey("America-RN"));
    }

    @Test
    void unifiesHyphenAndFullNameSpellingsOfTheSameClub() {
        assertEquals(TeamNames.canonicalKey("Atletico-MG"), TeamNames.canonicalKey("Atlético Mineiro"));
        assertEquals(TeamNames.canonicalKey("Athletico-PR"), TeamNames.canonicalKey("Atletico Paranaense"));
        assertEquals(TeamNames.canonicalKey("Atletico-GO"), TeamNames.canonicalKey("Atletico Goianiense"));
    }

    @Test
    void matchesOnSharedCanonicalKey() {
        assertTrue(TeamNames.matches("Palmeiras-SP", "palmeiras"));
        assertTrue(TeamNames.matches("São Paulo", "sao paulo"));
        assertFalse(TeamNames.matches("Santos", "Flamengo"));
    }
}
