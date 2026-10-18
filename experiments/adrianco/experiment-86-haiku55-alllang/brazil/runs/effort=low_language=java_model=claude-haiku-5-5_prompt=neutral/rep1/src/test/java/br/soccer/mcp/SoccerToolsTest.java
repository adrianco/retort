package br.soccer.mcp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.soccer.data.DataLoader;
import br.soccer.data.Dataset;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

class SoccerToolsTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final SoccerTools TOOLS = new SoccerTools(load());

    private static Dataset load() {
        try {
            return DataLoader.load(Path.of("data/kaggle"));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String call(String tool, String argumentsJson) {
        try {
            return TOOLS.call(tool, JSON.readTree(argumentsJson));
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    @Nested
    @DisplayName("Feature: Sample questions from the specification")
    class SampleQuestions {

        @Test
        @DisplayName("Scenario: Answer at least 20 sample questions with data, not errors")
        void twentySampleQuestionsAreAnswered() {
            List<String[]> questions = List.of(
                    new String[] {"search_matches", "{\"team\":\"Flamengo\",\"opponent\":\"Fluminense\"}"},
                    new String[] {"search_matches", "{\"team\":\"Palmeiras\",\"season\":2023}"},
                    new String[] {"search_matches", "{\"competition\":\"Copa do Brasil\",\"stage\":\"final\"}"},
                    new String[] {"search_matches", "{\"team\":\"Flamengo\",\"opponent\":\"Corinthians\",\"limit\":1}"},
                    new String[] {"search_matches", "{\"from\":\"2019-01-01\",\"to\":\"2019-12-31\",\"competition\":\"Brasileirão Série A\"}"},
                    new String[] {"search_matches", "{\"team\":\"Palmeiras\",\"venue\":\"away\",\"season\":2021,\"limit\":3}"},
                    new String[] {"search_matches", "{\"team\":\"Santos\",\"opponent\":\"Palmeiras\",\"competition\":\"Copa Libertadores\"}"},
                    new String[] {"team_record", "{\"team\":\"Corinthians\",\"season\":2022,\"venue\":\"home\"}"},
                    new String[] {"team_record", "{\"team\":\"Palmeiras\",\"season\":2023}"},
                    new String[] {"head_to_head", "{\"team\":\"Palmeiras\",\"opponent\":\"Santos\"}"},
                    new String[] {"standings", "{\"season\":2019}"},
                    new String[] {"standings", "{\"season\":2022}"},
                    new String[] {"find_players", "{\"name\":\"Messi\"}"},
                    new String[] {"find_players", "{\"nationality\":\"Brazil\",\"limit\":5}"},
                    new String[] {"find_players", "{\"club\":\"Santos\",\"limit\":5}"},
                    new String[] {"find_players", "{\"position\":\"ST\",\"nationality\":\"Brazil\",\"min_overall\":75}"},
                    new String[] {"club_player_summary", "{\"nationality\":\"Brazil\",\"limit\":5}"},
                    new String[] {"aggregate_stats", "{\"metric\":\"goals_per_match\",\"competition\":\"Brasileirão Série A\"}"},
                    new String[] {"aggregate_stats", "{\"metric\":\"outcome_rates\",\"competition\":\"Brasileirão Série A\"}"},
                    new String[] {"aggregate_stats", "{\"metric\":\"biggest_wins\",\"limit\":5}"},
                    new String[] {"aggregate_stats", "{\"metric\":\"best_home_record\",\"competition\":\"Brasileirão Série A\"}"},
                    new String[] {"aggregate_stats", "{\"metric\":\"best_away_record\",\"competition\":\"Brasileirão Série A\"}"});

            assertTrue(questions.size() >= 20);
            for (String[] q : questions) {
                String text = call(q[0], q[1]);
                assertFalse(text.isBlank(), q[0] + " " + q[1]);
                assertFalse(text.contains("No matches fit") || text.contains("No players fit"),
                        "expected data for " + q[0] + " " + q[1] + " but got: " + text);
            }
        }

        @Test
        @DisplayName("Scenario: Standings answer names the champion and lists the table")
        void standingsAnswerFormat() {
            String text = call("standings", "{\"season\":2019}");

            assertTrue(text.startsWith("2019 Brasileirão Série A standings"));
            assertTrue(text.contains("1. Flamengo"));
            assertTrue(text.contains("- Champion"));
        }

        @Test
        @DisplayName("Scenario: Team record answer uses the specified layout")
        void teamRecordFormat() {
            String text = call("team_record", "{\"team\":\"Corinthians\",\"season\":2022,"
                    + "\"venue\":\"home\",\"competition\":\"Brasileirão Série A\"}");

            assertTrue(text.startsWith("Corinthians record (Brasileirão Série A, 2022, home matches):"), text);
            assertTrue(text.contains("Matches: 19"), text);
            assertTrue(text.contains("Wins: 12, Draws: 4, Losses: 3"), text);
            assertTrue(text.contains("Goals For: 24, Goals Against: 11"), text);
            assertTrue(text.contains("Win rate: 63.2%"), text);
        }

        @Test
        @DisplayName("Scenario: Unknown teams are flagged so the model can ask for a correct spelling")
        void unknownTeamIsFlagged() {
            String text = call("search_matches", "{\"team\":\"Flamenguo\"}");

            assertTrue(text.startsWith("Unknown team 'Flamenguo'"));
        }
    }

    @Nested
    @DisplayName("Feature: Tool contract")
    class Contract {

        @Test
        @DisplayName("Scenario: Every tool advertises a JSON schema with required fields")
        void schemasAreAdvertised() {
            JsonNode definitions = TOOLS.definitions();

            assertEquals(7, definitions.size());
            for (JsonNode def : definitions) {
                assertTrue(def.path("inputSchema").path("type").asText().equals("object"));
                assertFalse(def.path("description").asText().isBlank());
            }
        }

        @Test
        @DisplayName("Scenario: A missing required argument is reported as a tool error")
        void missingRequiredArgument() {
            IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                    () -> call("standings", "{}"));

            assertTrue(e.getMessage().contains("season"));
        }

        @Test
        @DisplayName("Scenario: Bad dates and venues are rejected with a helpful message")
        void badArguments() {
            assertThrows(IllegalArgumentException.class,
                    () -> call("search_matches", "{\"from\":\"last tuesday\"}"));
            assertThrows(IllegalArgumentException.class,
                    () -> call("search_matches", "{\"venue\":\"neutral\"}"));
        }

        @Test
        @DisplayName("Scenario: Unknown tool names are rejected")
        void unknownTool() {
            assertThrows(IllegalArgumentException.class, () -> call("make_coffee", "{}"));
        }
    }
}
