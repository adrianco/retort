package com.soccer.mcp.query;

import com.soccer.mcp.data.DataStore;
import com.soccer.mcp.model.Player;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import java.nio.file.Paths;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@DisplayName("Feature: Player Queries")
class PlayerQueriesBddTest {

    private QueryService query;

    @BeforeAll
    void givenPlayerDataIsLoaded() throws Exception {
        DataStore store = DataStore.load(Paths.get("data", "kaggle"));
        query = new QueryService(store);
    }

    @Test
    @DisplayName("Scenario: search players by name substring")
    void whenISearchPlayersByName_thenIReceiveMatchingPlayers() {
        List<Player> results = query.findPlayersByName("Neymar");
        assertFalse(results.isEmpty(), "expected Neymar to be in dataset");
        assertTrue(results.stream().anyMatch(p ->
                p.name().toLowerCase().contains("neymar")));
    }

    @Test
    @DisplayName("Scenario: filter by nationality Brazil")
    void whenIRequestBrazilianPlayers_thenAllHaveNationalityBrazil() {
        List<Player> brazilians = query.findPlayersByNationality("Brazil");
        assertFalse(brazilians.isEmpty());
        for (Player p : brazilians) {
            assertTrue("Brazil".equalsIgnoreCase(p.nationality()));
        }
    }

    @Test
    @DisplayName("Scenario: top-rated Brazilians are sorted by overall descending")
    void whenIRequestTopBrazilians_thenOverallRatingsAreNonIncreasing() {
        List<Player> top = query.topRatedBrazilianPlayers(10);
        assertFalse(top.isEmpty());
        int prev = Integer.MAX_VALUE;
        for (Player p : top) {
            assertTrue(p.overall() <= prev, "list should be non-increasing");
            prev = p.overall();
            assertTrue("Brazil".equalsIgnoreCase(p.nationality()));
        }
    }
}
