/*
 * ============================================================================
 * QueryServicesTest.java
 * ============================================================================
 * Context:
 *   BDD (Given/When/Then) coverage of the five query-service capability
 *   categories from the spec: match search, team records, head-to-head, player
 *   search, standings and aggregate statistics. Assertions use real bundled
 *   data and known facts (e.g. Flamengo won the 2019 Brasileirão).
 * ============================================================================
 */
package com.brazilsoccer.mcp;

import com.brazilsoccer.mcp.data.DataStore;
import com.brazilsoccer.mcp.model.Match;
import com.brazilsoccer.mcp.model.Player;
import com.brazilsoccer.mcp.query.CompetitionService;
import com.brazilsoccer.mcp.query.MatchService;
import com.brazilsoccer.mcp.query.PlayerService;
import com.brazilsoccer.mcp.query.StatsService;
import com.brazilsoccer.mcp.query.TeamRecord;
import com.brazilsoccer.mcp.query.TeamService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class QueryServicesTest {

    // ---- Match Queries ------------------------------------------------

    @Test
    @DisplayName("Given match data, When I search Flamengo vs Fluminense, Then I get scored matches")
    void findMatchesBetweenTwoTeams() {
        // Given
        MatchService svc = new MatchService(TestData.store());
        MatchService.Criteria c = new MatchService.Criteria();
        c.team = "Flamengo";
        c.opponent = "Fluminense";

        // When
        List<Match> matches = svc.search(c);

        // Then
        assertFalse(matches.isEmpty(), "expected some Fla-Flu matches");
        for (Match m : matches) {
            assertTrue(m.involves(com.brazilsoccer.mcp.data.TeamNames.key("Flamengo"))
                            || m.homeTeamKey().contains("flamengo") || m.awayTeamKey().contains("flamengo"),
                    "each match should involve Flamengo");
        }
    }

    @Test
    @DisplayName("Given a season filter, When I search Palmeiras 2019, Then all results are from 2019")
    void filterMatchesBySeason() {
        MatchService svc = new MatchService(TestData.store());
        MatchService.Criteria c = new MatchService.Criteria();
        c.team = "Palmeiras";
        c.season = 2019;

        List<Match> matches = svc.search(c);

        assertFalse(matches.isEmpty());
        assertTrue(matches.stream().allMatch(m -> m.season() == 2019));
    }

    // ---- Team Queries -------------------------------------------------

    @Test
    @DisplayName("Given match data, When I request Palmeiras 2019 record, Then totals are consistent")
    void teamRecordConsistent() {
        TeamService svc = new TeamService(TestData.store());

        TeamRecord r = svc.record("Palmeiras", 2019, DataStore.BRASILEIRAO, TeamService.Venue.ALL);

        assertTrue(r.matches > 0);
        assertEquals(r.matches, r.wins + r.draws + r.losses, "W+D+L should equal matches");
    }

    @Test
    @DisplayName("Given a venue filter, When I request a home record, Then overlapping sources are not double-counted")
    void homeRecordNotDoubleCounted() {
        TeamService svc = new TeamService(TestData.store());

        // 2019 is a complete season present in three overlapping source files.
        TeamRecord all = svc.record("Flamengo", 2019, DataStore.BRASILEIRAO, TeamService.Venue.ALL);
        TeamRecord home = svc.record("Flamengo", 2019, DataStore.BRASILEIRAO, TeamService.Venue.HOME);

        assertTrue(home.matches > 0);
        assertTrue(home.matches <= all.matches, "home matches must be a subset of all matches");
        // A 20-team Série A season is 38 games (19 home) — overlapping sources
        // must NOT inflate this via double counting.
        assertEquals(38, all.matches, "a Série A season is 38 games, not double-counted");
        assertEquals(19, home.matches, "a Série A season has 19 home games");
    }

    @Test
    @DisplayName("Given two teams, When I compute head-to-head, Then wins+draws equal scored meetings")
    void headToHeadTallies() {
        TeamService svc = new TeamService(TestData.store());

        TeamService.HeadToHead h = svc.headToHead("Palmeiras", "Santos", null, null);

        assertFalse(h.matches.isEmpty(), "Palmeiras and Santos should have met");
        long scored = h.matches.stream().filter(Match::hasScore).count();
        assertEquals(scored, h.teamAWins + h.teamBWins + h.draws);
    }

    // ---- Player Queries -----------------------------------------------

    @Test
    @DisplayName("Given FIFA data, When I search Brazilians, Then many are returned, best-rated first")
    void searchBrazilianPlayers() {
        PlayerService svc = new PlayerService(TestData.store());
        PlayerService.Criteria c = new PlayerService.Criteria();
        c.nationality = "Brazil";
        c.limit = 10;

        List<Player> players = svc.search(c);

        assertEquals(10, players.size());
        // Sorted descending by overall.
        for (int i = 1; i < players.size(); i++) {
            assertTrue(players.get(i - 1).overall() >= players.get(i).overall(),
                    "players should be sorted by overall descending");
        }
        // Top Brazilian in this dataset is Neymar Jr.
        assertTrue(players.get(0).name().contains("Neymar"));
    }

    @Test
    @DisplayName("Given a name query, When I search 'Casemiro', Then the player is found")
    void searchPlayerByName() {
        PlayerService svc = new PlayerService(TestData.store());
        PlayerService.Criteria c = new PlayerService.Criteria();
        c.name = "Casemiro";

        List<Player> players = svc.search(c);

        assertFalse(players.isEmpty(), "expected to find Casemiro");
        assertTrue(players.get(0).name().contains("Casemiro"));
    }

    // ---- Competition Queries ------------------------------------------

    @Test
    @DisplayName("Given 2019 Brasileirão matches, When I compute standings, Then Flamengo is champion")
    void standings2019ChampionIsFlamengo() {
        CompetitionService svc = new CompetitionService(TestData.store());

        List<TeamRecord> table = svc.standings(DataStore.BRASILEIRAO, 2019);

        assertFalse(table.isEmpty());
        assertTrue(table.get(0).team.toLowerCase().contains("flamengo"),
                "2019 Brasileirão champion should be Flamengo, got " + table.get(0).team);
        // A 20-team league season has 380 fixtures => 38 games per team.
        assertEquals(38, table.get(0).matches);
        assertTrue(table.get(0).points() >= 85, "Flamengo earned ~90 points in 2019");
    }

    @Test
    @DisplayName("Given overlapping sources, When computing standings, Then fixtures are not double-counted")
    void standingsNotDoubleCounted() {
        CompetitionService svc = new CompetitionService(TestData.store());

        List<TeamRecord> table = svc.standings(DataStore.BRASILEIRAO, 2019);

        // Every team should play exactly 38 games, not 76 (which double counting would give).
        for (TeamRecord r : table) {
            assertEquals(38, r.matches, r.team + " should have 38 matches, got " + r.matches);
        }
    }

    // ---- Statistical Analysis -----------------------------------------

    @Test
    @DisplayName("Given a season, When I compute league stats, Then averages are in a sane range")
    void leagueStatsSane() {
        StatsService svc = new StatsService(TestData.store());

        StatsService.LeagueStats s = svc.leagueStats(DataStore.BRASILEIRAO, 2019);

        assertEquals(380, s.matches, "2019 Serie A has 380 fixtures");
        assertTrue(s.goalsPerMatch() > 1.5 && s.goalsPerMatch() < 4.0,
                "goals/match should be realistic, got " + s.goalsPerMatch());
        double total = s.homeWinRate() + s.awayWinRate() + s.drawRate();
        assertEquals(100.0, total, 0.01, "win/draw rates should sum to 100%");
    }

    @Test
    @DisplayName("Given matches, When I find biggest wins, Then they are sorted by margin")
    void biggestWinsSorted() {
        StatsService svc = new StatsService(TestData.store());

        List<Match> wins = svc.biggestWins(DataStore.BRASILEIRAO, 2019, 5);

        assertEquals(5, wins.size());
        for (int i = 1; i < wins.size(); i++) {
            int prev = Math.abs(wins.get(i - 1).homeGoal() - wins.get(i - 1).awayGoal());
            int cur = Math.abs(wins.get(i).homeGoal() - wins.get(i).awayGoal());
            assertTrue(prev >= cur, "biggest wins should be sorted by margin descending");
        }
    }

    @Test
    @DisplayName("Given a season, When I rank top scorers, Then the leader scored the most goals")
    void topScoringTeamsSorted() {
        StatsService svc = new StatsService(TestData.store());

        List<TeamRecord> teams = svc.topScoringTeams(DataStore.BRASILEIRAO, 2019, 5);

        assertEquals(5, teams.size());
        for (int i = 1; i < teams.size(); i++) {
            assertTrue(teams.get(i - 1).goalsFor >= teams.get(i).goalsFor);
        }
    }
}
