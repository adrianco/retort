package soccer;

import org.junit.jupiter.api.*;

import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/** BDD-style scenarios (Given data loaded / When query / Then answer) against the real datasets. */
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class SoccerFeatureTest {
    SoccerService svc;

    @BeforeAll void givenTheDataIsLoaded() throws Exception {
        svc = new SoccerService(DataStore.load(Path.of("data/kaggle")));
    }

    // ---- Feature: data coverage ----
    @Test void allSixFilesAreLoaded() {
        var rows = svc.data().rowsPerFile();
        assertEquals(6, rows.size());
        assertEquals(4180, rows.get("Brasileirao_Matches.csv"));
        assertEquals(1337, rows.get("Brazilian_Cup_Matches.csv"));
        assertEquals(1255, rows.get("Libertadores_Matches.csv"));
        assertEquals(10296, rows.get("BR-Football-Dataset.csv"));
        assertEquals(6886, rows.get("novo_campeonato_brasileiro.csv"));
        assertEquals(18207, rows.get("fifa_data.csv"));
        for (String src : List.of("Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv",
                "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv"))
            assertTrue(svc.data().matches().stream().anyMatch(m -> m.source().equals(src)), "queryable: " + src);
    }

    // ---- Feature: Match queries ----
    @Test void findMatchesBetweenTwoTeams() {
        var ms = svc.findMatches("Flamengo", "Fluminense", null, null, null, null, null);
        assertFalse(ms.isEmpty());
        for (Match m : ms) {
            assertNotNull(m.date());
            assertNotNull(m.competition());
            assertTrue(m.involves("Flamengo") && m.involves("Fluminense"));
        }
        String text = svc.searchMatches("Flamengo", "Fluminense", null, null, null, null, null, 5);
        assertTrue(text.contains("Fla-Flu"));
        assertTrue(text.contains("Head-to-head in dataset: Flamengo"));
    }

    @Test void matchesByTeamAndSeason() {
        String t = svc.searchMatches("Palmeiras", null, null, 2023, null, null, null, 100);
        assertTrue(t.startsWith("Found"));
        assertTrue(t.contains("2023-"));
        assertFalse(t.contains("2022-"));
    }

    @Test void matchesByDateRangeAndCompetition() {
        var ms = svc.findMatches(null, null, "Libertadores", null, DataStore.date("2019-01-01"), DataStore.date("2019-12-31"), null);
        assertFalse(ms.isEmpty());
        assertTrue(ms.stream().allMatch(m -> m.date().getYear() == 2019 && m.competition().equals("Libertadores")));
    }

    @Test void copaDoBrasilFinals() {
        String t = svc.finals("Copa do Brasil");
        assertTrue(t.contains("2019-09-18: Internacional 1-2 Athletico Paranaense"), t);
    }

    @Test void lastMatchAndScore() {
        String t = svc.lastMatch("Flamengo", "Corinthians");
        assertTrue(t.contains("Most recent match"));
        assertTrue(t.contains("Score:"));
    }

    @Test void derbiesInSeason() {
        String t = svc.derbies(2023, null);
        assertTrue(t.contains("Fla-Flu") || t.contains("Derby Paulista"), t);
    }

    // ---- Feature: Team queries ----
    @Test void teamStatisticsForSeason() {
        var r = svc.record("Palmeiras", 2023, null, null);
        assertTrue(r.played > 0);
        assertEquals(r.played, r.wins + r.draws + r.losses);
        String t = svc.teamStats("Palmeiras", 2023, null, null);
        assertTrue(t.contains("Wins:") && t.contains("Losses:") && t.contains("Goals For:"));
    }

    @Test void corinthiansHomeRecord2022() {
        String t = svc.teamStats("Corinthians", 2022, "Brasileirão", "home");
        assertTrue(t.contains("Corinthians home record (2022 Brasileirão)"), t);
        assertTrue(t.contains("Win rate:"));
    }

    @Test void headToHeadIsConsistent() {
        String t = svc.headToHead("Palmeiras", "Santos", null);
        assertTrue(t.contains("Matches:"));
        assertTrue(t.contains("Palmeiras") && t.contains("wins"));
    }

    @Test void competitionsForTeamAcrossFiles() {
        String t = svc.teamCompetitions("Palmeiras");
        assertTrue(t.contains("Brasileirão") && t.contains("Copa do Brasil") && t.contains("Libertadores"));
    }

    // ---- Feature: Competition queries ----
    @Test void flamengoWon2019() {
        String t = svc.champion(2019, null);
        assertTrue(t.startsWith("Flamengo won the 2019 Brasileirão with 90 points (28W, 6D, 4L)"), t);
    }

    @Test void standingsFromHistoricalFile() {
        var table = svc.standingsTable(2008, "Brasileirão");
        assertEquals(20, table.size());
        assertEquals("São Paulo", table.get(0).team);
    }

    @Test void relegatedTeams2020() {
        String t = svc.relegated(2020);
        assertTrue(t.contains("Botafogo") && t.contains("Coritiba"), t);
    }

    @Test void libertadoresBracket() {
        String t = svc.bracket("Libertadores", 2018);
        assertTrue(t.contains("final") && !t.contains("group stage"), t);
    }

    @Test void topScoringTeam() {
        assertTrue(svc.topScoringTeams(2019, "Brasileirão", 1).contains("1. Flamengo - 86 goals"));
    }

    // ---- Feature: Statistics ----
    @Test void averageGoalsAndHomeWinRate() {
        String t = svc.competitionStats("Brasileirão", null);
        assertTrue(t.contains("Average goals per match:") && t.contains("Home win rate:"));
    }

    @Test void biggestWins() {
        String t = svc.biggestWins(null, null, 3);
        assertTrue(t.contains("9-1") || t.contains("8-0"), t);
    }

    @Test void bestHomeAndAwayRecords() {
        assertTrue(svc.bestRecords("Brasileirão", null, "home", 50, 5).startsWith("Best home records"));
        assertTrue(svc.bestRecords(null, null, "away", 50, 5).contains("1. "));
    }

    @Test void compareSeasons() {
        String t = svc.compareSeasons(null, List.of(2018, 2019));
        assertTrue(t.contains("2018") && t.contains("2019") && t.contains("Champion"));
    }

    // ---- Feature: Player queries ----
    @Test void brazilianPlayersSortedByRating() {
        var ps = svc.findPlayers(null, "Brazil", null, null, null);
        assertTrue(ps.size() > 500);
        assertEquals("Neymar Jr", ps.get(0).name());
    }

    @Test void playerByName() {
        assertTrue(svc.searchPlayers("Gabriel Barbosa", null, null, null, null, 5).contains("Gabriel Barbosa")
                || svc.searchPlayers("Gabriel", "Brazil", null, null, null, 5).contains("Gabriel"));
    }

    @Test void forwardsAtClub() {
        var ps = svc.findPlayers(null, null, "Santos", "forwards", null);
        assertFalse(ps.isEmpty());
        assertTrue(ps.stream().allMatch(p -> SoccerService.POSITION_GROUPS.get("forward").contains(p.position())));
    }

    @Test void brazilianPlayersByClub() {
        assertTrue(svc.playersByClub("Brazil", 5).contains("avg rating"));
    }

    @Test void crossFileClubProfile() {
        String t = svc.clubProfile("Santos");
        assertTrue(t.contains("players") && t.contains("record") && t.contains("has played in"));
    }

    // ---- Performance ----
    @Test void queriesAreFast() {
        long t0 = System.nanoTime();
        svc.lastMatch("Flamengo", "Corinthians");
        assertTrue((System.nanoTime() - t0) / 1e9 < 2);
        t0 = System.nanoTime();
        svc.bestRecords(null, null, "home", 20, 10);
        svc.standings(2015, null, null);
        assertTrue((System.nanoTime() - t0) / 1e9 < 5);
    }
}
