package com.brazilsoccer.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Locale;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** "Match Queries" capability — finding matches by team, opponent, competition and season. */
class MatchQueryAcceptanceTest {

    private McpTestClient client;

    @BeforeEach
    void setUp() {
        client = McpTestClient.bootAndInitialize();
    }

    @Test
    void finds_all_matches_between_two_rival_teams() {
        JsonNode result = client.callTool("find_matches",
                Map.of("team", "Flamengo", "opponent", "Fluminense"));

        assertTrue(result.get("count").asInt() > 0, "the Fla-Flu derby should appear in the data");
        for (JsonNode match : result.get("matches")) {
            String home = match.get("homeTeam").asText().toLowerCase(Locale.ROOT);
            String away = match.get("awayTeam").asText().toLowerCase(Locale.ROOT);
            boolean involvesBoth =
                    (home.contains("flamengo") && away.contains("fluminense"))
                            || (home.contains("fluminense") && away.contains("flamengo"));
            assertTrue(involvesBoth, "every returned match must be between the two teams: " + match);
        }
    }

    @Test
    void finds_the_matches_a_team_played_in_a_given_season() {
        JsonNode result = client.callTool("find_matches",
                Map.of("team", "Palmeiras", "season", 2019));

        assertTrue(result.get("count").asInt() > 0);
        for (JsonNode match : result.get("matches")) {
            assertEquals(2019, match.get("season").asInt(), "season filter must hold");
            String home = match.get("homeTeam").asText().toLowerCase(Locale.ROOT);
            String away = match.get("awayTeam").asText().toLowerCase(Locale.ROOT);
            assertTrue(home.contains("palmeiras") || away.contains("palmeiras"),
                    "team filter must hold: " + match);
        }
    }

    @Test
    void filters_matches_by_competition() {
        JsonNode result = client.callTool("find_matches",
                Map.of("competition", "libertadores", "limit", 200));

        assertTrue(result.get("count").asInt() > 0);
        for (JsonNode match : result.get("matches")) {
            assertEquals("libertadores", match.get("competition").asText().toLowerCase(Locale.ROOT));
        }
    }

    @Test
    void restricts_a_team_to_its_home_fixtures() {
        JsonNode result = client.callTool("find_matches",
                Map.of("team", "Corinthians", "season", 2019, "venue", "home"));

        assertTrue(result.get("count").asInt() > 0);
        for (JsonNode match : result.get("matches")) {
            assertTrue(match.get("homeTeam").asText().toLowerCase(Locale.ROOT).contains("corinthians"),
                    "home-venue filter must only return home fixtures: " + match);
        }
    }

    @Test
    void each_match_reports_a_readable_scoreline() {
        JsonNode result = client.callTool("find_matches",
                Map.of("team", "Santos", "season", 2019, "limit", 5));

        JsonNode match = result.get("matches").get(0);
        int hg = match.get("homeGoals").asInt();
        int ag = match.get("awayGoals").asInt();
        assertEquals(hg + "-" + ag, match.get("score").asText());
    }
}
