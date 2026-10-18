package com.brazilsoccer.query;

import com.brazilsoccer.TestFixtures;
import com.brazilsoccer.data.DataLoader;
import com.brazilsoccer.data.DataRepository;
import com.brazilsoccer.data.Match;
import com.brazilsoccer.query.SoccerQueries.MatchFilter;
import com.brazilsoccer.query.SoccerQueries.PlayerFilter;
import com.brazilsoccer.query.SoccerQueries.Venue;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SoccerQueriesTest {

    private final SoccerQueries queries = new SoccerQueries(TestFixtures.smallRepository());

    @Test
    @DisplayName("Scenario: find matches between two teams, newest first")
    void givenTwoTeams_whenSearchingMatches_thenOnlyTheirGamesComeBackNewestFirst() {
        // Given the small dataset with Flamengo and Fluminense meetings
        // When matches between them are searched
        List<Match> found = queries.findMatches(
                new MatchFilter("Flamengo", "Fluminense", null, null, null, null, Venue.ANY), 10);

        // Then both 2023 meetings come back, newest first
        assertEquals(2, found.size());
        assertEquals(LocalDate.of(2023, 9, 3), found.get(0).date());
    }

    @Test
    @DisplayName("Scenario: search by season and competition narrows the results")
    void givenSeasonAndCompetition_whenSearching_thenCupGamesAreExcluded() {
        // Given Palmeiras matches in 2023, including one Copa do Brasil tie
        // When searching for Brasileirão games only
        List<Match> found = queries.findMatches(
                new MatchFilter("Palmeiras", null, "Brasileirão", 2023, null, null, Venue.ANY), 10);

        // Then no cup match appears
        assertEquals(3, found.size());
        assertTrue(found.stream().noneMatch(m -> m.competition().equals(DataLoader.COPA_DO_BRASIL)));
    }

    @Test
    @DisplayName("Scenario: the venue filter keeps only home or away games")
    void givenVenueFilter_whenSearching_thenOnlyThatVenueIsReturned() {
        // Given Palmeiras appears at home and away
        // When only home games are requested
        List<Match> home = queries.findMatches(
                new MatchFilter("Palmeiras", null, null, 2023, null, null, Venue.HOME), 10);

        // Then every result has Palmeiras as the home side
        assertTrue(home.stream().allMatch(m -> m.homeTeam().startsWith("Palmeiras")));
        assertEquals(3, home.size());
    }

    @Test
    @DisplayName("Scenario: team record counts wins, draws, losses and goals")
    void givenTeamWithResults_whenRecordRequested_thenTotalsAreCorrect() {
        // Given Corinthians beat Palmeiras 2-0 at home in 2022, and played nowhere away that year
        // When the home record is requested
        TeamTally home = queries.teamRecord("Corinthians", 2022, null, Venue.HOME);

        // Then one home win with two goals for and none against
        assertEquals(1, home.played());
        assertEquals(1, home.won());
        assertEquals(2, home.goalsFor());
        assertEquals(100.0, home.winRate(), 0.001);

        // And the away record for 2022 is empty
        assertEquals(0, queries.teamRecord("Corinthians", 2022, null, Venue.AWAY).played());
    }

    @Test
    @DisplayName("Scenario: head to head totals show each side's wins and goals")
    void givenMeetings_whenHeadToHeadRequested_thenWinsDrawsAndGoalsAreTallied() {
        // Given Flamengo and Fluminense met twice in the small dataset (2-1 and 0-1 in Fluminense's favour)
        // When the head-to-head record is requested
        SoccerQueries.HeadToHead h2h = queries.headToHead("Flamengo", "Fluminense", 10);

        // Then Flamengo has one win, Fluminense has one win, and the goals are summed
        assertEquals(2, h2h.matches().size());
        assertEquals(1, h2h.winsA());
        assertEquals(1, h2h.winsB());
        assertEquals(0, h2h.draws());
        assertEquals(2, h2h.goalsA());
        assertEquals(2, h2h.goalsB());
    }

    @Test
    @DisplayName("Scenario: standings are ordered by points, then wins and goal difference")
    void givenSeasonResults_whenStandingsRequested_thenTableIsOrdered() {
        // Given Palmeiras won 3-0 and drew 1-1 and 2-2 in the 2023 Serie A slice
        // When the table is requested
        List<TeamTally> table = queries.standings(DataLoader.SERIE_A, 2023);

        // Then Palmeiras leads with 5 points (one win and two draws)
        assertEquals("Palmeiras", table.get(0).team());
        assertEquals(5, table.get(0).points());
        assertEquals(3, table.get(0).played());
        assertTrue(table.get(0).points() > table.get(1).points());
    }

    @Test
    @DisplayName("Scenario: league stats report averages and the biggest margins")
    void givenResults_whenLeagueStatsRequested_thenAveragesAreCorrect() {
        // Given the 2023 Serie A slice with 5 scored matches (goals: 3,1,3,2,4)
        // When league stats are requested
        SoccerQueries.LeagueStats stats = queries.leagueStats(DataLoader.SERIE_A, 2023);

        // Then the average is 2.6 goals and the biggest win is Palmeiras 3-0 Santos
        assertEquals(5, stats.matches());
        assertEquals(2.6, stats.avgGoalsPerMatch(), 0.001);
        assertEquals("Palmeiras-SP", stats.biggestWins().get(0).homeTeam());
    }

    @Test
    @DisplayName("Scenario: teams are ranked by win rate and filtered by minimum matches")
    void givenMinimumMatches_whenRankingTeams_thenSmallSamplesAreExcluded() {
        // Given Palmeiras has 3 Brasileirão 2023 games and the rest have fewer
        // When teams with at least 3 games are ranked
        List<TeamTally> ranked = queries.rankTeams(DataLoader.SERIE_A, 2023, Venue.ANY, 3, 10);

        // Then only Palmeiras qualifies
        assertEquals(1, ranked.size());
        assertEquals("Palmeiras", ranked.get(0).team());
    }

    @Test
    @DisplayName("Scenario: player search filters by club and minimum rating")
    void givenClubAndRating_whenSearchingPlayers_thenOnlyMatchingPlayersReturn() {
        // Given the small player list with two Flamengo players
        // When Flamengo players rated 83 or more are requested
        List<com.brazilsoccer.data.Player> players = queries.searchPlayers(
                new PlayerFilter(null, null, "Flamengo", null, 83), 10);

        // Then only Gabriel Barbosa qualifies
        assertEquals(1, players.size());
        assertEquals("Gabriel Barbosa", players.get(0).name());
    }

    @Test
    @DisplayName("Scenario: player name search ignores case and accents")
    void givenPartialName_whenSearching_thenNameMatchesCaseInsensitively() {
        // Given a lowercase partial name
        // When it is searched
        List<com.brazilsoccer.data.Player> players = queries.searchPlayers(
                new PlayerFilter("neymar", null, null, null, null), 10);

        // Then Neymar Jr is found
        assertEquals("Neymar Jr", players.get(0).name());
    }

    @Test
    @DisplayName("Scenario: the real dataset answers the 2019 Brasileirão champion question")
    void givenRealDataset_whenAsked2019Champion_thenFlamengoIsFirst() throws IOException {
        // Given all provided datasets are loaded
        SoccerQueries real = new SoccerQueries(DataRepository.load(TestFixtures.REAL_DATA_DIR));

        // When the 2019 Brasileirão table is calculated
        List<TeamTally> table = real.standings(DataLoader.SERIE_A, 2019);

        // Then Flamengo is champion with 38 games played
        assertEquals("Flamengo", table.get(0).team());
        assertEquals(38, table.get(0).played());
        assertEquals(20, table.size());
    }

    @Test
    @DisplayName("Scenario: a simple lookup on the full dataset answers in under two seconds")
    void givenFullDataset_whenSimpleLookupRuns_thenItIsFast() throws IOException {
        // Given the full dataset is loaded
        SoccerQueries real = new SoccerQueries(DataRepository.load(TestFixtures.REAL_DATA_DIR));

        // When a team-and-opponent lookup runs
        long started = System.nanoTime();
        List<Match> found = real.findMatches(
                new MatchFilter("Flamengo", "Corinthians", null, null, null, null, Venue.ANY), 20);
        long elapsedMs = (System.nanoTime() - started) / 1_000_000;

        // Then results come back quickly and are non-empty
        assertFalse(found.isEmpty());
        assertTrue(elapsedMs < 2000, "lookup took " + elapsedMs + " ms");
    }
}
