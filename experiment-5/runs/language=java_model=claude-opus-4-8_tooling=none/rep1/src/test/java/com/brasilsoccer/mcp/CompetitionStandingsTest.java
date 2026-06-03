/*
 * ============================================================================
 * CompetitionStandingsTest - BDD scenarios for calculated standings (category 4)
 * ============================================================================
 * Context:
 *   Verifies league tables computed purely from match results. Uses the 2019
 *   Brasileirao Serie A as a ground-truth fixture: 20 teams, 38 games each, and
 *   Flamengo as champion on 90 points (a historically verifiable result that the
 *   dataset reproduces). Also confirms same-base clubs (Atletico-MG/PR) are not
 *   merged - the key reason standings group on the state-qualified key.
 * ============================================================================
 */
package com.brasilsoccer.mcp;

import com.brasilsoccer.mcp.data.KnowledgeBase;
import com.brasilsoccer.mcp.query.Results;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Competition standings")
class CompetitionStandingsTest {

    private final KnowledgeBase kb = TestData.kb();

    @Test
    @DisplayName("Given 2019 Brasileirao, When standings calculated, Then Flamengo are champions")
    void champion2019() {
        Results.Standings s = kb.standings("Brasileirao", 2019);

        assertEquals(20, s.rows().size(), "Serie A has 20 teams");
        Results.StandingRow first = s.rows().get(0);
        assertEquals(1, first.position());
        assertTrue(first.team().toLowerCase().contains("flamengo"),
                "2019 champion should be Flamengo, was " + first.team());
        assertEquals(90, first.points(), "Flamengo finished 2019 on 90 points");
        assertEquals(38, first.played());
    }

    @Test
    @DisplayName("Given a calculated table, When inspected, Then rows are ordered by points")
    void rowsOrderedByPoints() {
        Results.Standings s = kb.standings("Brasileirao", 2019);
        for (int i = 1; i < s.rows().size(); i++) {
            assertTrue(s.rows().get(i - 1).points() >= s.rows().get(i).points(),
                    "standings must be in descending points order");
        }
    }

    @Test
    @DisplayName("Given clubs sharing a base name, When standings built, Then they are not merged")
    void sameBaseClubsStayDistinct() {
        Results.Standings s = kb.standings("Brasileirao", 2019);
        long atleticoRows = s.rows().stream()
                .filter(r -> r.team().toLowerCase().startsWith("atletico"))
                .count();
        assertEquals(2, atleticoRows, "Atletico-MG and Atletico-PR must be separate rows");
        // No single club can play more than 38 league games in a season.
        for (Results.StandingRow r : s.rows()) {
            assertTrue(r.played() <= 38, r.team() + " has impossible game count " + r.played());
        }
    }

    @Test
    @DisplayName("Given each standings row, When points recomputed, Then they match W*3+D")
    void pointsAreConsistent() {
        Results.Standings s = kb.standings("Brasileirao", 2019);
        for (Results.StandingRow r : s.rows()) {
            assertEquals(r.wins() * 3 + r.draws(), r.points());
            assertEquals(r.played(), r.wins() + r.draws() + r.losses());
            assertEquals(r.goalsFor() - r.goalsAgainst(), r.goalDifference());
        }
    }
}
