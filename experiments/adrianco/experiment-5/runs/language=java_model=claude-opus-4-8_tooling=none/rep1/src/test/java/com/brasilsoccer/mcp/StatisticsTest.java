/*
 * ============================================================================
 * StatisticsTest - BDD scenarios for aggregated statistics (spec category 5)
 * ============================================================================
 * Context:
 *   Verifies league-wide aggregates (average goals per match, home/away/draw
 *   rates that sum to ~100%) and the "biggest wins" ranking, matching the spec's
 *   statistical-analysis examples.
 * ============================================================================
 */
package com.brasilsoccer.mcp;

import com.brasilsoccer.mcp.data.KnowledgeBase;
import com.brasilsoccer.mcp.model.Match;
import com.brasilsoccer.mcp.query.Results;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Statistical analysis")
class StatisticsTest {

    private final KnowledgeBase kb = TestData.kb();

    @Test
    @DisplayName("Given a season, When league stats computed, Then averages are plausible")
    void averageGoalsPlausible() {
        Results.LeagueStats s = kb.leagueStats("Brasileirao", 2019);
        assertTrue(s.matches() > 300, "a full season has hundreds of matches");
        assertTrue(s.avgGoalsPerMatch() > 1.5 && s.avgGoalsPerMatch() < 4.0,
                "avg goals/match should be realistic, was " + s.avgGoalsPerMatch());
    }

    @Test
    @DisplayName("Given league stats, When result rates summed, Then they total ~100%")
    void resultRatesSumToHundred() {
        Results.LeagueStats s = kb.leagueStats("Brasileirao", 2019);
        double sum = s.homeWinRate() + s.awayWinRate() + s.drawRate();
        assertTrue(Math.abs(sum - 100.0) < 0.5, "rates should sum to ~100, were " + sum);
        // Football has a well-known home advantage.
        assertTrue(s.homeWins() > s.awayWins(), "home wins should exceed away wins");
    }

    @Test
    @DisplayName("Given biggest-wins query, When ranked, Then margins are non-increasing")
    void biggestWinsRanked() {
        List<Match> wins = kb.biggestWins("Brasileirao", null, 10);
        assertFalse(wins.isEmpty());
        for (int i = 1; i < wins.size(); i++) {
            assertTrue(wins.get(i - 1).margin() >= wins.get(i).margin(),
                    "biggest wins must be ordered by margin descending");
        }
        assertTrue(wins.get(0).margin() >= 5, "the biggest Serie A win is a blowout");
    }
}
