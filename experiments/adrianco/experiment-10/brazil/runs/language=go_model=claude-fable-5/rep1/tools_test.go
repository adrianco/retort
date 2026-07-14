// tools_test.go — BDD (Given/When/Then) scenarios for the MCP tools,
// covering the sample questions from the specification.
package main

import (
	"regexp"
	"strings"
	"testing"
	"time"
)

// whenIToolCall invokes a tool by name and fails the test on error.
func whenIToolCall(t *testing.T, s *Store, name string, args map[string]any) string {
	t.Helper()
	for _, tool := range AllTools() {
		if tool.Name == name {
			out, err := tool.Handler(s, args)
			if err != nil {
				t.Fatalf("When I call %s(%v): unexpected error: %v", name, args, err)
			}
			return out
		}
	}
	t.Fatalf("unknown tool %q", name)
	return ""
}

func TestScenario_FindMatchesBetweenTwoTeams(t *testing.T) {
	// Given the match data is loaded
	s := givenTheDataIsLoaded(t)

	// When I search for matches between "Flamengo" and "Fluminense"
	out := whenIToolCall(t, s, "search_matches", map[string]any{
		"team": "Flamengo", "opponent": "Fluminense",
	})

	// Then I should receive a list of matches
	if strings.Contains(out, "No matches found") {
		t.Fatalf("expected Fla-Flu matches, got: %s", out)
	}
	// And each match should have date, scores, and competition
	line := regexp.MustCompile(`(?m)^- (\d{4}-\d{2}-\d{2}): .* (\d+)-(\d+) .*\((Brasileirão|Copa)`)
	if !line.MatchString(out) {
		t.Errorf("match lines missing date/score/competition:\n%s", out)
	}
	// And a head-to-head summary is included
	if !strings.Contains(out, "Head-to-head") {
		t.Errorf("expected head-to-head summary:\n%s", out)
	}
}

func TestScenario_GetTeamStatisticsForASeason(t *testing.T) {
	// Given the match data is loaded
	s := givenTheDataIsLoaded(t)

	// When I request statistics for "Palmeiras" in season "2018"
	out := whenIToolCall(t, s, "get_team_stats", map[string]any{
		"team": "Palmeiras", "season": 2018, "competition": "Brasileirão",
	})

	// Then I should receive wins, losses, draws, and goals
	for _, want := range []string{"Wins:", "Draws:", "Losses:", "Goals For:", "Goals Against:", "Win rate:"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in stats output:\n%s", want, out)
		}
	}
	// And Palmeiras (2018 champions) played a full 38-match season
	if !strings.Contains(out, "Matches: 38") {
		t.Errorf("expected 38 matches for Palmeiras in 2018 Série A:\n%s", out)
	}
}

func TestScenario_CorinthiansHomeRecord2022(t *testing.T) {
	// Given the match data is loaded
	s := givenTheDataIsLoaded(t)

	// When I ask for Corinthians' home record in the 2022 Brasileirão
	out := whenIToolCall(t, s, "get_team_stats", map[string]any{
		"team": "Corinthians", "season": 2022, "competition": "Brasileirão", "venue": "home",
	})

	// Then the record covers exactly the 19 home matches
	if !strings.Contains(out, "Matches: 19") {
		t.Errorf("expected 19 home matches in 2022:\n%s", out)
	}
	if !strings.Contains(out, "home") {
		t.Errorf("expected the title to mention the home venue:\n%s", out)
	}
}

func TestScenario_StandingsIdentifyThe2019Champion(t *testing.T) {
	// Given the match data is loaded
	s := givenTheDataIsLoaded(t)

	// When I calculate the 2019 Brasileirão standings
	out := whenIToolCall(t, s, "get_standings", map[string]any{"season": 2019})

	// Then Flamengo is champion with 90 points (28W 6D 4L)
	lines := strings.Split(out, "\n")
	if len(lines) < 21 {
		t.Fatalf("expected a 20-team table, got:\n%s", out)
	}
	top := lines[1]
	if !strings.Contains(top, "Flamengo") || !strings.Contains(top, "90 pts") ||
		!strings.Contains(top, "Champion") {
		t.Errorf("expected 'Flamengo — 90 pts ... Champion' on top, got: %s", top)
	}
	if !strings.Contains(top, "28W 6D 4L") {
		t.Errorf("expected 28W 6D 4L for 2019 Flamengo, got: %s", top)
	}
	// And the bottom of the table is marked as the relegation zone
	if !strings.Contains(out, "Relegation zone") {
		t.Errorf("expected relegation zone markers:\n%s", out)
	}
}

func TestScenario_StandingsFor2003UseHistoricalData(t *testing.T) {
	// Given the historical 2003-2019 dataset is loaded
	s := givenTheDataIsLoaded(t)

	// When I calculate the 2003 standings (only in novo_campeonato_brasileiro.csv)
	out := whenIToolCall(t, s, "get_standings", map[string]any{"season": 2003})

	// Then Cruzeiro is the 2003 champion
	first := strings.Split(out, "\n")[1]
	if !strings.Contains(first, "Cruzeiro") {
		t.Errorf("expected Cruzeiro as 2003 champion, got: %s", first)
	}
}

func TestScenario_SearchPlayersByNationality(t *testing.T) {
	// Given the player data is loaded
	s := givenTheDataIsLoaded(t)

	// When I search for Brazilian players
	out := whenIToolCall(t, s, "search_players", map[string]any{
		"nationality": "Brazil", "limit": 10,
	})

	// Then I receive a ranked list including top Brazilians like Neymar
	if !strings.Contains(out, "Neymar") {
		t.Errorf("expected Neymar among top Brazilian players:\n%s", out)
	}
	if !strings.Contains(out, "Nationality: Brazil") {
		t.Errorf("expected Brazilian nationality in output:\n%s", out)
	}
}

func TestScenario_WhoIsGabrielJesus(t *testing.T) {
	// Given the player data is loaded
	// (Note: this FIFA snapshot has no Gabriel Barbosa entry, so the
	// spec's "Who is <player>?" lookup is exercised with Gabriel Jesus.)
	s := givenTheDataIsLoaded(t)

	// When I look up "Gabriel Jesus"
	out := whenIToolCall(t, s, "get_player_details", map[string]any{"name": "Gabriel Jesus"})

	// Then I get his FIFA profile
	for _, want := range []string{"Gabriel Jesus", "Overall:", "Nationality: Brazil", "Position:"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in player details:\n%s", want, out)
		}
	}

	// And an unknown player yields a friendly message, not an error
	out = whenIToolCall(t, s, "get_player_details", map[string]any{"name": "Zé Inexistente"})
	if !strings.Contains(out, "No player matching") {
		t.Errorf("expected friendly not-found message, got:\n%s", out)
	}
}

func TestScenario_PlayersAtAClub(t *testing.T) {
	// Given the player data is loaded (FIFA 19 includes Fluminense but not
	// every Brazilian club)
	s := givenTheDataIsLoaded(t)

	// When I ask which players play for Fluminense
	out := whenIToolCall(t, s, "search_players", map[string]any{"club": "Fluminense", "limit": 30})

	// Then every listed player is at Fluminense
	if strings.Contains(out, "No players found") {
		t.Fatalf("expected Fluminense players, got none")
	}
	for _, line := range strings.Split(out, "\n")[1:] {
		if line == "" {
			continue
		}
		if !strings.Contains(line, "Fluminense") {
			t.Errorf("non-Fluminense player in club search: %s", line)
		}
	}
}

func TestScenario_FilterForwardsByPositionGroup(t *testing.T) {
	// Given the player data is loaded
	s := givenTheDataIsLoaded(t)

	// When I search for Brazilian forwards
	out := whenIToolCall(t, s, "search_players", map[string]any{
		"nationality": "Brazil", "position": "forwards", "limit": 15,
	})

	// Then every listed player has a forward position code
	fwd := regexp.MustCompile(`Position: (ST|CF|LS|RS|LF|RF|LW|RW)\b`)
	lines := strings.Split(out, "\n")[1:]
	if len(lines) == 0 {
		t.Fatal("expected forwards in result")
	}
	for _, line := range lines {
		if line == "" {
			continue
		}
		if !fwd.MatchString(line) {
			t.Errorf("non-forward in forwards search: %s", line)
		}
	}
}

func TestScenario_HeadToHeadComparison(t *testing.T) {
	// Given the match data is loaded
	s := givenTheDataIsLoaded(t)

	// When I compare Palmeiras and Santos head-to-head
	out := whenIToolCall(t, s, "head_to_head", map[string]any{
		"team1": "Palmeiras", "team2": "Santos",
	})

	// Then I get win counts for both sides, draws, and recent meetings
	h2h := regexp.MustCompile(`Head-to-head: .*Palmeiras.* (\d+) wins, .*Santos.* (\d+) wins, (\d+) draws`)
	if !h2h.MatchString(out) {
		t.Errorf("missing head-to-head summary:\n%s", out)
	}
	if !strings.Contains(out, "Most recent meetings:") {
		t.Errorf("missing recent meetings list:\n%s", out)
	}
}

func TestScenario_FindCopaDoBrasilFinals(t *testing.T) {
	// Given the cup data is loaded
	s := givenTheDataIsLoaded(t)

	// When I search for Copa do Brasil finals
	out := whenIToolCall(t, s, "search_matches", map[string]any{
		"competition": "Copa do Brasil", "stage": "final", "limit": 50,
	})

	// Then I receive final matches across multiple seasons
	if strings.Contains(out, "No matches found") {
		t.Fatalf("expected cup finals, got none")
	}
	finals := strings.Count(out, "Final")
	if finals < 10 {
		t.Errorf("expected finals from many seasons, got %d lines:\n%s", finals, out)
	}
	if strings.Contains(out, "Round ") {
		t.Errorf("stage filter leaked non-final rounds:\n%s", out)
	}
}

func TestScenario_LibertadoresStageFilter(t *testing.T) {
	// Given the Libertadores data is loaded
	s := givenTheDataIsLoaded(t)

	// When I search the 2019 Libertadores final
	out := whenIToolCall(t, s, "search_matches", map[string]any{
		"competition": "Libertadores", "season": 2019, "stage": "final",
	})

	// Then Flamengo's 2-1 win over River Plate is returned
	if !strings.Contains(out, "Flamengo") || !strings.Contains(out, "River Plate") {
		t.Errorf("expected Flamengo vs River Plate 2019 final:\n%s", out)
	}
}

func TestScenario_MatchesByDateRange(t *testing.T) {
	// Given the match data is loaded
	s := givenTheDataIsLoaded(t)

	// When I search Palmeiras matches in May 2018
	out := whenIToolCall(t, s, "search_matches", map[string]any{
		"team": "Palmeiras", "date_from": "2018-05-01", "date_to": "2018-05-31", "limit": 100,
	})

	// Then every listed match falls inside the range
	dates := regexp.MustCompile(`(?m)^- (\d{4}-\d{2}-\d{2}):`).FindAllStringSubmatch(out, -1)
	if len(dates) == 0 {
		t.Fatalf("expected matches in May 2018:\n%s", out)
	}
	for _, d := range dates {
		if d[1] < "2018-05-01" || d[1] > "2018-05-31" {
			t.Errorf("match outside date range: %s", d[1])
		}
	}
}

func TestScenario_AverageGoalsAndHomeWinRate(t *testing.T) {
	// Given the match data is loaded
	s := givenTheDataIsLoaded(t)

	// When I ask for Brasileirão aggregate statistics
	out := whenIToolCall(t, s, "get_competition_stats", map[string]any{
		"competition": "Brasileirão",
	})

	// Then I get a plausible average goals per match and result split
	avg := regexp.MustCompile(`Average goals per match: ([\d.]+)`).FindStringSubmatch(out)
	if avg == nil {
		t.Fatalf("missing average goals:\n%s", out)
	}
	if avg[1] < "1.5" || avg[1] > "3.5" {
		t.Errorf("implausible average goals per match: %s", avg[1])
	}
	for _, want := range []string{"Home wins:", "Draws:", "Away wins:", "Biggest victories:"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q:\n%s", want, out)
		}
	}
}

func TestScenario_ListCompetitionsShowsAllSources(t *testing.T) {
	// Given all datasets are loaded
	s := givenTheDataIsLoaded(t)

	// When I list the available competitions
	out := whenIToolCall(t, s, "list_competitions", nil)

	// Then all five competitions and the player database are reported
	for _, want := range []string{CompSerieA, CompSerieB, CompSerieC, CompCopaDoBrasil, CompLibertadores, "players"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in competitions list:\n%s", want, out)
		}
	}
}

func TestScenario_WhenDidFlamengoLastPlayCorinthians(t *testing.T) {
	// Given the match data is loaded
	s := givenTheDataIsLoaded(t)

	// When I search Flamengo vs Corinthians with limit 1 (results are newest first)
	out := whenIToolCall(t, s, "search_matches", map[string]any{
		"team": "Flamengo", "opponent": "Corinthians", "limit": 1,
	})

	// Then the single listed match is the most recent meeting
	dates := regexp.MustCompile(`(?m)^- (\d{4}-\d{2}-\d{2}):`).FindAllStringSubmatch(out, -1)
	if len(dates) != 1 {
		t.Fatalf("expected exactly 1 listed match:\n%s", out)
	}
	// And it is from the recent era covered by the data
	if dates[0][1] < "2019-01-01" {
		t.Errorf("most recent Fla-Corinthians meeting suspiciously old: %s", dates[0][1])
	}
}

func TestScenario_UnknownTeamReturnsFriendlyMessage(t *testing.T) {
	// Given the match data is loaded
	s := givenTheDataIsLoaded(t)

	// When I search for a nonexistent team
	out := whenIToolCall(t, s, "search_matches", map[string]any{"team": "Real Madrid Castilla XYZ"})

	// Then I get a clear empty result rather than an error
	if !strings.Contains(out, "No matches found") {
		t.Errorf("expected friendly empty result, got:\n%s", out)
	}
}

func TestScenario_InvalidArgumentsProduceErrors(t *testing.T) {
	// Given the data is loaded
	s := givenTheDataIsLoaded(t)

	// When I call tools with bad arguments / Then I get descriptive errors
	for _, tc := range []struct {
		tool string
		args map[string]any
	}{
		{"get_team_stats", map[string]any{}},                                             // missing team
		{"get_standings", map[string]any{}},                                              // missing season
		{"get_standings", map[string]any{"season": 2019, "competition": "Libertadores"}}, // not a league
		{"search_matches", map[string]any{"competition": "Premier League"}},              // unknown competition
		{"search_matches", map[string]any{"date_from": "not-a-date"}},                    // bad date
	} {
		for _, tool := range AllTools() {
			if tool.Name != tc.tool {
				continue
			}
			if _, err := tool.Handler(s, tc.args); err == nil {
				t.Errorf("%s(%v): expected error, got none", tc.tool, tc.args)
			}
		}
	}
}

func TestScenario_QueriesAreFast(t *testing.T) {
	// Given the data is loaded
	s := givenTheDataIsLoaded(t)

	// When I run a simple lookup and an aggregate query
	start := time.Now()
	whenIToolCall(t, s, "search_matches", map[string]any{"team": "Flamengo", "opponent": "Fluminense"})
	simple := time.Since(start)

	start = time.Now()
	whenIToolCall(t, s, "get_competition_stats", map[string]any{})
	aggregate := time.Since(start)

	// Then the simple lookup takes < 2s and the aggregate < 5s
	if simple > 2*time.Second {
		t.Errorf("simple lookup took %v, want < 2s", simple)
	}
	if aggregate > 5*time.Second {
		t.Errorf("aggregate query took %v, want < 5s", aggregate)
	}
}
