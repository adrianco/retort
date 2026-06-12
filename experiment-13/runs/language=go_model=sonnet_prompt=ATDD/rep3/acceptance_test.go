package main_test

import (
	"context"
	"encoding/json"
	"strings"
	"testing"

	"brazilian-soccer-mcp/internal/server"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/mcptest"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupTestServer(t *testing.T) *mcptest.Server {
	t.Helper()
	tools, err := server.RegisterTools("./data/kaggle/")
	require.NoError(t, err, "RegisterTools should not fail")
	srv, err := mcptest.NewServer(t, tools...)
	require.NoError(t, err, "mcptest.NewServer should not fail")
	t.Cleanup(func() { srv.Close() })
	return srv
}

func callTool(t *testing.T, srv *mcptest.Server, toolName string, args map[string]any) string {
	t.Helper()
	ctx := context.Background()
	var req mcp.CallToolRequest
	req.Params.Name = toolName
	req.Params.Arguments = args
	result, err := srv.Client().CallTool(ctx, req)
	require.NoError(t, err, "CallTool %q should not fail", toolName)
	require.False(t, result.IsError, "CallTool %q should not return an error result", toolName)
	var sb strings.Builder
	for _, content := range result.Content {
		if tc, ok := content.(mcp.TextContent); ok {
			sb.WriteString(tc.Text)
		}
	}
	return sb.String()
}

func TestFindMatchesByBothTeams(t *testing.T) {
	srv := setupTestServer(t)

	// Find all matches involving Flamengo
	resp := callTool(t, srv, "find_matches", map[string]any{
		"team": "Flamengo",
	})

	var result map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(resp), &result))

	total, _ := result["total"].(float64)
	assert.Greater(t, int(total), 0, "should find matches for Flamengo")

	// Also test head-to-head
	h2hResp := callTool(t, srv, "get_head_to_head", map[string]any{
		"team1": "Flamengo",
		"team2": "Fluminense",
	})
	var h2h map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(h2hResp), &h2h))
	assert.Equal(t, "Flamengo", h2h["team1"])
	assert.Equal(t, "Fluminense", h2h["team2"])
	totalH2H, _ := h2h["total"].(float64)
	assert.GreaterOrEqual(t, int(totalH2H), 0, "head to head should have a total")
}

func TestFindMatchesByTeamAndSeason(t *testing.T) {
	srv := setupTestServer(t)

	resp := callTool(t, srv, "find_matches", map[string]any{
		"team":   "Palmeiras",
		"season": float64(2023),
	})

	var result map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(resp), &result))

	total, _ := result["total"].(float64)
	assert.Greater(t, int(total), 0, "should find Palmeiras matches in 2023")

	// Verify all matches are from season 2023 and involve Palmeiras
	matches, _ := result["matches"].([]interface{})
	for _, m := range matches {
		match, _ := m.(map[string]interface{})
		season, _ := match["season"].(float64)
		assert.Equal(t, float64(2023), season, "all matches should be from season 2023")
		homeTeam, _ := match["home_team"].(string)
		awayTeam, _ := match["away_team"].(string)
		hasPalmeiras := strings.Contains(strings.ToLower(homeTeam), "palmeiras") ||
			strings.Contains(strings.ToLower(awayTeam), "palmeiras")
		assert.True(t, hasPalmeiras, "match should involve Palmeiras: %s vs %s", homeTeam, awayTeam)
	}
}

func TestFindCupMatches(t *testing.T) {
	srv := setupTestServer(t)

	resp := callTool(t, srv, "find_matches", map[string]any{
		"competition": "copa",
	})

	var result map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(resp), &result))

	total, _ := result["total"].(float64)
	assert.Greater(t, int(total), 0, "should find Copa do Brasil matches")

	// Verify all returned matches are Cup matches
	matches, _ := result["matches"].([]interface{})
	require.Greater(t, len(matches), 0, "should have match entries")
	for _, m := range matches {
		match, _ := m.(map[string]interface{})
		competition, _ := match["competition"].(string)
		isCup := strings.Contains(strings.ToLower(competition), "copa") ||
			strings.Contains(strings.ToLower(competition), "cup") ||
			strings.Contains(strings.ToLower(competition), "brasil")
		assert.True(t, isCup, "competition should be cup-related: %s", competition)
	}
}

func TestGetTeamStats(t *testing.T) {
	srv := setupTestServer(t)

	resp := callTool(t, srv, "get_team_stats", map[string]any{
		"team":   "Corinthians",
		"season": float64(2022),
		"venue":  "home",
	})

	var result map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(resp), &result))

	assert.Equal(t, "Corinthians", result["team"])
	matches, _ := result["matches"].(float64)
	assert.GreaterOrEqual(t, int(matches), 0, "matches should be non-negative")

	// Check required fields exist
	_, hasWins := result["wins"]
	_, hasDraws := result["draws"]
	_, hasLosses := result["losses"]
	_, hasGoalsFor := result["goals_for"]
	_, hasGoalsAgainst := result["goals_against"]
	_, hasGoalDiff := result["goal_diff"]
	_, hasWinRate := result["win_rate"]
	assert.True(t, hasWins, "should have wins field")
	assert.True(t, hasDraws, "should have draws field")
	assert.True(t, hasLosses, "should have losses field")
	assert.True(t, hasGoalsFor, "should have goals_for field")
	assert.True(t, hasGoalsAgainst, "should have goals_against field")
	assert.True(t, hasGoalDiff, "should have goal_diff field")
	assert.True(t, hasWinRate, "should have win_rate field")
}

func TestGetHeadToHead(t *testing.T) {
	srv := setupTestServer(t)

	resp := callTool(t, srv, "get_head_to_head", map[string]any{
		"team1": "Flamengo",
		"team2": "Palmeiras",
	})

	var result map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(resp), &result))

	assert.Equal(t, "Flamengo", result["team1"])
	assert.Equal(t, "Palmeiras", result["team2"])

	_, hasTeam1Wins := result["team1_wins"]
	_, hasTeam2Wins := result["team2_wins"]
	_, hasDraws := result["draws"]
	_, hasMatches := result["matches"]
	assert.True(t, hasTeam1Wins, "should have team1_wins field")
	assert.True(t, hasTeam2Wins, "should have team2_wins field")
	assert.True(t, hasDraws, "should have draws field")
	assert.True(t, hasMatches, "should have matches field")

	// The total should equal sum of wins and draws
	team1Wins, _ := result["team1_wins"].(float64)
	team2Wins, _ := result["team2_wins"].(float64)
	draws, _ := result["draws"].(float64)
	total, _ := result["total"].(float64)
	assert.Equal(t, int(total), int(team1Wins)+int(team2Wins)+int(draws), "total should equal wins+draws")
}

func TestFindBrazilianPlayers(t *testing.T) {
	srv := setupTestServer(t)

	resp := callTool(t, srv, "find_players", map[string]any{
		"nationality": "Brazil",
	})

	var result map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(resp), &result))

	total, _ := result["total"].(float64)
	assert.Greater(t, int(total), 0, "should find Brazilian players")

	players, _ := result["players"].([]interface{})
	require.Greater(t, len(players), 0, "should have player entries")
	for _, p := range players {
		player, _ := p.(map[string]interface{})
		nationality, _ := player["nationality"].(string)
		assert.Equal(t, "Brazil", nationality, "all players should be Brazilian")
	}
}

func TestFindPlayersByClub(t *testing.T) {
	srv := setupTestServer(t)

	resp := callTool(t, srv, "find_players", map[string]any{
		"club":  "Flamengo",
		"limit": float64(5),
	})

	var result map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(resp), &result))

	players, _ := result["players"].([]interface{})
	assert.LessOrEqual(t, len(players), 5, "should return at most 5 players")

	// Verify players belong to Flamengo
	for _, p := range players {
		player, _ := p.(map[string]interface{})
		club, _ := player["club"].(string)
		assert.Contains(t, strings.ToLower(club), "flamengo", "player club should contain 'flamengo'")
	}

	// Verify sorted by overall descending
	if len(players) >= 2 {
		prev := players[0].(map[string]interface{})
		for _, p := range players[1:] {
			curr := p.(map[string]interface{})
			prevOverall, _ := prev["overall"].(float64)
			currOverall, _ := curr["overall"].(float64)
			assert.GreaterOrEqual(t, int(prevOverall), int(currOverall), "players should be sorted by overall descending")
			prev = curr
		}
	}
}

func TestGetStandings(t *testing.T) {
	srv := setupTestServer(t)

	resp := callTool(t, srv, "get_standings", map[string]any{
		"season": float64(2019),
	})

	var result map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(resp), &result))

	season, _ := result["season"].(float64)
	assert.Equal(t, float64(2019), season)

	standings, _ := result["standings"].([]interface{})
	assert.Greater(t, len(standings), 0, "should have standings entries")

	// Verify structure of first entry
	if len(standings) > 0 {
		first, _ := standings[0].(map[string]interface{})
		_, hasRank := first["rank"]
		_, hasTeam := first["team"]
		_, hasPoints := first["points"]
		_, hasMatches := first["matches"]
		assert.True(t, hasRank, "standings entry should have rank")
		assert.True(t, hasTeam, "standings entry should have team")
		assert.True(t, hasPoints, "standings entry should have points")
		assert.True(t, hasMatches, "standings entry should have matches")
	}

	// Verify sorted by points descending
	if len(standings) >= 2 {
		first, _ := standings[0].(map[string]interface{})
		second, _ := standings[1].(map[string]interface{})
		firstPoints, _ := first["points"].(float64)
		secondPoints, _ := second["points"].(float64)
		assert.GreaterOrEqual(t, firstPoints, secondPoints, "standings should be sorted by points descending")
	}
}

func TestBiggestWins(t *testing.T) {
	srv := setupTestServer(t)

	resp := callTool(t, srv, "get_statistics", map[string]any{
		"stat_type": "biggest_wins",
		"limit":     float64(5),
	})

	var result map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(resp), &result))

	assert.Equal(t, "biggest_wins", result["stat_type"])
	results, _ := result["results"].([]interface{})
	assert.LessOrEqual(t, len(results), 5, "should return at most 5 results")
	assert.Greater(t, len(results), 0, "should have biggest win entries")

	// Verify sorted by goal_diff descending
	if len(results) >= 2 {
		first, _ := results[0].(map[string]interface{})
		second, _ := results[1].(map[string]interface{})
		firstDiff, _ := first["goal_diff"].(float64)
		secondDiff, _ := second["goal_diff"].(float64)
		assert.GreaterOrEqual(t, firstDiff, secondDiff, "results should be sorted by goal_diff descending")
	}
}

func TestAvgGoals(t *testing.T) {
	srv := setupTestServer(t)

	resp := callTool(t, srv, "get_statistics", map[string]any{
		"stat_type": "avg_goals",
	})

	var result map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(resp), &result))

	assert.Equal(t, "avg_goals", result["stat_type"])
	results, _ := result["results"].([]interface{})
	assert.Greater(t, len(results), 0, "should have avg_goals entries")

	// Verify each entry has required fields
	for _, r := range results {
		entry, _ := r.(map[string]interface{})
		_, hasComp := entry["competition"]
		_, hasAvg := entry["avg_goals"]
		_, hasMatches := entry["matches"]
		assert.True(t, hasComp, "entry should have competition")
		assert.True(t, hasAvg, "entry should have avg_goals")
		assert.True(t, hasMatches, "entry should have matches")
	}
}
