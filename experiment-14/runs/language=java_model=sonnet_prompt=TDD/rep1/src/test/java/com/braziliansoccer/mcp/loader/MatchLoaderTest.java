package com.braziliansoccer.mcp.loader;

import com.braziliansoccer.mcp.model.Match;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class MatchLoaderTest {
    private static final String DATA_DIR = "./data/kaggle/";

    @Test void testLoadsAllFilesWithoutException() {
        assertDoesNotThrow(() -> {
            MatchLoader loader = new MatchLoader(DATA_DIR);
            List<Match> matches = loader.loadAll();
            assertNotNull(matches);
        });
    }

    @Test void testTotalMatchCount() {
        MatchLoader loader = new MatchLoader(DATA_DIR);
        List<Match> matches = loader.loadAll();
        assertTrue(matches.size() > 5000, "Expected >5000 matches, got: " + matches.size());
    }

    @Test void testPalmeirasMatchExists() {
        MatchLoader loader = new MatchLoader(DATA_DIR);
        List<Match> matches = loader.loadAll();
        boolean found = matches.stream().anyMatch(m ->
            m.homeTeam().equalsIgnoreCase("Palmeiras") || m.awayTeam().equalsIgnoreCase("Palmeiras"));
        assertTrue(found, "Should find at least one Palmeiras match");
    }

    @Test void testFlamengoMatchExists() {
        MatchLoader loader = new MatchLoader(DATA_DIR);
        List<Match> matches = loader.loadAll();
        boolean found = matches.stream().anyMatch(m ->
            m.homeTeam().equalsIgnoreCase("Flamengo") || m.awayTeam().equalsIgnoreCase("Flamengo"));
        assertTrue(found, "Should find at least one Flamengo match");
    }
}
