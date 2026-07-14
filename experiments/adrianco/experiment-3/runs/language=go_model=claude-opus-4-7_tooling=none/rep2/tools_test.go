// tools_test.go exercises every MCP tool handler end-to-end against the real
// datasets, asserting that the formatted answers contain the expected facts.
package main

import (
	"strings"
	"testing"
)

// callTool looks up a tool by name and invokes its handler.
func callTool(t *testing.T, tools []Tool, name string, args map[string]any) (string, error) {
	t.Helper()
	for _, tool := range tools {
		if tool.Name == name {
			return tool.Handler(args)
		}
	}
	t.Fatalf("tool %q not registered", name)
	return "", nil
}

func TestTools_AllRegistered(t *testing.T) {
	store := loadedStore(t)
	tools := BuildTools(store)
	want := []string{
		"search_matches", "team_stats", "head_to_head", "search_players",
		"competition_standings", "competition_stats", "list_competitions",
	}
	if len(tools) != len(want) {
		t.Fatalf("got %d tools, want %d", len(tools), len(want))
	}
	for _, name := range want {
		found := false
		for _, tool := range tools {
			if tool.Name == name {
				found = true
				if tool.Description == "" || tool.InputSchema == nil {
					t.Errorf("tool %q missing description or schema", name)
				}
			}
		}
		if !found {
			t.Errorf("tool %q not registered", name)
		}
	}
}

func TestTool_SearchMatches(t *testing.T) {
	tools := BuildTools(loadedStore(t))
	// When I search a specific fixture
	out, err := callTool(t, tools, "search_matches", map[string]any{
		"team":     "Flamengo",
		"opponent": "Fluminense",
	})
	if err != nil {
		t.Fatalf("search_matches error: %v", err)
	}
	// Then the answer lists matches and a head-to-head summary
	if !strings.Contains(out, "Flamengo") || !strings.Contains(out, "Fluminense") {
		t.Errorf("output missing team names:\n%s", out)
	}
	if !strings.Contains(out, "Head-to-head") {
		t.Errorf("expected head-to-head summary:\n%s", out)
	}
}

func TestTool_SearchMatchesBySeason(t *testing.T) {
	tools := BuildTools(loadedStore(t))
	out, err := callTool(t, tools, "search_matches", map[string]any{
		"team":   "Palmeiras",
		"season": float64(2019), // JSON numbers decode to float64
	})
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if !strings.Contains(out, "Palmeiras") {
		t.Errorf("expected Palmeiras matches:\n%s", out)
	}
}

func TestTool_TeamStats(t *testing.T) {
	tools := BuildTools(loadedStore(t))
	// When I ask for a team's seasonal record
	out, err := callTool(t, tools, "team_stats", map[string]any{
		"team":        "Palmeiras",
		"season":      float64(2019),
		"competition": "Brasileirão",
	})
	if err != nil {
		t.Fatalf("team_stats error: %v", err)
	}
	for _, want := range []string{"Matches: 38", "Wins:", "Win rate:"} {
		if !strings.Contains(out, want) {
			t.Errorf("output missing %q:\n%s", want, out)
		}
	}
}

func TestTool_TeamStatsRequiresTeam(t *testing.T) {
	tools := BuildTools(loadedStore(t))
	// When the required 'team' argument is missing
	_, err := callTool(t, tools, "team_stats", map[string]any{})
	// Then the handler reports an error
	if err == nil {
		t.Error("expected an error when 'team' is omitted")
	}
}

func TestTool_HeadToHead(t *testing.T) {
	tools := BuildTools(loadedStore(t))
	out, err := callTool(t, tools, "head_to_head", map[string]any{
		"team1": "Palmeiras",
		"team2": "Santos",
	})
	if err != nil {
		t.Fatalf("head_to_head error: %v", err)
	}
	if !strings.Contains(out, "head-to-head") {
		t.Errorf("expected head-to-head wording:\n%s", out)
	}
	if !strings.Contains(out, "wins:") {
		t.Errorf("expected win counts:\n%s", out)
	}
}

func TestTool_SearchPlayers(t *testing.T) {
	tools := BuildTools(loadedStore(t))
	// When I search for top Brazilian players
	out, err := callTool(t, tools, "search_players", map[string]any{
		"nationality": "Brazil",
		"min_overall": float64(85),
		"limit":       float64(5),
	})
	if err != nil {
		t.Fatalf("search_players error: %v", err)
	}
	if !strings.Contains(out, "Overall:") {
		t.Errorf("expected player ratings:\n%s", out)
	}
	// And the ranked list starts at 1.
	if !strings.Contains(out, "1. ") {
		t.Errorf("expected a numbered ranking:\n%s", out)
	}
}

func TestTool_CompetitionStandings(t *testing.T) {
	tools := BuildTools(loadedStore(t))
	// When I request the 2019 Brasileirão table
	out, err := callTool(t, tools, "competition_standings", map[string]any{
		"competition": "Brasileirão",
		"season":      float64(2019),
	})
	if err != nil {
		t.Fatalf("competition_standings error: %v", err)
	}
	// Then Flamengo are shown as champions
	if !strings.Contains(out, "Flamengo") || !strings.Contains(out, "Champion") {
		t.Errorf("expected Flamengo champion line:\n%s", out)
	}
	if !strings.Contains(out, "Relegation zone") {
		t.Errorf("expected relegation zone summary:\n%s", out)
	}
}

func TestTool_CompetitionStandingsRequiresSeason(t *testing.T) {
	tools := BuildTools(loadedStore(t))
	_, err := callTool(t, tools, "competition_standings", map[string]any{
		"competition": "Brasileirão",
	})
	if err == nil {
		t.Error("expected an error when 'season' is omitted")
	}
}

func TestTool_CompetitionStats(t *testing.T) {
	tools := BuildTools(loadedStore(t))
	out, err := callTool(t, tools, "competition_stats", map[string]any{
		"competition": "Brasileirão",
		"season":      float64(2019),
	})
	if err != nil {
		t.Fatalf("competition_stats error: %v", err)
	}
	for _, want := range []string{"Average goals per match", "Home wins", "Biggest victories"} {
		if !strings.Contains(out, want) {
			t.Errorf("output missing %q:\n%s", want, out)
		}
	}
}

func TestTool_ListCompetitions(t *testing.T) {
	tools := BuildTools(loadedStore(t))
	out, err := callTool(t, tools, "list_competitions", map[string]any{})
	if err != nil {
		t.Fatalf("list_competitions error: %v", err)
	}
	for _, want := range []string{"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"} {
		if !strings.Contains(out, want) {
			t.Errorf("output missing competition %q:\n%s", want, out)
		}
	}
}

func TestTool_NoResultsIsGraceful(t *testing.T) {
	tools := BuildTools(loadedStore(t))
	// When a query cannot match anything
	out, err := callTool(t, tools, "search_matches", map[string]any{
		"team": "Nonexistent United FC",
	})
	// Then the handler returns a friendly message rather than an error
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(strings.ToLower(out), "no matches") {
		t.Errorf("expected a 'no matches' message, got:\n%s", out)
	}
}
