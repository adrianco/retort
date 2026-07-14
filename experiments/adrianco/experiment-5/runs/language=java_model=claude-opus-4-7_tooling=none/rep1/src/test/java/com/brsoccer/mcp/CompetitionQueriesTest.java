package com.brsoccer.mcp;

import com.brsoccer.mcp.model.Competition;
import com.brsoccer.mcp.server.SoccerKnowledgeBase;
import com.brsoccer.mcp.service.TeamStats;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Competition Queries")
class CompetitionQueriesTest {

    @Nested
    @DisplayName("Scenario: Compute standings")
    class Standings {
        @Test
        @DisplayName("Given Brasileirão match data When I compute 2019 standings Then teams are sorted by points and Flamengo leads")
        void brasileirao2019() {
            SoccerKnowledgeBase kb = TestData.get();
            List<TeamStats> table = kb.competitions().standings(Competition.HISTORICAL_BRASILEIRAO, 2019);
            if (table.isEmpty()) {
                table = kb.competitions().standings(Competition.BRASILEIRAO, 2019);
            }
            assertFalse(table.isEmpty());
            for (int i = 1; i < table.size(); i++) {
                assertTrue(table.get(i - 1).points() >= table.get(i).points(),
                    "standings must be sorted by points desc");
            }
            assertEquals("flamengo", table.get(0).team, "2019 Brasileirão champion was Flamengo");
        }
    }

    @Nested
    @DisplayName("Scenario: Season champion")
    class Champion {
        @Test
        @DisplayName("Given the data When I ask for 2009 Brasileirão champion Then I get a non-null team")
        void champ2009() {
            SoccerKnowledgeBase kb = TestData.get();
            TeamStats champ = kb.competitions().champion(Competition.HISTORICAL_BRASILEIRAO, 2009);
            assertNotNull(champ);
            assertTrue(champ.points() > 0);
        }
    }
}
