/*
 * ============================================================================
 * TeamQueryTest - BDD scenarios for team records and head-to-head (category 2)
 * ============================================================================
 * Context:
 *   Verifies team statistics (W/D/L, goals, win rate), home/away splits and
 *   head-to-head consistency, matching the spec's "Get team statistics" scenario.
 * ============================================================================
 */
package com.brasilsoccer.mcp;

import com.brasilsoccer.mcp.data.KnowledgeBase;
import com.brasilsoccer.mcp.query.MatchQuery;
import com.brasilsoccer.mcp.query.Results;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Team queries")
class TeamQueryTest {

    private final KnowledgeBase kb = TestData.kb();

    @Test
    @DisplayName("Given Palmeiras 2019, When records requested, Then W+D+L equals matches played")
    void teamRecordIsInternallyConsistent() {
        Results.TeamRecord r = kb.teamRecord("Palmeiras", 2019, "Brasileirao", MatchQuery.Venue.ANY);

        assertTrue(r.played() > 0, "should have played matches");
        assertEquals(r.played(), r.wins() + r.draws() + r.losses(),
                "W+D+L must equal games played");
        assertTrue(r.winRate() >= 0 && r.winRate() <= 100);
        assertEquals(r.wins() * 3 + r.draws(), r.points());
    }

    @Test
    @DisplayName("Given a 38-game league season, When team record requested, Then exactly 38 games")
    void leagueSeasonHas38Games() {
        // 20-team double round-robin = 38 games per team.
        Results.TeamRecord r = kb.teamRecord("Flamengo", 2019, "Brasileirao", MatchQuery.Venue.ANY);
        assertEquals(38, r.played(), "2019 Serie A is a 38-game season");
        assertEquals(19, kb.teamRecord("Flamengo", 2019, "Brasileirao", MatchQuery.Venue.HOME).played());
        assertEquals(19, kb.teamRecord("Flamengo", 2019, "Brasileirao", MatchQuery.Venue.AWAY).played());
    }

    @Test
    @DisplayName("Given two clubs, When head-to-head requested, Then wins+draws reconcile")
    void headToHeadReconciles() {
        Results.HeadToHead h = kb.headToHead("Palmeiras", "Santos");
        assertTrue(h.total() > 0, "Palmeiras and Santos have met");
        assertEquals(h.total(), h.team1Wins() + h.team2Wins() + h.draws());
    }

    @Test
    @DisplayName("Given home and away splits, When summed, Then they equal the overall record")
    void homeAwaySplitSumsToTotal() {
        Results.TeamRecord all = kb.teamRecord("Santos", 2019, "Brasileirao", MatchQuery.Venue.ANY);
        Results.TeamRecord home = kb.teamRecord("Santos", 2019, "Brasileirao", MatchQuery.Venue.HOME);
        Results.TeamRecord away = kb.teamRecord("Santos", 2019, "Brasileirao", MatchQuery.Venue.AWAY);
        assertEquals(all.played(), home.played() + away.played());
        assertEquals(all.goalsFor(), home.goalsFor() + away.goalsFor());
    }
}
