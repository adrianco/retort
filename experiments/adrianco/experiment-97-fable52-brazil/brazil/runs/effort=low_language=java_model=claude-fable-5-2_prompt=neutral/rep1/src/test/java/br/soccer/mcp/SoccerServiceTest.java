package br.soccer.mcp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

/** BDD-style scenarios (Given the data is loaded / When a query runs / Then ...) over the real data. */
class SoccerServiceTest {
    private final SoccerService svc = TestData.SERVICE;
    private final DataStore ds = TestData.STORE;

    private static SoccerService.MatchFilter filter() { return new SoccerService.MatchFilter(); }

    private static void assertContains(String text, String... parts) {
        for (String p : parts) assertTrue(text.contains(p), "expected <" + p + "> in:\n" + text);
    }

    @Nested
    @DisplayName("Feature: Match queries")
    class MatchQueries {
        @Test
        @DisplayName("Scenario: find matches between two teams")
        void betweenTwoTeams() {
            // When I search for matches between "Flamengo" and "Fluminense"
            SoccerService.MatchFilter f = filter();
            f.team = "Flamengo";
            f.opponent = "Fluminense";
            List<Match> ms = svc.select(f);
            // Then I receive matches, each with date, scores and competition
            assertTrue(ms.size() > 30);
            for (Match m : ms) {
                assertTrue(Set.of(m.home, m.away).equals(Set.of("flamengo", "fluminense")));
                assertTrue(m.date != null && m.competition != null);
            }
            String text = svc.findMatches(f, 5, false, false);
            assertContains(text, "Flamengo vs Fluminense (Fla-Flu)", "Head-to-head in dataset: Flamengo", "more matches in dataset");
            assertEquals(5, text.lines().filter(l -> l.startsWith("- ")).count());
            // And the head-to-head tally adds up
            long played = ms.stream().filter(Match::played).count();
            java.util.regex.Matcher mt = java.util.regex.Pattern
                    .compile("Flamengo (\\d+) wins, Fluminense (\\d+) wins, (\\d+) draws").matcher(text);
            assertTrue(mt.find());
            assertEquals(played, Integer.parseInt(mt.group(1)) + Integer.parseInt(mt.group(2)) + Integer.parseInt(mt.group(3)));
        }

        @Test
        @DisplayName("Scenario: matches by team and season span several competitions")
        void teamSeason() {
            SoccerService.MatchFilter f = filter();
            f.team = "Palmeiras";
            f.season = 2019;
            List<Match> ms = svc.select(f);
            assertEquals(38, ms.stream().filter(m -> m.competition.equals(DataStore.SERIE_A)).count());
            assertTrue(ms.stream().anyMatch(m -> m.competition.equals(DataStore.LIBERTADORES)));
            assertTrue(ms.stream().anyMatch(m -> m.competition.equals(DataStore.COPA_DO_BRASIL)));
        }

        @Test
        @DisplayName("Scenario: filter by venue, competition and date range")
        void venueAndDates() {
            SoccerService.MatchFilter f = filter();
            f.team = "Santos";
            f.venue = "home";
            f.competition = "Brasileirão";
            f.from = LocalDate.of(2015, 1, 1);
            f.to = LocalDate.of(2015, 12, 31);
            List<Match> ms = svc.select(f);
            assertEquals(19, ms.size());
            assertTrue(ms.stream().allMatch(m -> m.home.equals("santos") && m.date.getYear() == 2015));
        }

        @Test
        @DisplayName("Scenario: find all Copa do Brasil finals")
        void cupFinals() {
            SoccerService.MatchFilter f = filter();
            f.competition = "Copa do Brasil";
            f.stage = "final";
            List<Match> ms = svc.select(f);
            assertFalse(ms.isEmpty());
            // 2019 final: Athletico-PR beat Internacional over two legs
            List<Match> f19 = ms.stream().filter(m -> m.season == 2019).collect(Collectors.toList());
            assertEquals(2, f19.size());
            assertTrue(f19.stream().allMatch(m -> Set.of(m.home, m.away).equals(Set.of("atletico-pr", "internacional"))));
            // early preliminary rounds with few ties are not mistaken for finals
            assertTrue(ms.stream().collect(Collectors.groupingBy(m -> m.season)).values().stream().allMatch(l -> l.size() <= 2));
        }

        @Test
        @DisplayName("Scenario: every CSV file can be searched on its own")
        void everySource() {
            for (String src : List.of(DataStore.F_BRASILEIRAO, DataStore.F_CUP, DataStore.F_LIBERTADORES,
                    DataStore.F_EXTENDED, DataStore.F_HISTORICAL)) {
                SoccerService.MatchFilter f = filter();
                f.source = src;
                f.team = "Flamengo";
                List<Match> ms = svc.select(f);
                assertFalse(ms.isEmpty(), src);
                assertTrue(ms.stream().allMatch(m -> m.source.equals(src)));
            }
        }

        @Test
        @DisplayName("Scenario: extended statistics are shown on request")
        void extendedStats() {
            SoccerService.MatchFilter f = filter();
            f.team = "Flamengo";
            f.season = 2023;
            assertContains(svc.findMatches(f, 3, false, true), "corners ", "shots ");
        }

        @Test
        @DisplayName("Scenario: most recent meeting is listed first")
        void lastMeeting() {
            SoccerService.MatchFilter f = filter();
            f.team = "Flamengo";
            f.opponent = "Corinthians";
            String text = svc.findMatches(f, 1, false, false);
            Match latest = svc.select(f).stream().max((a, b) -> a.date.compareTo(b.date)).get();
            assertContains(text, "- " + latest.date);
        }

        @Test
        @DisplayName("Scenario: invalid input is rejected with a helpful message")
        void invalidInput() {
            SoccerService.MatchFilter f = filter();
            f.team = "Nonexistent United";
            assertThrows(IllegalArgumentException.class, () -> svc.select(f));
            SoccerService.MatchFilter g = filter();
            g.competition = "Premier";
            assertThrows(IllegalArgumentException.class, () -> svc.select(g));
            SoccerService.MatchFilter h = filter();
            h.from = LocalDate.of(2020, 1, 1);
            h.to = LocalDate.of(2019, 1, 1);
            assertThrows(IllegalArgumentException.class, () -> svc.select(h));
            SoccerService.MatchFilter v = filter();
            v.team = "Santos";
            v.venue = "neutral";
            assertThrows(IllegalArgumentException.class, () -> svc.select(v));
            assertThrows(IllegalArgumentException.class, () -> svc.findMatches(filter(), 0, false, false));
        }

        @Test
        @DisplayName("Scenario: no results is a normal answer, not an error")
        void noResults() {
            SoccerService.MatchFilter f = filter();
            f.team = "Flamengo";
            f.season = 1990;
            assertContains(svc.findMatches(f, null, false, false), "0 found", "No matches");
        }
    }

    @Nested
    @DisplayName("Feature: Team queries")
    class TeamQueries {
        @Test
        @DisplayName("Scenario: get team statistics for a season")
        void seasonStats() {
            // Flamengo's 2019 title season: 28W 6D 4L, 86 goals for, 37 against
            String text = svc.teamStats("Flamengo", 2019, "Brasileirão", null);
            assertContains(text, "Matches: 38", "Wins: 28, Draws: 6, Losses: 4", "Goals For: 86, Goals Against: 37", "Home:", "Away:");
        }

        @Test
        @DisplayName("Scenario: home record")
        void homeRecord() {
            String text = svc.teamStats("Corinthians", 2022, "Brasileirão", "home");
            assertContains(text, "Corinthians home record", "Matches: 19", "Win rate:");
        }

        @Test
        @DisplayName("Scenario: compare two teams head-to-head")
        void headToHead() {
            String text = svc.headToHead("Palmeiras", "Santos", null, null, 5);
            assertContains(text, "Palmeiras vs Santos", "Palmeiras wins:", "Santos wins:", "Draws:", "By competition:", "Most recent matches:");
            // symmetric: swapping the teams swaps the win counts
            String rev = svc.headToHead("Santos-SP", "Palmeiras-SP", null, null, 5);
            String wins = text.lines().filter(l -> l.startsWith("Palmeiras wins")).findFirst().get();
            String[] n = wins.replaceAll("[^0-9,]", "").split(",");
            assertContains(rev, "Santos wins: " + n[1] + ", Palmeiras wins: " + n[0] + ", Draws: " + n[2]);
        }

        @Test
        @DisplayName("Scenario: ambiguous or identical teams are rejected")
        void ambiguous() {
            IllegalArgumentException e = assertThrows(IllegalArgumentException.class, () -> svc.teamStats("Atlético", null, null, null));
            assertContains(e.getMessage(), "ambiguous", "Atlético-MG");
            assertThrows(IllegalArgumentException.class, () -> svc.headToHead("Flamengo", "Flamengo-RJ", null, null, null));
        }

        @Test
        @DisplayName("Scenario: which team scored the most goals in a season")
        void mostGoals() {
            String text = svc.teamRankings("goals_for", null, "Serie A", 2019, null, 3);
            assertContains(text, "1. Flamengo", "goals 86-37");
        }

        @Test
        @DisplayName("Scenario: best home and away records")
        void homeAwayRankings() {
            assertContains(svc.teamRankings("win_rate", "away", "Serie A", null, null, 5), "away matches only", "1. ", "5. ");
            assertContains(svc.teamRankings(null, "home", null, 2018, null, 5), "home matches only", "win rate");
            assertThrows(IllegalArgumentException.class, () -> svc.teamRankings("bogus", null, null, null, null, null));
        }

        @Test
        @DisplayName("Scenario: team profile combines match files and FIFA players (cross-file)")
        void profile() {
            String text = svc.teamProfile("Grêmio");
            assertContains(text, DataStore.SERIE_A, DataStore.COPA_DO_BRASIL, DataStore.LIBERTADORES, "Internacional (Gre-Nal)",
                    "FIFA player data: 20 players");
        }

        @Test
        @DisplayName("Scenario: derbies in a season")
        void derbies() {
            String text = svc.derbies(2023, null, null, null);
            assertContains(text, "Fla-Flu", "Gre-Nal");
            assertContains(svc.derbies(2019, "Brasileirão", "Grêmio", null), ": 2 found", "Gre-Nal");
        }
    }

    @Nested
    @DisplayName("Feature: Competition queries")
    class CompetitionQueries {
        @Test
        @DisplayName("Scenario: who won the 2019 Brasileirão")
        void champion2019() {
            String text = svc.standings(null, 2019, null);
            assertContains(text, "1. Flamengo - 90 pts (28W, 6D, 4L)", "Champion", "2. Santos - 74 pts (22W, 8D, 8L)",
                    "3. Palmeiras - 74 pts (21W, 11D, 6L)");
            assertEquals(20, text.lines().filter(l -> l.matches("^\\d+\\. .*")).count());
        }

        @Test
        @DisplayName("Scenario: which teams were relegated in 2020")
        void relegated2020() {
            String text = svc.standings("Brasileirão", 2020, null);
            Set<String> relegated = text.lines().filter(l -> l.endsWith("Relegated"))
                    .map(l -> l.substring(l.indexOf(' ') + 1, l.indexOf(" - "))).collect(Collectors.toSet());
            assertEquals(Set.of("Vasco", "Goiás", "Coritiba", "Botafogo"), relegated);
        }

        @Test
        @DisplayName("Scenario: league table is internally consistent")
        void tableConsistency() {
            for (int season = 2006; season <= 2021; season++) { // 2022 lacks one result in the data
                List<Map.Entry<String, SoccerService.Rec>> t = svc.table(DataStore.SERIE_A, season);
                assertEquals(20, t.size(), "teams in " + season);
                assertEquals(760, t.stream().mapToInt(e -> e.getValue().p).sum(), "matches in " + season);
                assertEquals(0, t.stream().mapToInt(e -> e.getValue().gd()).sum());
            }
        }

        @Test
        @DisplayName("Scenario: incomplete seasons do not claim a champion")
        void incompleteSeason() {
            String text = svc.standings("Serie B", 2018, 5);
            assertFalse(text.contains("Champion"));
            assertContains(text, "partial");
        }

        @Test
        @DisplayName("Scenario: 2018 Copa Libertadores bracket")
        void bracket() {
            String text = svc.bracket("Libertadores", 2018, false);
            assertContains(text, "Round of 16:", "Quarterfinals:", "Semifinals:", "Final:",
                    "Boca Juniors vs River Plate: aggregate 3-5 — River Plate advance as champions");
            assertContains(svc.bracket("Copa do Brasil", 2019, false), "Athletico-PR vs Internacional: aggregate 3-1");
        }

        @Test
        @DisplayName("Scenario: wrong tool for the competition type is explained")
        void wrongType() {
            assertThrows(IllegalArgumentException.class, () -> svc.standings("Libertadores", 2018, null));
            assertThrows(IllegalArgumentException.class, () -> svc.bracket("Brasileirão", 2018, false));
            assertThrows(IllegalArgumentException.class, () -> svc.standings(null, null, null));
            assertContains(svc.standings(null, 1995, null), "No Brasileirão Serie A matches for season 1995");
        }
    }

    @Nested
    @DisplayName("Feature: Player queries")
    class PlayerQueries {
        @Test
        @DisplayName("Scenario: top Brazilian players")
        void brazilians() {
            String text = svc.searchPlayers(null, "Brazil", null, null, null, null, false, null, 3);
            assertContains(text, "1. Neymar Jr - Overall: 92", "Position: LW", "Club: Paris Saint-Germain", "827 found");
            assertEquals(827, svc.selectPlayers(null, "Brazilian", null, null, null, null, false).size());
        }

        @Test
        @DisplayName("Scenario: search by name ignores accents and case")
        void byName() {
            assertContains(svc.playerDetails("neymar", null), "Neymar Jr", "Nationality: Brazil", "Overall: 92", "Attributes:");
            assertContains(svc.playerDetails(null, 158023L), "L. Messi");
            assertContains(svc.playerDetails("Zzyzx Qqq", null), "No player matching");
            assertThrows(IllegalArgumentException.class, () -> svc.playerDetails(null, null));
        }

        @Test
        @DisplayName("Scenario: players at a club, filtered by position group")
        void byClubAndPosition() {
            List<Player> santos = svc.selectPlayers(null, null, "Santos", null, null, null, true);
            assertEquals(20, santos.size());
            assertTrue(santos.stream().allMatch(p -> p.club.equals("Santos")));
            List<Player> fw = svc.selectPlayers(null, null, "Grêmio", "forwards", null, null, false);
            assertFalse(fw.isEmpty());
            assertTrue(fw.stream().allMatch(p -> Set.of("ST", "CF", "LF", "RF", "LS", "RS", "LW", "RW").contains(p.position)));
            // club lookup by an alias used in the match files (cross-file name normalisation)
            assertEquals(20, svc.selectPlayers(null, null, "Atlético-MG", null, null, null, false).size());
        }

        @Test
        @DisplayName("Scenario: Brazilian players at Brazilian clubs")
        void byClub() {
            String text = svc.playersByClub("Brazil", true, null);
            assertContains(text, "Grêmio: 20 players (avg rating:", "Santos:");
            assertFalse(text.contains("Boavista"), "foreign namesakes are not Brazilian clubs");
        }

        @Test
        @DisplayName("Scenario: unknown club lists the clubs that are available")
        void unknownClub() {
            assertContains(svc.searchPlayers(null, null, "Flamengo", null, null, null, false, null, null), "0 found", "Brazilian clubs present");
            assertThrows(IllegalArgumentException.class,
                    () -> svc.searchPlayers(null, null, null, null, null, null, false, "height", null));
        }
    }

    @Nested
    @DisplayName("Feature: Statistical analysis")
    class Statistics {
        @Test
        @DisplayName("Scenario: average goals per match in the Brasileirão")
        void averageGoals() {
            SoccerService.MatchFilter f = filter();
            f.competition = "Brasileirão";
            String text = svc.leagueStats(f);
            List<Match> ms = ds.matches.stream().filter(m -> m.primary && m.played() && m.competition.equals(DataStore.SERIE_A))
                    .collect(Collectors.toList());
            double avg = ms.stream().mapToInt(Match::totalGoals).average().orElse(0);
            assertContains(text, "Average goals per match: " + String.format(java.util.Locale.ROOT, "%.2f", avg), "Home win rate:",
                    "Goals per match by season:");
            assertTrue(avg > 2.0 && avg < 3.2);
        }

        @Test
        @DisplayName("Scenario: biggest wins in the dataset")
        void biggestWins() {
            String text = svc.biggestWins(filter(), 5);
            assertContains(text, "1. 2021-06-08: São Paulo 9-1 4 de Julho");
            SoccerService.MatchFilter f = filter();
            f.competition = "Serie A";
            f.season = 2019;
            assertContains(svc.biggestWins(f, 3), "1. ", "Brasileirão Serie A 2019");
        }

        @Test
        @DisplayName("Scenario: compare the 2018 and 2019 seasons")
        void compareSeasons() {
            String text = svc.compareSeasons(null, 2018, 2019);
            assertContains(text, "2018:", "2019:", "Top of the table: Palmeiras (80 pts", "Top of the table: Flamengo (90 pts",
                    "Matches played: 380");
            assertThrows(IllegalArgumentException.class, () -> svc.compareSeasons(null, 2018, null));
        }

        @Test
        @DisplayName("Scenario: queries respond well within the performance targets")
        void performance() {
            long t0 = System.nanoTime();
            svc.teamStats("Palmeiras", 2019, null, null);
            svc.searchPlayers("Gabriel", null, null, null, null, null, false, null, null);
            long simple = (System.nanoTime() - t0) / 1_000_000;
            t0 = System.nanoTime();
            svc.leagueStats(filter());
            svc.teamRankings("win_rate", "home", null, null, null, 20);
            svc.biggestWins(filter(), 20);
            long aggregate = (System.nanoTime() - t0) / 1_000_000;
            assertTrue(simple < 2000, "simple lookups took " + simple + " ms");
            assertTrue(aggregate < 5000, "aggregates took " + aggregate + " ms");
        }
    }
}
