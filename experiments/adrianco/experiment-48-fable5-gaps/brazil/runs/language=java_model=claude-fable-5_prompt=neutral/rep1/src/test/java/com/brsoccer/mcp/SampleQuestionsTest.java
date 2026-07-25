package com.brsoccer.mcp;

import com.brsoccer.mcp.tools.McpTools;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Success criterion: at least 20 sample questions can be answered.
 * Each row is: question -> tool + JSON arguments an LLM would produce -> expected substring.
 */
class SampleQuestionsTest {

    private final McpTools tools = TestData.tools();
    private final ObjectMapper om = new ObjectMapper();

    @ParameterizedTest(name = "[{index}] {0}")
    @CsvSource(delimiter = '|', value = {
        // question | tool | arguments | expected substring of the answer
        "Show me all Flamengo vs Fluminense matches | search_matches | {\"team\":\"Flamengo\",\"opponent\":\"Fluminense\"} | Fluminense",
        "What matches did Palmeiras play in 2023? | search_matches | {\"team\":\"Palmeiras\",\"season\":2023} | Palmeiras",
        "Find all Copa do Brasil finals | search_matches | {\"competition\":\"Copa do Brasil\",\"stage\":\"final\"} | Copa do Brasil",
        "When did Flamengo last play Corinthians (and the score)? | search_matches | {\"team\":\"Flamengo\",\"opponent\":\"Corinthians\",\"limit\":1} | Flamengo",
        "Show me Palmeiras matches in the 2018 Libertadores | search_matches | {\"team\":\"Palmeiras\",\"competition\":\"Libertadores\",\"season\":2018} | Copa Libertadores",
        "Show me Vasco matches from 2003 (historical data) | search_matches | {\"team\":\"Vasco da Gama\",\"season\":2003,\"limit\":5} | Vasco",
        "What is Corinthians' home record in 2022? | team_stats | {\"team\":\"Corinthians\",\"season\":2022,\"competition\":\"Brasileirão\",\"venue\":\"home\"} | Win rate",
        "How has Grêmio done across all competitions? | team_stats | {\"team\":\"Gremio\"} | Grêmio",
        "Compare Palmeiras and Santos head-to-head | head_to_head | {\"team1\":\"Palmeiras\",\"team2\":\"Santos\"} | wins",
        "Fla-Flu derby head-to-head | head_to_head | {\"team1\":\"Flamengo\",\"team2\":\"Fluminense\"} | draws",
        "Who won the 2019 Brasileirão? | league_standings | {\"season\":2019} | Champion: Flamengo",
        "Show the 2005 Brasileirão table (historical file) | league_standings | {\"season\":2005,\"limit\":5} | Corinthians",
        "Which teams were relegated in 2019? | league_standings | {\"season\":2019} | Relegation zone",
        "Which team scored the most goals in Serie A 2023? | team_rankings | {\"metric\":\"goals_scored\",\"season\":2023,\"competition\":\"Serie A\",\"min_matches\":10} | goals_scored",
        "Which team has the best away record? | team_rankings | {\"metric\":\"win_rate\",\"venue\":\"away\",\"competition\":\"Brasileirão\",\"min_matches\":100} | away",
        "Which team has the best home record? | team_rankings | {\"metric\":\"win_rate\",\"venue\":\"home\",\"competition\":\"Brasileirão\",\"min_matches\":100} | win_rate",
        "Who is Neymar? | player_info | {\"name\":\"Neymar\"} | Neymar",
        "Find top Brazilian players | search_players | {\"nationality\":\"Brazil\",\"limit\":10} | Brazil",
        "Who are the highest-rated goalkeepers from Brazil? | search_players | {\"nationality\":\"Brazil\",\"position\":\"GK\",\"limit\":5} | GK",
        "Show me strikers rated 85+ | search_players | {\"position\":\"ST\",\"min_overall\":85} | ST",
        "What's the average goals per match in the Brasileirão? | competition_stats | {\"competition\":\"Brasileirão\"} | Average goals per match",
        "Show me the biggest wins in the dataset | competition_stats | {} | Biggest wins",
        "How competitive was Libertadores 2019? | competition_stats | {\"competition\":\"Libertadores\",\"season\":2019} | Copa Libertadores",
        "What data is available? | list_competitions | {} | fifa_data.csv",
    })
    void questionCanBeAnswered(String question, String tool, String json, String expected) throws Exception {
        String answer = tools.call(tool.trim(), om.readTree(json.trim()));
        assertFalse(answer.isBlank(), "empty answer for: " + question);
        assertFalse(answer.startsWith("No "), "no-result answer for: " + question + "\n" + answer);
        assertTrue(answer.contains(expected.trim()),
            "answer for '" + question + "' should contain '" + expected.trim() + "' but was:\n" + answer);
    }
}
