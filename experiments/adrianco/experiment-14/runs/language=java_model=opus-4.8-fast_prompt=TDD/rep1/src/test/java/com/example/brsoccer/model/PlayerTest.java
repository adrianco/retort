package com.example.brsoccer.model;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class PlayerTest {

    private Player neymar() {
        return new Player(190871, "Neymar Jr", 27, "Brazil", 92, 93,
                "Paris Saint-Germain", "LW", 10);
    }

    @Test
    void exposesCoreAttributes() {
        Player p = neymar();
        assertEquals("Neymar Jr", p.name());
        assertEquals("Brazil", p.nationality());
        assertEquals(92, p.overall());
        assertEquals("Paris Saint-Germain", p.club());
    }

    @Test
    void isBrazilianIgnoresCase() {
        assertTrue(neymar().isBrazilian());
        assertFalse(new Player(1, "L. Messi", 31, "Argentina", 94, 94,
                "FC Barcelona", "RF", 10).isBrazilian());
    }

    @Test
    void nameMatchesSubstringCaseAndAccentInsensitive() {
        Player p = new Player(1, "Éderson", 25, "Brazil", 88, 90, "Manchester City", "GK", 31);
        assertTrue(p.nameMatches("eder"));
        assertTrue(p.nameMatches("EDERSON"));
        assertFalse(p.nameMatches("messi"));
    }

    @Test
    void playsForMatchesClubSubstringIgnoringAccents() {
        Player p = new Player(1, "Pedro", 26, "Brazil", 80, 84, "Flamengo", "ST", 9);
        assertTrue(p.playsFor("flamengo"));
        assertTrue(p.playsFor("FLA"));
        assertFalse(p.playsFor("Santos"));
    }
}
