// tools_test.go - BDD (Given/When/Then) tests for the MCP tool handlers of
// the Brazilian Soccer MCP server.
//
// Context: Exercises every exposed tool through its handler (the same code
// path tools/call uses), checks the formatted answer text, and runs the
// spec's "at least 20 sample questions" coverage scenario.
package main

import (
	"strings"
	"testing"
	"time"
)

func testTools(t *testing.T) map[string]Tool {
	t.Helper()
	tools := BuildTools(sharedStore(t))
	m := map[string]Tool{}
	for _, tool := range tools {
		m[tool.Name] = tool
	}
	return m
}

func callTool(t *testing.T, name string, args map[string]any) string {
	t.Helper()
	tool, ok := testTools(t)[name]
	if !ok {
		t.Fatalf("tool %s not registered", name)
	}
	out, err := tool.Handler(args)
	if err != nil {
		t.Fatalf("tool %s returned error: %v", name, err)
	}
	if strings.TrimSpace(out) == "" {
		t.Fatalf("tool %s returned empty output", name)
	}
	return out
}

func TestToolSearchMatchesWithHeadToHead(t *testing.T) {
	// Scenario: "Show me all Flamengo vs Fluminense matches."
	// Given the MCP tools are built over the loaded store
	// When search_matches is called with both teams
	out := callTool(t, "search_matches", map[string]any{
		"team": "Flamengo", "opponent": "Fluminense",
	})
	// Then the answer lists matches and a head-to-head summary
	if !strings.Contains(out, "Head-to-head in dataset:") {
		t.Errorf("missing head-to-head summary:\n%s", out)
	}
	if !strings.Contains(out, "Flamengo") || !strings.Contains(out, "Fluminense") {
		t.Errorf("missing team names:\n%s", out)
	}
}

func TestToolTeamStats(t *testing.T) {
	// Scenario: "What is Corinthians' home record in 2022?"
	// When team_stats is called for home matches
	out := callTool(t, "team_stats", map[string]any{
		"team": "Corinthians", "season": float64(2022), "competition": "Brasileirão", "venue": "home",
	})
	// Then the formatted record shows 19 matches with W/D/L and goals
	if !strings.Contains(out, "Matches: 19") {
		t.Errorf("expected 19 home matches:\n%s", out)
	}
	for _, want := range []string{"Wins:", "Draws:", "Losses:", "Goals For:", "Win rate:"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in:\n%s", want, out)
		}
	}
}

func TestToolLeagueStandings(t *testing.T) {
	// Scenario: "Who won the 2019 Brasileirão?" / "Which teams were relegated?"
	// When league_standings is called for 2019
	out := callTool(t, "league_standings", map[string]any{"season": float64(2019)})
	// Then Flamengo tops the table as champion with 90 points
	if !strings.Contains(out, "Champion") {
		t.Errorf("missing champion tag:\n%s", out)
	}
	first := strings.SplitN(out, "\n", 3)[1]
	if !strings.Contains(first, "Flamengo") || !strings.Contains(first, "90 pts") {
		t.Errorf("first row should be Flamengo with 90 pts, got: %s", first)
	}
	// And the relegation zone is shown
	if !strings.Contains(out, "Relegation zone") {
		t.Errorf("missing relegation zone:\n%s", out)
	}
}

func TestToolSearchPlayers(t *testing.T) {
	// Scenario: "Who are the top Brazilian players?"
	// When search_players is called for Brazilians
	out := callTool(t, "search_players", map[string]any{
		"nationality": "Brazil", "limit": float64(5),
	})
	// Then the best Brazilian (Neymar Jr, overall 92) leads the list
	if !strings.Contains(out, "Neymar Jr") || !strings.Contains(out, "Overall: 92") {
		t.Errorf("expected Neymar Jr with overall 92 first:\n%s", out)
	}
}

func TestToolPlayerInfo(t *testing.T) {
	// Scenario: "Who is Casemiro?"
	// When player_info is called by name
	out := callTool(t, "player_info", map[string]any{"name": "Casemiro"})
	// Then a detailed profile with ratings and club is returned
	for _, want := range []string{"Casemiro", "Overall:", "Position:", "Club:", "Top skills:"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in:\n%s", want, out)
		}
	}
}

func TestToolCompetitionStats(t *testing.T) {
	// Scenario: "What's the average goals per match? Show the biggest wins."
	// When competition_stats is called over the Brasileirão
	out := callTool(t, "competition_stats", map[string]any{"competition": "Brasileirão"})
	// Then averages and biggest victories are reported
	for _, want := range []string{"average", "per match", "Home wins:", "Biggest victories:"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in:\n%s", want, out)
		}
	}
}

func TestToolDataSummary(t *testing.T) {
	// Scenario: Discover what data is available.
	// When data_summary is called
	out := callTool(t, "data_summary", map[string]any{})
	// Then all competitions and the player count are listed
	for _, want := range []string{CompSerieA, CompCopaDoBrasil, CompLibertadores, "FIFA players: 18207"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in:\n%s", want, out)
		}
	}
}

func TestToolHandlersRejectMissingRequiredArgs(t *testing.T) {
	// Scenario: Required arguments are validated.
	tools := testTools(t)
	for _, c := range []struct {
		tool string
		args map[string]any
	}{
		{"head_to_head", map[string]any{"team1": "Flamengo"}},
		{"team_stats", map[string]any{}},
		{"league_standings", map[string]any{}},
		{"player_info", map[string]any{}},
	} {
		// When the tool is called without a required argument
		_, err := tools[c.tool].Handler(c.args)
		// Then an error is returned
		if err == nil {
			t.Errorf("%s: expected error for args %v", c.tool, c.args)
		}
	}
}

// TestTwentySampleQuestions runs the spec's data-coverage criterion: at
// least 20 sample questions can be answered by the server's tools.
func TestTwentySampleQuestions(t *testing.T) {
	// Given the 20+ sample questions from the specification
	samples := []struct {
		question string
		tool     string
		args     map[string]any
		expect   string // substring that must appear in the answer
	}{
		{"Show me all Flamengo vs Fluminense matches", "search_matches",
			map[string]any{"team": "Flamengo", "opponent": "Fluminense"}, "Head-to-head"},
		{"What matches did Palmeiras play in 2023?", "search_matches",
			map[string]any{"team": "Palmeiras", "season": float64(2023)}, "Palmeiras"},
		{"Find Copa do Brasil matches in 2019", "search_matches",
			map[string]any{"competition": "Copa do Brasil", "season": float64(2019)}, "Copa do Brasil"},
		{"When did Flamengo last play Corinthians?", "search_matches",
			map[string]any{"team": "Flamengo", "opponent": "Corinthians", "limit": float64(1)}, "Flamengo"},
		{"Show me Libertadores knockout matches", "search_matches",
			map[string]any{"competition": "Libertadores"}, "Copa Libertadores"},
		{"Find Santos matches in November 2019", "search_matches",
			map[string]any{"team": "Santos", "date_from": "2019-11-01", "date_to": "2019-11-30"}, "Santos"},
		{"What is Corinthians' home record in 2022?", "team_stats",
			map[string]any{"team": "Corinthians", "season": float64(2022), "venue": "home"}, "Wins:"},
		{"How does Palmeiras perform across competitions?", "team_stats",
			map[string]any{"team": "Palmeiras"}, "By competition:"},
		{"What is Flamengo's away record?", "team_stats",
			map[string]any{"team": "Flamengo", "venue": "away"}, "Win rate:"},
		{"Compare Palmeiras and Santos head-to-head", "head_to_head",
			map[string]any{"team1": "Palmeiras", "team2": "Santos"}, "wins"},
		{"Gre-Nal derby record", "head_to_head",
			map[string]any{"team1": "Grêmio", "team2": "Internacional"}, "Draws:"},
		{"Fla-Flu derby in the Brasileirão only", "head_to_head",
			map[string]any{"team1": "Flamengo", "team2": "Fluminense", "competition": "Brasileirão"}, "Brasileirão"},
		{"Who won the 2019 Brasileirão?", "league_standings",
			map[string]any{"season": float64(2019)}, "Champion"},
		{"Which teams were relegated in 2015?", "league_standings",
			map[string]any{"season": float64(2015)}, "Relegation zone"},
		{"Who won the 2006 Brasileirão?", "league_standings",
			map[string]any{"season": float64(2006)}, "Champion"},
		{"Find all Brazilian players in the dataset", "search_players",
			map[string]any{"nationality": "Brazil"}, "Brazil"},
		{"Who are the highest-rated players rated 88+?", "search_players",
			map[string]any{"min_overall": float64(88)}, "Overall:"},
		{"Show me all goalkeepers at Santos", "search_players",
			map[string]any{"club": "Santos", "position": "goalkeeper"}, "GK"},
		{"Find young Brazilian forwards", "search_players",
			map[string]any{"nationality": "Brazil", "position": "forward", "max_age": float64(23)}, "Brazil"},
		{"Who is Gabriel Jesus?", "player_info",
			map[string]any{"name": "Gabriel Jesus"}, "Gabriel Jesus"},
		{"Who is Alisson?", "player_info",
			map[string]any{"name": "Alisson"}, "Overall:"},
		{"What's the average goals per match in the Brasileirão?", "competition_stats",
			map[string]any{"competition": "Brasileirão"}, "average"},
		{"Show me the biggest wins in the dataset", "competition_stats",
			map[string]any{}, "Biggest victories:"},
		{"Compare the 2018 and 2019 seasons (2018 side)", "competition_stats",
			map[string]any{"competition": "Brasileirão", "season": float64(2018)}, "Matches: 380"},
		{"What data is available?", "data_summary",
			map[string]any{}, "FIFA players"},
	}
	if len(samples) < 20 {
		t.Fatalf("need at least 20 sample questions, have %d", len(samples))
	}
	tools := testTools(t)
	for _, q := range samples {
		// When the question's tool is invoked
		start := time.Now()
		out, err := tools[q.tool].Handler(q.args)
		elapsed := time.Since(start)
		// Then a useful answer is produced
		if err != nil {
			t.Errorf("%q: error %v", q.question, err)
			continue
		}
		if !strings.Contains(out, q.expect) {
			t.Errorf("%q: answer missing %q:\n%s", q.question, q.expect, out)
		}
		// And aggregate queries respond well under the 5 second budget
		if elapsed > 5*time.Second {
			t.Errorf("%q: took %s, budget is 5s", q.question, elapsed)
		}
	}
}
