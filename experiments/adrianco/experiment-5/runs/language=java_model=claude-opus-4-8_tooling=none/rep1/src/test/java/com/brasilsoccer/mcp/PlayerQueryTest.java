/*
 * ============================================================================
 * PlayerQueryTest - BDD scenarios for player search (spec category 3)
 * ============================================================================
 * Context:
 *   Verifies searching FIFA players by name, nationality, club and rating, and
 *   that results are sorted by overall rating by default. Uses stable, well-known
 *   facts (Neymar Jr is a 92-rated Brazilian) where exact assertions are safe.
 * ============================================================================
 */
package com.brasilsoccer.mcp;

import com.brasilsoccer.mcp.data.KnowledgeBase;
import com.brasilsoccer.mcp.model.Player;
import com.brasilsoccer.mcp.query.Results;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Player queries")
class PlayerQueryTest {

    private final KnowledgeBase kb = TestData.kb();

    @Test
    @DisplayName("Given a name, When searching 'Neymar', Then the Brazilian forward is found")
    void searchByName() {
        Results.PlayerSearch r = kb.searchPlayers("Neymar", null, null, null, null, null, 10);
        assertFalse(r.players().isEmpty());
        Player neymar = r.players().get(0);
        assertTrue(neymar.name().toLowerCase().contains("neymar"));
        assertEquals("Brazil", neymar.nationality());
        assertTrue(neymar.overall() >= 90, "Neymar should be highly rated");
    }

    @Test
    @DisplayName("Given nationality Brazil, When searched, Then all results are Brazilian")
    void searchByNationality() {
        Results.PlayerSearch r = kb.searchPlayers(null, "Brazil", null, null, null, null, 0);
        assertTrue(r.totalFound() > 500, "FIFA data has many Brazilians");
        for (Player p : r.players()) {
            assertEquals("Brazil", p.nationality());
        }
    }

    @Test
    @DisplayName("Given default sort, When searching by nationality, Then sorted by overall desc")
    void resultsSortedByOverall() {
        Results.PlayerSearch r = kb.searchPlayers(null, "Brazil", null, null, null, null, 20);
        for (int i = 1; i < r.players().size(); i++) {
            assertTrue(r.players().get(i - 1).overall() >= r.players().get(i).overall(),
                    "results must be sorted by overall rating descending");
        }
    }

    @Test
    @DisplayName("Given a minimum rating, When filtered, Then every player meets the threshold")
    void filterByMinOverall() {
        Results.PlayerSearch r = kb.searchPlayers(null, "Brazil", null, null, 85, null, 0);
        assertFalse(r.players().isEmpty());
        for (Player p : r.players()) {
            assertTrue(p.overall() >= 85);
        }
    }

    @Test
    @DisplayName("Given a club, When searching players, Then results belong to that club")
    void searchByClub() {
        // Note: FIFA 19 only licensed some Brazilian clubs (e.g. Gremio, Santos,
        // Botafogo); Flamengo/Palmeiras are absent. Accent-insensitive matching
        // means the query "Gremio" finds the club stored as "Grêmio".
        Results.PlayerSearch r = kb.searchPlayers(null, null, "Gremio", null, null, null, 0);
        assertFalse(r.players().isEmpty(), "Gremio should have players in FIFA data");
        for (Player p : r.players()) {
            assertTrue(p.clubKey().contains("gremio"), "club mismatch: " + p.club());
        }
    }
}
