package com.example.brsoccer.query;

import com.example.brsoccer.model.Match;
import com.example.brsoccer.model.Player;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class SoccerDatabaseTest {

    private SoccerDatabase db;

    private static Match m(String comp, int season, String date, String home, int hg, int ag, String away) {
        return new Match(comp, season, LocalDate.parse(date), null, home, away, hg, ag);
    }

    @BeforeEach
    void setUp() {
        List<Match> matches = List.of(
                m("Brasileirão", 2023, "2023-05-28", "Fluminense", 1, 0, "Flamengo"),
                m("Brasileirão", 2023, "2023-09-03", "Flamengo", 2, 1, "Fluminense"),
                m("Brasileirão", 2023, "2023-06-01", "Palmeiras", 3, 0, "Santos"),
                m("Brasileirão", 2023, "2023-07-01", "Santos", 0, 0, "Palmeiras"),
                m("Brasileirão", 2023, "2023-08-01", "Flamengo", 4, 0, "Santos"),
                m("Brasileirão", 2023, "2023-08-15", "Palmeiras", 2, 2, "Flamengo"),
                m("Brasileirão", 2022, "2022-05-01", "Flamengo", 1, 2, "Palmeiras"),
                m("Copa Libertadores", 2023, "2023-04-01", "Flamengo", 5, 0, "Palmeiras")
        );
        List<Player> players = List.of(
                new Player(1, "Neymar Jr", 27, "Brazil", 92, 93, "Paris Saint-Germain", "LW", 10),
                new Player(2, "L. Messi", 31, "Argentina", 94, 94, "FC Barcelona", "RF", 10),
                new Player(3, "Pedro", 26, "Brazil", 80, 84, "Flamengo", "ST", 9),
                new Player(4, "Gabriel Barbosa", 26, "Brazil", 83, 85, "Flamengo", "ST", 9),
                new Player(5, "Alisson", 25, "Brazil", 89, 90, "Liverpool", "GK", 1)
        );
        db = new SoccerDatabase(matches, players);
    }

    // ---- match queries ----

    @Test
    void findMatchesByTeamCompetitionAndSeason() {
        List<Match> result = db.findMatches(new MatchQuery()
                .team("Flamengo").competition("Brasileirão").season(2023));
        assertEquals(4, result.size());
    }

    @Test
    void findMatchesByTeamMatchesAcrossNameVariations() {
        List<Match> result = db.findMatches(new MatchQuery().team("palmeiras-sp"));
        // 3 in 2023 Brasileirão + 2022 Brasileirão Fla-Pal + 2023 Libertadores Fla-Pal
        assertEquals(5, result.size());
    }

    @Test
    void findMatchesByCompetitionAccentInsensitive() {
        List<Match> result = db.findMatches(new MatchQuery().competition("libertadores"));
        assertEquals(1, result.size());
        assertEquals("Copa Libertadores", result.get(0).competition());
    }

    @Test
    void brasileiraoAndSerieAAreTreatedAsTheSameCompetition() {
        SoccerDatabase local = new SoccerDatabase(List.of(
                m("Serie A", 2023, "2023-10-01", "Palmeiras", 1, 0, "Santos"),
                m("Serie B", 2023, "2023-10-01", "Guarani", 2, 1, "Sport")
        ), List.of());
        // "Serie A" rows are the Brasileirão top flight...
        assertEquals(1, local.findMatches(new MatchQuery().competition("Brasileirão").season(2023)).size());
        // ...but Serie B must NOT be included.
        assertEquals(1, local.findMatches(new MatchQuery().competition("Serie A")).size());
        assertTrue(local.findMatches(new MatchQuery().competition("Brasileirão"))
                .stream().noneMatch(x -> x.competition().equals("Serie B")));
    }

    @Test
    void findMatchesByDateRange() {
        List<Match> result = db.findMatches(new MatchQuery()
                .from(LocalDate.of(2023, 6, 1)).to(LocalDate.of(2023, 8, 1)));
        assertEquals(3, result.size());
    }

    @Test
    void findMatchesByHomeVenueOnly() {
        List<Match> result = db.findMatches(new MatchQuery()
                .team("Flamengo").competition("Brasileirão").season(2023).venue(Venue.HOME));
        assertEquals(2, result.size());
        assertTrue(result.stream().allMatch(x -> x.homeTeam().equals("Flamengo")));
    }

    @Test
    void findMatchesBetweenTwoTeams() {
        List<Match> result = db.findMatches(new MatchQuery().team("Flamengo").opponent("Fluminense"));
        assertEquals(2, result.size());
    }

    @Test
    void findMatchesSortedByDateAscending() {
        List<Match> result = db.findMatches(new MatchQuery().team("Flamengo").competition("Brasileirão").season(2023));
        for (int i = 1; i < result.size(); i++) {
            assertFalse(result.get(i).date().isBefore(result.get(i - 1).date()));
        }
    }

    // ---- head to head ----

    @Test
    void headToHeadCountsWinsAndDraws() {
        HeadToHead h2h = db.headToHead("Flamengo", "Fluminense");
        assertEquals(1, h2h.teamAWins());
        assertEquals(1, h2h.teamBWins());
        assertEquals(0, h2h.draws());
        assertEquals(2, h2h.totalMatches());
    }

    @Test
    void headToHeadHandlesDrawsAndMultipleCompetitions() {
        HeadToHead h2h = db.headToHead("Flamengo", "Palmeiras");
        // 2022 Bras (Pal win), 2023 Bras draw, 2023 Libertadores (Fla win)
        assertEquals(1, h2h.teamAWins());
        assertEquals(1, h2h.teamBWins());
        assertEquals(1, h2h.draws());
        assertEquals(3, h2h.totalMatches());
    }

    // ---- team record ----

    @Test
    void teamRecordAggregatesResults() {
        TeamRecord r = db.teamRecord("Flamengo", 2023, "Brasileirão", Venue.ANY);
        assertEquals(4, r.played());
        assertEquals(2, r.wins());
        assertEquals(1, r.draws());
        assertEquals(1, r.losses());
        assertEquals(8, r.goalsFor());
        assertEquals(4, r.goalsAgainst());
        assertEquals(7, r.points());
        assertEquals(50.0, r.winRate(), 0.001);
    }

    @Test
    void teamRecordHomeOnly() {
        TeamRecord r = db.teamRecord("Flamengo", 2023, "Brasileirão", Venue.HOME);
        assertEquals(2, r.played());
        assertEquals(2, r.wins());
        assertEquals(6, r.goalsFor());
        assertEquals(1, r.goalsAgainst());
    }

    // ---- standings ----

    @Test
    void standingsAreOrderedByPointsThenGoalDifference() {
        List<StandingRow> table = db.standings("Brasileirão", 2023);
        assertEquals(4, table.size());
        assertEquals("Flamengo", table.get(0).team());
        assertEquals(7, table.get(0).points());
        assertEquals("Palmeiras", table.get(1).team());
        assertEquals(5, table.get(1).points());
        assertEquals("Fluminense", table.get(2).team());
        assertEquals("Santos", table.get(3).team());
        assertEquals(1, table.get(0).position());
        assertEquals(4, table.get(3).position());
    }

    @Test
    void championIsTopOfStandings() {
        assertEquals("Flamengo", db.standings("Brasileirão", 2023).get(0).team());
    }

    // ---- statistics ----

    @Test
    void averageGoalsPerMatch() {
        double avg = db.averageGoalsPerMatch(new MatchQuery().competition("Brasileirão").season(2023));
        assertEquals(2.5, avg, 0.001);
    }

    @Test
    void homeWinRate() {
        double rate = db.homeWinRate(new MatchQuery().competition("Brasileirão").season(2023));
        // home wins: Flu 1-0 Fla, Fla 2-1 Flu, Pal 3-0 Santos, Fla 4-0 Santos = 4 of 6
        assertEquals(66.667, rate, 0.01);
    }

    @Test
    void biggestWinsOrderedByMargin() {
        List<Match> biggest = db.biggestWins(new MatchQuery(), 3);
        assertEquals(5, biggest.get(0).goalMargin());
        assertEquals("Flamengo", biggest.get(0).homeTeam());
        for (int i = 1; i < biggest.size(); i++) {
            assertTrue(biggest.get(i).goalMargin() <= biggest.get(i - 1).goalMargin());
        }
    }

    @Test
    void topScoringTeamsRanksByGoalsFor() {
        List<TeamRecord> top = db.topScoringTeams("Brasileirão", 2023, 2);
        assertEquals("Flamengo", top.get(0).team());
        assertEquals(8, top.get(0).goalsFor());
        assertEquals("Palmeiras", top.get(1).team());
        assertEquals(5, top.get(1).goalsFor());
    }

    // ---- player queries ----

    @Test
    void searchPlayersByNationalitySortedByOverall() {
        List<Player> brazilians = db.searchPlayers(new PlayerQuery().nationality("Brazil"));
        assertEquals(4, brazilians.size());
        assertEquals("Neymar Jr", brazilians.get(0).name());
        assertEquals("Alisson", brazilians.get(1).name());
    }

    @Test
    void searchPlayersByClub() {
        List<Player> flamengo = db.searchPlayers(new PlayerQuery().club("Flamengo"));
        assertEquals(2, flamengo.size());
        assertTrue(flamengo.stream().allMatch(p -> p.club().equals("Flamengo")));
    }

    @Test
    void searchPlayersByName() {
        List<Player> result = db.searchPlayers(new PlayerQuery().name("gabriel"));
        assertEquals(1, result.size());
        assertEquals("Gabriel Barbosa", result.get(0).name());
    }

    @Test
    void searchPlayersByPositionAndMinOverall() {
        List<Player> result = db.searchPlayers(new PlayerQuery().position("ST").minOverall(82));
        assertEquals(1, result.size());
        assertEquals("Gabriel Barbosa", result.get(0).name());
    }

    @Test
    void searchPlayersRespectsLimit() {
        List<Player> result = db.searchPlayers(new PlayerQuery().nationality("Brazil").limit(2));
        assertEquals(2, result.size());
    }

    @Test
    void exposesCountsAndCompetitions() {
        assertEquals(8, db.matchCount());
        assertEquals(5, db.playerCount());
        assertTrue(db.competitions().contains("Brasileirão"));
        assertTrue(db.competitions().contains("Copa Libertadores"));
    }
}
