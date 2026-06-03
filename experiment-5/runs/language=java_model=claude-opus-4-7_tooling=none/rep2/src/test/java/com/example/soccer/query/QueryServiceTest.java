package com.example.soccer.query;

import com.example.soccer.TestData;
import com.example.soccer.data.DataStore;
import com.example.soccer.data.Match;
import com.example.soccer.data.Player;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@DisplayName("Feature: Querying matches, teams, players and competitions")
class QueryServiceTest {

    private QueryService q;

    @BeforeAll
    void loadAll() throws Exception {
        DataStore store = TestData.load();
        q = new QueryService(store);
    }

    @Test
    @DisplayName("Scenario: Given matches loaded, searching by two teams returns only those matchups")
    void scenario_searchMatchesBetweenTwoTeams() {
        // GIVEN match data is loaded
        // WHEN I search for matches between Flamengo and Fluminense
        List<Match> matches = q.searchMatches("Flamengo", "Fluminense",
                null, null, null, null, null);
        // THEN at least one match exists and every match involves both teams
        assertFalse(matches.isEmpty(), "expected at least one Fla-Flu match");
        for (Match m : matches) {
            String home = m.homeTeam().toLowerCase();
            String away = m.awayTeam().toLowerCase();
            boolean ok = (home.contains("flamengo") && away.contains("fluminense"))
                    || (home.contains("fluminense") && away.contains("flamengo"));
            assertTrue(ok, "unexpected pairing: " + m.homeTeam() + " vs " + m.awayTeam());
        }
    }

    @Test
    @DisplayName("Scenario: Given a season, filtering matches returns only that season")
    void scenario_searchMatchesBySeason() {
        List<Match> matches = q.searchMatches("Palmeiras", null, 2019, "Brasileirão",
                null, null, null);
        assertFalse(matches.isEmpty());
        for (Match m : matches) {
            assertEquals(Integer.valueOf(2019), m.season());
            assertTrue(m.competition().toLowerCase().contains("brasileir"));
        }
    }

    @Test
    @DisplayName("Scenario: Given a team and season, team record sums to total matches")
    void scenario_teamRecordIsConsistent() {
        // GIVEN match data
        // WHEN I request stats for Corinthians in 2019 Brasileirao at home venue
        TeamRecord rec = q.teamRecord("Corinthians", 2019, "Brasileirão", "home");
        // THEN wins + draws + losses == matches
        assertTrue(rec.matches > 0, "expected some matches");
        assertEquals(rec.matches, rec.wins + rec.draws + rec.losses);
        assertTrue(rec.goalsFor >= 0);
        assertTrue(rec.goalsAgainst >= 0);
    }

    @Test
    @DisplayName("Scenario: Given two teams, head-to-head counts each match exactly once per side")
    void scenario_headToHeadConsistency() {
        QueryService.HeadToHead h = q.headToHead("Palmeiras", "Santos", null, null);
        int played = h.matches.size();
        assertTrue(played > 0);
        // Every scored match contributes exactly one outcome bucket
        int outcomeSum = h.winsA + h.winsB + h.draws;
        long scored = h.matches.stream().filter(Match::hasScore).count();
        assertEquals(scored, outcomeSum, "win/draw/loss buckets must sum to scored matches");
    }

    @Test
    @DisplayName("Scenario: Given a season, computed standings sort by points and balance W/D/L")
    void scenario_standingsSorted() {
        List<QueryService.Standing> rows = q.standings(2019, "Brasileirão");
        assertFalse(rows.isEmpty());
        for (int i = 1; i < rows.size(); i++) {
            assertTrue(rows.get(i - 1).record.points() >= rows.get(i).record.points(),
                    "standings should be in descending point order");
        }
        // Wins across all teams must equal losses (each win has a paired loss).
        int totalWins = rows.stream().mapToInt(s -> s.record.wins).sum();
        int totalLosses = rows.stream().mapToInt(s -> s.record.losses).sum();
        assertEquals(totalWins, totalLosses);
    }

    @Test
    @DisplayName("Scenario: Given the dataset, biggest_wins returns matches sorted by margin desc")
    void scenario_biggestWins() {
        List<Match> wins = q.biggestWins(null, 4, 5);
        assertEquals(5, wins.size());
        int prevMargin = Integer.MAX_VALUE;
        for (Match m : wins) {
            int margin = Math.abs(m.homeGoal() - m.awayGoal());
            assertTrue(margin >= 4);
            assertTrue(margin <= prevMargin, "should be in descending margin");
            prevMargin = margin;
        }
    }

    @Test
    @DisplayName("Scenario: Given the dataset, match_stats reports plausible averages")
    void scenario_matchStats() {
        Map<String, Object> s = q.matchStats(null, "Brasileirão");
        long matches = (long) s.get("matches");
        assertTrue(matches > 0);
        double avg = (double) s.get("avg_goals_per_match");
        assertTrue(avg > 1.0 && avg < 6.0, "avg goals per match should be in a soccer-realistic range, got " + avg);
        double homeWinRate = (double) s.get("home_win_rate");
        assertTrue(homeWinRate > 0.30 && homeWinRate < 0.70, "home win rate odd: " + homeWinRate);
    }

    @Test
    @DisplayName("Scenario: Given FIFA data, Brazilian player search returns Brazilian players only")
    void scenario_brazilianPlayers() {
        List<Player> players = q.searchPlayers(null, "Brazil", null, null, 80, 20);
        assertFalse(players.isEmpty());
        for (Player p : players) {
            assertEquals("Brazil", p.nationality());
            assertNotNull(p.overall());
            assertTrue(p.overall() >= 80);
        }
        // Sorted by overall desc
        for (int i = 1; i < players.size(); i++) {
            assertTrue(players.get(i - 1).overall() >= players.get(i).overall());
        }
    }

    @Test
    @DisplayName("Scenario: Given a player name substring, search returns matching player(s)")
    void scenario_playerNameSearch() {
        List<Player> players = q.searchPlayers("Neymar", null, null, null, null, 10);
        assertFalse(players.isEmpty());
        assertTrue(players.stream().anyMatch(p -> p.name().toLowerCase().contains("neymar")));
    }

    @Test
    @DisplayName("Scenario: Given a date range, only matches inside the range are returned")
    void scenario_dateRange() {
        LocalDate from = LocalDate.of(2019, 1, 1);
        LocalDate to = LocalDate.of(2019, 12, 31);
        List<Match> matches = q.searchMatches("Flamengo", null, null, null, from, to, null);
        assertFalse(matches.isEmpty());
        for (Match m : matches) {
            assertNotNull(m.date());
            assertTrue(!m.date().isBefore(from) && !m.date().isAfter(to),
                    "match date outside requested range: " + m.date());
        }
    }
}
