/*
 * ===========================================================================
 * Context: Brazilian Soccer MCP Server
 * File:    test/query/SoccerQueriesTest.java
 * Purpose: BDD (Given/When/Then) scenarios for the query engine, mirroring the
 *          spec's required capabilities: match search, head-to-head, team
 *          statistics, computed standings, player search/ranking and aggregate
 *          statistics. Runs against the real shipped datasets.
 * ===========================================================================
 */
package com.brazilsoccer.mcp.query;

import com.brazilsoccer.mcp.TestData;
import com.brazilsoccer.mcp.data.TeamNames;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Player;
import com.brazilsoccer.mcp.query.QueryResults.HeadToHead;
import com.brazilsoccer.mcp.query.QueryResults.StandingRow;
import com.brazilsoccer.mcp.query.QueryResults.TeamStats;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

@DisplayName("Feature: Soccer queries")
class SoccerQueriesTest {

    private final SoccerQueries q = TestData.queries();

    /** Tolerant check that a match involves the given team (any spelling). */
    private static boolean teamInvolved(Match m, String team) {
        String k = TeamNames.key(team);
        return TeamNames.matches(m.homeTeamKey(), k) || TeamNames.matches(m.awayTeamKey(), k);
    }

    @Test
    @DisplayName("Scenario: find matches between two rival teams")
    void givenTwoTeams_whenSearched_thenMatchesReturnedWithScores() {
        // Given the match data is loaded
        // When I search for matches between Flamengo and Fluminense
        List<Match> matches = q.findMatchesBetween("Flamengo", "Fluminense");
        // Then I receive a non-empty list, each involving both teams
        assertFalse(matches.isEmpty());
        for (Match m : matches) {
            assertTrue(teamInvolved(m, "Flamengo"));
            assertTrue(teamInvolved(m, "Fluminense"));
        }
    }

    @Test
    @DisplayName("Scenario: matches are sorted newest first")
    void givenMatches_whenListed_thenSortedDescendingByDate() {
        List<Match> matches = q.findMatches("Palmeiras", null, null, null, null);
        assertFalse(matches.isEmpty());
        for (int i = 1; i < matches.size(); i++) {
            var prev = matches.get(i - 1).date();
            var cur = matches.get(i).date();
            if (prev != null && cur != null) {
                assertTrue(!cur.isAfter(prev), "matches should be newest-first");
            }
        }
    }

    @Test
    @DisplayName("Scenario: overlapping sources are de-duplicated for head-to-head")
    void givenOverlappingSources_whenCountingFixtures_thenNoGrossDoubleCounting() {
        // The same Fla-Flu fixtures live in several files under different
        // spellings; after naming-tolerant de-duplication the count must be
        // realistic, not 2-3x inflated.
        int meetings = q.findMatchesBetween("Flamengo", "Fluminense").size();
        assertTrue(meetings > 20 && meetings < 60,
                "Fla-Flu meetings after de-dup was " + meetings);
    }

    @Test
    @DisplayName("Scenario: head-to-head totals are internally consistent")
    void givenTwoTeams_whenHeadToHead_thenWinsPlusDrawsEqualMatches() {
        HeadToHead h = q.headToHead("Palmeiras", "Santos");
        assertTrue(h.totalMatches() > 0);
        // wins + draws never exceed total scored matches
        assertTrue(h.teamAWins() + h.teamBWins() + h.draws() <= h.totalMatches());
    }

    @Test
    @DisplayName("Scenario: team statistics aggregate wins, draws, losses and goals")
    void givenTeamAndSeason_whenStats_thenRecordsAreConsistent() {
        // When I request statistics for a team in a season
        TeamStats s = q.teamStats("Flamengo", "Brasileirão", 2019, false, false);
        // Then wins + draws + losses equals matches played
        assertEquals(s.matches(), s.wins() + s.draws() + s.losses());
        assertTrue(s.matches() > 0);
        assertTrue(s.goalsFor() >= 0 && s.goalsAgainst() >= 0);
    }

    @Test
    @DisplayName("Scenario: home-only filter restricts to home matches")
    void givenVenueHome_whenStats_thenSubsetOfAllMatches() {
        TeamStats all = q.teamStats("Corinthians", "Brasileirão", 2019, false, false);
        TeamStats home = q.teamStats("Corinthians", "Brasileirão", 2019, true, false);
        assertTrue(home.matches() <= all.matches());
        assertTrue(home.matches() > 0);
    }

    @Test
    @DisplayName("Scenario: compute 2019 Brasileirao standings (Flamengo champion)")
    void givenSeason_whenStandings_thenChampionAndCountsCorrect() {
        // When I compute the 2019 Brasileirão table
        List<StandingRow> table = q.standings("Brasileirão", 2019);
        // Then it has 20 teams and Flamengo top with 38 games played
        assertEquals(20, table.size());
        StandingRow champion = table.get(0);
        assertTrue(TeamNames.matches(TeamNames.key(champion.team()), TeamNames.key("Flamengo")),
                "champion was " + champion.team());
        assertEquals(38, champion.played());
        // And positions are strictly increasing with non-increasing points
        for (int i = 1; i < table.size(); i++) {
            assertEquals(i + 1, table.get(i).position());
            assertTrue(table.get(i).points() <= table.get(i - 1).points());
        }
    }

    @Test
    @DisplayName("Scenario: search players by name")
    void givenName_whenSearched_thenPlayerFound() {
        List<Player> players = q.searchPlayersByName("Neymar", 5);
        assertFalse(players.isEmpty());
        assertTrue(players.get(0).name().toLowerCase().contains("neymar"));
    }

    @Test
    @DisplayName("Scenario: top Brazilian players ranked by rating")
    void givenBrazilianFilter_whenRanked_thenSortedByOverall() {
        List<Player> players = q.findPlayers("Brazil", null, null, 10);
        assertFalse(players.isEmpty());
        for (Player p : players) {
            assertEquals("brazil", p.nationalityKey());
        }
        // Ranked descending by overall rating
        for (int i = 1; i < players.size(); i++) {
            assertTrue(players.get(i).overall() <= players.get(i - 1).overall());
        }
    }

    @Test
    @DisplayName("Scenario: filter players by club")
    void givenClub_whenFiltered_thenAllBelongToClub() {
        // (The FIFA dataset ships with a subset of licensed Brazilian clubs;
        //  Grêmio is present, whereas e.g. Flamengo is not.)
        List<Player> players = q.findPlayers(null, "Grêmio", null, 50);
        assertFalse(players.isEmpty());
        for (Player p : players) {
            assertTrue(TeamNames.matches(p.clubKey(), TeamNames.key("Grêmio")));
        }
    }

    @Test
    @DisplayName("Scenario: average goals per match is plausible")
    void givenCompetition_whenAveraged_thenWithinExpectedRange() {
        double avg = q.averageGoalsPerMatch("Brasileirão", null);
        assertTrue(avg > 1.5 && avg < 4.0, "avg goals per match was " + avg);
    }

    @Test
    @DisplayName("Scenario: biggest wins are ordered by margin")
    void givenData_whenBiggestWins_thenOrderedByMargin() {
        List<Match> wins = q.biggestWins(null, null, 10);
        assertFalse(wins.isEmpty());
        for (int i = 1; i < wins.size(); i++) {
            int prev = Math.abs(wins.get(i - 1).homeGoal() - wins.get(i - 1).awayGoal());
            int cur = Math.abs(wins.get(i).homeGoal() - wins.get(i).awayGoal());
            assertTrue(cur <= prev);
        }
    }

    @Test
    @DisplayName("Scenario: filter matches by competition and season")
    void givenCompetitionAndSeason_whenSearched_thenAllMatchFilters() {
        List<Match> matches = q.findMatches(null, "Libertadores", 2019, null, null);
        assertFalse(matches.isEmpty());
        for (Match m : matches) {
            assertEquals(2019, m.season());
            assertTrue(m.competition().toLowerCase().contains("libertadores"));
        }
    }
}
