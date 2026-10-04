package br.soccer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

/** BDD-style scenarios (Given the data is loaded / When a query runs / Then ...) on the real data. */
class QueryServiceTest {
    private final DataStore ds = TestData.STORE;
    private final QueryService q = TestData.QUERIES;

    private static void assertContains(String text, String expected) {
        assertTrue(text.contains(expected), () -> "Expected to find \"" + expected + "\" in:\n" + text);
    }

    @Nested
    @DisplayName("Feature: Data loading")
    class Loading {
        @Test
        @DisplayName("Scenario: all six CSV files are loaded with the documented row counts")
        void allFilesLoaded() {
            Map<String, int[]> s = ds.fileStats();
            assertEquals(4180, s.get(DataStore.F_BRASILEIRAO)[0]);
            assertEquals(1337, s.get(DataStore.F_CUP)[0]);
            assertEquals(1255, s.get(DataStore.F_LIBERTADORES)[0]);
            assertEquals(10296, s.get(DataStore.F_EXTENDED)[0]);
            assertEquals(6886, s.get(DataStore.F_HISTORICAL)[0]);
            assertEquals(18207, s.get(DataStore.F_FIFA)[0]);
            assertEquals(18207, ds.players().size());
        }

        @Test
        @DisplayName("Scenario: every file contributes matches and overlapping files are merged")
        void filesContributeAndMerge() {
            for (String f : List.of(DataStore.F_BRASILEIRAO, DataStore.F_CUP, DataStore.F_LIBERTADORES,
                    DataStore.F_EXTENDED, DataStore.F_HISTORICAL)) {
                assertTrue(ds.matches().stream().anyMatch(m -> m.sources.contains(f)), f);
            }
            // A 20-team double round-robin has exactly 380 matches even though 2019 is in three files.
            long serieA2019 = ds.matches().stream()
                    .filter(m -> m.competition.equals(DataStore.SERIE_A) && m.season == 2019).count();
            assertEquals(380, serieA2019);
            assertTrue(ds.matches().stream().anyMatch(m -> m.sources.size() == 3));
        }

        @Test
        @DisplayName("Scenario: accented names survive UTF-8 decoding")
        void utf8() {
            assertTrue(ds.players().stream().anyMatch(p -> p.club().equals("Grêmio")));
            assertTrue(ds.matches().stream().anyMatch(m -> "Maracanã".equals(m.stadium)));
        }
    }

    @Nested
    @DisplayName("Feature: Match queries")
    class Matches {
        @Test
        @DisplayName("Scenario: find matches between two teams")
        void betweenTwoTeams() {
            String out = q.searchMatches(new QueryService.Filter().team("Flamengo").opponent("Fluminense"), 5);
            assertContains(out, "Flamengo");
            assertContains(out, "Fluminense");
            assertContains(out, "more matches in dataset");
            assertContains(out, "Head-to-head in dataset: Flamengo");
            // Each listed match has a date, a score and a competition.
            List<String> lines = out.lines().filter(l -> l.startsWith("- ")).toList();
            assertEquals(5, lines.size());
            for (String l : lines) {
                assertTrue(l.matches("- \\d{4}-\\d{2}-\\d{2}: .+ \\d+-\\d+ .+ \\((Brasileirão|Copa).*\\)"), l);
            }
        }

        @Test
        @DisplayName("Scenario: spelling variants of a team return the same matches")
        void variantsEquivalent() {
            String a = q.searchMatches(new QueryService.Filter().team("São Paulo").season(2015), 500);
            String b = q.searchMatches(new QueryService.Filter().team("sao paulo-sp").season(2015), 500);
            String c = q.searchMatches(new QueryService.Filter().team("São Paulo FC").season(2015), 500);
            assertEquals(a, b);
            assertEquals(a, c);
        }

        @Test
        @DisplayName("Scenario: filter by team and season")
        void byTeamAndSeason() {
            String out = q.searchMatches(new QueryService.Filter().team("Palmeiras").season(2023), 200);
            assertContains(out, "Palmeiras");
            out.lines().filter(l -> l.startsWith("- ")).forEach(l -> assertContains(l, " 2023"));
        }

        @Test
        @DisplayName("Scenario: filter by date range and venue")
        void byDateRangeAndVenue() {
            String out = q.searchMatches(new QueryService.Filter().team("Santos").venue("home")
                    .from(LocalDate.of(2019, 5, 1)).to(LocalDate.of(2019, 5, 31)), 50);
            List<String> lines = out.lines().filter(l -> l.startsWith("- ")).toList();
            assertFalse(lines.isEmpty());
            for (String l : lines) {
                assertTrue(l.startsWith("- 2019-05-"), l);
                assertTrue(l.matches("- \\S+ Santos \\d+-\\d+ .*"), l);
            }
        }

        @Test
        @DisplayName("Scenario: find all Copa do Brasil finals")
        void cupFinals() {
            String out = q.searchMatches(new QueryService.Filter().competition("Copa do Brasil").stage("finals"), 50);
            assertContains(out, "2018-10-17: Corinthians 1-2 Cruzeiro (Copa do Brasil 2018, final)");
            out.lines().filter(l -> l.startsWith("- ")).forEach(l -> assertContains(l, "final"));
        }

        @Test
        @DisplayName("Scenario: Libertadores matches are searchable by stage")
        void libertadoresFinal() {
            String out = q.searchMatches(new QueryService.Filter().competition("Libertadores").stage("final")
                    .season(2019), 10);
            assertContains(out, "Flamengo 2-1 River Plate");
        }

        @Test
        @DisplayName("Scenario: most recent meeting is returned first")
        void lastMeeting() {
            String out = q.searchMatches(new QueryService.Filter().team("Flamengo").opponent("Corinthians"), 1);
            List<LocalDate> dates = new ArrayList<>();
            ds.matches().stream().filter(m -> m.involves("flamengo") && m.involves("corinthians"))
                    .forEach(m -> dates.add(m.date));
            assertContains(out, "- " + dates.stream().max(LocalDate::compareTo).get());
        }

        @Test
        @DisplayName("Scenario: unknown and ambiguous teams give a helpful message")
        void unknownTeam() {
            IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                    () -> q.teamStats("Real Madrid Galacticos", null, null, null));
            assertContains(e.getMessage(), "No team found");
            e = assertThrows(IllegalArgumentException.class, () -> q.teamStats("Atletico", null, null, null));
            assertContains(e.getMessage(), "ambiguous");
            assertContains(e.getMessage(), "Atlético Mineiro");
            assertEquals("No matches found for the given criteria.",
                    q.searchMatches(new QueryService.Filter().team("Flamengo").season(1950), null));
        }
    }

    @Nested
    @DisplayName("Feature: Team queries")
    class Teams {
        @Test
        @DisplayName("Scenario: get team statistics for a season")
        void seasonStats() {
            QueryService.Rec r = q.teamRecord("Flamengo", 2019, "Brasileirão", null);
            assertEquals(38, r.played);
            assertEquals(28, r.wins);
            assertEquals(6, r.draws);
            assertEquals(4, r.losses);
            assertEquals(86, r.goalsFor);
            assertEquals(37, r.goalsAgainst);
            String out = q.teamStats("Palmeiras", 2023, null, null);
            assertContains(out, "Wins:");
            assertContains(out, "Draws:");
            assertContains(out, "Losses:");
            assertContains(out, "Goals For:");
        }

        @Test
        @DisplayName("Scenario: home record in a season")
        void homeRecord() {
            String out = q.teamStats("Corinthians", 2022, "Brasileirão", "home");
            assertContains(out, "Corinthians home record (2022 Brasileirão Série A)");
            assertContains(out, "- Matches: 19");
            assertContains(out, "Win rate:");
            QueryService.Rec home = q.teamRecord("Corinthians", 2022, "serie a", "home");
            QueryService.Rec away = q.teamRecord("Corinthians", 2022, "serie a", "away");
            assertEquals(38, home.played + away.played);
        }

        @Test
        @DisplayName("Scenario: compare two teams head-to-head")
        void headToHead() {
            String out = q.headToHead("Palmeiras", "Santos", null, null);
            assertContains(out, "Palmeiras vs Santos");
            assertContains(out, "Head-to-head in dataset: Palmeiras");
            // Swapping the teams mirrors the tally.
            QueryService.Rec a = q.teamRecord("Palmeiras", null, null, null);
            assertTrue(a.played > 0);
            String swapped = q.headToHead("Santos", "Palmeiras", null, null);
            int matches = Integer.parseInt(out.lines().filter(l -> l.startsWith("- Matches: ")).findFirst().get().substring(11));
            assertContains(swapped, "- Matches: " + matches);
        }

        @Test
        @DisplayName("Scenario: list the competitions a team has played in")
        void competitions() {
            String out = q.teamStats("Palmeiras", null, null, null);
            assertContains(out, "By competition:");
            assertContains(out, "Brasileirão Série A");
            assertContains(out, "Copa do Brasil");
            assertContains(out, "Copa Libertadores");
        }

        @Test
        @DisplayName("Scenario: rank teams by home and away record")
        void rankings() {
            String home = q.teamRankings("win_rate", "home", "serie a", null, 100, 5);
            assertContains(home, "home matches");
            assertEquals(5, home.lines().filter(l -> l.matches("\\d+\\. .*")).count());
            String goals = q.teamRankings("goals_for", null, "serie a", 2019, null, 1);
            assertContains(goals, "1. Flamengo");
            assertContains(goals, "goals 86-37");
            assertThrows(IllegalArgumentException.class, () -> q.teamRankings("bogus", null, null, null, null, null));
        }
    }

    @Nested
    @DisplayName("Feature: Player queries")
    class Players {
        @Test
        @DisplayName("Scenario: search players by name")
        void byName() {
            String out = q.searchPlayers("Neymar", null, null, null, null, null);
            assertContains(out, "Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain");
            assertContains(q.playerDetails("neymar jr"), "Nationality: Brazil");
            assertContains(q.playerDetails("Nobody McNobody"), "No player found");
        }

        @Test
        @DisplayName("Scenario: top Brazilian players sorted by rating")
        void brazilians() {
            List<Player> ps = q.findPlayers(null, "Brazil", null, null, null);
            assertTrue(ps.size() > 500);
            assertEquals("Neymar Jr", ps.get(0).name());
            assertTrue(ps.stream().allMatch(p -> p.nationality().equals("Brazil")));
            for (int i = 1; i < ps.size(); i++) assertTrue(ps.get(i - 1).overall() >= ps.get(i).overall());
            assertEquals(ps, q.findPlayers(null, "brazilian", null, null, null));
        }

        @Test
        @DisplayName("Scenario: filter by club and position group, ignoring accents")
        void byClubAndPosition() {
            List<Player> ps = q.findPlayers(null, null, "Gremio", "forwards", null);
            assertFalse(ps.isEmpty());
            assertTrue(ps.stream().allMatch(p -> p.club().equals("Grêmio")));
            assertTrue(ps.stream().allMatch(p -> List.of("ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS").contains(p.position())));
            assertTrue(q.findPlayers(null, null, "Santos", "GK", 60).stream().allMatch(p -> p.position().equals("GK")));
        }

        @Test
        @DisplayName("Scenario: Brazilian players grouped by Brazilian club")
        void byClub() {
            String out = q.playersByClub(null, null, null);
            assertContains(out, "Brazil players at Brazilian clubs");
            assertContains(out, "- Santos: ");
            assertContains(out, "avg rating");
            assertFalse(out.contains("Boavista FC"), "Portuguese Boavista must not count as Brazilian");
        }

        @Test
        @DisplayName("Scenario: cross-file query combines match record and FIFA squad")
        void clubProfile() {
            String out = q.clubProfile("Grêmio");
            assertContains(out, "Grêmio record (all competitions)");
            assertContains(out, "FIFA squad for Grêmio");
            assertContains(out, "players, average overall");
            assertContains(q.clubProfile("Flamengo"), "No players for this club in the FIFA dataset");
        }
    }

    @Nested
    @DisplayName("Feature: Competition queries")
    class Competitions {
        @Test
        @DisplayName("Scenario: who won the 2019 Brasileirão")
        void champion2019() {
            String out = q.standings(2019, null);
            assertContains(out, "2019 Brasileirão Série A Final Standings (calculated from matches)");
            assertContains(out, "1. Flamengo - 90 pts (28W, 6D, 4L");
            assertContains(out, "- Champion");
            assertContains(out, "2. Santos - 74 pts (22W, 8D, 8L");
            assertContains(out, "3. Palmeiras - 74 pts (21W, 11D, 6L");
        }

        @Test
        @DisplayName("Scenario: which teams were relegated in 2020")
        void relegated2020() {
            List<String> relegated = q.standings(2020, "Brasileirão").lines()
                    .filter(l -> l.endsWith("- Relegated")).map(l -> l.split(" - ")[0].replaceAll("^\\d+\\. ", ""))
                    .sorted().toList();
            assertEquals(List.of("Botafogo", "Coritiba", "Goiás", "Vasco"), relegated);
        }

        @Test
        @DisplayName("Scenario: every complete Serie A season has a consistent table")
        void tablesConsistent() {
            for (int season = 2006; season <= 2022; season++) {
                Map<String, QueryService.Rec> t = q.standingsTable(season, null);
                assertEquals(20, t.size(), "teams in " + season);
                int wins = 0, losses = 0, gf = 0, ga = 0;
                for (QueryService.Rec r : t.values()) {
                    assertEquals(38, r.played, "matches in " + season);
                    wins += r.wins;
                    losses += r.losses;
                    gf += r.goalsFor;
                    ga += r.goalsAgainst;
                }
                assertEquals(wins, losses);
                assertEquals(gf, ga);
            }
        }

        @Test
        @DisplayName("Scenario: show the 2018 Copa Libertadores bracket")
        void bracket() {
            String out = q.knockoutStages("Libertadores", 2018);
            assertContains(out, "Round of 16:");
            assertContains(out, "Quarterfinals:");
            assertContains(out, "Semifinals:");
            assertContains(out, "Final:");
            assertContains(out, "Aggregate:");
            assertContains(out, "River Plate");
        }

        @Test
        @DisplayName("Scenario: Serie B tables come from the extended dataset")
        void serieB() {
            assertContains(q.standings(2022, "Serie B"), "1. Cruzeiro");
            assertContains(q.standings(1990, "Serie A"), "No Brasileirão Série A matches");
        }
    }

    @Nested
    @DisplayName("Feature: Statistical analysis")
    class Statistics {
        @Test
        @DisplayName("Scenario: average goals per match and home win rate")
        void averages() {
            int[] a = q.aggregate("Brasileirão", 2019);
            assertEquals(380, a[0]);
            assertEquals(876, a[1]);
            assertEquals(a[0], a[2] + a[3] + a[4]);
            String out = q.matchStatistics("Brasileirão", null);
            assertContains(out, "Average goals per match: ");
            assertContains(out, "Home win rate: ");
            assertContains(out, "Goals per match by season:");
        }

        @Test
        @DisplayName("Scenario: biggest wins are ordered by margin")
        void biggestWins() {
            String out = q.biggestWins(null, null, null, 10);
            List<Integer> margins = out.lines().filter(l -> l.matches("\\d+\\. .*")).map(l -> {
                java.util.regex.Matcher m = java.util.regex.Pattern.compile(" (\\d+)-(\\d+) ").matcher(l);
                assertTrue(m.find(), l);
                return Math.abs(Integer.parseInt(m.group(1)) - Integer.parseInt(m.group(2)));
            }).toList();
            assertEquals(10, margins.size());
            for (int i = 1; i < margins.size(); i++) assertTrue(margins.get(i - 1) >= margins.get(i));
            assertTrue(margins.get(0) >= 7);
        }

        @Test
        @DisplayName("Scenario: compare the 2018 and 2019 seasons")
        void compareSeasons() {
            String out = q.compareSeasons(2018, 2019, null);
            assertContains(out, "2018:");
            assertContains(out, "2019:");
            assertContains(out, "Top of table: Palmeiras (80 pts)");
            assertContains(out, "Top of table: Flamengo (90 pts)");
        }

        @Test
        @DisplayName("Scenario: show all derbies in a season")
        void derbies() {
            String out = q.derbies(2023, null, null, 100);
            assertContains(out, "Fla-Flu");
            assertContains(out, "Gre-Nal");
            out.lines().filter(l -> l.startsWith("- ")).forEach(l -> assertContains(l, "2023"));
        }

        @Test
        @DisplayName("Scenario: simple lookups answer in under 2s and aggregates in under 5s")
        void performance() {
            long t0 = System.nanoTime();
            q.searchMatches(new QueryService.Filter().team("Flamengo").opponent("Corinthians"), 1);
            q.searchPlayers("Gabriel", null, null, null, null, null);
            long simple = (System.nanoTime() - t0) / 1_000_000;
            t0 = System.nanoTime();
            q.teamRankings("win_rate", "away", null, null, null, null);
            q.matchStatistics(null, null);
            q.standings(2019, null);
            long aggregate = (System.nanoTime() - t0) / 1_000_000;
            assertTrue(simple < 2000, "simple lookups took " + simple + " ms");
            assertTrue(aggregate < 5000, "aggregate queries took " + aggregate + " ms");
        }
    }
}
