package com.soccer.mcp.query;

import com.soccer.mcp.data.DataStore;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import java.nio.file.Paths;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@DisplayName("Feature: Team Queries")
class TeamQueriesBddTest {

    private QueryService query;

    @BeforeAll
    void givenMatchDataIsLoaded() throws Exception {
        DataStore store = DataStore.load(Paths.get("data", "kaggle"));
        query = new QueryService(store);
    }

    @Test
    @DisplayName("Scenario: team stats sum consistently")
    void whenIRequestStatsForPalmeiras_thenWinsDrawsLossesEqualPlayed() {
        TeamStats stats = query.teamStats("Palmeiras");
        assertEquals(stats.played(), stats.wins() + stats.draws() + stats.losses(),
                "wins+draws+losses must equal played");
    }

    @Test
    @DisplayName("Scenario: head-to-head record is symmetric")
    void givenTwoTeams_whenIRequestHeadToHead_thenMatchCountsAreConsistent() {
        HeadToHead h2h = query.headToHead("Flamengo", "Fluminense");
        assertEquals(h2h.totalMatches(),
                h2h.teamAWins() + h2h.teamBWins() + h2h.draws(),
                "h2h totals should add up");
        assertTrue(h2h.totalMatches() > 0);
    }

    @Test
    @DisplayName("Scenario: home-only stats omit away matches")
    void whenIRequestHomeStatsForCorinthians_thenLossesAreLessThanOrEqualToAllStats() {
        TeamStats all = query.teamStats("Corinthians");
        TeamStats home = query.teamStats("Corinthians", null, null, "home");
        assertTrue(home.played() <= all.played());
        assertTrue(home.played() > 0);
    }

    @Test
    @DisplayName("Scenario: stats for season+competition filter to that competition only")
    void whenIRequestBrasileirao2019StatsForFlamengo_thenPlayedCountIsAroundOneSeason() {
        TeamStats stats = query.teamStats("Flamengo", 2019, "Brasileirão", null);
        assertNotNull(stats);
        assertTrue(stats.played() > 0, "Flamengo should have 2019 Brasileirão matches");
        // A single Brasileirão season has 38 matches per team
        assertTrue(stats.played() < 80, "season+competition count looks too high: " + stats.played());
    }
}
