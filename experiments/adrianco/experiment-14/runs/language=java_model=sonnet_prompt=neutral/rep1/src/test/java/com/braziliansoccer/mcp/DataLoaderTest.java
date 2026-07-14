package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.data.DataLoader;
import com.braziliansoccer.mcp.data.Match;
import com.braziliansoccer.mcp.data.Player;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class DataLoaderTest {

    private static DataLoader loader;

    @BeforeAll
    static void setup() {
        loader = new DataLoader("data/kaggle");
        loader.load();
    }

    @Test
    void testMatchesLoaded() {
        List<Match> matches = loader.getAllMatches();
        assertFalse(matches.isEmpty(), "Matches should be loaded");
        // We have 4180 + 1337 + 1255 + 10296 + 6886 matches across all files
        assertTrue(matches.size() > 10000, "Should have more than 10,000 matches");
    }

    @Test
    void testPlayersLoaded() {
        List<Player> players = loader.getAllPlayers();
        assertFalse(players.isEmpty(), "Players should be loaded");
        assertTrue(players.size() > 5000, "Should have more than 5,000 players");
    }

    @Test
    void testBrasileiraoMatchesHaveCorrectCompetition() {
        long brasileiraoCount = loader.getAllMatches().stream()
            .filter(m -> "Brasileirao Serie A".equals(m.competition))
            .count();
        assertTrue(brasileiraoCount > 1000, "Should have many Brasileirao matches");
    }

    @Test
    void testCopaBrasilMatchesLoaded() {
        long copaCount = loader.getAllMatches().stream()
            .filter(m -> "Copa do Brasil".equals(m.competition))
            .count();
        assertTrue(copaCount > 100, "Should have Copa do Brasil matches");
    }

    @Test
    void testLibertadoresMatchesLoaded() {
        long libCount = loader.getAllMatches().stream()
            .filter(m -> "Copa Libertadores".equals(m.competition))
            .count();
        assertTrue(libCount > 100, "Should have Libertadores matches");
    }

    @Test
    void testMatchesHaveSeasons() {
        long withSeason = loader.getAllMatches().stream()
            .filter(m -> m.season > 2000)
            .count();
        assertTrue(withSeason > 5000, "Most matches should have valid seasons");
    }

    @Test
    void testPlayersHaveNames() {
        long withNames = loader.getAllPlayers().stream()
            .filter(p -> p.name != null && !p.name.isEmpty())
            .count();
        assertEquals(loader.getAllPlayers().size(), withNames, "All players should have names");
    }

    @Test
    void testBrazilianPlayersExist() {
        long brazilians = loader.getAllPlayers().stream()
            .filter(p -> "Brazil".equalsIgnoreCase(p.nationality))
            .count();
        assertTrue(brazilians > 500, "Should have many Brazilian players");
    }

    @Test
    void testPlayerOverallRatings() {
        boolean hasHighRated = loader.getAllPlayers().stream()
            .anyMatch(p -> p.overall >= 90);
        assertTrue(hasHighRated, "Should have some high-rated players");
    }

    @Test
    void testMatchWinnerField() {
        long validWinner = loader.getAllMatches().stream()
            .filter(m -> "home".equals(m.winner) || "away".equals(m.winner) || "draw".equals(m.winner))
            .count();
        assertEquals(loader.getAllMatches().size(), validWinner, "All matches should have valid winner");
    }
}
