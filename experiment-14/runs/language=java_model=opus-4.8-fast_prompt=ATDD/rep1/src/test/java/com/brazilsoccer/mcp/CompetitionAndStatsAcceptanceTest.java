package com.brazilsoccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Locale;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** "Competition Queries" and "Statistical Analysis" capabilities. */
class CompetitionAndStatsAcceptanceTest {

    private McpTestClient client;

    @BeforeEach
    void setUp() {
        client = McpTestClient.bootAndInitialize();
    }

    @Test
    void calculates_the_2019_brasileirao_final_standings() {
        JsonNode standings = client.callTool("competition_standings",
                Map.of("competition", "serie_a", "season", 2019));

        JsonNode table = standings.get("table");
        assertEquals(20, table.size(), "Serie A is a 20-team league");

        JsonNode champion = table.get(0);
        assertEquals(1, champion.get("rank").asInt());
        assertTrue(champion.get("team").asText().toLowerCase(Locale.ROOT).contains("flamengo"),
                "Flamengo won the 2019 Brasileirao");
        assertEquals(90, champion.get("points").asInt(), "Flamengo finished on 90 points");
        assertTrue(standings.get("champion").asText().toLowerCase(Locale.ROOT).contains("flamengo"));

        // The table must be ordered by points, descending.
        int previous = Integer.MAX_VALUE;
        for (JsonNode row : table) {
            int pts = row.get("points").asInt();
            assertTrue(pts <= previous, "standings must be sorted by points");
            previous = pts;
            assertEquals(row.get("wins").asInt() * 3 + row.get("draws").asInt(), pts,
                    "points = 3*wins + draws");
        }
    }

    @Test
    void computes_league_wide_statistics() {
        JsonNode stats = client.callTool("league_statistics",
                Map.of("competition", "serie_a", "season", 2019));

        assertTrue(stats.get("matches").asInt() > 0);
        double avg = stats.get("averageGoalsPerMatch").asDouble();
        assertTrue(avg > 1.5 && avg < 4.0, "average goals per match should be football-plausible: " + avg);

        double homeWinRate = stats.get("homeWinRate").asDouble();
        assertTrue(homeWinRate > 0.30 && homeWinRate < 0.70, "home win rate plausibility: " + homeWinRate);

        assertEquals(stats.get("matches").asInt(),
                stats.get("homeWins").asInt() + stats.get("awayWins").asInt() + stats.get("draws").asInt(),
                "every match is a home win, away win or draw");
    }

    @Test
    void surfaces_the_biggest_wins_ordered_by_margin() {
        JsonNode stats = client.callTool("league_statistics",
                Map.of("competition", "serie_a", "season", 2019));

        JsonNode biggest = stats.get("biggestWins");
        assertTrue(biggest.size() > 0);
        int previousMargin = Integer.MAX_VALUE;
        for (JsonNode win : biggest) {
            int margin = win.get("margin").asInt();
            assertTrue(margin >= 1);
            assertTrue(margin <= previousMargin, "biggest wins must be ordered by margin, descending");
            previousMargin = margin;
        }
    }
}
