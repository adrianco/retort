/*
 * ============================================================================
 * CompetitionsTest.java
 * ============================================================================
 * Context:
 *   Coverage for competition canonicalization/matching, including the
 *   regression where "Brasileirão" wrongly matched "Brasileirão Série B" and
 *   folded the second division (e.g. 2019 Série B champion Bragantino) into the
 *   top-flight standings.
 * ============================================================================
 */
package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.data.Competitions;
import com.brazilsoccer.mcp.data.DataStore;
import com.brazilsoccer.mcp.query.CompetitionService;
import com.brazilsoccer.mcp.query.TeamRecord;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class CompetitionsTest {

    @Test
    @DisplayName("Given aliases, When canonicalized, Then top-flight synonyms collapse together")
    void aliasesCollapse() {
        assertEquals(Competitions.A, Competitions.canonical("brasileirao"));
        assertEquals(Competitions.A, Competitions.canonical("seriea"));
        assertEquals(Competitions.A, Competitions.canonical("campeonatobrasileiro"));
        assertEquals(Competitions.LIBERTADORES, Competitions.canonical("copalibertadores"));
        assertEquals(Competitions.COPA_BRASIL, Competitions.canonical("copadobrasil"));
    }

    @Test
    @DisplayName("Given the top flight, When matching, Then Série B/C are excluded")
    void topFlightDoesNotMatchLowerDivisions() {
        assertTrue(Competitions.matches("Brasileirão Série A", "Brasileirão"));
        assertFalse(Competitions.matches("Brasileirão Série B", "Brasileirão"));
        assertFalse(Competitions.matches("Brasileirão Série C", "Serie A"));
        assertTrue(Competitions.matches("Brasileirão Série B", "Serie B"));
    }

    @Test
    @DisplayName("Given the user term 'Brasileirão', When standings computed, Then no Série B team leaks in")
    void standingsExcludeSecondDivision() {
        CompetitionService svc = new CompetitionService(TestData.store());

        // Use the loose user term (not the canonical constant) to exercise matching.
        List<TeamRecord> table = svc.standings("Brasileirão", 2019);

        assertEquals(20, table.size(), "the top flight had 20 teams in 2019");
        assertTrue(table.get(0).team.toLowerCase().contains("flamengo"));
        // Bragantino won Série B in 2019; it must not appear in the Série A table.
        assertTrue(table.stream().noneMatch(r -> r.team.toLowerCase().contains("bragantino")),
                "Série B champion must not appear in the Série A standings");
    }

    @Test
    @DisplayName("Given a null competition filter, When matching, Then everything matches")
    void nullFilterMatchesAll() {
        assertTrue(Competitions.matches(DataStore.LIBERTADORES, null));
        assertTrue(Competitions.matches(DataStore.BRASILEIRAO, ""));
    }
}
