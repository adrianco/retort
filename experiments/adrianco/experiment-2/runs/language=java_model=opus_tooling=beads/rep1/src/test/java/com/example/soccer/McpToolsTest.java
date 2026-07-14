package com.example.soccer;

import com.example.soccer.data.CsvLoader;
import com.example.soccer.mcp.McpTools;
import com.example.soccer.query.QueryEngine;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

public class McpToolsTest {
    private static McpTools tools;
    private static final ObjectMapper M = new ObjectMapper();

    @BeforeAll
    static void init() throws Exception {
        CsvLoader.Dataset ds = new CsvLoader().loadAll(CsvLoader.defaultDataDir());
        tools = new McpTools(new QueryEngine(ds.matches, ds.players));
    }

    @Test void listExposesTools() {
        ObjectNode r = tools.list();
        assertTrue(r.get("tools").size() >= 7);
    }

    @Test void callFindMatches() {
        ObjectNode params = M.createObjectNode();
        params.put("name", "find_matches");
        ObjectNode args = params.putObject("arguments");
        args.put("team", "Flamengo");
        args.put("opponent", "Fluminense");
        args.put("limit", 5);
        ObjectNode r = tools.call(params);
        String text = r.get("content").get(0).get("text").asText();
        assertTrue(text.contains("Flamengo") || text.contains("Fluminense"));
    }

    @Test void callTeamStats() {
        ObjectNode params = M.createObjectNode();
        params.put("name", "team_stats");
        ObjectNode args = params.putObject("arguments");
        args.put("team", "Palmeiras");
        args.put("season", 2019);
        args.put("competition", "Brasileirão");
        ObjectNode r = tools.call(params);
        String text = r.get("content").get(0).get("text").asText();
        assertTrue(text.contains("Palmeiras"));
        assertTrue(text.contains("matches"));
    }

    @Test void callStandings() {
        ObjectNode params = M.createObjectNode();
        params.put("name", "standings");
        ObjectNode args = params.putObject("arguments");
        args.put("season", 2019);
        args.put("competition", "Brasileirão");
        String text = tools.call(params).get("content").get(0).get("text").asText();
        assertTrue(text.toLowerCase().contains("flamengo"));
    }
}
