package com.soccer.mcp;

import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.*;

import java.io.IOException;
import java.nio.file.*;
import java.util.List;

@DisplayName("Feature: Data Loading and Queries")
class DataStoreTest {

    private static DataStore dataStore;
    private static boolean dataAvailable;

    @BeforeAll
    static void loadData() {
        dataStore = new DataStore();
        Path dataDir = Path.of("data/kaggle");
        dataAvailable = Files.exists(dataDir);
        if (dataAvailable) {
            try {
                dataStore.loadAll("data/kaggle");
            } catch (IOException e) {
                dataAvailable = false;
            }
        }
    }

    @Nested
    @DisplayName("Scenario: Load all CSV data files")
    class DataLoading {
        @Test
        @DisplayName("Given the data directory exists, all matches should be loaded")
        void loadsMatches() {
            assumeTrue(dataAvailable, "Data files not available");
            assertTrue(dataStore.matchCount() > 10000, "Should load at least 10000 matches, got " + dataStore.matchCount());
        }

        @Test
        @DisplayName("Given the FIFA data file exists, all players should be loaded")
        void loadsPlayers() {
            assumeTrue(dataAvailable, "Data files not available");
            assertTrue(dataStore.playerCount() > 15000, "Should load at least 15000 players, got " + dataStore.playerCount());
        }
    }

    @Nested
    @DisplayName("Scenario: Search matches between two teams")
    class MatchSearch {
        @Test
        @DisplayName("Given match data, searching for Flamengo vs Fluminense returns matches")
        void findDerbyMatches() {
            assumeTrue(dataAvailable, "Data files not available");
            List<Match> results = dataStore.searchMatches("Flamengo", "Fluminense", null, null, null, null, 100);
            assertFalse(results.isEmpty(), "Should find Fla-Flu matches");
            for (Match m : results) {
                assertTrue(
                    (TeamNameNormalizer.matches(m.homeTeam(), "Flamengo") && TeamNameNormalizer.matches(m.awayTeam(), "Fluminense"))
                    || (TeamNameNormalizer.matches(m.homeTeam(), "Fluminense") && TeamNameNormalizer.matches(m.awayTeam(), "Flamengo")),
                    "Each match should be between Flamengo and Fluminense: " + m.summary());
            }
        }

        @Test
        @DisplayName("Given match data, searching by season filters correctly")
        void filterBySeason() {
            assumeTrue(dataAvailable, "Data files not available");
            List<Match> results = dataStore.searchMatches("Palmeiras", null, null, "2019", null, null, 100);
            assertFalse(results.isEmpty());
            for (Match m : results) {
                assertEquals("2019", m.season());
            }
        }

        @Test
        @DisplayName("Given match data, searching by competition filters correctly")
        void filterByCompetition() {
            assumeTrue(dataAvailable, "Data files not available");
            List<Match> results = dataStore.searchMatches(null, null, "Copa Libertadores", null, null, null, 50);
            assertFalse(results.isEmpty());
            for (Match m : results) {
                assertTrue(m.competition().toLowerCase().contains("libertadores"));
            }
        }

        @Test
        @DisplayName("Given match data, searching by date range filters correctly")
        void filterByDateRange() {
            assumeTrue(dataAvailable, "Data files not available");
            List<Match> results = dataStore.searchMatches(null, null, null, null, "2019-01-01", "2019-12-31", 50);
            assertFalse(results.isEmpty());
            for (Match m : results) {
                assertTrue(m.date().compareTo("2019-01-01") >= 0 && m.date().compareTo("2019-12-31") <= 0,
                    "Match date should be in range: " + m.date());
            }
        }

        @Test
        @DisplayName("Given no matching criteria, search returns empty list")
        void noResults() {
            assumeTrue(dataAvailable, "Data files not available");
            List<Match> results = dataStore.searchMatches("NonExistentTeam", null, null, null, null, null, 20);
            assertTrue(results.isEmpty());
        }
    }

    @Nested
    @DisplayName("Scenario: Get team statistics")
    class TeamStatistics {
        @Test
        @DisplayName("Given match data, team stats should have correct totals")
        void teamStatsConsistent() {
            assumeTrue(dataAvailable, "Data files not available");
            DataStore.TeamStats stats = dataStore.getTeamStats("Palmeiras", null, "2019");
            assertTrue(stats.matches() > 0, "Palmeiras should have matches in 2019");
            assertEquals(stats.matches(), stats.wins() + stats.draws() + stats.losses(),
                "W+D+L should equal total matches");
            assertTrue(stats.winRate() >= 0 && stats.winRate() <= 100);
        }

        @Test
        @DisplayName("Given match data, team stats for nonexistent team returns zero")
        void noMatchesForUnknownTeam() {
            assumeTrue(dataAvailable, "Data files not available");
            DataStore.TeamStats stats = dataStore.getTeamStats("NonExistent FC", null, null);
            assertEquals(0, stats.matches());
        }
    }

    @Nested
    @DisplayName("Scenario: Head-to-head comparison")
    class HeadToHeadComparison {
        @Test
        @DisplayName("Given match data, head-to-head has consistent totals")
        void headToHeadConsistent() {
            assumeTrue(dataAvailable, "Data files not available");
            DataStore.HeadToHead h2h = dataStore.headToHead("Flamengo", "Fluminense", null, null);
            assertFalse(h2h.matches().isEmpty());
            assertEquals(h2h.matches().size(), h2h.team1Wins() + h2h.team2Wins() + h2h.draws());
        }
    }

    @Nested
    @DisplayName("Scenario: Search players")
    class PlayerSearch {
        @Test
        @DisplayName("Given FIFA data, searching for Messi returns results")
        void findMessi() {
            assumeTrue(dataAvailable, "Data files not available");
            List<Player> results = dataStore.searchPlayers("Messi", null, null, null, null, 10);
            assertFalse(results.isEmpty(), "Should find Messi");
            assertTrue(results.get(0).name().contains("Messi"));
        }

        @Test
        @DisplayName("Given FIFA data, filtering by Brazilian nationality returns players")
        void findBrazilianPlayers() {
            assumeTrue(dataAvailable, "Data files not available");
            List<Player> results = dataStore.searchPlayers(null, "Brazil", null, null, null, 50);
            assertFalse(results.isEmpty());
            for (Player p : results) {
                assertTrue(p.nationality().toLowerCase().contains("brazil"));
            }
        }

        @Test
        @DisplayName("Given FIFA data, filtering by club returns players from that club")
        void findByClub() {
            assumeTrue(dataAvailable, "Data files not available");
            List<Player> results = dataStore.searchPlayers(null, null, "Cruzeiro", null, null, 50);
            assertFalse(results.isEmpty());
            for (Player p : results) {
                assertTrue(p.club().toLowerCase().contains("cruzeiro"));
            }
        }

        @Test
        @DisplayName("Given FIFA data, filtering by min rating returns high-rated players")
        void findHighRated() {
            assumeTrue(dataAvailable, "Data files not available");
            List<Player> results = dataStore.searchPlayers(null, null, null, null, 90, 20);
            assertFalse(results.isEmpty());
            for (Player p : results) {
                assertTrue(p.overall() >= 90, p.name() + " overall " + p.overall() + " should be >= 90");
            }
        }
    }

    @Nested
    @DisplayName("Scenario: Competition standings")
    class Standings {
        @Test
        @DisplayName("Given match data, standings for 2019 Brasileirão return teams sorted by points")
        void standings2019() {
            assumeTrue(dataAvailable, "Data files not available");
            List<DataStore.StandingsEntry> standings = dataStore.getStandings("Brasileirao", "2019");
            assertFalse(standings.isEmpty(), "Should have standings for 2019");
            for (int i = 1; i < standings.size(); i++) {
                assertTrue(standings.get(i - 1).points() >= standings.get(i).points(),
                    "Standings should be sorted by points");
            }
        }

        @Test
        @DisplayName("Given match data, each team's W+D+L equals total matches")
        void standingsConsistent() {
            assumeTrue(dataAvailable, "Data files not available");
            List<DataStore.StandingsEntry> standings = dataStore.getStandings("Brasileirao", "2019");
            for (DataStore.StandingsEntry e : standings) {
                assertEquals(e.matches(), e.wins() + e.draws() + e.losses(),
                    e.team() + " W+D+L should equal matches");
                assertEquals(e.goalDifference(), e.goalsFor() - e.goalsAgainst(),
                    e.team() + " GD should be GF-GA");
                assertEquals(e.points(), e.wins() * 3 + e.draws(),
                    e.team() + " points should be 3*W+D");
            }
        }
    }

    @Nested
    @DisplayName("Scenario: Biggest wins")
    class BiggestWins {
        @Test
        @DisplayName("Given match data, biggest wins are sorted by goal difference desc")
        void biggestWinsSorted() {
            assumeTrue(dataAvailable, "Data files not available");
            List<Match> wins = dataStore.getBiggestWins(null, null, 10);
            assertFalse(wins.isEmpty());
            for (int i = 1; i < wins.size(); i++) {
                assertTrue(wins.get(i - 1).goalDifference() >= wins.get(i).goalDifference(),
                    "Should be sorted by goal difference");
            }
            for (Match m : wins) {
                assertFalse(m.isDraw(), "Biggest wins should not include draws");
            }
        }
    }

    @Nested
    @DisplayName("Scenario: Date normalization")
    class DateNormalization {
        @Test
        @DisplayName("Given Brazilian date format DD/MM/YYYY, it should normalize to YYYY-MM-DD")
        void normalizeBrazilianDate() {
            assertEquals("2003-03-29", DataStore.normalizeDate("29/03/2003"));
            assertEquals("2019-12-08", DataStore.normalizeDate("08/12/2019"));
        }

        @Test
        @DisplayName("Given ISO datetime, it should extract the date part")
        void normalizeIsoDatetime() {
            assertEquals("2012-05-19", DataStore.normalizeDate("2012-05-19 18:30:00"));
        }

        @Test
        @DisplayName("Given ISO date, it should remain unchanged")
        void normalizeIsoDate() {
            assertEquals("2023-09-24", DataStore.normalizeDate("2023-09-24"));
        }

        @Test
        @DisplayName("Given null or blank, it should return empty string")
        void normalizeNullBlank() {
            assertEquals("", DataStore.normalizeDate(null));
            assertEquals("", DataStore.normalizeDate(""));
            assertEquals("", DataStore.normalizeDate("   "));
        }
    }

    @Nested
    @DisplayName("Scenario: Safe integer parsing")
    class SafeIntParsing {
        @Test
        @DisplayName("Given various numeric formats, safeInt should parse correctly")
        void parsesVariousFormats() {
            assertEquals(1, DataStore.safeInt("1"));
            assertEquals(1, DataStore.safeInt("1.0"));
            assertEquals(3, DataStore.safeInt("3.7"));
            assertEquals(0, DataStore.safeInt(""));
            assertEquals(0, DataStore.safeInt(null));
            assertEquals(0, DataStore.safeInt("abc"));
        }
    }
}
