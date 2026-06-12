package com.brazilsoccer.mcp;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/** Unit tests for team-name normalization (the basis for cross-dataset matching). */
class TeamNamesTest {

    @Test
    void strips_state_suffix_and_accents_into_a_stable_key() {
        // The same club spelled three different ways across datasets must share one key.
        String fromBrasileirao = TeamNames.identityKey("Flamengo-RJ", null);
        String fromNovo = TeamNames.identityKey("Flamengo", "RJ");
        String fromExtended = TeamNames.identityKey("Flamengo", null);

        assertEquals(fromBrasileirao, fromNovo);
        assertEquals("flamengo-rj", fromBrasileirao);
        // Without a state we still get a usable key that the others contain.
        assertTrue(fromBrasileirao.startsWith(fromExtended));
    }

    @Test
    void distinguishes_clubs_that_share_a_base_name_but_differ_by_state() {
        // Atletico Mineiro, Paranaense and Goianiense are different clubs.
        String mg = TeamNames.identityKey("Atletico-MG", null);
        String pr = TeamNames.identityKey("Atlético-PR", null);
        String go = TeamNames.identityKey("Atletico", "GO");

        assertNotEquals(mg, pr);
        assertNotEquals(mg, go);
        assertEquals("atletico-mg", mg);
        assertEquals("atletico-pr", pr);
    }

    @Test
    void normalizes_accents_and_case_for_matching() {
        assertEquals(TeamNames.matchKey("São Paulo"), TeamNames.matchKey("Sao Paulo"));
        assertEquals(TeamNames.matchKey("GRÊMIO"), TeamNames.matchKey("gremio"));
    }

    @Test
    void handles_country_code_parentheses_and_spaced_state_suffixes() {
        assertEquals("nacional", TeamNames.matchKey("Nacional (URU)"));
        assertEquals("america-mg", TeamNames.identityKey("América - MG", null));
    }
}
