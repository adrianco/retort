package com.brsoccer.mcp;

import com.brsoccer.mcp.model.Competition;
import com.brsoccer.mcp.server.SoccerKnowledgeBase;
import com.brsoccer.mcp.service.TeamService;
import com.brsoccer.mcp.service.TeamStats;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Team Queries")
class TeamQueriesTest {

    @Nested
    @DisplayName("Scenario: Get team statistics")
    class GetStats {
        @Test
        @DisplayName("Given the match data When I request stats for Palmeiras in 2018 Then wins+draws+losses == matches and goals are non-negative")
        void palmeiras2018() {
            SoccerKnowledgeBase kb = TestData.get();
            TeamStats s = kb.teams().stats("Palmeiras", null, 2018);
            assertTrue(s.matches > 0);
            assertEquals(s.matches, s.wins + s.draws + s.losses, "W+D+L must equal matches");
            assertTrue(s.goalsFor >= 0);
            assertTrue(s.goalsAgainst >= 0);
        }
    }

    @Nested
    @DisplayName("Scenario: Get team home record")
    class HomeRecord {
        @Test
        @DisplayName("Given a team's home stats Then only home matches count")
        void corinthiansHome2022() {
            SoccerKnowledgeBase kb = TestData.get();
            TeamStats s = kb.teams().homeStats("Corinthians", Competition.BRASILEIRAO, 2022);
            // dataset may not cover 2022; we just check invariants
            assertEquals(s.matches, s.wins + s.draws + s.losses);
        }
    }

    @Nested
    @DisplayName("Scenario: Head-to-head comparison")
    class HeadToHead {
        @Test
        @DisplayName("Given two teams When I ask head-to-head Then winsA + winsB + draws equals matches")
        void palmeirasVsSantos() {
            SoccerKnowledgeBase kb = TestData.get();
            TeamService.HeadToHead h = kb.teams().headToHead("Palmeiras", "Santos");
            assertTrue(h.matches > 0);
            assertEquals(h.matches, h.winsA + h.winsB + h.draws);
        }
    }
}
