// Acceptance tests for the Brazilian Soccer MCP server.
// Each test exercises the system only through its public MCP tool interface.
// Tests are independent: each builds a fresh server from the real CSV data.
package main_test

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"brazilian-soccer-mcp/mcp"
)

func call(t *testing.T, srv *mcp.Server, tool string, args map[string]any) map[string]any {
	t.Helper()
	raw, err := srv.Call(context.Background(), tool, args)
	if err != nil {
		t.Fatalf("tool %s error: %v", tool, err)
	}
	var result map[string]any
	if err := json.Unmarshal([]byte(raw), &result); err != nil {
		t.Fatalf("tool %s: unmarshal error: %v\nraw=%s", tool, err, raw)
	}
	return result
}

func newServer(t *testing.T) *mcp.Server {
	t.Helper()
	srv, err := mcp.NewServer("data/kaggle")
	if err != nil {
		t.Fatalf("NewServer: %v", err)
	}
	return srv
}

// AC1: find_matches returns matches between two specific teams
func TestFindMatchesBetweenTwoTeams(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "find_matches", map[string]any{
		"team1": "Flamengo",
		"team2": "Fluminense",
	})

	matches, ok := result["matches"].([]any)
	if !ok || len(matches) == 0 {
		t.Fatalf("expected matches between Flamengo and Fluminense, got: %v", result)
	}

	for _, m := range matches {
		match := m.(map[string]any)
		home := strings.ToLower(match["home_team"].(string))
		away := strings.ToLower(match["away_team"].(string))
		hasFla := strings.Contains(home, "flamengo") || strings.Contains(away, "flamengo")
		hasFlu := strings.Contains(home, "fluminense") || strings.Contains(away, "fluminense")
		if !hasFla || !hasFlu {
			t.Errorf("match does not involve both teams: home=%s away=%s", home, away)
		}
	}
}

// AC2: find_matches with season filter returns only matches from that season
func TestFindMatchesBySeason(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "find_matches", map[string]any{
		"team":   "Palmeiras",
		"season": 2023,
	})

	matches, ok := result["matches"].([]any)
	if !ok || len(matches) == 0 {
		t.Fatalf("expected Palmeiras 2023 matches, got: %v", result)
	}
	for _, m := range matches {
		match := m.(map[string]any)
		if int(match["season"].(float64)) != 2023 {
			t.Errorf("expected season 2023, got %v", match["season"])
		}
	}
}

// AC3: find_matches with competition filter returns only matches from that competition
func TestFindMatchesByCompetition(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "find_matches", map[string]any{
		"competition": "Copa do Brasil",
		"season":      2022,
	})

	matches, ok := result["matches"].([]any)
	if !ok || len(matches) == 0 {
		t.Fatalf("expected Copa do Brasil 2022 matches, got: %v", result)
	}
	for _, m := range matches {
		match := m.(map[string]any)
		comp := match["competition"].(string)
		if !strings.Contains(comp, "Copa do Brasil") {
			t.Errorf("expected Copa do Brasil, got %s", comp)
		}
	}
}

// AC4: get_team_stats returns win/loss/draw record for a team in a season
func TestGetTeamStats(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "get_team_stats", map[string]any{
		"team":        "Corinthians",
		"season":      2022,
		"competition": "Brasileirao",
	})

	for _, key := range []string{"team", "wins", "draws", "losses", "goals_for", "goals_against"} {
		if _, ok := result[key]; !ok {
			t.Errorf("missing field %q in team stats result", key)
		}
	}
	wins := result["wins"].(float64)
	draws := result["draws"].(float64)
	losses := result["losses"].(float64)
	if wins+draws+losses == 0 {
		t.Error("expected non-zero match totals for Corinthians 2022")
	}
}

// AC5: find_players returns players matching a name search
func TestFindPlayersByName(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "find_players", map[string]any{
		"name": "Neymar",
	})

	players, ok := result["players"].([]any)
	if !ok || len(players) == 0 {
		t.Fatalf("expected players matching Neymar, got: %v", result)
	}
	found := false
	for _, p := range players {
		player := p.(map[string]any)
		if strings.Contains(strings.ToLower(player["name"].(string)), "neymar") {
			found = true
			break
		}
	}
	if !found {
		t.Error("Neymar not found in results")
	}
}

// AC6: find_players filters by nationality
func TestFindPlayersByNationality(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "find_players", map[string]any{
		"nationality": "Brazil",
		"limit":       10,
	})

	players, ok := result["players"].([]any)
	if !ok || len(players) == 0 {
		t.Fatalf("expected Brazilian players, got: %v", result)
	}
	for _, p := range players {
		player := p.(map[string]any)
		nat := player["nationality"].(string)
		if !strings.EqualFold(nat, "brazil") {
			t.Errorf("expected Brazilian player, got nationality=%s", nat)
		}
	}
}

// AC7: find_players filters by club (Fluminense is present in the FIFA dataset)
func TestFindPlayersByClub(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "find_players", map[string]any{
		"club": "Fluminense",
	})

	players, ok := result["players"].([]any)
	if !ok || len(players) == 0 {
		t.Fatalf("expected Fluminense players, got: %v", result)
	}
	for _, p := range players {
		player := p.(map[string]any)
		club := player["club"].(string)
		if !strings.Contains(strings.ToLower(club), "fluminense") {
			t.Errorf("expected Fluminense club, got %s", club)
		}
	}
}

// AC8: get_standings returns ordered standings for a season
func TestGetStandings(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "get_standings", map[string]any{
		"competition": "Brasileirao",
		"season":      2019,
	})

	standings, ok := result["standings"].([]any)
	if !ok || len(standings) == 0 {
		t.Fatalf("expected 2019 Brasileirao standings, got: %v", result)
	}

	first := standings[0].(map[string]any)
	if !strings.Contains(strings.ToLower(first["team"].(string)), "flamengo") {
		t.Errorf("expected Flamengo as 2019 champion, got %v", first["team"])
	}

	prevPts := 1000.0
	for i, s := range standings {
		row := s.(map[string]any)
		pts := row["points"].(float64)
		if pts > prevPts {
			t.Errorf("standings not sorted by points at position %d: %v > %v", i, pts, prevPts)
		}
		prevPts = pts
	}
}

// AC9: get_statistics returns aggregate stats (goals per match, home win rate)
func TestGetStatistics(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "get_statistics", map[string]any{
		"competition": "Brasileirao",
		"season":      2022,
	})

	for _, key := range []string{"total_matches", "avg_goals_per_match", "home_win_rate"} {
		if _, ok := result[key]; !ok {
			t.Errorf("missing field %q in statistics result", key)
		}
	}

	avgGoals := result["avg_goals_per_match"].(float64)
	if avgGoals < 1.0 || avgGoals > 6.0 {
		t.Errorf("avg_goals_per_match %v out of realistic range", avgGoals)
	}

	homeWinRate := result["home_win_rate"].(float64)
	if homeWinRate < 0.0 || homeWinRate > 1.0 {
		t.Errorf("home_win_rate %v not a valid ratio", homeWinRate)
	}
}

// AC10: team name normalization — "Palmeiras-SP" and "Palmeiras" match the same team
func TestTeamNameNormalization(t *testing.T) {
	srv := newServer(t)
	r1 := call(t, srv, "find_matches", map[string]any{"team": "Palmeiras", "season": 2019})
	r2 := call(t, srv, "find_matches", map[string]any{"team": "Palmeiras-SP", "season": 2019})

	m1, _ := r1["matches"].([]any)
	m2, _ := r2["matches"].([]any)
	if len(m1) == 0 || len(m2) == 0 {
		t.Fatalf("expected matches for both forms: plain=%d suffixed=%d", len(m1), len(m2))
	}
	if len(m1) != len(m2) {
		t.Errorf("name normalization mismatch: plain=%d suffixed=%d", len(m1), len(m2))
	}
}

// AC11: find_matches with date range filter
func TestFindMatchesByDateRange(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "find_matches", map[string]any{
		"date_from": "2023-01-01",
		"date_to":   "2023-03-31",
	})

	matches, ok := result["matches"].([]any)
	if !ok || len(matches) == 0 {
		t.Fatalf("expected matches in Q1 2023, got: %v", result)
	}
}

// AC12: head-to-head summary included when two teams specified
func TestHeadToHeadSummary(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "find_matches", map[string]any{
		"team1": "Flamengo",
		"team2": "Fluminense",
	})

	h2h, ok := result["head_to_head"].(map[string]any)
	if !ok {
		t.Fatalf("expected head_to_head summary, got: %v", result)
	}
	for _, key := range []string{"team1_wins", "team2_wins", "draws"} {
		if _, ok := h2h[key]; !ok {
			t.Errorf("head_to_head missing field %q", key)
		}
	}
}

// AC13: find_players sorted by overall rating descending when filtered
func TestFindPlayersRatingSorted(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "find_players", map[string]any{
		"nationality": "Brazil",
		"limit":       5,
	})

	players, ok := result["players"].([]any)
	if !ok || len(players) < 2 {
		t.Fatalf("expected at least 2 players, got: %v", result)
	}
	prev := 999.0
	for i, p := range players {
		player := p.(map[string]any)
		rating := player["overall"].(float64)
		if rating > prev {
			t.Errorf("players not sorted by overall desc at index %d: %v > %v", i, rating, prev)
		}
		prev = rating
	}
}

// AC14: Libertadores data is accessible via find_matches with competition filter
func TestLibertadoresMatches(t *testing.T) {
	srv := newServer(t)
	result := call(t, srv, "find_matches", map[string]any{
		"competition": "Libertadores",
		"team":        "Flamengo",
	})

	matches, ok := result["matches"].([]any)
	if !ok || len(matches) == 0 {
		t.Fatalf("expected Flamengo Libertadores matches, got: %v", result)
	}
}

// AC15: performance - simple lookup responds in under 2 seconds (server already loaded)
func TestPerformanceSimpleLookup(t *testing.T) {
	srv := newServer(t)
	start := time.Now()
	call(t, srv, "find_matches", map[string]any{"team": "Santos", "season": 2023})
	elapsed := time.Since(start)
	if elapsed > 2*time.Second {
		t.Errorf("find_matches took %v, expected < 2s", elapsed)
	}
}
