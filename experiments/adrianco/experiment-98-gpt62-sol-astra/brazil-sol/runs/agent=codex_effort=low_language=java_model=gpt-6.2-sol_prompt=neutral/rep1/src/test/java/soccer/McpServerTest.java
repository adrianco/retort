package soccer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import java.io.*;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;

class McpServerTest {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static SoccerData data;

    @BeforeAll
    static void loadDatasets() throws IOException {
        data = new SoccerData(Path.of("data/kaggle"));
    }

    @Test
    void givenAllSixFilesWhenQueryingEachSourceThenEveryRowIsAvailable() {
        Map<String, Integer> expected = Map.of(SoccerData.SERIE_A, 4180, SoccerData.CUP_FILE, 1337,
                SoccerData.LIBERTADORES_FILE, 1255, SoccerData.EXTENDED, 10296, SoccerData.HISTORICAL, 6886);
        McpServer server = new McpServer(data);
        expected.forEach((source, total) -> {
            JsonNode page = call(server, "search_matches", Map.of("source", source, "limit", 1));
            assertEquals(total.intValue(), page.path("total").asInt(), source);
            assertEquals(source, page.at("/items/0/sources/0").asText());
        });
        assertEquals(18207, call(server, "search_players", Map.of("limit", 1)).path("total").asInt());
    }

    @Test
    void givenDerbyWhenComparingTeamsThenFixturesAndRecordsAgree() {
        McpServer server = new McpServer(data);
        JsonNode answer = call(server, "head_to_head", Map.of("team", "Flamengo-RJ", "opponent", "Fluminense FC",
                "playedOnly", true, "limit", 200));
        JsonNode matches = answer.at("/fixtures/items");
        assertTrue(matches.size() > 20);
        int wins = 0, losses = 0, draws = 0, scored = 0;
        for (JsonNode match : matches) {
            assertTrue(List.of("Flamengo", "Fluminense").contains(match.path("home").asText()));
            assertTrue(List.of("Flamengo", "Fluminense").contains(match.path("away").asText()));
            assertNotEquals(match.path("home"), match.path("away"));
            assertFalse(match.path("date").asText().isBlank());
            assertFalse(match.path("competition").asText().isBlank());
            boolean home = match.path("home").asText().equals("Flamengo");
            int goals = match.path(home ? "homeGoals" : "awayGoals").intValue();
            int conceded = match.path(home ? "awayGoals" : "homeGoals").intValue();
            wins += goals > conceded ? 1 : 0;
            losses += goals < conceded ? 1 : 0;
            draws += goals == conceded ? 1 : 0;
            scored += goals;
        }
        assertEquals(matches.size(), answer.at("/record/matches").intValue());
        assertEquals(wins, answer.at("/record/wins").intValue());
        assertEquals(losses, answer.path("opponentWins").intValue());
        assertEquals(draws, answer.at("/record/draws").intValue());
        assertEquals(scored, answer.at("/record/goalsFor").intValue());
    }

    @Test
    void givenOverlappingLeaguesWhenCalculatingStandingsThenEachFixtureCountsOnce() {
        McpServer server = new McpServer(data);
        JsonNode table = call(server, "standings", Map.of("season", 2019));
        assertEquals("Flamengo", table.path("leader").asText());
        assertEquals(20, table.path("standings").size());
        assertEquals(90, table.at("/standings/0/points").intValue());
        assertEquals(28, table.at("/standings/0/wins").intValue());
        assertEquals(6, table.at("/standings/0/draws").intValue());
        assertEquals(4, table.at("/standings/0/losses").intValue());
        JsonNode matches = call(server, "search_matches", Map.of("season", 2019, "competition", "Serie A", "limit", 1));
        assertEquals(380, matches.path("total").intValue());
        assertTrue(matches.at("/items/0/statistics").has("home_corner"));
        assertTrue(matches.at("/items/0/sources").size() > 1);
        JsonNode relegation = call(server, "standings", Map.of("season", 2020));
        assertEquals(JSON.valueToTree(List.of("Vasco", "Goiás", "Coritiba", "Botafogo-RJ")),
                relegation.path("bottomPositions"));
        assertFalse(call(server, "standings", Map.of("season", 2023)).path("completeDoubleRoundRobin").asBoolean());
    }

    @Test
    void givenDateRangeAndVenueWhenSearchingThenDatesAreInclusiveAndAliasesWork() {
        McpServer server = new McpServer(data);
        JsonNode page = call(server, "search_matches", Map.of("home", "SPFC", "from", "24/09/2023",
                "to", "2023-09-24", "competition", "Copa do Brasil"));
        assertEquals(1, page.path("total").intValue());
        assertEquals("São Paulo", page.at("/items/0/home").asText());
        assertEquals("2023-09-24", page.at("/items/0/date").asText());
        assertEquals("final", page.at("/items/0/stage").asText());
        assertEquals(1, page.at("/items/0/awayGoals").intValue());
        assertEquals(24, call(server, "search_matches", Map.of("competition", "Copa do Brasil", "stage", "final"))
                .path("total").intValue());
    }

    @Test
    void givenPaginatedMatchesWhenReadingNextPageThenRowsAreDistinctAndTotalIsStable() {
        McpServer server = new McpServer(data);
        JsonNode first = call(server, "search_matches", Map.of("team", "Palmeiras", "season", 2023, "limit", 2));
        JsonNode second = call(server, "search_matches", Map.of("team", "Palmeiras", "season", 2023,
                "limit", 2, "offset", first.path("nextOffset").intValue()));
        assertEquals(first.path("total"), second.path("total"));
        assertEquals(2, second.path("offset").intValue());
        assertNotEquals(first.at("/items/1"), second.at("/items/0"));
        assertTrue(first.at("/items/1/date").asText().compareTo(second.at("/items/0/date").asText()) >= 0);
    }

    @Test
    void givenTwoFinalLegsWhenAggregatingThenAveragesUseRecordedScores() {
        JsonNode summary = call(new McpServer(data), "match_statistics",
                Map.of("competition", "Copa do Brasil", "season", 2023, "stage", "final"));
        assertEquals(2, summary.path("matches").intValue());
        assertEquals(3, summary.path("goals").intValue());
        assertEquals(1.5, summary.path("averageGoals").doubleValue());
        assertEquals(0, summary.path("homeWins").intValue());
        assertEquals(1, summary.path("awayWins").intValue());
        assertEquals(1, summary.path("draws").intValue());
    }

    @Test
    void givenAClubWhenCombiningSnapshotsThenRosterAndHistoricalRecordUseSameClub() {
        JsonNode profile = call(new McpServer(data), "club_profile",
                Map.of("team", "Grêmio-RS", "season", 2019, "competition", "Série A", "limit", 1));
        assertEquals("Grêmio", profile.at("/matchRecord/overall/team").asText());
        assertEquals(38, profile.at("/matchRecord/overall/matches").intValue());
        assertEquals(20, profile.at("/players/total").intValue());
        assertEquals("Grêmio", profile.at("/players/items/0/club").asText());
    }

    @Test
    void givenAClientWhenItNegotiatesAndCallsToolsThenStdioCarriesOnlyJsonRpcResponses() throws IOException {
        McpServer server = new McpServer(data);
        String requests = """
                {"jsonrpc":"2.0","id":"init","method":"initialize","params":{"protocolVersion":"2025-06-18"}}
                {"jsonrpc":"2.0","method":"notifications/initialized"}
                {"jsonrpc":"2.0","id":2,"method":"tools/list"}
                malformed-json
                {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"limit":0}}}
                {"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search_matches","arguments":{"from":"31/02/2023"}}}
                {"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"search_players","arguments":{"name":"Neymar","limit":1}}}
                """;
        StringWriter responses = new StringWriter();
        server.serve(new BufferedReader(new StringReader(requests)), new BufferedWriter(responses));
        List<String> lines = responses.toString().lines().toList();
        assertEquals(6, lines.size());
        assertEquals("2025-06-18", JSON.readTree(lines.get(0)).at("/result/protocolVersion").asText());
        assertEquals(8, JSON.readTree(lines.get(1)).at("/result/tools").size());
        assertEquals(-32700, JSON.readTree(lines.get(2)).at("/error/code").intValue());
        assertEquals(-32602, JSON.readTree(lines.get(3)).at("/error/code").intValue());
        assertTrue(JSON.readTree(lines.get(4)).at("/result/isError").asBoolean());
        assertEquals("Neymar Jr", JSON.readTree(lines.get(5)).at("/result/structuredContent/items/0/name").asText());
    }

    record Scenario(String question, String tool, Map<String, Object> arguments, String path, Object expected) {
        @Override public String toString() { return question; }
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("questions")
    void givenLocalDataWhenAnMcpClientTranslatesTheQuestionThenItGetsGroundedData(Scenario scenario) {
        McpServer server = new McpServer(data);
        Duration deadline = Duration.ofSeconds(scenario.tool.startsWith("search_") ? 2 : 5);
        JsonNode answer = assertTimeout(deadline, () -> call(server, scenario.tool, scenario.arguments));
        JsonNode value = answer.at(scenario.path);
        if (scenario.expected == null) {
            assertFalse(value.isMissingNode() || value.isNull());
        } else {
            assertEquals(JSON.valueToTree(scenario.expected), value);
        }
    }

    static Stream<Scenario> questions() {
        return Stream.of(
                new Scenario("What matches did Palmeiras play in 2023?", "search_matches",
                        Map.of("team", "Palmeiras", "season", 2023), "/items/0/home", null),
                new Scenario("When did Flamengo last play Corinthians?", "search_matches",
                        Map.of("team", "Flamengo", "opponent", "Corinthians", "limit", 1), "/items/0/date", "2023-10-08"),
                new Scenario("What was the score?", "search_matches",
                        Map.of("team", "Flamengo", "opponent", "Corinthians", "limit", 1), "/items/0/homeGoals", 1),
                new Scenario("Find Copa do Brasil finals", "search_matches",
                        Map.of("competition", "Copa do Brasil", "stage", "final"), "/items/0/stage", "final"),
                new Scenario("Show 2018 Libertadores bracket fixtures", "search_matches",
                        Map.of("competition", "Libertadores", "season", 2018, "limit", 200), "/total", 126),
                new Scenario("Show derbies in 2023", "search_matches", Map.of("season", 2023, "derby", true), "/items/0/home", null),
                new Scenario("What was Corinthians' home record in 2022?", "team_record",
                        Map.of("team", "Sport Club Corinthians Paulista", "season", 2022, "competition", "Serie A"), "/home/matches", 19),
                new Scenario("What competitions has Palmeiras played in?", "team_record",
                        Map.of("team", "Sociedade Esportiva Palmeiras"), "/groups/Libertadores/matches", null),
                new Scenario("How did Palmeiras perform in 2023?", "team_record",
                        Map.of("team", "Palmeiras", "season", 2023, "competition", "Serie A"), "/overall/goalsFor", 61),
                new Scenario("Compare Palmeiras and Santos", "head_to_head",
                        Map.of("team", "Palmeiras", "opponent", "Santos"), "/opponent", "Santos"),
                new Scenario("Who won the 2019 Brasileirão?", "standings", Map.of("season", 2019), "/leader", "Flamengo"),
                new Scenario("Who finished last in 2020?", "standings", Map.of("season", 2020), "/bottomPositions/3", "Botafogo-RJ"),
                new Scenario("Find all Brazilian players", "search_players", Map.of("nationality", "Brazilian"), "/total", 827),
                new Scenario("Who is Gabriel Barbosa?", "search_players", Map.of("name", "Gabriel Barbosa"), "/total", 0),
                new Scenario("Find Neymar's FIFA attributes", "search_players", Map.of("name", "Neymar"), "/items/0/attributes/Potential", "93"),
                new Scenario("Which players play for Flamengo in FIFA?", "search_players", Map.of("club", "Flamengo"), "/total", 0),
                new Scenario("Show Santos forwards", "search_players", Map.of("club", "Santos FC", "position", "forward"), "/items/0/club", "Santos"),
                new Scenario("Show the highest-rated Brazilian player", "search_players", Map.of("nationality", "Brazil", "limit", 1), "/items/0/name", "Neymar Jr"),
                new Scenario("Average goals per Série A match?", "match_statistics", Map.of("competition", "Série A"), "/averageGoals", null),
                new Scenario("What were the biggest wins?", "match_statistics", Map.of("mode", "biggestWins"), "/items/0/homeGoals", null),
                new Scenario("Which team scored most goals in Série A in 2023?", "team_rankings",
                        Map.of("metric", "goals", "competition", "Série A", "season", 2023), "/items/0/team", "Grêmio"),
                new Scenario("Who had the best home record in the 2019 league?", "team_rankings",
                        Map.of("competition", "Série A", "season", 2019, "venue", "home"), "/items/0/team", "Flamengo"),
                new Scenario("Who had the best away record in the 2019 league?", "team_rankings",
                        Map.of("competition", "Série A", "season", 2019, "venue", "away"), "/items/0/team", "Flamengo"),
                new Scenario("Compare 2018 and 2019 league seasons", "match_statistics",
                        Map.of("mode", "bySeason", "competition", "Série A", "fromSeason", 2018, "toSeason", 2019),
                        "/2018/matches", 380),
                new Scenario("Show Bahia performance by season", "team_record",
                        Map.of("team", "EC Bahia", "groupBy", "season"), "/groups/2019/wins", null)
        );
    }

    private static JsonNode call(McpServer server, String tool, Map<String, ?> args) {
        JsonNode response = server.dispatch(JSON.valueToTree(Map.of("jsonrpc", "2.0", "id", 1, "method", "tools/call",
                "params", Map.of("name", tool, "arguments", args))));
        assertFalse(response.has("error"), response::toString);
        assertFalse(response.at("/result/isError").asBoolean(), response::toString);
        JsonNode content = response.at("/result/structuredContent");
        assertTrue(content.isObject(), response::toString);
        return content;
    }
}
