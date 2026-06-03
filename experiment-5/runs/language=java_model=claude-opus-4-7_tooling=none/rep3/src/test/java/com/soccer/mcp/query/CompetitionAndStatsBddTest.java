package com.soccer.mcp.query;

import com.soccer.mcp.data.DataStore;
import com.soccer.mcp.model.Match;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import java.nio.file.Paths;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@DisplayName("Feature: Competitions and statistical analysis")
class CompetitionAndStatsBddTest {

    private QueryService query;

    @BeforeAll
    void givenMatchDataIsLoaded() throws Exception {
        DataStore store = DataStore.load(Paths.get("data", "kaggle"));
        query = new QueryService(store);
    }

    @Test
    @DisplayName("Scenario: 2019 Brasileirão champion is Flamengo")
    void whenIComputeBrasileirao2019Standings_thenFlamengoIsAtTheTop() {
        TeamStats champ = query.champion(DataStore.COMP_BRASILEIRAO, 2019);
        assertNotNull(champ, "expected a 2019 Brasileirão champion");
        assertTrue(champ.team().toLowerCase().contains("flamengo"),
                "expected Flamengo champion, got " + champ.team());
    }

    @Test
    @DisplayName("Scenario: standings rows sort by points descending")
    void whenIComputeStandings_thenPointsAreNonIncreasing() {
        List<TeamStats> table = query.standings(DataStore.COMP_BRASILEIRAO, 2019);
        assertFalse(table.isEmpty());
        int prev = Integer.MAX_VALUE;
        for (TeamStats s : table) {
            assertTrue(s.points() <= prev, "points should be non-increasing");
            prev = s.points();
        }
    }

    @Test
    @DisplayName("Scenario: average goals per match in Brasileirão is plausible")
    void whenIAggregateGoals_thenAverageIsBetween1And5() {
        double avg = query.averageGoalsPerMatch(DataStore.COMP_BRASILEIRAO);
        assertTrue(avg > 1.0 && avg < 5.0, "implausible avg goals: " + avg);
    }

    @Test
    @DisplayName("Scenario: home win rate is bounded between 0 and 1")
    void whenIComputeHomeWinRate_thenBetweenZeroAndOne() {
        double rate = query.homeWinRate(null);
        assertTrue(rate >= 0.0 && rate <= 1.0);
    }

    @Test
    @DisplayName("Scenario: biggest wins are sorted by goal margin")
    void whenIRequestBiggestWins_thenMarginsAreNonIncreasing() {
        List<Match> top = query.biggestWins(5);
        assertEquals(5, top.size());
        int prevMargin = Integer.MAX_VALUE;
        for (Match m : top) {
            int margin = Math.abs(m.homeGoals() - m.awayGoals());
            assertTrue(margin <= prevMargin);
            prevMargin = margin;
        }
    }
}
