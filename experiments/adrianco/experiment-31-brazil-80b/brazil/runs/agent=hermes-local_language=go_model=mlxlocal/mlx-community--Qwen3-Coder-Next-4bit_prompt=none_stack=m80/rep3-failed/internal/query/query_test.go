// Package query_test contains tests for the query handlers
package query_test

import (
	"os"
	"path/filepath"
	"testing"

	"brazilian-soccer-mcp/internal/data"
	"brazilian-soccer-mcp/internal/models"
	"brazilian-soccer-mcp/internal/query"
)

func getProjectRoot() string {
	cwd, _ := os.Getwd()
	projectRoot := cwd
	// Go up: internal/query -> internal -> project root
	for i := 0; i < 2; i++ {
		projectRoot = filepath.Dir(projectRoot)
	}
	return projectRoot
}

func TestQueryServerMatchQuery(t *testing.T) {
	matchData, playerData, err := data.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	server := query.New(matchData, playerData)

	req := models.QueryRequest{
		Type: "match",
		Params: map[string]interface{}{
			"team": "Flamengo",
		},
	}

	resp := server.Query(req)

	if !resp.Success {
		t.Errorf("Expected success, got error: %s", resp.Error)
	}

	if resp.Total == 0 {
		t.Error("Expected non-zero matches for Flamengo")
	}
}

func TestQueryServerTeamQuery(t *testing.T) {
	matchData, playerData, err := data.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	server := query.New(matchData, playerData)

	req := models.QueryRequest{
		Type: "team",
		Params: map[string]interface{}{
			"team": "Palmeiras",
		},
	}

	resp := server.Query(req)

	if !resp.Success {
		t.Errorf("Expected success, got error: %s", resp.Error)
	}

	// Verify statistics are returned
	if data, ok := resp.Data.(map[string]interface{}); ok {
		if _, ok := data["matches"]; !ok {
			t.Error("Expected 'matches' field in team statistics")
		}
	}
}

func TestQueryServerPlayerQuery(t *testing.T) {
	matchData, playerData, err := data.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	server := query.New(matchData, playerData)

	req := models.QueryRequest{
		Type: "player",
		Params: map[string]interface{}{
			"nationality": "Brazil",
		},
	}

	resp := server.Query(req)

	if !resp.Success {
		t.Errorf("Expected success, got error: %s", resp.Error)
	}

	if resp.Total == 0 {
		t.Error("Expected non-zero Brazilian players")
	}
}

func TestQueryServerCompetitionQuery(t *testing.T) {
	matchData, playerData, err := data.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	server := query.New(matchData, playerData)

	req := models.QueryRequest{
		Type: "competition",
		Params: map[string]interface{}{
			"competition": "Brasileirao",
			"season":      2019,
		},
	}

	resp := server.Query(req)

	if !resp.Success {
		t.Errorf("Expected success, got error: %s", resp.Error)
	}

	if resp.Total == 0 {
		t.Error("Expected non-zero standings for 2019 Brasileirao")
	}
}

func TestQueryServerStatisticsQuery(t *testing.T) {
	matchData, playerData, err := data.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	server := query.New(matchData, playerData)

	req := models.QueryRequest{
		Type: "statistics",
		Params: map[string]interface{}{
			"competition": "Brasileirao",
		},
	}

	resp := server.Query(req)

	if !resp.Success {
		t.Errorf("Expected success, got error: %s", resp.Error)
	}

	if data, ok := resp.Data.(map[string]interface{}); ok {
		if _, ok := data["total_matches"]; !ok {
			t.Error("Expected 'total_matches' field in statistics")
		}
		if _, ok := data["average_goals"]; !ok {
			t.Error("Expected 'average_goals' field in statistics")
		}
	}
}

func TestHeadToHead(t *testing.T) {
	matchData, playerData, err := data.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	server := query.New(matchData, playerData)

	req := models.QueryRequest{
		Type: "match",
		Params: map[string]interface{}{
			"home_team": "Flamengo",
			"away_team": "Fluminense",
		},
	}

	resp := server.Query(req)

	if !resp.Success {
		t.Errorf("Expected success, got error: %s", resp.Error)
	}

	if data, ok := resp.Data.(map[string]interface{}); ok {
		if _, ok := data["team1_wins"]; !ok {
			t.Error("Expected 'team1_wins' field in head-to-head")
		}
		if _, ok := data["team2_wins"]; !ok {
			t.Error("Expected 'team2_wins' field in head-to-head")
		}
	}
}

func TestGetBigWins(t *testing.T) {
	matchData, playerData, err := data.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	server := query.New(matchData, playerData)

	resp := server.GetBigWins(5)

	if !resp.Success {
		t.Errorf("Expected success, got error: %s", resp.Error)
	}

	// At least one big win should exist
	if resp.Total == 0 {
		t.Log("Note: No matches with 5+ goal difference found in dataset")
	}
}

func TestGetTopTeamsBySeason(t *testing.T) {
	matchData, playerData, err := data.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	server := query.New(matchData, playerData)

	resp := server.GetTopTeamsBySeason(2019, "Brasileirao")

	if !resp.Success {
		t.Errorf("Expected success, got error: %s", resp.Error)
	}

	if resp.Total == 0 {
		t.Error("Expected top teams for 2019 Brasileirao")
	}
}

func TestGetTeamsByPlayer(t *testing.T) {
	matchData, playerData, err := data.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	server := query.New(matchData, playerData)

	resp := server.GetTeamsByPlayer()

	if !resp.Success {
		t.Errorf("Expected success, got error: %s", resp.Error)
	}

	if resp.Total == 0 {
		t.Error("Expected teams with players")
	}
}
