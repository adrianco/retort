// bdd_test.go runs the behaviour described in the specification as
// Given/When/Then scenarios against the real MCP tools and the real datasets.
//
// The Gherkin text of each feature is kept next to its test so the two cannot
// drift apart; `go test -v ./internal/soccerserver/` prints the steps as they
// run.
package soccerserver

import (
	"fmt"
	"strings"
	"testing"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// ---------------------------------------------------------------------------
// A very small Given/When/Then harness
// ---------------------------------------------------------------------------

type scenario struct {
	t    *testing.T
	name string
}

func newScenario(t *testing.T, feature, name string) *scenario {
	t.Helper()
	t.Logf("Feature: %s", feature)
	t.Logf("  Scenario: %s", name)
	return &scenario{t: t, name: name}
}

func (s *scenario) step(keyword, text string, fn func()) *scenario {
	s.t.Helper()
	s.t.Logf("    %s %s", keyword, text)
	if fn != nil {
		fn()
	}
	return s
}

func (s *scenario) Given(text string, fn func()) *scenario { return s.step("Given", text, fn) }
func (s *scenario) When(text string, fn func()) *scenario  { return s.step("When", text, fn) }
func (s *scenario) Then(text string, fn func()) *scenario  { return s.step("Then", text, fn) }
func (s *scenario) And(text string, fn func()) *scenario   { return s.step("And", text, fn) }

// ---------------------------------------------------------------------------
// Feature: Match Queries
// ---------------------------------------------------------------------------

const featureMatchQueries = `
Feature: Match Queries

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
    And the head-to-head record should be summarised

  Scenario: Find a club's matches in one season
    Given the match data is loaded
    When I ask for the matches Palmeiras played in 2023
    Then every match returned involves Palmeiras in 2023

  Scenario: Find the finals of a cup competition
    Given the match data is loaded
    When I search Copa do Brasil matches at the "final" stage
    Then only finals are returned, two legs per season
`

func TestFeatureMatchQueries(t *testing.T) {
	t.Log(featureMatchQueries)

	newScenario(t, "Match Queries", "Find matches between two teams").
		Given("the match data is loaded", func() { testServer(t) }).
		When(`I search for matches between "Flamengo" and "Fluminense"`, nil).
		Then("I should receive a list of matches", func() {
			data := structured(t, "head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Fluminense", "limit": 5})
			matches, _ := data["matches"].([]map[string]any)
			if len(matches) == 0 {
				t.Fatal("no matches returned")
			}
			for _, m := range matches {
				for _, field := range []string{"date", "home_goals", "away_goals", "competition"} {
					if _, ok := m[field]; !ok {
						t.Errorf("match is missing %q: %v", field, m)
					}
				}
			}
		}).
		And("each match should have date, scores, and competition", func() {
			got := answer(t, "head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Fluminense", "limit": 5})
			if !strings.Contains(got, "Brasileirão") {
				t.Errorf("competition is missing from the prose:\n%s", got)
			}
		}).
		And("the head-to-head record should be summarised", func() {
			got := answer(t, "head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Fluminense", "limit": 5})
			containsAll(t, got, "Head-to-head in dataset:", "Flamengo", "Fluminense", "wins", "draws")
		})

	newScenario(t, "Match Queries", "Find a club's matches in one season").
		Given("the match data is loaded", nil).
		When("I ask for the matches Palmeiras played in 2023", nil).
		Then("every match returned involves Palmeiras in 2023", func() {
			data := structured(t, "search_matches", map[string]any{"team": "Palmeiras", "season": 2023, "limit": 50})
			matches := data["matches"].([]map[string]any)
			if len(matches) < 30 {
				t.Fatalf("only %d matches in 2023", len(matches))
			}
			for _, m := range matches {
				if m["season"].(int) != 2023 {
					t.Errorf("match from %v", m["season"])
				}
				if m["home_id"] != "palmeiras-sp" && m["away_id"] != "palmeiras-sp" {
					t.Errorf("match without Palmeiras: %v", m)
				}
			}
		})

	newScenario(t, "Match Queries", "Find the finals of a cup competition").
		Given("the match data is loaded", nil).
		When(`I search Copa do Brasil matches at the "final" stage`, nil).
		Then("only finals are returned, two legs per season", func() {
			data := structured(t, "search_matches", map[string]any{
				"competition": "copa-do-brasil", "stage": "final", "limit": 100, "sort": "date_asc"})
			matches := data["matches"].([]map[string]any)
			perSeason := map[int]int{}
			for _, m := range matches {
				round := fmt.Sprint(m["round"])
				if !strings.Contains(round, "final") {
					t.Errorf("not a final: %v", m)
				}
				perSeason[m["season"].(int)]++
			}
			if len(perSeason) < 10 {
				t.Errorf("finals found for only %d seasons", len(perSeason))
			}
			for season, n := range perSeason {
				if n != 2 {
					t.Errorf("%d has %d final legs, want 2", season, n)
				}
			}
		})
}

// ---------------------------------------------------------------------------
// Feature: Team Queries
// ---------------------------------------------------------------------------

const featureTeamQueries = `
Feature: Team Queries

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals

  Scenario: Home record for one season
    Given the match data is loaded
    When I request the home record of Corinthians in the 2022 Brasileirão
    Then the record covers nineteen home matches and reports a win rate

  Scenario: Team name variations
    Given the match data is loaded
    When I ask for the same club by several spellings
    Then every spelling returns the same club
`

func TestFeatureTeamQueries(t *testing.T) {
	t.Log(featureTeamQueries)

	newScenario(t, "Team Queries", "Get team statistics").
		Given("the match data is loaded", func() { testServer(t) }).
		When(`I request statistics for "Palmeiras" in season "2023"`, nil).
		Then("I should receive wins, losses, draws, and goals", func() {
			got := answer(t, "team_stats", map[string]any{"team": "Palmeiras", "season": 2023})
			containsAll(t, got, "Matches:", "Wins:", "Draws:", "Losses:", "Goals For:", "Goals Against:")
			data := structured(t, "team_stats", map[string]any{"team": "Palmeiras", "season": 2023})
			rec := data["record"]
			if rec == nil {
				t.Fatal("no structured record")
			}
		})

	newScenario(t, "Team Queries", "Home record for one season").
		Given("the match data is loaded", nil).
		When("I request the home record of Corinthians in the 2022 Brasileirão", nil).
		Then("the record covers nineteen home matches and reports a win rate", func() {
			got := answer(t, "team_stats", map[string]any{
				"team": "Corinthians", "competition": "brasileirao", "season": 2022, "venue": "home"})
			containsAll(t, got, "Corinthians home record", "Matches: 19", "Win rate:")
		})

	newScenario(t, "Team Queries", "Team name variations").
		Given("the match data is loaded", nil).
		When("I ask for the same club by several spellings", nil).
		Then("every spelling returns the same club", func() {
			for _, spelling := range []string{"Atletico Mineiro", "Atlético-MG", "atletico-mg", "Atletico MG"} {
				data := structured(t, "team_profile", map[string]any{"team": spelling})
				team, ok := data["team"].(*soccer.Team)
				if !ok {
					t.Fatalf("team_profile returned %T as the team", data["team"])
				}
				if team.ID != "atletico-mg" {
					t.Errorf("%q resolved to %s", spelling, team.ID)
				}
			}
		})
}

// ---------------------------------------------------------------------------
// Feature: Player Queries
// ---------------------------------------------------------------------------

const featurePlayerQueries = `
Feature: Player Queries

  Scenario: Find players by nationality
    Given the player data is loaded
    When I search for Brazilian players
    Then I receive them sorted by rating, best first

  Scenario: Look a player up by name
    Given the player data is loaded
    When I ask who Neymar is
    Then I receive his rating, position, club and attributes

  Scenario: A player who is not in the snapshot
    Given the player data is loaded
    When I ask about a player who is missing from the FIFA snapshot
    Then the server says so and suggests the closest names
`

func TestFeaturePlayerQueries(t *testing.T) {
	t.Log(featurePlayerQueries)

	newScenario(t, "Player Queries", "Find players by nationality").
		Given("the player data is loaded", func() { testServer(t) }).
		When("I search for Brazilian players", nil).
		Then("I receive them sorted by rating, best first", func() {
			data := structured(t, "search_players", map[string]any{"nationality": "Brazil", "limit": 10})
			players := data["players"].([]map[string]any)
			if len(players) != 10 {
				t.Fatalf("got %d players", len(players))
			}
			if data["total"].(int) < 800 {
				t.Errorf("only %v Brazilian players", data["total"])
			}
			prev := 100
			for _, p := range players {
				overall := p["overall"].(int)
				if overall > prev {
					t.Error("players are not sorted by rating")
				}
				prev = overall
				if p["nationality"] != "Brazil" {
					t.Errorf("%v is not Brazilian", p["name"])
				}
			}
		})

	newScenario(t, "Player Queries", "Look a player up by name").
		Given("the player data is loaded", nil).
		When("I ask who Neymar is", nil).
		Then("I receive his rating, position, club and attributes", func() {
			got := answer(t, "player_profile", map[string]any{"name": "Neymar"})
			containsAll(t, got, "Neymar Jr", "Overall: 92", "Position: LW", "Paris Saint-Germain", "Best attributes:")
		})

	newScenario(t, "Player Queries", "A player who is not in the snapshot").
		Given("the player data is loaded", nil).
		When("I ask about a player who is missing from the FIFA snapshot", nil).
		Then("the server says so and suggests the closest names", func() {
			got := failure(t, "player_profile", map[string]any{"name": "Gabriel Barbosa"})
			containsAll(t, got, "fifa_data.csv")
			if !strings.Contains(got, "Closest names") && !strings.Contains(got, "No player name close") {
				t.Errorf("the answer should explain itself:\n%s", got)
			}
		})
}

// ---------------------------------------------------------------------------
// Feature: Competition Queries
// ---------------------------------------------------------------------------

const featureCompetitionQueries = `
Feature: Competition Queries

  Scenario: Standings calculated from match results
    Given the match data is loaded
    When I ask who won the 2019 Brasileirão
    Then Flamengo is reported as champion with 90 points
    And the relegated clubs are listed

  Scenario: A season whose fixtures are incomplete
    Given the match data is loaded
    When I ask who won the 2023 Brasileirão
    Then the server reports the leader but refuses to name a champion

  Scenario: Cup bracket
    Given the match data is loaded
    When I ask for the 2018 Copa Libertadores
    Then the bracket runs from the group stage to the final
`

func TestFeatureCompetitionQueries(t *testing.T) {
	t.Log(featureCompetitionQueries)

	newScenario(t, "Competition Queries", "Standings calculated from match results").
		Given("the match data is loaded", func() { testServer(t) }).
		When("I ask who won the 2019 Brasileirão", nil).
		Then("Flamengo is reported as champion with 90 points", func() {
			got := answer(t, "standings", map[string]any{"competition": "brasileirao", "season": 2019})
			containsAll(t, got, "Flamengo", "90 pts", "Champion")
		}).
		And("the relegated clubs are listed", func() {
			got := answer(t, "standings", map[string]any{"competition": "brasileirao", "season": 2019})
			containsAll(t, got, "Relegated")
		})

	newScenario(t, "Competition Queries", "A season whose fixtures are incomplete").
		Given("the match data is loaded", nil).
		When("I ask who won the 2023 Brasileirão", nil).
		Then("the server reports the leader but refuses to name a champion", func() {
			got := answer(t, "standings", map[string]any{"competition": "brasileirao", "season": 2023})
			containsAll(t, got, "leads the table", "fixtures are missing")
			if strings.Contains(got, "Champion:") {
				t.Errorf("a champion was declared from incomplete data:\n%s", got)
			}
		})

	newScenario(t, "Competition Queries", "Cup bracket").
		Given("the match data is loaded", nil).
		When("I ask for the 2018 Copa Libertadores", nil).
		Then("the bracket runs from the group stage to the final", func() {
			got := answer(t, "season_summary", map[string]any{"competition": "libertadores", "season": 2018})
			containsAll(t, got, "Group stage", "Round of 16", "Quarterfinals", "Semifinals", "Final", "Winner")
			if !strings.Contains(got, "River Plate") {
				t.Errorf("the 2018 final was Boca against River:\n%s", got)
			}
		})
}

// ---------------------------------------------------------------------------
// Feature: Statistical Analysis
// ---------------------------------------------------------------------------

const featureStatistics = `
Feature: Statistical Analysis

  Scenario: League averages
    Given the match data is loaded
    When I ask for the Brasileirão averages
    Then I receive goals per match and the home/draw/away split

  Scenario: Best records
    Given the match data is loaded
    When I ask which club has the best home record
    Then clubs are ranked by home win rate

  Scenario: Cross-file query
    Given both the match and player data are loaded
    When I ask about a club that appears in both files
    Then the answer combines its match record with its squad
`

func TestFeatureStatistics(t *testing.T) {
	t.Log(featureStatistics)

	newScenario(t, "Statistical Analysis", "League averages").
		Given("the match data is loaded", func() { testServer(t) }).
		When("I ask for the Brasileirão averages", nil).
		Then("I receive goals per match and the home/draw/away split", func() {
			got := answer(t, "league_statistics", map[string]any{"competition": "brasileirao"})
			containsAll(t, got, "average goals per match", "Home wins", "draws", "away wins", "Biggest victories")
			data := structured(t, "league_statistics", map[string]any{"competition": "brasileirao"})
			stats := data["statistics"]
			if stats == nil {
				t.Fatal("no structured statistics")
			}
		})

	newScenario(t, "Statistical Analysis", "Best records").
		Given("the match data is loaded", nil).
		When("I ask which club has the best home record", nil).
		Then("clubs are ranked by home win rate", func() {
			got := answer(t, "best_records", map[string]any{
				"venue": "home", "metric": "win_rate", "min_matches": 100, "limit": 5})
			containsAll(t, got, "home records", "win rate")
		})

	newScenario(t, "Statistical Analysis", "Cross-file query").
		Given("both the match and player data are loaded", nil).
		When("I ask about a club that appears in both files", nil).
		Then("the answer combines its match record with its squad", func() {
			got := answer(t, "team_profile", map[string]any{"team": "Grêmio"})
			containsAll(t, got, "Overall record", "By competition", "FIFA squad in the player dataset")
		})
}
