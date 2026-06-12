package com.brazilsoccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Locale;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** "Team Queries" capability — records, goals, head-to-head and home/away splits. */
class TeamQueryAcceptanceTest {

    private McpTestClient client;

    @BeforeEach
    void setUp() {
        client = McpTestClient.bootAndInitialize();
    }

    @Test
    void reports_a_teams_record_consistently() {
        JsonNode stats = client.callTool("team_stats",
                Map.of("team", "Flamengo", "season", 2019, "competition", "serie_a"));

        int matches = stats.get("matches").asInt();
        int wins = stats.get("wins").asInt();
        int draws = stats.get("draws").asInt();
        int losses = stats.get("losses").asInt();

        assertTrue(matches > 0);
        assertEquals(matches, wins + draws + losses, "W+D+L must equal matches played");
        assertTrue(stats.get("goalsFor").asInt() >= 0);
        assertTrue(stats.get("goalsAgainst").asInt() >= 0);
        // Win rate is expressed as a fraction in [0,1].
        double winRate = stats.get("winRate").asDouble();
        assertTrue(winRate >= 0.0 && winRate <= 1.0);
    }

    @Test
    void a_home_record_only_counts_home_matches() {
        JsonNode all = client.callTool("team_stats",
                Map.of("team", "Corinthians", "season", 2019, "competition", "serie_a"));
        JsonNode home = client.callTool("team_stats",
                Map.of("team", "Corinthians", "season", 2019, "competition", "serie_a", "venue", "home"));

        assertTrue(home.get("matches").asInt() < all.get("matches").asInt(),
                "home matches must be a subset of all matches");
    }

    @Test
    void compares_two_teams_head_to_head() {
        JsonNode h2h = client.callTool("head_to_head",
                Map.of("teamA", "Palmeiras", "teamB", "Santos"));

        int total = h2h.get("totalMatches").asInt();
        int a = h2h.get("teamAWins").asInt();
        int b = h2h.get("teamBWins").asInt();
        int d = h2h.get("draws").asInt();

        assertTrue(total > 0, "Palmeiras and Santos have met in the data");
        assertEquals(total, a + b + d, "wins + draws must reconcile with total meetings");
        // The header teams must reflect what was asked.
        assertTrue(h2h.get("teamA").asText().toLowerCase(Locale.ROOT).contains("palmeiras"));
        assertTrue(h2h.get("teamB").asText().toLowerCase(Locale.ROOT).contains("santos"));
    }
}
