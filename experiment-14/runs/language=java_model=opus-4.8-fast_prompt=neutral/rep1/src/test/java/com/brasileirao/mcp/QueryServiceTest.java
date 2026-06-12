/*
 * ============================================================================
 *  Brazilian Soccer MCP Server - Tests
 * ----------------------------------------------------------------------------
 *  File    : QueryServiceTest.java
 *  Purpose : Exercise every required query capability against the real data.
 *  Context : One test per spec capability category (match / team / player /
 *            competition / statistics). The headline assertion reproduces the
 *            spec's worked example: the 2019 Brasileirão Série A table must have
 *            Flamengo champions on 90 points.
 * ============================================================================
 */
package com.brasileirao.mcp;

import com.brasileirao.mcp.model.Match;
import com.brasileirao.mcp.model.Player;
import com.brasileirao.mcp.query.QueryService;
import com.brasileirao.mcp.query.QueryService.GoalStats;
import com.brasileirao.mcp.query.QueryService.HeadToHead;
import com.brasileirao.mcp.query.QueryService.MatchQuery;
import com.brasileirao.mcp.query.QueryService.PlayerQuery;
import com.brasileirao.mcp.query.QueryService.Scope;
import com.brasileirao.mcp.query.QueryService.StandingRow;
import com.brasileirao.mcp.query.QueryService.TeamRecord;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class QueryServiceTest {

    private final QueryService q = TestData.query();

    // --------------------------------------------------------------- matches

    @Test
    void searchMatchesByTeamAndOpponent() {
        MatchQuery mq = new MatchQuery();
        mq.team = "Flamengo";
        mq.opponent = "Fluminense";
        List<Match> matches = q.searchMatches(mq);
        assertFalse(matches.isEmpty());
        for (Match m : matches) {
            assertTrue(m.involves(com.brasileirao.mcp.util.TeamNames.canonical("Flamengo")));
            assertTrue(m.involves(com.brasileirao.mcp.util.TeamNames.canonical("Fluminense")));
        }
    }

    @Test
    void searchMatchesByCompetitionAndSeason() {
        MatchQuery mq = new MatchQuery();
        mq.team = "Palmeiras";
        mq.competition = "Libertadores";
        mq.limit = 500;
        List<Match> matches = q.searchMatches(mq);
        assertFalse(matches.isEmpty());
        for (Match m : matches) {
            assertTrue(m.competition().toLowerCase().contains("libertadores"));
        }
    }

    @Test
    void searchMatchesSortedNewestFirst() {
        MatchQuery mq = new MatchQuery();
        mq.team = "Santos";
        mq.limit = 5;
        List<Match> matches = q.searchMatches(mq);
        for (int i = 1; i < matches.size(); i++) {
            if (matches.get(i - 1).date() != null && matches.get(i).date() != null) {
                assertTrue(!matches.get(i - 1).date().isBefore(matches.get(i).date()));
            }
        }
    }

    // --------------------------------------------------------------- teams

    @Test
    void headToHeadIsSymmetric() {
        HeadToHead ab = q.headToHead("Palmeiras", "Santos");
        HeadToHead ba = q.headToHead("Santos", "Palmeiras");
        assertEquals(ab.total(), ba.total());
        assertEquals(ab.aWins(), ba.bWins());
        assertEquals(ab.bWins(), ba.aWins());
        assertEquals(ab.draws(), ba.draws());
        assertTrue(ab.total() > 0);
    }

    @Test
    void teamRecordWinsDrawsLossesAddUp() {
        TeamRecord r = q.teamRecord("Corinthians", null, "Brasileirão Série A", Scope.HOME);
        assertEquals(r.matches(), r.wins() + r.draws() + r.losses());
        assertTrue(r.matches() > 0);
    }

    @Test
    void homeAndAwayRecordsPartitionTotal() {
        TeamRecord all = q.teamRecord("Flamengo", 2019, "Brasileirão Série A", Scope.ALL);
        TeamRecord home = q.teamRecord("Flamengo", 2019, "Brasileirão Série A", Scope.HOME);
        TeamRecord away = q.teamRecord("Flamengo", 2019, "Brasileirão Série A", Scope.AWAY);
        assertEquals(all.matches(), home.matches() + away.matches());
        assertEquals(38, all.matches()); // 20-team league, 38 rounds
    }

    // --------------------------------------------------------------- players

    @Test
    void findBrazilianPlayers() {
        PlayerQuery pq = new PlayerQuery();
        pq.nationality = "Brazil";
        pq.limit = 1000;
        List<Player> players = q.searchPlayers(pq);
        assertTrue(players.size() > 500);
        // Sorted by overall rating descending.
        assertTrue(players.get(0).overall() >= players.get(players.size() - 1).overall());
        assertEquals("Brazil", players.get(0).nationality());
    }

    @Test
    void findPlayerByName() {
        PlayerQuery pq = new PlayerQuery();
        pq.name = "Neymar";
        List<Player> players = q.searchPlayers(pq);
        assertFalse(players.isEmpty());
        assertTrue(players.get(0).name().toLowerCase().contains("neymar"));
    }

    @Test
    void filterPlayersByPositionAndRating() {
        PlayerQuery pq = new PlayerQuery();
        pq.nationality = "Brazil";
        pq.position = "GK";
        pq.minOverall = 80;
        List<Player> players = q.searchPlayers(pq);
        assertFalse(players.isEmpty());
        for (Player p : players) {
            assertEquals("GK", p.position());
            assertTrue(p.overall() >= 80);
        }
    }

    // --------------------------------------------------------------- competition

    @Test
    void brasileirao2019FlamengoChampionWith90Points() {
        List<StandingRow> table = q.standings("Brasileirão Série A", 2019);
        assertEquals(20, table.size());
        StandingRow champion = table.get(0);
        assertEquals("Flamengo", champion.team());
        assertEquals(90, champion.points());
        assertEquals(28, champion.wins());
        assertEquals(6, champion.draws());
        assertEquals(4, champion.losses());
    }

    @Test
    void standingsPointsConsistentWithResults() {
        List<StandingRow> table = q.standings("Brasileirão Série A", 2018);
        for (StandingRow r : table) {
            assertEquals(r.wins() * 3 + r.draws(), r.points());
            assertEquals(r.played(), r.wins() + r.draws() + r.losses());
        }
        // Each of 20 teams plays 38 matches.
        assertEquals(20, table.size());
        assertEquals(38, table.get(0).played());
    }

    // --------------------------------------------------------------- statistics

    @Test
    void averageGoalsIsReasonable() {
        GoalStats s = q.averageGoals("Brasileirão Série A", null);
        assertTrue(s.matches() > 1000);
        // Brazilian league football: roughly 2-3 goals per game.
        assertTrue(s.averageGoals() > 2.0 && s.averageGoals() < 3.5,
                "avg goals was " + s.averageGoals());
        assertEquals(s.matches(), s.homeWins() + s.awayWins() + s.draws());
    }

    @Test
    void biggestWinsAreSortedByMargin() {
        List<Match> wins = q.biggestWins("Brasileirão Série A", null, 10);
        assertEquals(10, wins.size());
        for (int i = 1; i < wins.size(); i++) {
            int prev = Math.abs(wins.get(i - 1).homeGoals() - wins.get(i - 1).awayGoals());
            int cur = Math.abs(wins.get(i).homeGoals() - wins.get(i).awayGoals());
            assertTrue(prev >= cur);
        }
        assertTrue(Math.abs(wins.get(0).homeGoals() - wins.get(0).awayGoals()) >= 5);
    }

    @Test
    void bestHomeRecordsRanked() {
        List<TeamRecord> best = q.bestRecords("Brasileirão Série A", 2019, Scope.HOME, 5, 5);
        assertFalse(best.isEmpty());
        for (int i = 1; i < best.size(); i++) {
            assertTrue(best.get(i - 1).winRate() >= best.get(i).winRate());
        }
    }
}
