package com.braziliansoccer.mcp.service;

import com.braziliansoccer.mcp.model.Match;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class StatisticsServiceTest {
    private StatisticsService service;

    @BeforeEach void setUp() {
        List<Match> testMatches = List.of(
            new Match("Brasileirao", "2023-05-01", "Flamengo", "Corinthians", 2, 1, 2023, "1", null),
            new Match("Brasileirao", "2023-06-01", "Palmeiras", "Flamengo", 0, 1, 2023, "5", null),
            new Match("Brasileirao", "2023-07-01", "Flamengo", "Palmeiras", 2, 2, 2023, "10", null),
            new Match("Copa do Brasil", "2022-08-01", "Flamengo", "Santos", 3, 0, 2022, "Final", null)
        );
        service = new StatisticsService(testMatches);
    }

    @Test void testGetTeamRecord() {
        StatisticsService.TeamRecord record = service.getTeamRecord("Flamengo", null, null);
        assertEquals(3, record.wins());
        assertEquals(1, record.draws());
        assertEquals(0, record.losses());
        assertEquals(8, record.goalsFor());
        assertEquals(3, record.goalsAgainst());
    }

    @Test void testGetHeadToHead() {
        StatisticsService.HeadToHead h2h = service.getHeadToHead("Flamengo", "Palmeiras");
        assertEquals(1, h2h.team1Wins());
        assertEquals(0, h2h.team2Wins());
        assertEquals(1, h2h.draws());
    }

    @Test void testGetStandings() {
        List<StatisticsService.StandingEntry> standings = service.getStandings(2023, "Brasileirao");
        assertFalse(standings.isEmpty());
        assertEquals("Flamengo", standings.get(0).team());
    }

    @Test void testGetBiggestWins() {
        List<Match> biggest = service.getBiggestWins(3);
        assertFalse(biggest.isEmpty());
        Match first = biggest.get(0);
        assertTrue(Math.abs(first.homeGoals() - first.awayGoals()) >= 3);
    }

    @Test void testAverageGoalsPerMatch() {
        double avg = service.getAverageGoalsPerMatch("Brasileirao");
        assertEquals((2.0+1+0+1+2+2)/3.0, avg, 0.01);
    }
}
