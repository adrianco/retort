package com.brsoccer.mcp;

import com.brsoccer.mcp.model.Competition;
import com.brsoccer.mcp.model.Match;
import com.brsoccer.mcp.server.SoccerKnowledgeBase;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Match Queries")
class MatchQueriesTest {

    @Nested
    @DisplayName("Scenario: Find matches between two teams")
    class BetweenTwoTeams {
        @Test
        @DisplayName("Given the match data is loaded When I search for matches between Flamengo and Fluminense Then I receive a list of matches with date, scores and competition")
        void flaFluDerby() {
            SoccerKnowledgeBase kb = TestData.get();
            List<Match> ms = kb.matches().findBetween("Flamengo", "Fluminense");
            assertFalse(ms.isEmpty(), "expected Fla-Flu derby matches");
            for (Match m : ms) {
                assertNotNull(m.getDate(), "every match has a date");
                assertNotNull(m.getCompetition(), "every match has a competition");
                assertNotNull(m.getHomeGoals(), "every match has scores");
                assertNotNull(m.getAwayGoals(), "every match has scores");
            }
        }
    }

    @Nested
    @DisplayName("Scenario: Find matches by team and season")
    class ByTeamAndSeason {
        @Test
        @DisplayName("Given the data When I ask for Palmeiras matches in 2018 Then I get only Palmeiras 2018 matches")
        void palmeiras2018() {
            SoccerKnowledgeBase kb = TestData.get();
            List<Match> ms = kb.matches().filter("Palmeiras", null, 2018);
            assertFalse(ms.isEmpty());
            for (Match m : ms) {
                assertEquals(2018, m.getSeason());
                assertTrue("palmeiras".equals(m.getHomeTeamNormalized())
                    || "palmeiras".equals(m.getAwayTeamNormalized()));
            }
        }
    }

    @Nested
    @DisplayName("Scenario: Find matches by competition")
    class ByCompetition {
        @Test
        @DisplayName("Given the data When I ask for Libertadores matches Then they all have stage info")
        void libertadores() {
            SoccerKnowledgeBase kb = TestData.get();
            List<Match> ms = kb.matches().findByCompetition(Competition.LIBERTADORES);
            assertFalse(ms.isEmpty());
            for (Match m : ms) {
                assertEquals(Competition.LIBERTADORES, m.getCompetition());
            }
        }
    }

    @Nested
    @DisplayName("Scenario: Find matches by date range")
    class ByDateRange {
        @Test
        @DisplayName("Given the data When I filter to a one-year window Then all results fall within it")
        void oneYearWindow() {
            SoccerKnowledgeBase kb = TestData.get();
            java.time.LocalDate from = java.time.LocalDate.of(2015, 1, 1);
            java.time.LocalDate to = java.time.LocalDate.of(2015, 12, 31);
            List<Match> ms = kb.matches().findInRange(from, to);
            assertFalse(ms.isEmpty());
            for (Match m : ms) {
                assertTrue(!m.getDate().isBefore(from) && !m.getDate().isAfter(to));
            }
        }
    }
}
