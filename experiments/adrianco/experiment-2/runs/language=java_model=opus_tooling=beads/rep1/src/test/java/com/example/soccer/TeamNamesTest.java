package com.example.soccer;

import com.example.soccer.data.TeamNames;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class TeamNamesTest {
    @Test void stripsStateSuffix() {
        assertEquals(TeamNames.normalize("Palmeiras"), TeamNames.normalize("Palmeiras-SP"));
        assertEquals(TeamNames.normalize("Flamengo"), TeamNames.normalize("Flamengo-RJ"));
    }

    @Test void matchesLooseQuery() {
        assertTrue(TeamNames.matches("Palmeiras-SP", "Palmeiras"));
        assertTrue(TeamNames.matches("São Paulo", "Sao Paulo"));
        assertFalse(TeamNames.matches("Corinthians", "Palmeiras"));
    }

    @Test void stripsCountryCode() {
        assertEquals(TeamNames.normalize("Nacional"), TeamNames.normalize("Nacional (URU)"));
    }
}
