package com.brsoccer.mcp;

import com.brsoccer.mcp.model.Player;
import com.brsoccer.mcp.server.SoccerKnowledgeBase;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Player Queries")
class PlayerQueriesTest {

    @Nested
    @DisplayName("Scenario: Search by name")
    class ByName {
        @Test
        @DisplayName("Given the player data When I search for 'Neymar' Then results include a Brazilian forward")
        void neymar() {
            SoccerKnowledgeBase kb = TestData.get();
            List<Player> ps = kb.players().searchByName("Neymar");
            assertFalse(ps.isEmpty());
            assertTrue(ps.stream().anyMatch(p -> "Brazil".equalsIgnoreCase(p.getNationality())));
        }
    }

    @Nested
    @DisplayName("Scenario: Filter by nationality")
    class ByNationality {
        @Test
        @DisplayName("Given the player data When I filter by 'Brazil' Then I get many Brazilian players")
        void brazil() {
            SoccerKnowledgeBase kb = TestData.get();
            List<Player> ps = kb.players().byNationality("Brazil");
            assertTrue(ps.size() > 100, "Expect many Brazilian players, got " + ps.size());
            for (Player p : ps) {
                assertEquals("Brazil", p.getNationality());
            }
        }
    }

    @Nested
    @DisplayName("Scenario: Sort by overall rating")
    class TopRated {
        @Test
        @DisplayName("Given the player data When I ask for top 5 players Then they are sorted by overall rating descending")
        void top5() {
            SoccerKnowledgeBase kb = TestData.get();
            List<Player> ps = kb.players().topRated(5);
            assertEquals(5, ps.size());
            for (int i = 1; i < ps.size(); i++) {
                assertTrue(ps.get(i - 1).getOverall() >= ps.get(i).getOverall(),
                    "list must be sorted by overall desc");
            }
        }
    }
}
