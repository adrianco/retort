/*
 * ============================================================================
 *  Brazilian Soccer MCP Server - Tests
 * ----------------------------------------------------------------------------
 *  File    : TeamNamesTest.java
 *  Purpose : Verify club-name normalization across the dataset spellings.
 *  Context : Name normalization is the linchpin of cross-dataset matching;
 *            these tests pin down suffix stripping, accent folding, aliasing
 *            and — critically — that ambiguous clubs (the three Atléticos) do
 *            NOT collapse into one key.
 * ============================================================================
 */
package com.brasileirao.mcp;

import com.brasileirao.mcp.util.TeamNames;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TeamNamesTest {

    @Test
    void stripsStateSuffixForUnambiguousClubs() {
        assertEquals(TeamNames.canonical("Palmeiras"), TeamNames.canonical("Palmeiras-SP"));
        assertEquals(TeamNames.canonical("Flamengo"), TeamNames.canonical("Flamengo-RJ"));
        assertEquals(TeamNames.canonical("Sao Paulo"), TeamNames.canonical("São Paulo-SP"));
    }

    @Test
    void foldsAccents() {
        assertEquals(TeamNames.canonical("Gremio"), TeamNames.canonical("Grêmio"));
        assertEquals("sao paulo", TeamNames.canonical("São Paulo"));
    }

    @Test
    void appliesLongNameAliases() {
        assertEquals(TeamNames.canonical("Corinthians"),
                TeamNames.canonical("Sport Club Corinthians Paulista"));
        assertEquals(TeamNames.canonical("Vasco"), TeamNames.canonical("Vasco da Gama"));
    }

    @Test
    void keepsAmbiguousClubsDistinct() {
        String mg = TeamNames.canonical("Atletico-MG");
        String pr = TeamNames.canonical("Atletico-PR");
        String go = TeamNames.canonical("Atletico-GO");
        assertNotEquals(mg, pr);
        assertNotEquals(mg, go);
        assertNotEquals(pr, go);
    }

    @Test
    void unifiesAtleticoSpellingsToSameKey() {
        assertEquals(TeamNames.canonical("Atletico-MG"), TeamNames.canonical("Atletico Mineiro"));
        assertEquals(TeamNames.canonical("Atletico-MG"), TeamNames.canonical("Atlético-MG"));
        assertEquals(TeamNames.canonical("Atletico-PR"), TeamNames.canonical("Athletico Paranaense"));
        assertEquals(TeamNames.canonical("America-MG"), TeamNames.canonical("America MG"));
    }

    @Test
    void countrySuffixHandled() {
        assertEquals("nacional uru", TeamNames.canonical("Nacional (URU)"));
        assertEquals("barcelona equ", TeamNames.canonical("Barcelona-EQU"));
    }

    @Test
    void sameTeamHelper() {
        assertTrue(TeamNames.sameTeam("Flamengo-RJ", "Clube de Regatas do Flamengo"));
        assertFalse(TeamNames.sameTeam("Atletico-MG", "Atletico-PR"));
    }

    @Test
    void displayKeepsAmbiguousSuffix() {
        assertEquals("Palmeiras", TeamNames.display("Palmeiras-SP"));
        assertEquals("Atletico-MG", TeamNames.display("Atletico-MG"));
    }
}
