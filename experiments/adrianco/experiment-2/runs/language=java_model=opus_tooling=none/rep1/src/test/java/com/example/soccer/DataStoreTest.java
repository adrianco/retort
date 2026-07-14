package com.example.soccer;

import com.example.soccer.model.Match;
import com.example.soccer.model.Player;
import com.example.soccer.model.TeamStats;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Paths;

import static org.junit.jupiter.api.Assertions.*;

/**
 * BDD-style tests covering the main MCP capabilities.
 *
 * Feature: Brazilian Soccer data queries
 */
class DataStoreTest {
    static DataStore store;
    static QueryService q;

    @BeforeAll
    static void loadData() throws IOException {
        store = DataStore.load(Paths.get("data/kaggle"));
        q = new QueryService(store);
    }

    // Scenario: All six CSV files load
    @Test
    void loadsAllSixCsvFiles() {
        assertTrue(store.matches().size() > 20000, "expected matches loaded from 5 match CSVs");
        assertTrue(store.players().size() > 15000, "expected players loaded from fifa_data");
    }

    // Scenario: Find matches between two teams
    @Test
    void findsMatchesBetweenTwoTeams() {
        var ms = q.matchesBetween("Flamengo", "Fluminense");
        assertFalse(ms.isEmpty(), "expected Fla-Flu matches");
        for (Match m : ms) {
            assertTrue(TeamNames.matches(m.homeTeam, "Flamengo") || TeamNames.matches(m.awayTeam, "Flamengo"));
            assertTrue(TeamNames.matches(m.homeTeam, "Fluminense") || TeamNames.matches(m.awayTeam, "Fluminense"));
            assertNotNull(m.competition);
        }
    }

    // Scenario: Head-to-head computation
    @Test
    void headToHeadHasWinsAndDraws() {
        var h2h = q.headToHead("Palmeiras", "Santos");
        int total = h2h.get("Palmeiras") + h2h.get("Santos") + h2h.get("draws");
        assertTrue(total > 0);
    }

    // Scenario: Team stats for a season
    @Test
    void teamStatsForSeason() {
        TeamStats s = q.teamStats("Palmeiras", 2019, "Brasileirão", null);
        assertTrue(s.matches > 0);
        assertEquals(s.matches, s.wins + s.draws + s.losses);
    }

    // Scenario: Search by team name variation (with state suffix)
    @Test
    void handlesTeamNameWithStateSuffix() {
        var a = q.matchesForTeam("Palmeiras");
        var b = q.matchesForTeam("Palmeiras-SP");
        assertFalse(a.isEmpty());
        assertFalse(b.isEmpty());
        // both should return same matches for rows stored with suffix
        assertTrue(a.size() >= b.size());
    }

    // Scenario: Competition filter
    @Test
    void findsMatchesByCompetition() {
        var libs = q.matchesByCompetition("Libertadores");
        assertFalse(libs.isEmpty());
        for (Match m : libs) {
            assertTrue(m.competition.toLowerCase().contains("libertadores"));
        }
    }

    // Scenario: Season filter
    @Test
    void findsMatchesBySeason() {
        var ms = q.matchesBySeason(2019);
        assertFalse(ms.isEmpty());
        for (Match m : ms) assertEquals(2019, m.season);
    }

    // Scenario: Standings computation for a season
    @Test
    void standingsForBrasileirao2019() {
        var table = q.standings(2019, "Brasileirão");
        assertFalse(table.isEmpty());
        // sorted by points desc
        for (int i = 1; i < table.size(); i++) {
            assertTrue(table.get(i - 1).points() >= table.get(i).points());
        }
    }

    // Scenario: Player lookup by name
    @Test
    void findsPlayerByName() {
        var ps = q.playersByName("Neymar");
        assertFalse(ps.isEmpty());
    }

    // Scenario: Filter Brazilian players
    @Test
    void findsBrazilianPlayers() {
        var ps = q.playersByNationality("Brazil");
        assertTrue(ps.size() > 100, "expected many Brazilian players");
        for (Player p : ps) assertEquals("Brazil", p.nationality);
    }

    // Scenario: Top rated players
    @Test
    void topPlayersSortedByOverall() {
        var top = q.topPlayers(5);
        assertEquals(5, top.size());
        for (int i = 1; i < top.size(); i++) {
            assertTrue(top.get(i - 1).overall >= top.get(i).overall);
        }
    }

    // Scenario: Average goals per match
    @Test
    void averageGoalsReasonable() {
        double avg = q.averageGoalsPerMatch("Brasileirão");
        assertTrue(avg > 1.0 && avg < 5.0, "avg goals should be plausible, was " + avg);
    }

    // Scenario: Home win rate
    @Test
    void homeWinRateBetween0And1() {
        double r = q.homeWinRate(null);
        assertTrue(r > 0.2 && r < 0.7, "home win rate: " + r);
    }

    // Scenario: Biggest wins
    @Test
    void biggestWinsByMargin() {
        var big = q.biggestWins(5);
        assertEquals(5, big.size());
        int prev = Integer.MAX_VALUE;
        for (Match m : big) {
            int margin = Math.abs(m.homeGoals - m.awayGoals);
            assertTrue(margin <= prev);
            prev = margin;
        }
    }

    // Scenario: Date formats parsed (ISO + Brazilian)
    @Test
    void handlesMultipleDateFormats() {
        // historical CSV uses dd/MM/yyyy
        boolean foundBR = store.matches().stream()
            .anyMatch(m -> m.competition != null && m.competition.contains("histórico") && m.date != null);
        assertTrue(foundBR);
        // others use ISO
        boolean foundIso = store.matches().stream()
            .anyMatch(m -> "Brasileirão".equals(m.competition) && m.date != null);
        assertTrue(foundIso);
    }

    // Scenario: MCP server handles commands
    @Test
    void mcpServerRespondsToCommands() {
        McpServer s = new McpServer(q);
        String r = s.handle("matches between Flamengo|Fluminense");
        assertTrue(r.contains("total:"));
        assertTrue(s.handle("top players 3").contains("Overall"));
        assertTrue(s.handle("stats avg-goals").matches("\\d+\\.\\d+"));
        assertTrue(s.handle("help").contains("Commands"));
        assertTrue(s.handle("bogus command").contains("unknown"));
    }
}
