package com.example.brsoccer.mcp;

import com.example.brsoccer.model.Match;
import com.example.brsoccer.model.Player;
import com.example.brsoccer.query.SoccerDatabase;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class SoccerToolsTest {

    private final ObjectMapper json = new ObjectMapper();
    private SoccerTools tools;

    private static Match m(String comp, int season, String date, String home, int hg, int ag, String away) {
        return new Match(comp, season, LocalDate.parse(date), null, home, away, hg, ag);
    }

    @BeforeEach
    void setUp() {
        List<Match> matches = List.of(
                m("Brasileirão", 2023, "2023-05-28", "Fluminense", 1, 0, "Flamengo"),
                m("Brasileirão", 2023, "2023-09-03", "Flamengo", 2, 1, "Fluminense"),
                m("Brasileirão", 2023, "2023-06-01", "Palmeiras", 3, 0, "Santos"),
                m("Brasileirão", 2023, "2023-08-01", "Flamengo", 4, 0, "Santos"),
                m("Brasileirão", 2023, "2023-08-15", "Palmeiras", 2, 2, "Flamengo")
        );
        List<Player> players = List.of(
                new Player(1, "Neymar Jr", 27, "Brazil", 92, 93, "Paris Saint-Germain", "LW", 10),
                new Player(3, "Pedro", 26, "Brazil", 80, 84, "Flamengo", "ST", 9)
        );
        tools = new SoccerTools(new SoccerDatabase(matches, players));
    }

    private ObjectNode args() {
        return json.createObjectNode();
    }

    @Test
    void findMatchesListsResults() {
        String out = tools.call("find_matches", args().put("team", "Flamengo"));
        assertTrue(out.contains("Flamengo 2-1 Fluminense"), out);
        assertTrue(out.contains("Brasileirão"), out);
    }

    @Test
    void headToHeadSummarizesRecord() {
        ObjectNode a = args();
        a.put("team_a", "Flamengo");
        a.put("team_b", "Fluminense");
        String out = tools.call("head_to_head", a);
        assertTrue(out.contains("Flamengo"), out);
        assertTrue(out.contains("Fluminense"), out);
        assertTrue(out.contains("2"), out); // total matches
    }

    @Test
    void teamRecordReportsAggregates() {
        ObjectNode a = args();
        a.put("team", "Flamengo");
        a.put("season", 2023);
        a.put("competition", "Brasileirão");
        String out = tools.call("team_record", a);
        assertTrue(out.contains("Played: 4"), out);
        assertTrue(out.contains("Points: 7"), out);
    }

    @Test
    void standingsRenderTable() {
        ObjectNode a = args();
        a.put("competition", "Brasileirão");
        a.put("season", 2023);
        String out = tools.call("competition_standings", a);
        assertTrue(out.contains("Flamengo"), out);
        assertTrue(out.startsWith("Brasileirão 2023") || out.contains("standings"), out);
        // Flamengo should be ranked first
        assertTrue(out.indexOf("Flamengo") < out.indexOf("Santos"), out);
    }

    @Test
    void searchPlayersListsByRating() {
        String out = tools.call("search_players", args().put("nationality", "Brazil"));
        assertTrue(out.contains("Neymar Jr"), out);
        assertTrue(out.contains("92"), out);
        assertTrue(out.indexOf("Neymar Jr") < out.indexOf("Pedro"), out);
    }

    @Test
    void matchStatisticsReportsAveragesAndBiggestWins() {
        ObjectNode a = args();
        a.put("competition", "Brasileirão");
        a.put("season", 2023);
        String out = tools.call("match_statistics", a);
        assertTrue(out.toLowerCase().contains("average goals"), out);
        assertTrue(out.contains("Flamengo 4-0 Santos"), out);
    }

    @Test
    void listCompetitionsShowsAll() {
        String out = tools.call("list_competitions", args());
        assertTrue(out.contains("Brasileirão"), out);
    }

    @Test
    void unknownToolReturnsError() {
        String out = tools.call("does_not_exist", args());
        assertTrue(out.toLowerCase().contains("unknown tool"), out);
    }

    @Test
    void emptyResultIsReportedClearly() {
        String out = tools.call("find_matches", args().put("team", "Nonexistent FC"));
        assertTrue(out.toLowerCase().contains("no matches"), out);
    }

    @Test
    void exposesToolDefinitions() {
        assertTrue(tools.definitions().size() >= 6);
        assertTrue(tools.definitions().stream().anyMatch(d -> d.name().equals("find_matches")));
    }
}
