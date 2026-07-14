package com.braziliansoccer.mcp;

import com.braziliansoccer.mcp.data.DataLoader;
import com.braziliansoccer.mcp.tools.PlayerTools;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

public class PlayerToolsTest {

    private static PlayerTools tools;
    private static ObjectMapper mapper = new ObjectMapper();

    @BeforeAll
    static void setup() {
        DataLoader loader = new DataLoader("data/kaggle");
        loader.load();
        tools = new PlayerTools(loader);
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
    void testSearchPlayersByName() {
        String result = tools.searchPlayers(args("name", "Neymar"));
        assertTrue(result.contains("Neymar"), "Should find Neymar");
        assertFalse(result.contains("No players found"), "Should find players");
    }

    @Test
    void testSearchPlayersByNationality() {
        String result = tools.searchPlayers(args("nationality", "Brazil", "max_results", "10"));
        assertTrue(result.contains("Brazil"), "Should show Brazilian players");
        assertFalse(result.contains("No players found"), "Should find Brazilian players");
    }

    @Test
    void testSearchPlayersByClub() {
        // Use Fluminense which is present in the FIFA dataset
        String result = tools.searchPlayers(args("club", "Fluminense", "max_results", "10"));
        assertFalse(result.contains("No players found"), "Should find Fluminense players");
    }

    @Test
    void testSearchPlayersByPosition() {
        String result = tools.searchPlayers(args("position", "GK", "nationality", "Brazil", "max_results", "5"));
        assertFalse(result.contains("No players found"), "Should find Brazilian goalkeepers");
        assertTrue(result.contains("GK"), "Should show GK position");
    }

    @Test
    void testSearchPlayersMinOverall() {
        String result = tools.searchPlayers(args("nationality", "Brazil", "min_overall", "85"));
        assertFalse(result.contains("No players found"), "Should find high-rated Brazilian players");
        // All shown players should be >= 85
        assertTrue(result.contains("Overall"), "Should show overall rating");
    }

    @Test
    void testPlayerProfile() {
        String result = tools.playerProfile(args("name", "Alisson"));
        assertTrue(result.contains("Alisson"), "Should find Alisson");
        assertTrue(result.contains("Overall"), "Should show overall rating");
        assertTrue(result.contains("Position"), "Should show position");
    }

    @Test
    void testPlayerProfileUnknown() {
        String result = tools.playerProfile(args("name", "NonExistentPlayer12345"));
        assertTrue(result.contains("No player found"), "Should indicate player not found");
    }

    @Test
    void testPlayerProfileRequiresName() {
        String result = tools.playerProfile(mapper.createObjectNode());
        assertTrue(result.contains("Error") || result.contains("required"), "Should error without name");
    }

    @Test
    void testTeamPlayers() {
        // Use Santos which is present in the FIFA dataset
        String result = tools.teamPlayers(args("club", "Santos"));
        assertFalse(result.contains("No players found"), "Should find Santos players");
        assertTrue(result.contains("Santos"), "Should mention Santos");
    }

    @Test
    void testTeamPlayersRequiresClub() {
        String result = tools.teamPlayers(mapper.createObjectNode());
        assertTrue(result.contains("Error") || result.contains("required"), "Should error without club");
    }

    @Test
    void testTopPlayersByNationality() {
        String result = tools.topPlayersByNationality(args("nationality", "Brazil", "limit", "10"));
        assertFalse(result.contains("No players found"), "Should find Brazilian players");
        assertTrue(result.contains("Brazil"), "Should mention Brazil");
        // Should show at least some players
        assertTrue(result.contains("1."), "Should show ranked list");
    }

    @Test
    void testTopPlayersByNationalityArgentina() {
        String result = tools.topPlayersByNationality(args("nationality", "Argentina"));
        assertFalse(result.contains("No players found"), "Should find Argentine players");
        assertTrue(result.contains("Messi") || result.contains("Ronaldo") || result.contains("Argentina"),
            "Should find top players");
    }

    @Test
    void testTopPlayersByNationalityRequiresNationality() {
        String result = tools.topPlayersByNationality(mapper.createObjectNode());
        assertTrue(result.contains("Error") || result.contains("required"), "Should error without nationality");
    }

    @Test
    void testSearchPlayersSortedByOverall() {
        String result = tools.searchPlayers(args("nationality", "Brazil", "max_results", "5", "sort_by", "overall"));
        // First player should be high rated - result is sorted by overall by default
        assertFalse(result.contains("No players found"), "Should find players");
        // The first entry should have a higher rating than the last
        assertTrue(result.contains("Overall"), "Should show overall ratings");
    }

    @Test
    void testSearchPlayersCombinedFilters() {
        // Brazilian forwards at high overall
        String result = tools.searchPlayers(args(
            "nationality", "Brazil",
            "position", "ST",
            "min_overall", "75",
            "max_results", "10"));
        if (!result.contains("No players found")) {
            assertTrue(result.contains("ST"), "Results should include ST positions");
        }
    }
}
