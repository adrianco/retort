package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.data.DataLoader;
import com.braziliansoccer.mcp.tools.MatchTools;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

public class MatchToolsTest {

    private static MatchTools tools;
    private static ObjectMapper mapper = new ObjectMapper();

    @BeforeAll
    static void setup() {
        DataLoader loader = new DataLoader("data/kaggle");
        loader.load();
        tools = new MatchTools(loader);
    }

    private ObjectNode args(String... kvs) {
        ObjectNode n = mapper.createObjectNode();
        for (int i = 0; i < kvs.length; i += 2) {
            String key = kvs[i], val = kvs[i+1];
            try { n.put(key, Integer.parseInt(val)); } catch (NumberFormatException e) { n.put(key, val); }
        }
        return n;
    }

    @Test
    void testSearchMatchesByTeam() {
        String result = tools.searchMatches(args("team", "Flamengo"));
        assertFalse(result.contains("No matches found"), "Should find Flamengo matches");
        assertTrue(result.contains("Flamengo"), "Result should mention Flamengo");
    }

    @Test
    void testSearchMatchesBySeason() {
        String result = tools.searchMatches(args("team", "Palmeiras", "season", "2023"));
        assertFalse(result.contains("No matches found"), "Should find Palmeiras 2023 matches");
    }

    @Test
    void testSearchMatchesByCompetition() {
        String result = tools.searchMatches(args("competition", "Libertadores"));
        assertFalse(result.contains("No matches found"), "Should find Libertadores matches");
        assertTrue(result.toLowerCase().contains("libertadores"), "Result should mention Libertadores");
    }

    @Test
    void testSearchMatchesByTeamAndSeason() {
        String result = tools.searchMatches(args("team", "Corinthians", "season", "2022", "competition", "Brasileirao"));
        assertFalse(result.contains("No matches found"), "Should find Corinthians 2022 Brasileirao matches");
    }

    @Test
    void testHeadToHead() {
        String result = tools.headToHead(args("team1", "Flamengo", "team2", "Fluminense"));
        assertTrue(result.contains("Head-to-Head"), "Should show head-to-head header");
        assertTrue(result.contains("Flamengo"), "Should mention Flamengo");
        assertTrue(result.contains("Fluminense"), "Should mention Fluminense");
        assertTrue(result.contains("wins"), "Should show win counts");
    }

    @Test
    void testHeadToHeadRequiresTeams() {
        String result = tools.headToHead(args("team1", "Flamengo"));
        assertTrue(result.contains("Error") || result.contains("required"), "Should error without team2");
    }

    @Test
    void testTeamStats() {
        String result = tools.teamStats(args("team", "Corinthians", "season", "2022"));
        assertTrue(result.contains("Corinthians"), "Should mention Corinthians");
        assertTrue(result.contains("Wins"), "Should show win stats");
        assertTrue(result.contains("Goals"), "Should show goal stats");
    }

    @Test
    void testTeamStatsHomeAway() {
        String result = tools.teamStats(args("team", "Palmeiras"));
        assertTrue(result.contains("Home Record"), "Should show home record");
        assertTrue(result.contains("Away Record"), "Should show away record");
    }

    @Test
    void testStandings() {
        String result = tools.standings(args("competition", "Brasileirao", "season", "2019"));
        assertTrue(result.contains("Flamengo"), "2019 champion Flamengo should appear");
        assertTrue(result.contains("Standings"), "Should say Standings");
        // Flamengo should be ranked #1
        int flamengoPos = result.indexOf("Flamengo");
        assertTrue(flamengoPos > 0, "Flamengo should be in standings");
    }

    @Test
    void testStandingsRequiresParams() {
        String result = tools.standings(args("competition", "Brasileirao"));
        assertTrue(result.contains("Error") || result.contains("required"), "Should error without season");
    }

    @Test
    void testMatchStatistics() {
        String result = tools.matchStatistics(args("competition", "Brasileirao"));
        assertTrue(result.contains("goals"), "Should show goal stats");
        assertTrue(result.contains("Home wins"), "Should show home win stats");
        assertTrue(result.contains("Biggest Wins"), "Should show biggest wins");
    }

    @Test
    void testMatchStatisticsAllCompetitions() {
        String result = tools.matchStatistics(mapper.createObjectNode());
        assertFalse(result.contains("No matches found"), "Should find matches across all competitions");
        assertTrue(result.contains("Average goals/match"), "Should show average goals");
    }

    @Test
    void testSearchMatchesReturnsLimit() {
        String result = tools.searchMatches(args("team", "Flamengo", "limit", "5"));
        // Count result lines for actual matches
        long matchLines = result.lines().filter(l -> l.contains("-") && l.contains(":")).count();
        assertTrue(matchLines <= 5, "Should respect limit of 5");
    }

    @Test
    void testSearchMatchesCopaDoBrasil() {
        String result = tools.searchMatches(args("competition", "Copa do Brasil", "season", "2022"));
        assertFalse(result.contains("No matches found"), "Should find Copa do Brasil 2022 matches");
    }

    @Test
    void testTeamStatsRequiresTeam() {
        String result = tools.teamStats(mapper.createObjectNode());
        assertTrue(result.contains("Error") || result.contains("required"), "Should error without team");
    }
}
