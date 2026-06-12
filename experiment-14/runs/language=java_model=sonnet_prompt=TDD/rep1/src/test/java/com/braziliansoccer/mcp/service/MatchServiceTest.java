package com.braziliansoccer.mcp.service;

import com.braziliansoccer.mcp.model.Match;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class MatchServiceTest {
    private MatchService service;

    @BeforeEach void setUp() {
        List<Match> testMatches = List.of(
            new Match("Brasileirao", "2023-05-01", "Flamengo", "Corinthians", 2, 1, 2023, "1", null),
            new Match("Brasileirao", "2023-06-01", "Palmeiras", "Flamengo", 0, 1, 2023, "5", null),
            new Match("Copa do Brasil", "2022-08-01", "Flamengo", "Santos", 3, 0, 2022, "Final", null)
        );
        service = new MatchService(testMatches);
    }

    @Test void testFindByTeamFlamengo() { assertEquals(3, service.findByTeam("Flamengo").size()); }
    @Test void testFindByTeams() { assertEquals(1, service.findByTeams("Flamengo", "Corinthians").size()); }
    @Test void testFindByCompetition() { assertEquals(2, service.findByCompetition("Brasileirao").size()); }
    @Test void testFindBySeason() { assertEquals(1, service.findBySeason(2022).size()); }
    @Test void testFindBySeasonAndCompetition() { assertEquals(2, service.findBySeasonAndCompetition(2023, "Brasileirao").size()); }
}
