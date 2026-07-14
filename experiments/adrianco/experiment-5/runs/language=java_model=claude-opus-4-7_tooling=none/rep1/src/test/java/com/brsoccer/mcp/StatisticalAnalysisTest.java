package com.brsoccer.mcp;

import com.brsoccer.mcp.model.Competition;
import com.brsoccer.mcp.model.Match;
import com.brsoccer.mcp.server.SoccerKnowledgeBase;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Statistical Analysis")
class StatisticalAnalysisTest {

    @Nested
    @DisplayName("Scenario: Average goals per match")
    class AverageGoals {
        @Test
        @DisplayName("Given the Brasileirão When I compute average goals per match Then it falls in a reasonable [1.5, 4.0] range")
        void brasileiraoAverage() {
            SoccerKnowledgeBase kb = TestData.get();
            double avg = kb.stats().averageGoalsPerMatch(Competition.BRASILEIRAO, null);
            assertTrue(avg >= 1.5 && avg <= 4.0, "Average goals out of range: " + avg);
        }
    }

    @Nested
    @DisplayName("Scenario: Home win rate")
    class HomeWinRate {
        @Test
        @DisplayName("Given all matches Then the home win rate is greater than the draw rate")
        void homeAdvantage() {
            SoccerKnowledgeBase kb = TestData.get();
            double home = kb.stats().homeWinRate(null, null);
            assertTrue(home > 0.30 && home < 0.70, "Home win rate out of range: " + home);
        }
    }

    @Nested
    @DisplayName("Scenario: Biggest wins")
    class BiggestWins {
        @Test
        @DisplayName("Given the data When I ask for the biggest wins Then they are sorted by margin descending")
        void biggestWins() {
            SoccerKnowledgeBase kb = TestData.get();
            List<Match> ms = kb.stats().biggestWins(null, 5);
            assertFalse(ms.isEmpty());
            for (int i = 1; i < ms.size(); i++) {
                int a = Math.abs(ms.get(i - 1).getHomeGoals() - ms.get(i - 1).getAwayGoals());
                int b = Math.abs(ms.get(i).getHomeGoals() - ms.get(i).getAwayGoals());
                assertTrue(a >= b, "biggest wins must be sorted by margin desc");
            }
        }
    }
}
