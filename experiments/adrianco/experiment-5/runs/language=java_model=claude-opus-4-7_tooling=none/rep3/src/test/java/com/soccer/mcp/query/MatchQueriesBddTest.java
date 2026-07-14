package com.soccer.mcp.query;

import com.soccer.mcp.data.DataStore;
import com.soccer.mcp.model.Match;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import java.nio.file.Paths;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@DisplayName("Feature: Match Queries")
class MatchQueriesBddTest {

    private QueryService query;

    @BeforeAll
    void givenMatchDataIsLoaded() throws Exception {
        DataStore store = DataStore.load(Paths.get("data", "kaggle"));
        query = new QueryService(store);
    }

    @Test
    @DisplayName("Scenario: find matches between Flamengo and Fluminense")
    void whenISearchForMatchesBetweenFlamengoAndFluminense_thenIReceiveAListOfMatches() {
        // When
        List<Match> matches = query.findMatchesBetween("Flamengo", "Fluminense");
        // Then
        assertFalse(matches.isEmpty(), "expected at least one Fla-Flu match");
        for (Match m : matches) {
            assertNotNull(m.homeTeam());
            assertNotNull(m.awayTeam());
            assertNotNull(m.competition());
        }
    }

    @Test
    @DisplayName("Scenario: find matches for Palmeiras in 2023")
    void whenIRequestPalmeirasMatchesIn2023_thenIReceiveSeasonResults() {
        // When
        List<Match> matches = query.findMatches("Palmeiras", null, 2023, null, null);
        // Then
        assertFalse(matches.isEmpty(), "expected Palmeiras 2023 matches");
        for (Match m : matches) {
            assertTrue(m.season() == null || m.season() == 2023);
        }
    }

    @Test
    @DisplayName("Scenario: filter matches by competition")
    void whenISearchByCompetition_thenAllMatchesInThatCompetition() {
        List<Match> matches = query.findMatchesByCompetition("Libertadores");
        assertFalse(matches.isEmpty());
        for (Match m : matches) {
            assertTrue(m.competition().toLowerCase().contains("libertadores"));
        }
    }

    @Test
    @DisplayName("Scenario: matches are ordered chronologically")
    void whenIListMatchesForATeam_thenTheyComeOutInDateOrder() {
        List<Match> matches = query.findMatchesByTeam("Corinthians");
        assertFalse(matches.isEmpty());
        // verify non-null dates appear in ascending order
        java.time.LocalDate prev = null;
        for (Match m : matches) {
            if (m.date() == null) continue;
            if (prev != null) {
                assertTrue(!m.date().isBefore(prev),
                        "matches out of order: " + prev + " then " + m.date());
            }
            prev = m.date();
        }
    }
}
