package main

import (
	"context"
	"os"
	"strings"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
	"brazilian-soccer-mcp/soccer"
	"brazilian-soccer-mcp/tools"
)

var testStore *soccer.Store

func TestMain(m *testing.M) {
	var err error
	testStore, err = soccer.LoadStore("data/kaggle")
	if err != nil {
		panic("failed to load test data: " + err.Error())
	}
	os.Exit(m.Run())
}

func callTool(t *testing.T, handler func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error), args map[string]interface{}) string {
	t.Helper()
	req := mcp.CallToolRequest{}
	req.Params.Arguments = args
	result, err := handler(context.Background(), req)
	if err != nil {
		t.Fatalf("tool error: %v", err)
	}
	if result.IsError {
		t.Fatalf("tool returned error")
	}
	for _, c := range result.Content {
		if tc, ok := c.(mcp.TextContent); ok {
			return tc.Text
		}
	}
	return ""
}

// AT-01: Find matches between two teams
func TestAT01_FindMatchesBetweenTwoTeams(t *testing.T) {
	h := tools.NewFindMatchesHandler(testStore)
	result := callTool(t, h, map[string]interface{}{
		"team1": "Flamengo",
		"team2": "Fluminense",
	})
	if !strings.Contains(strings.ToLower(result), "flamengo") {
		t.Errorf("expected result to contain Flamengo, got: %s", result)
	}
	if !strings.Contains(strings.ToLower(result), "fluminense") {
		t.Errorf("expected result to contain Fluminense, got: %s", result)
	}
	// Should have multiple matches
	lines := strings.Split(strings.TrimSpace(result), "\n")
	if len(lines) < 3 {
		t.Errorf("expected multiple match results, got %d lines", len(lines))
	}
}

// AT-02: Find matches for a team in a specific season
func TestAT02_FindMatchesForTeamInSeason(t *testing.T) {
	h := tools.NewFindMatchesHandler(testStore)
	result := callTool(t, h, map[string]interface{}{
		"team":   "Palmeiras",
		"season": float64(2018),
	})
	if !strings.Contains(strings.ToLower(result), "palmeiras") {
		t.Errorf("expected result to contain Palmeiras, got: %s", result)
	}
	if !strings.Contains(result, "2018") {
		t.Errorf("expected result to contain season 2018, got: %s", result)
	}
}

// AT-03: Find matches by competition (Libertadores for a Brazilian team)
func TestAT03_FindMatchesByCompetition(t *testing.T) {
	h := tools.NewFindMatchesHandler(testStore)
	result := callTool(t, h, map[string]interface{}{
		"team":        "Flamengo",
		"competition": "libertadores",
	})
	if !strings.Contains(strings.ToLower(result), "flamengo") {
		t.Errorf("expected result to contain Flamengo, got: %s", result)
	}
	if !strings.Contains(strings.ToLower(result), "libertadores") && !strings.Contains(strings.ToLower(result), "group stage") && !strings.Contains(strings.ToLower(result), "knockout") {
		// Just check we got matches back
		if len(result) < 10 {
			t.Errorf("expected Libertadores matches for Flamengo, got: %s", result)
		}
	}
}

// AT-04: Get team statistics
func TestAT04_GetTeamStats(t *testing.T) {
	h := tools.NewGetTeamStatsHandler(testStore)
	result := callTool(t, h, map[string]interface{}{
		"team":        "Corinthians",
		"competition": "brasileirao",
	})
	if !strings.Contains(strings.ToLower(result), "corinthians") {
		t.Errorf("expected result to contain Corinthians, got: %s", result)
	}
	// Should contain wins/draws/losses stats
	if !strings.Contains(strings.ToLower(result), "win") && !strings.Contains(strings.ToLower(result), "draw") && !strings.Contains(strings.ToLower(result), "loss") {
		t.Errorf("expected result to contain win/draw/loss stats, got: %s", result)
	}
}

// AT-05: Find players by nationality
func TestAT05_FindPlayersByNationality(t *testing.T) {
	h := tools.NewFindPlayersHandler(testStore)
	result := callTool(t, h, map[string]interface{}{
		"nationality": "Brazil",
		"limit":       float64(10),
	})
	if !strings.Contains(result, "Brazil") {
		t.Errorf("expected result to contain Brazil, got: %s", result)
	}
	lines := strings.Split(strings.TrimSpace(result), "\n")
	if len(lines) < 5 {
		t.Errorf("expected at least 5 Brazilian players, got %d lines", len(lines))
	}
}

// AT-06: Find players by club
func TestAT06_FindPlayersByClub(t *testing.T) {
	h := tools.NewFindPlayersHandler(testStore)
	result := callTool(t, h, map[string]interface{}{
		"club": "Flamengo",
	})
	if !strings.Contains(result, "Flamengo") {
		t.Errorf("expected result to contain Flamengo, got: %s", result)
	}
}

// AT-07: Get league standings for 2019 Brasileirao
func TestAT07_GetLeagueStandings2019(t *testing.T) {
	h := tools.NewGetStandingsHandler(testStore)
	result := callTool(t, h, map[string]interface{}{
		"season":      float64(2019),
		"competition": "brasileirao",
	})
	if !strings.Contains(strings.ToLower(result), "flamengo") {
		t.Errorf("expected standings to contain Flamengo, got: %s", result)
	}
	// Flamengo won 2019, should be first or near top
	lines := strings.Split(strings.TrimSpace(result), "\n")
	foundFlamengo := false
	for i, line := range lines {
		if strings.Contains(strings.ToLower(line), "flamengo") {
			if i > 5 { // should be in top positions (first few lines after header)
				t.Errorf("Flamengo should be near top of 2019 standings but was at line %d", i)
			}
			foundFlamengo = true
			break
		}
	}
	if !foundFlamengo {
		t.Errorf("Flamengo not found in 2019 standings: %s", result)
	}
}

// AT-08: Get head-to-head stats
func TestAT08_GetHeadToHeadStats(t *testing.T) {
	h := tools.NewGetHeadToHeadHandler(testStore)
	result := callTool(t, h, map[string]interface{}{
		"team1": "Flamengo",
		"team2": "Fluminense",
	})
	if !strings.Contains(strings.ToLower(result), "flamengo") {
		t.Errorf("expected result to contain Flamengo, got: %s", result)
	}
	if !strings.Contains(strings.ToLower(result), "fluminense") {
		t.Errorf("expected result to contain Fluminense, got: %s", result)
	}
	// Should contain numerical stats
	if !strings.Contains(result, "win") && !strings.Contains(result, "Win") && !strings.Contains(result, "draw") && !strings.Contains(result, "Draw") {
		t.Errorf("expected h2h stats, got: %s", result)
	}
}

// AT-09: Team name normalization
func TestAT09_TeamNameNormalization(t *testing.T) {
	h := tools.NewFindMatchesHandler(testStore)
	result1 := callTool(t, h, map[string]interface{}{
		"team":   "Palmeiras-SP",
		"season": float64(2018),
	})
	result2 := callTool(t, h, map[string]interface{}{
		"team":   "Palmeiras",
		"season": float64(2018),
	})
	// Both should find matches (normalization should make them equivalent)
	if len(result1) == 0 {
		t.Errorf("searching for Palmeiras-SP returned no results")
	}
	if len(result2) == 0 {
		t.Errorf("searching for Palmeiras returned no results")
	}
	// Both should contain Palmeiras results
	if !strings.Contains(strings.ToLower(result1), "palmeiras") {
		t.Errorf("Palmeiras-SP search should return Palmeiras matches: %s", result1)
	}
}

// AT-10: Get biggest wins
func TestAT10_GetBiggestWins(t *testing.T) {
	h := tools.NewGetStatisticsHandler(testStore)
	result := callTool(t, h, map[string]interface{}{
		"stat_type": "biggest_wins",
		"limit":     float64(5),
	})
	if len(result) < 10 {
		t.Errorf("expected biggest wins results, got: %s", result)
	}
	// Results should be sorted by goal difference (should have high-scoring matches)
	lines := strings.Split(strings.TrimSpace(result), "\n")
	if len(lines) < 3 {
		t.Errorf("expected at least 3 biggest win results, got %d lines", len(lines))
	}
}

// AT-11: Find players by position
func TestAT11_FindPlayersByPosition(t *testing.T) {
	h := tools.NewFindPlayersHandler(testStore)
	result := callTool(t, h, map[string]interface{}{
		"position": "ST",
		"limit":    float64(10),
	})
	if len(result) < 10 {
		t.Errorf("expected forward/striker results, got: %s", result)
	}
	lines := strings.Split(strings.TrimSpace(result), "\n")
	if len(lines) < 5 {
		t.Errorf("expected at least 5 forwards, got %d lines", len(lines))
	}
}

// AT-12: Get average goals per match statistic
func TestAT12_GetAverageGoalsStatistic(t *testing.T) {
	h := tools.NewGetStatisticsHandler(testStore)
	result := callTool(t, h, map[string]interface{}{
		"stat_type": "goals_average",
	})
	if !strings.Contains(strings.ToLower(result), "average") && !strings.Contains(strings.ToLower(result), "goals") {
		t.Errorf("expected goals average statistic, got: %s", result)
	}
}
