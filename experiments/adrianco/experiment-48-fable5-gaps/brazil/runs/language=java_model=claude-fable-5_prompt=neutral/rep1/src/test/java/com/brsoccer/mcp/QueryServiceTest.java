package com.brsoccer.mcp;

import com.brsoccer.mcp.data.DataStore;
import com.brsoccer.mcp.model.Match;
import com.brsoccer.mcp.model.Player;
import com.brsoccer.mcp.query.QueryService;
import com.brsoccer.mcp.query.QueryService.HeadToHead;
import com.brsoccer.mcp.query.QueryService.MatchFilter;
import com.brsoccer.mcp.query.QueryService.StandingRow;
import com.brsoccer.mcp.query.QueryService.TeamStats;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * BDD-style scenarios from the specification's Testing Approach section.
 */
class QueryServiceTest {

    private final QueryService q = TestData.query();

    @Nested
    class MatchQueries {

        /**
         * Scenario: Find matches between two teams
         *   Given the match data is loaded
         *   When I search for matches between "Flamengo" and "Fluminense"
         *   Then I should receive a list of matches
         *   And each match should have date, scores, and competition
         */
        @Test
        void findMatchesBetweenTwoTeams() {
            List<Match> ms = q.findMatches(new MatchFilter("Flamengo", "Fluminense", null, null, null, null, null));
            assertTrue(ms.size() > 20, "Fla-Flu derby should appear many times, got " + ms.size());
            for (Match m : ms) {
                assertNotNull(m.date);
                assertNotNull(m.competition);
                assertTrue(m.homeGoals >= 0 && m.awayGoals >= 0);
            }
            // Exactly one of the two sides is Flamengo in every result
            String fla = com.brsoccer.mcp.data.TeamRegistry.canonicalKey("Flamengo");
            for (Match m : ms) {
                assertTrue(m.homeKey.equals(fla) ^ m.awayKey.equals(fla));
            }
        }

        @Test
        void filterByCompetitionAndSeason() {
            List<Match> ms = q.findMatches(new MatchFilter("Palmeiras", null, "Brasileirão", 2022, null, null, null));
            assertEquals(38, ms.size(), "Palmeiras played 38 Série A matches in 2022");
            assertTrue(ms.stream().allMatch(m -> m.competition.equals(DataStore.SERIE_A)));
        }

        @Test
        void filterByDateRange() {
            List<Match> ms = q.findMatches(new MatchFilter("Corinthians", null, null, null,
                LocalDate.parse("2019-01-01"), LocalDate.parse("2019-12-31"), null));
            assertFalse(ms.isEmpty());
            assertTrue(ms.stream().allMatch(m -> m.date.getYear() == 2019));
        }

        @Test
        void teamNameVariantsReturnSameMatches() {
            var a = q.findMatches(new MatchFilter("Flamengo", null, "Brasileirão", 2019, null, null, null));
            var b = q.findMatches(new MatchFilter("Flamengo-RJ", null, "Brasileirão", 2019, null, null, null));
            var c = q.findMatches(new MatchFilter("flamengo rj", null, "Brasileirão", 2019, null, null, null));
            assertEquals(38, a.size());
            assertEquals(a.size(), b.size());
            assertEquals(a.size(), c.size());
        }

        @Test
        void copaDoBrasilFinalsAreIdentifiable() {
            List<Match> finals = q.findMatches(new MatchFilter(null, null, "Copa do Brasil", null, null, null, "final"));
            assertFalse(finals.isEmpty());
            // Two-legged finals: roughly 2 per season across 2012-2022
            assertTrue(finals.size() >= 15 && finals.size() <= 30, "got " + finals.size());
            assertTrue(finals.stream().allMatch(m -> m.competition.equals(DataStore.COPA_DO_BRASIL)));
        }

        @Test
        void libertadoresStageFilterWorks() {
            List<Match> finals = q.findMatches(new MatchFilter(null, null, "Libertadores", 2018, null, null, "final"));
            assertFalse(finals.isEmpty());
            assertTrue(finals.stream().allMatch(m -> "final".equals(m.stage)));
        }
    }

    @Nested
    class TeamStatistics {

        /**
         * Scenario: Get team statistics
         *   Given the match data is loaded
         *   When I request statistics for "Palmeiras" in season "2023"
         *   Then I should receive wins, losses, draws, and goals
         */
        @Test
        void teamStatisticsForSeason() {
            TeamStats st = q.teamStats("Palmeiras", 2023, null, null);
            assertTrue(st.played() > 0);
            assertEquals(st.played(), st.wins() + st.draws() + st.losses());
            assertTrue(st.goalsFor() > 0);
        }

        @Test
        void homeAndAwaySplitsSumToTotal() {
            TeamStats all = q.teamStats("Corinthians", 2022, "Brasileirão", null);
            TeamStats home = q.teamStats("Corinthians", 2022, "Brasileirão", "home");
            TeamStats away = q.teamStats("Corinthians", 2022, "Brasileirão", "away");
            assertEquals(38, all.played());
            assertEquals(19, home.played());
            assertEquals(19, away.played());
            assertEquals(all.wins(), home.wins() + away.wins());
            assertEquals(all.goalsFor(), home.goalsFor() + away.goalsFor());
        }

        @Test
        void headToHeadRecordIsConsistent() {
            HeadToHead h = q.headToHead("Palmeiras", "Santos");
            assertTrue(h.matches().size() > 20);
            assertEquals(h.matches().size(), h.team1Wins() + h.team2Wins() + h.draws());
            // Swapping the order swaps the perspective but not the totals
            HeadToHead r = q.headToHead("Santos", "Palmeiras");
            assertEquals(h.team1Wins(), r.team2Wins());
            assertEquals(h.draws(), r.draws());
        }
    }

    @Nested
    class CompetitionQueries {

        /** "Who won the 2019 Brasileirão?" -> Flamengo, 90 points (28W 6D 4L). */
        @Test
        void standings2019MatchKnownResult() {
            List<StandingRow> rows = q.standings(2019, "Brasileirão");
            assertEquals(20, rows.size(), "Série A has 20 teams");
            for (StandingRow r : rows) {
                assertEquals(38, r.played(), "every team plays 38 matches; duplicate rows would break this");
            }
            StandingRow champion = rows.get(0);
            assertEquals("flamengo rj", champion.teamKey());
            assertEquals(90, champion.points());
            assertEquals(28, champion.wins());
            assertEquals(6, champion.draws());
            assertEquals(4, champion.losses());
        }

        /** Historical file only: 2005 season pre-dates the other Brasileirão files. */
        @Test
        void standingsFromHistoricalFileOnly() {
            List<StandingRow> rows = q.standings(2005, "Brasileirão");
            assertEquals(22, rows.size(), "2005 Série A had 22 teams");
            assertEquals("corinthians", rows.get(0).teamKey(), "Corinthians won the 2005 title");
        }

        @Test
        void relegationCandidatesAreAtTheBottom() {
            List<StandingRow> rows = q.standings(2019, null);
            // 2019 relegated: Avaí, CSA, Chapecoense, Cruzeiro
            List<String> bottom4 = rows.subList(16, 20).stream().map(StandingRow::teamKey).toList();
            assertTrue(bottom4.contains("avai"));
            assertTrue(bottom4.contains("csa"));
            assertTrue(bottom4.contains("chapecoense"));
            assertTrue(bottom4.contains("cruzeiro"));
        }
    }

    @Nested
    class PlayerQueries {

        @Test
        void searchByNameFindsNeymar() {
            List<Player> ps = q.searchPlayers("Neymar", null, null, null, null, null, 5);
            assertFalse(ps.isEmpty());
            assertTrue(ps.get(0).name.contains("Neymar"));
            assertEquals("Brazil", ps.get(0).nationality);
        }

        @Test
        void filterBrazilianPlayers() {
            List<Player> ps = q.searchPlayers(null, "Brazil", null, null, null, "overall", 0);
            assertEquals(827, ps.size());
            // sorted by overall descending
            for (int i = 1; i < ps.size(); i++) {
                assertTrue(ps.get(i - 1).overall >= ps.get(i).overall);
            }
        }

        @Test
        void filterByClubAndPosition() {
            List<Player> ps = q.searchPlayers(null, null, "FC Barcelona", null, null, null, 0);
            assertTrue(ps.size() >= 20);
            List<Player> gks = q.searchPlayers(null, "Brazil", null, "GK", null, null, 0);
            assertFalse(gks.isEmpty());
            assertTrue(gks.stream().allMatch(p -> "GK".equals(p.position)));
        }

        @Test
        void accentInsensitiveNameSearch() {
            List<Player> a = q.searchPlayers("Coutinho", null, null, null, null, null, 10);
            assertFalse(a.isEmpty());
        }
    }

    @Nested
    class StatisticalAnalysis {

        @Test
        void averageGoalsIsPlausible() {
            var agg = q.aggregate("Brasileirão", null);
            assertTrue(agg.matches() > 7000);
            assertTrue(agg.avgGoals() > 1.8 && agg.avgGoals() < 3.2, "avg=" + agg.avgGoals());
            assertTrue(agg.homeWinPct() > agg.awayWinPct(), "home advantage should exist");
            assertEquals(100.0, agg.homeWinPct() + agg.awayWinPct() + agg.drawPct(), 0.01);
        }

        @Test
        void biggestWinsAreOrderedByMargin() {
            List<Match> big = q.biggestWins(null, null, 10);
            assertEquals(10, big.size());
            assertTrue(big.get(0).margin() >= 6, "there should be a 6+ goal margin somewhere");
            for (int i = 1; i < big.size(); i++) {
                assertTrue(big.get(i - 1).margin() >= big.get(i).margin());
            }
        }

        @Test
        void rankingsBestAwayRecord() {
            var ranks = q.rankings("win_rate", "away", null, "Brasileirão", 100, 10);
            assertFalse(ranks.isEmpty());
            for (var r : ranks) {
                assertTrue(r.stats().played() >= 100);
            }
            for (int i = 1; i < ranks.size(); i++) {
                assertTrue(ranks.get(i - 1).value() >= ranks.get(i).value());
            }
        }
    }
}
