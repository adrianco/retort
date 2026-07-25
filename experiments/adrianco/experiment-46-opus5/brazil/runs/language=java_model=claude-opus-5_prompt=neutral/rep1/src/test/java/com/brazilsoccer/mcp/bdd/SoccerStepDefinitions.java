package com.brazilsoccer.mcp.bdd;

import com.brazilsoccer.mcp.support.TestFixtures;
import com.brazilsoccer.mcp.tools.ToolException;
import io.cucumber.datatable.DataTable;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Step definitions shared by every feature file.
 *
 * <p>The steps call the same {@code ToolRegistry} the MCP server exposes, so a passing scenario
 * means an MCP client would get that answer.
 */
public class SoccerStepDefinitions {

    /** "- 2019-11-24: Flamengo 4-1 Ceará (Brasileirão Série A 2019, round 36)" */
    private static final Pattern MATCH_LINE = Pattern.compile(
            "^- (\\d{4}-\\d{2}-\\d{2}|date unknown): .+ (\\d+-\\d+|vs) .+ \\(.+\\).*$");

    private String answer;
    private String errorMessage;
    private long elapsedMillis;

    // ------------------------------------------------------------------ Given

    @Given("the match data is loaded")
    public void theMatchDataIsLoaded() {
        assertThat(TestFixtures.graph().matches()).isNotEmpty();
    }

    @Given("the player data is loaded")
    public void thePlayerDataIsLoaded() {
        assertThat(TestFixtures.graph().players()).isNotEmpty();
    }

    @Given("the knowledge graph is loaded")
    public void theKnowledgeGraphIsLoaded() {
        assertThat(TestFixtures.graph().teamCount()).isPositive();
    }

    // ------------------------------------------------------------------ When

    @When("I search for matches between {string} and {string}")
    public void iSearchForMatchesBetween(String teamA, String teamB) {
        call("search_matches", Map.of("team", teamA, "opponent", teamB, "limit", 25));
    }

    @When("I request the head-to-head record between {string} and {string}")
    public void iRequestTheHeadToHeadRecord(String teamA, String teamB) {
        call("head_to_head", Map.of("team_a", teamA, "team_b", teamB));
    }

    @When("I request statistics for {string} in season {string}")
    public void iRequestStatisticsFor(String team, String season) {
        call("team_stats", Map.of("team", team, "season", season));
    }

    @When("I request the {string} record for {string} in season {string}")
    public void iRequestTheVenueRecord(String venue, String team, String season) {
        call("team_stats", Map.of("team", team, "season", season, "venue", venue, "competition", "serie_a"));
    }

    @When("I request the {string} table for season {string}")
    public void iRequestTheTable(String competition, String season) {
        call("standings", Map.of("competition", competition, "season", season));
    }

    @When("I call the {string} tool with:")
    public void iCallTheToolWith(String tool, DataTable table) {
        call(tool, new LinkedHashMap<>(table.asMap(String.class, String.class)));
    }

    @When("I call the {string} tool without arguments")
    public void iCallTheToolWithoutArguments(String tool) {
        call(tool, Map.of());
    }

    @When("I ask {string} using the {string} tool with {string}")
    public void iAskUsingTheToolWith(String question, String tool, String arguments) {
        call(tool, parseArguments(arguments));
    }

    // ------------------------------------------------------------------ Then

    @Then("I should receive a list of matches")
    public void iShouldReceiveAListOfMatches() {
        assertNoError();
        assertThat(matchLines()).as("match lines in:\n" + answer).isNotEmpty();
    }

    @Then("I should receive at least {int} matches")
    public void iShouldReceiveAtLeastMatches(int count) {
        assertNoError();
        assertThat(matchLines()).as("match lines in:\n" + answer).hasSizeGreaterThanOrEqualTo(count);
    }

    @Then("each match should have date, scores, and competition")
    public void eachMatchShouldHaveDateScoresAndCompetition() {
        assertNoError();
        List<String> lines = matchLines();
        assertThat(lines).isNotEmpty();
        assertThat(lines).allSatisfy(line ->
                assertThat(MATCH_LINE.matcher(line).matches()).as("badly formatted line: " + line).isTrue());
    }

    @Then("I should receive wins, losses, draws, and goals")
    public void iShouldReceiveWinsLossesDrawsAndGoals() {
        assertNoError();
        assertThat(answer).contains("Wins:").contains("Draws:").contains("Losses:")
                .contains("Goals For:").contains("Goals Against:");
    }

    @Then("the answer should contain {string}")
    public void theAnswerShouldContain(String expected) {
        assertNoError();
        assertThat(answer).as(answer).contains(expected);
    }

    @Then("the answer should contain:")
    public void theAnswerShouldContainAll(DataTable table) {
        assertNoError();
        for (String expected : table.asList()) {
            assertThat(answer).as(answer).contains(expected);
        }
    }

    @Then("the answer should not contain {string}")
    public void theAnswerShouldNotContain(String unexpected) {
        assertNoError();
        assertThat(answer).doesNotContain(unexpected);
    }

    @Then("the answer should match {string}")
    public void theAnswerShouldMatch(String regex) {
        assertNoError();
        assertThat(Pattern.compile(regex, Pattern.DOTALL).matcher(answer).find())
                .as("expected /" + regex + "/ in:\n" + answer).isTrue();
    }

    @Then("the tool should report an error containing {string}")
    public void theToolShouldReportAnError(String expected) {
        assertThat(errorMessage).as("expected an error, got:\n" + answer).isNotNull();
        assertThat(errorMessage).contains(expected);
    }

    @Then("the answer should be produced in less than {int} milliseconds")
    public void theAnswerShouldBeProducedInLessThan(int budget) {
        assertNoError();
        assertThat(elapsedMillis).as("query took %d ms", elapsedMillis).isLessThan(budget);
    }

    // ------------------------------------------------------------------ helpers

    private void call(String tool, Map<String, Object> arguments) {
        answer = null;
        errorMessage = null;
        long start = System.nanoTime();
        try {
            answer = TestFixtures.call(tool, arguments);
        } catch (ToolException e) {
            errorMessage = e.getMessage();
        } finally {
            elapsedMillis = (System.nanoTime() - start) / 1_000_000;
        }
    }

    private void assertNoError() {
        assertThat(errorMessage).as("the tool reported an error").isNull();
        assertThat(answer).isNotBlank();
    }

    /** Bullet lines that start with a date - i.e. the match lines, not the summary bullets. */
    private List<String> matchLines() {
        List<String> lines = new ArrayList<>();
        for (String line : answer.split("\n")) {
            if (MATCH_LINE_PREFIX.matcher(line).find()) {
                lines.add(line);
            }
        }
        return lines;
    }

    private static final Pattern MATCH_LINE_PREFIX = Pattern.compile("^- (\\d{4}-\\d{2}-\\d{2}|date unknown)");

    /** Parses "team=Flamengo;season=2019" into a tool argument map. */
    private static Map<String, Object> parseArguments(String arguments) {
        Map<String, Object> parsed = new LinkedHashMap<>();
        if (arguments == null || arguments.isBlank()) {
            return parsed;
        }
        for (String pair : arguments.split(";")) {
            int separator = pair.indexOf('=');
            if (separator > 0) {
                parsed.put(pair.substring(0, separator).trim(), pair.substring(separator + 1).trim());
            }
        }
        return parsed;
    }
}
