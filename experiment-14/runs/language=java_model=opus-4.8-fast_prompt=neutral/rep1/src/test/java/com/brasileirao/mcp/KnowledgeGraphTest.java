/*
 * ============================================================================
 *  Brazilian Soccer MCP Server - Tests
 * ----------------------------------------------------------------------------
 *  File    : KnowledgeGraphTest.java
 *  Purpose : Verify all six CSV files load and the indexes are populated.
 *  Context : Covers the spec's "Data Coverage" success criteria: every file is
 *            loadable, players are present, competitions are recognised, and
 *            date parsing handles the three different conventions.
 * ============================================================================
 */
package com.brasileirao.mcp;

import com.brasileirao.mcp.data.KnowledgeGraph;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class KnowledgeGraphTest {

    @Test
    void loadsAllPlayers() {
        assertEquals(18207, TestData.graph().playerCount());
    }

    @Test
    void loadsMatchesFromEveryCompetition() {
        KnowledgeGraph g = TestData.graph();
        assertTrue(g.competitions().contains(KnowledgeGraph.BRASILEIRAO));
        assertTrue(g.competitions().contains(KnowledgeGraph.COPA_DO_BRASIL));
        assertTrue(g.competitions().contains(KnowledgeGraph.LIBERTADORES));
        assertTrue(g.competitions().contains(KnowledgeGraph.BRASILEIRAO_HISTORICAL));
        // BR-Football contributes Serie A/B/C tournament labels.
        assertTrue(g.competitions().contains("Serie A"));
    }

    @Test
    void loadsLargeMatchCorpus() {
        // Five match files combined; comfortably over 20k rows.
        assertTrue(TestData.graph().matchCount() > 20000,
                "expected >20000 matches, got " + TestData.graph().matchCount());
    }

    @Test
    void indexesMatchesByTeam() {
        assertTrue(TestData.graph().matchesForTeam("Flamengo").size() > 100);
        assertTrue(TestData.graph().matchesForTeam("Palmeiras-SP").size() > 100);
    }

    @Test
    void parsesIsoAndBrazilianDates() {
        assertEquals(java.time.LocalDate.of(2003, 3, 29), KnowledgeGraph.parseDate("29/03/2003"));
        assertEquals(java.time.LocalDate.of(2012, 5, 19), KnowledgeGraph.parseDate("2012-05-19 18:30:00"));
        assertEquals(java.time.LocalDate.of(2023, 9, 24), KnowledgeGraph.parseDate("2023-09-24"));
    }
}
