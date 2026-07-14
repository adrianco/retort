package com.braziliansoccer.mcp.loader;

import com.braziliansoccer.mcp.model.Player;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class PlayerLoaderTest {
    private static final String DATA_DIR = "./data/kaggle/";

    @Test void testLoadsWithoutException() {
        assertDoesNotThrow(() -> {
            PlayerLoader loader = new PlayerLoader(DATA_DIR);
            List<Player> players = loader.loadAll();
            assertNotNull(players);
        });
    }

    @Test void testPlayerCount() {
        PlayerLoader loader = new PlayerLoader(DATA_DIR);
        List<Player> players = loader.loadAll();
        assertTrue(players.size() > 5000, "Expected >5000 players, got: " + players.size());
    }

    @Test void testMessiExists() {
        PlayerLoader loader = new PlayerLoader(DATA_DIR);
        List<Player> players = loader.loadAll();
        boolean found = players.stream().anyMatch(p -> p.name().contains("Messi"));
        assertTrue(found, "Should find Messi in the data");
    }

    @Test void testBrazilianPlayersExist() {
        PlayerLoader loader = new PlayerLoader(DATA_DIR);
        List<Player> players = loader.loadAll();
        boolean found = players.stream().anyMatch(p -> "Brazil".equalsIgnoreCase(p.nationality()));
        assertTrue(found, "Should find Brazilian players");
    }
}
