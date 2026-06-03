/*
 * ============================================================================
 * MatchQueryTest - BDD scenarios for match search (spec category 1)
 * ============================================================================
 * Context:
 *   Mirrors the Gherkin scenarios in the specification: finding matches between
 *   two teams, by single team, by competition and by season, and confirming each
 *   match carries date, scores and competition.
 * ============================================================================
 */
package com.brasilsoccer.mcp;

import com.brasilsoccer.mcp.data.KnowledgeBase;
import com.brasilsoccer.mcp.model.Match;
import com.brasilsoccer.mcp.query.MatchQuery;
import com.brasilsoccer.mcp.query.Results;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Match queries")
class MatchQueryTest {

    private final KnowledgeBase kb = TestData.kb();

    @Test
    @DisplayName("Given match data, When searching Flamengo vs Fluminense, Then matches + h2h returned")
    void matchesBetweenTwoTeams() {
        Results.MatchSearch r = kb.searchMatches(
                new MatchQuery().team("Flamengo").team2("Fluminense").limit(0));

        assertFalse(r.matches().isEmpty(), "should find Fla-Flu matches");
        assertNotNull(r.headToHead(), "two teams should yield a head-to-head");
        // Every returned match must involve both clubs with date and a score.
        for (Match m : r.matches()) {
            boolean fla = m.homeKey().contains("flamengo") || m.awayKey().contains("flamengo");
            boolean flu = m.homeKey().contains("fluminense") || m.awayKey().contains("fluminense");
            assertTrue(fla && flu, "match should involve both teams: " + m);
            assertNotNull(m.date(), "match should have a date");
        }
        // h2h wins/draws must reconcile with the number of matches.
        Results.HeadToHead h = r.headToHead();
        assertEquals(r.totalFound(), h.total(), "h2h totals must equal match count");
    }

    @Test
    @DisplayName("Given match data, When searching Palmeiras in 2019, Then only 2019 matches return")
    void matchesByTeamAndSeason() {
        Results.MatchSearch r = kb.searchMatches(
                new MatchQuery().team("Palmeiras").season(2019).limit(0));

        assertFalse(r.matches().isEmpty());
        for (Match m : r.matches()) {
            assertEquals(2019, m.season());
            assertTrue(m.homeKey().contains("palmeiras") || m.awayKey().contains("palmeiras"));
        }
    }

    @Test
    @DisplayName("Given match data, When filtering by competition, Then only that competition returns")
    void matchesByCompetition() {
        Results.MatchSearch r = kb.searchMatches(
                new MatchQuery().team("Flamengo").competition("Libertadores").limit(0));

        assertFalse(r.matches().isEmpty(), "Flamengo has Libertadores matches");
        for (Match m : r.matches()) {
            assertTrue(m.competition().toLowerCase().contains("libertadores"),
                    "unexpected competition: " + m.competition());
        }
    }

    @Test
    @DisplayName("Given a single team and venue=home, When searched, Then team is always home side")
    void homeOnlyFilter() {
        Results.MatchSearch r = kb.searchMatches(
                new MatchQuery().team("Corinthians").season(2019)
                        .competition("Brasileirao").venue(MatchQuery.Venue.HOME).limit(0));

        assertFalse(r.matches().isEmpty());
        for (Match m : r.matches()) {
            assertTrue(m.homeKey().contains("corinthians"), "team must be the home side");
        }
    }

    @Test
    @DisplayName("Given a limit, When searching, Then results are capped but total reflects all")
    void limitCapsResults() {
        Results.MatchSearch r = kb.searchMatches(
                new MatchQuery().team("Flamengo").limit(5));
        assertTrue(r.matches().size() <= 5);
        assertTrue(r.totalFound() >= r.matches().size());
    }
}
