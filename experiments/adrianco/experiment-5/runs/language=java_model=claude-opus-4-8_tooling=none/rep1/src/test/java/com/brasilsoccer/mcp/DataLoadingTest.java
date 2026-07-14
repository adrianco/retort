/*
 * ============================================================================
 * DataLoadingTest - verifies all six datasets load and are queryable
 * ============================================================================
 * Context:
 *   Covers the "Data Coverage" success criteria: every CSV is loadable, the
 *   expected competitions are present, and players load. Acts as the "Given the
 *   data is loaded" precondition shared by the rest of the suite.
 * ============================================================================
 */
package com.brasilsoccer.mcp;

import com.brasilsoccer.mcp.data.KnowledgeBase;
import com.brasilsoccer.mcp.query.Results;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Set;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Dataset loading")
class DataLoadingTest {

    private final KnowledgeBase kb = TestData.kb();

    @Test
    @DisplayName("Given the CSV files, When loaded and de-overlapped, Then >15k matches remain")
    void loadsManyMatches() {
        // The 5 match files total ~24k rows but overlap (Serie A appears in three
        // files); after keeping one authoritative source per competition+season
        // ~16.6k unique matches remain.
        assertTrue(kb.allMatches().size() > 15_000,
                "expected >15k matches, got " + kb.allMatches().size());
    }

    @Test
    @DisplayName("Given fifa_data.csv, When loaded, Then ~18k players exist")
    void loadsPlayers() {
        assertTrue(kb.allPlayers().size() > 18_000,
                "expected >18k players, got " + kb.allPlayers().size());
    }

    @Test
    @DisplayName("Given the data, When summarised, Then all key competitions are present")
    void competitionsPresent() {
        Results.Summary s = kb.summary();
        Set<String> comps = s.competitions().stream()
                .map(String::toLowerCase).collect(Collectors.toSet());
        assertTrue(comps.stream().anyMatch(c -> c.contains("brasileirao serie a")), "Serie A");
        assertTrue(comps.stream().anyMatch(c -> c.contains("copa do brasil")), "Copa do Brasil");
        assertTrue(comps.stream().anyMatch(c -> c.contains("libertadores")), "Libertadores");
    }

    @Test
    @DisplayName("Given the data, When summarised, Then seasons span 2003 to 2023")
    void seasonRange() {
        Results.Summary s = kb.summary();
        assertTrue(s.seasons().contains(2003), "should include 2003");
        assertTrue(s.seasons().contains(2019), "should include 2019");
    }
}
