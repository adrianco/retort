package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.support.TestFixtures;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.function.Supplier;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Performance budget from the specification: simple lookups under 2 seconds, aggregations under
 * 5 seconds. The graph is loaded once at start-up, so queries only walk the adjacency indexes.
 */
class QueryPerformanceTest {

    @BeforeAll
    static void warmUp() {
        TestFixtures.registry().call("dataset_info", Map.of());
    }

    private long millis(Supplier<String> query) {
        long start = System.nanoTime();
        String result = query.get();
        long elapsed = (System.nanoTime() - start) / 1_000_000;
        assertThat(result).isNotBlank();
        return elapsed;
    }

    @Test
    @DisplayName("the whole dataset loads in a couple of seconds")
    void loadsQuickly() {
        assertThat(TestFixtures.graph().report().loadMillis()).isLessThan(10_000);
    }

    @Test
    @DisplayName("simple lookups answer in well under 2 seconds")
    void simpleLookupsAreFast() {
        assertThat(millis(() -> TestFixtures.call("search_matches",
                Map.of("team", "Flamengo", "opponent", "Corinthians", "limit", 5)))).isLessThan(2000);
        assertThat(millis(() -> TestFixtures.call("player_profile",
                Map.of("name", "Neymar")))).isLessThan(2000);
        assertThat(millis(() -> TestFixtures.call("team_stats",
                Map.of("team", "Palmeiras", "season", 2019)))).isLessThan(2000);
        assertThat(millis(() -> TestFixtures.call("head_to_head",
                Map.of("team_a", "Grêmio", "team_b", "Internacional")))).isLessThan(2000);
    }

    @Test
    @DisplayName("aggregations over the full dataset answer in well under 5 seconds")
    void aggregationsAreFast() {
        assertThat(millis(() -> TestFixtures.call("statistics",
                Map.of("metric", "overview")))).isLessThan(5000);
        assertThat(millis(() -> TestFixtures.call("statistics",
                Map.of("metric", "team_ranking", "rank_by", "win_rate", "venue", "home",
                        "competition", "serie_a", "min_matches", 100)))).isLessThan(5000);
        assertThat(millis(() -> TestFixtures.call("standings",
                Map.of("season", 2019)))).isLessThan(5000);
        assertThat(millis(() -> TestFixtures.call("compare_seasons",
                Map.of("seasons", java.util.List.of(2015, 2016, 2017, 2018, 2019))))).isLessThan(5000);
        assertThat(millis(() -> TestFixtures.call("player_club_summary",
                Map.of("nationality", "Brazil", "limit", 50)))).isLessThan(5000);
    }
}
