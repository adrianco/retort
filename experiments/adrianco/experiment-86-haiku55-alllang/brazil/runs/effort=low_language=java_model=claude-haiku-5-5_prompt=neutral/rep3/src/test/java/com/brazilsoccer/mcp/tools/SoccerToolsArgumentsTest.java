/*
 * Context block: Given/When/Then tests for tool argument validation that do not depend on the
 * shape of the output: required fields, limit bounds, and metric names.
 */
package com.brazilsoccer.mcp.tools;

import com.brazilsoccer.mcp.data.SoccerDatabase;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class SoccerToolsArgumentsTest {

    private final ObjectMapper mapper = new ObjectMapper();
    private final SoccerTools tools = new SoccerTools(new SoccerDatabase(List.of(), List.of()), mapper);

    @Test
    @DisplayName("Given team_stats without a team, when called, then a missing-argument error is raised")
    void requiredTeam() throws Exception {
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                () -> tools.call("team_stats", mapper.readTree("{}")));

        assertEquals("Missing required argument: team", e.getMessage());
    }

    @Test
    @DisplayName("Given a limit above the maximum, when a search is called, then the limit is rejected")
    void limitBounds() throws Exception {
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                () -> tools.call("search_matches", mapper.readTree("{\"limit\":500}")));

        assertEquals("limit must be between 1 and 100", e.getMessage());
    }

    @Test
    @DisplayName("Given an unknown statistics metric, when called, then the valid metrics are listed")
    void unknownMetric() throws Exception {
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                () -> tools.call("match_statistics", mapper.readTree("{\"metric\":\"xg\"}")));

        assertEquals(true, e.getMessage().contains("summary, biggest_wins or best_away_record"));
    }

    @Test
    @DisplayName("Given standings for a cup competition, when called, then the request is rejected as not a league")
    void standingsOnlyForLeagues() throws Exception {
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                () -> tools.call("competition_standings", mapper.readTree("{\"competition\":\"copa do brasil\",\"season\":2021}")));

        assertEquals(true, e.getMessage().startsWith("Standings are only calculated for league competitions"));
    }
}
