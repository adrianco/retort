/*
 * ============================================================================
 * DataLoadingTest.java
 * ============================================================================
 * Context:
 *   BDD (Given/When/Then) coverage for the data-loading layer: verifies that
 *   all six bundled CSV files are loaded into the unified model, that the
 *   expected competitions are present, and that UTF-8 / numeric / date parsing
 *   behaves as required by the spec's Data Quality Notes.
 * ============================================================================
 */
package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.data.DataStore;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Player;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Set;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

class DataLoadingTest {

    @Test
    @DisplayName("Given the six datasets, When loaded, Then all matches and players are available")
    void loadsAllDatasets() {
        // Given / When
        DataStore store = TestData.store();

        // Then: the de-duplicated corpus should still be substantial (>15k
        // matches) and the raw set larger still (overlaps before de-dup).
        assertTrue(store.matches().size() > 15_000,
                "expected >15k de-duplicated matches, got " + store.matches().size());
        assertTrue(store.allMatches().size() > store.matches().size(),
                "raw match count should exceed the de-duplicated count");
        assertTrue(store.players().size() > 18_000,
                "expected >18k players, got " + store.players().size());
    }

    @Test
    @DisplayName("Given the loaded matches, When grouping by source, Then every CSV contributed")
    void everySourceContributed() {
        // Given
        DataStore store = TestData.store();

        // When
        Set<String> sources = store.matches().stream()
                .map(Match::source).collect(Collectors.toSet());

        // Then
        assertTrue(sources.contains("Brasileirao_Matches.csv"));
        assertTrue(sources.contains("Brazilian_Cup_Matches.csv"));
        assertTrue(sources.contains("Libertadores_Matches.csv"));
        assertTrue(sources.contains("BR-Football-Dataset.csv"));
        assertTrue(sources.contains("novo_campeonato_brasileiro.csv"));
    }

    @Test
    @DisplayName("Given the loaded matches, When inspecting competitions, Then the three majors are present")
    void competitionsPresent() {
        DataStore store = TestData.store();
        Set<String> comps = store.matches().stream()
                .map(Match::competition).collect(Collectors.toSet());

        assertTrue(comps.contains(DataStore.BRASILEIRAO));
        assertTrue(comps.contains(DataStore.COPA_BRASIL));
        assertTrue(comps.contains(DataStore.LIBERTADORES));
    }

    @Test
    @DisplayName("Given UTF-8 data, When searching players, Then accented names are preserved")
    void utf8Preserved() {
        DataStore store = TestData.store();
        // "Neymar Jr" is a known Brazilian entry; ensure player parsing worked.
        boolean hasNeymar = store.players().stream()
                .anyMatch(p -> p.name().contains("Neymar"));
        assertTrue(hasNeymar, "expected to find Neymar in player data");

        // Some team somewhere should retain an accent (e.g. São Paulo / Grêmio).
        boolean hasAccent = store.matches().stream()
                .anyMatch(m -> m.homeTeam().chars().anyMatch(c -> c > 127));
        assertTrue(hasAccent, "expected at least one accented team name to be preserved");
    }

    @Test
    @DisplayName("Given parsed matches, When checking scores and dates, Then most are populated")
    void scoresAndDatesParsed() {
        DataStore store = TestData.store();
        long scored = store.matches().stream().filter(Match::hasScore).count();
        long dated = store.matches().stream().filter(m -> m.date() != null).count();

        assertTrue(scored > 14_000, "expected most matches to have scores, got " + scored);
        assertTrue(dated > 14_000, "expected most matches to have parsed dates, got " + dated);
    }
}
