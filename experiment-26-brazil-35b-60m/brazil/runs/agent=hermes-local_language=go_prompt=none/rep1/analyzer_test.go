package main

import (
	"fmt"
	"strings"
	"testing"
)

func TestNormalizeTeamName(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"Corinthians-SP", "Corinthians"},
		{"Sao Paulo-SP", "Sao Paulo"},
		{"Atletico-MG", "Atletico-MG"},
		{"Gremio-RS", "Gremio"},
		{"Internacional-RS", "Internacional"},
		{"Sport-PE", "Sport"},
		{"Figueirense-SC", "Figueirense"},
	}

	for _, tt := range tests {
		result := NormalizeTeamName(tt.input)
		if result != tt.expected {
			t.Errorf("NormalizeTeamName(%q) = %q, want %q", tt.input, result, tt.expected)
		}
	}
}

func TestNormalizeName(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"S\u00e3o Paulo", "sao paulo"},
		{"Grimio", "gremio"},
		{"Ava\u00ed", "avai"},
		{"Cear\u00e1", "ceara"},
		{"Palmeiras", "palmeiras"},
	}

	for _, tt := range tests {
		result := NormalizeName(tt.input)
		if result != tt.expected {
			t.Errorf("NormalizeName(%q) = %q, want %q", tt.input, result, tt.expected)
		}
	}
}

func TestSimilarName(t *testing.T) {
	tests := []struct {
		a, b     string
		expected bool
	}{
		{"Palmeiras-SP", "Palmeiras", true},
		{"Flamengo-RJ", "Flamengo", true},
		{"Palmeiras", "Corinthians", false},
		{"S\u00e3o Paulo", "Sao Paulo", true},
	}

	for _, tt := range tests {
		result := SimilarName(tt.a, tt.b)
		if result != tt.expected {
			t.Errorf("SimilarName(%q, %q) = %v, want %v", tt.a, tt.b, result, tt.expected)
		}
	}
}

func TestExtractDate(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"2023-09-03 18:30:00", "2023-09-03"},
		{"2023-09-03", "2023-09-03"},
		{"29/03/2003", "29/03/2003"},
		{"", ""},
	}

	for _, tt := range tests {
		result := ExtractDate(tt.input)
		if result != tt.expected {
			t.Errorf("ExtractDate(%q) = %q, want %q", tt.input, result, tt.expected)
		}
	}
}

func TestParseInt(t *testing.T) {
	if parseInt("42") != 42 {
		t.Errorf("parseInt(\"42\") = %d, want 42", parseInt("42"))
	}
	if parseInt("") != 0 {
		t.Errorf("parseInt(\"\") = %d, want 0", parseInt(""))
	}
	if parseInt("abc") != 0 {
		t.Errorf("parseInt(\"abc\") = %d, want 0", parseInt("abc"))
	}
	if parseInt(" 10 ") != 10 {
		t.Errorf("parseInt(\" 10 \") = %d, want 10", parseInt(" 10 "))
	}
}

func TestParseFloat(t *testing.T) {
	if parseFloat("1.5") != 1.5 {
		t.Errorf("parseFloat(\"1.5\") = %f, want 1.5", parseFloat("1.5"))
	}
	if parseFloat("") != 0 {
		t.Errorf("parseFloat(\"\") = %f, want 0", parseFloat(""))
	}
	if parseFloat("abc") != 0 {
		t.Errorf("parseFloat(\"abc\") = %f, want 0", parseFloat("abc"))
	}
	if parseFloat("2.0") != 2.0 {
		t.Errorf("parseFloat(\"2.0\") = %f, want 2.0", parseFloat("2.0"))
	}
}

func TestNewDataStore(t *testing.T) {
	store := NewDataStore()
	if store == nil {
		t.Error("NewDataStore() returned nil")
	}
}

func TestParseIntOrFloat(t *testing.T) {
	if parseIntOrFloat("42") != 42 {
		t.Errorf("parseIntOrFloat(\"42\") = %d, want 42", parseIntOrFloat("42"))
	}
	if parseIntOrFloat("3.7") != 3 {
		t.Errorf("parseIntOrFloat(\"3.7\") = %d, want 3", parseIntOrFloat("3.7"))
	}
}

func TestSearchMatchesByTeam(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	results := analyzer.SearchMatchesByTeam("Palmeiras")
	if len(results) == 0 {
		t.Error("SearchMatchesByTeam(\"Palmeiras\") returned no results")
	}

	for _, r := range results {
		if !SimilarName(r.HomeTeam, "Palmeiras") && !SimilarName(r.AwayTeam, "Palmeiras") {
			t.Errorf("Result contains unexpected team: %s vs %s", r.HomeTeam, r.AwayTeam)
		}
	}
}

func TestSearchMatchesBetweenTeams(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	results := analyzer.SearchMatchesByTeams("Palmeiras", "Corinthians")
	t.Logf("Palmeiras vs Corinthians: %d matches found", len(results))
}

func TestGetTeamStats(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	stats := analyzer.GetTeamStats("Palmeiras", "", "")
	if stats == nil {
		t.Fatal("GetTeamStats returned nil")
	}
	if stats.Matches == 0 {
		t.Error("GetTeamStats for Palmeiras returned 0 matches")
	}

	if stats.Wins+stats.Draws+stats.Losses != stats.Matches {
		t.Errorf("Wins(%d) + Draws(%d) + Losses(%d) = %d, want Matches(%d)",
			stats.Wins, stats.Draws, stats.Losses, stats.Wins+stats.Draws+stats.Losses, stats.Matches)
	}

	if stats.GoalsFor < 0 {
		t.Error("GoalsFor is negative")
	}
	if stats.GoalsAgainst < 0 {
		t.Error("GoalsAgainst is negative")
	}
}

func TestHeadToHead(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	h2h := analyzer.GetHeadToHead("Palmeiras", "Corinthians")
	if h2h == nil {
		t.Fatal("GetHeadToHead returned nil")
	}
	if h2h.Team1 != "Palmeiras" || h2h.Team2 != "Corinthians" {
		t.Errorf("Wrong teams: %s vs %s", h2h.Team1, h2h.Team2)
	}

	if h2h.Team1Wins+h2h.Team2Wins+h2h.Draws != h2h.TotalMatches {
		t.Errorf("Team1Wins(%d) + Team2Wins(%d) + Draws(%d) = %d, want Total(%d)",
			h2h.Team1Wins, h2h.Team2Wins, h2h.Draws,
			h2h.Team1Wins+h2h.Team2Wins+h2h.Draws, h2h.TotalMatches)
	}
}

func TestSearchPlayersByName(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	results := analyzer.SearchPlayersByName("Neymar")
	if len(results) == 0 {
		t.Error("SearchPlayersByName(\"Neymar\") returned no results")
	} else {
		t.Logf("Found %d Neymar players", len(results))
	}

	results2 := analyzer.SearchPlayersByName("Pe")
	if len(results2) == 0 {
		t.Error("SearchPlayersByName(\"Pe\") returned no results")
	}
}

func TestGetPlayersByClub(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	results := analyzer.GetPlayersByClub("Flamengo")
	t.Logf("Flamengo has %d players in FIFA dataset", len(results))

	for _, p := range results {
		if len(p.Club) > 0 && !ContainsIgnoreCase(p.Club, "flamengo") {
			t.Errorf("Player %s at club %q doesn't match", p.Name, p.Club)
		}
	}
}

func TestGetBrazilianPlayers(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	results := analyzer.GetBrazilianPlayers(100)
	if len(results) == 0 {
		t.Error("GetBrazilianPlayers returned no results")
	}

	for i := 0; i < len(results)-1; i++ {
		if results[i].Overall < results[i+1].Overall {
			t.Errorf("Results not sorted: %s(%d) < %s(%d)",
				results[i].Name, results[i].Overall,
				results[i+1].Name, results[i+1].Overall)
			break
		}
	}
}

func TestGetPlayersByNationality(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	results := analyzer.GetPlayersByNationality("Argentina")
	if len(results) == 0 {
		t.Error("GetPlayersByNationality(\"Argentina\") returned no results")
	}

	foundArgentine := false
	for _, p := range results {
		if ContainsIgnoreCase(p.Nationality, "argentina") {
			foundArgentine = true
			break
		}
	}
	if !foundArgentine {
		t.Error("No Argentine players found in results")
	}
}

func TestGetTopPlayersByPosition(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	results := analyzer.GetTopPlayersByPosition("FW", 10)
	t.Logf("Found %d FW players", len(results))

	results2 := analyzer.GetTopPlayersByPosition("GK", 10)
	t.Logf("Found %d GK players", len(results2))

	if len(results) == 0 && len(results2) == 0 {
		t.Error("No results found for either position")
	}
}

func TestGetBiggestWins(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	results := analyzer.GetBiggestWins(20)
	if len(results) == 0 {
		t.Error("GetBiggestWins returned no results")
	}

	for i := 0; i < len(results)-1; i++ {
		if results[i].Margin < results[i+1].Margin {
			t.Errorf("Results not sorted: margin %d < %d at index %d",
				results[i].Margin, results[i+1].Margin, i)
			break
		}
	}

	for _, w := range results {
		if w.Margin < 4 {
			t.Errorf("BigWin with margin %d found (should be >= 4)", w.Margin)
		}
	}
}

func TestGetAverageGoals(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	stats := analyzer.GetAverageGoals("")
	if stats == nil {
		t.Fatal("GetAverageGoals returned nil")
	}
	if stats.TotalMatches == 0 {
		t.Error("GetAverageGoals returned 0 total matches")
	}
	if stats.AvgGoalsPerMatch <= 0 {
		t.Errorf("GetAverageGoals returned avg goals per match: %f", stats.AvgGoalsPerMatch)
	}

	t.Logf("Average goals per match: %.2f, Home win rate: %.1f%%, Total matches: %d",
		stats.AvgGoalsPerMatch, stats.HomeWinRate, stats.TotalMatches)
}

func TestGetStatsByCompetition(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	stats := analyzer.GetStatsByCompetitionKeys()
	if len(stats) == 0 {
		t.Error("GetStatsByCompetition returned no results")
	}

	for comp, s := range stats {
		t.Logf("%s: %d matches, %.2f avg goals, %.1f%% home win rate",
			comp, s.TotalMatches, s.AvgGoalsPerMatch, s.HomeWinRate)
	}
}

func TestGetCompetitionStandings(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	standings := analyzer.GetCompetitionStandings("Brasileirao", "")
	if len(standings) == 0 {
		t.Error("GetCompetitionStandings returned no results")
	}

	for i := 0; i < len(standings)-1; i++ {
		if standings[i].Points < standings[i+1].Points {
			t.Errorf("Standings not sorted: %s(%d) < %s(%d)",
				standings[i].Team, standings[i].Points,
				standings[i+1].Team, standings[i+1].Points)
			break
		}
	}

	if len(standings) > 0 {
		t.Logf("Top team in standings: %s with %d points", standings[0].Team, standings[0].Points)
	}
}

func TestGetClubPlayersSummary(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	summaries := analyzer.GetClubPlayersSummary()
	t.Logf("Found %d clubs with Brazilian players", len(summaries))

	for i := 0; i < len(summaries)-1; i++ {
		if summaries[i].PlayerCount < summaries[i+1].PlayerCount {
			t.Errorf("Not sorted: %s(%d) < %s(%d)",
				summaries[i].Club, summaries[i].PlayerCount,
				summaries[i+1].Club, summaries[i+1].PlayerCount)
			break
		}
	}
}

func TestGetDataSummaryTool(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)

	handler := BuildMCPToolHandlers(analyzer, store)["get_data_summary"]
	result, err := handler(nil)
	if err != nil {
		t.Fatalf("get_data_summary returned error: %v", err)
	}

	r, ok := result.(map[string]interface{})
	if !ok {
		t.Fatalf("get_data_summary returned non-map result: %T", result)
	}

	datasets, ok := r["datasets"].(map[string]interface{})
	if !ok {
		t.Fatal("datasets not found in result")
	}

	for name, val := range datasets {
		t.Logf("Dataset: %s = %v", name, val)
	}

	if datasets["brasileirao_matches"].(int) == 0 {
		t.Error("No Brasileirao matches loaded")
	}
	if datasets["fifa_players"].(int) == 0 {
		t.Error("No FIFA players loaded")
	}
}

func TestMCPToolsRegistration(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	tools := BuildMCPTools(analyzer, store)
	handlers := BuildMCPToolHandlers(analyzer, store)

	if len(tools) == 0 {
		t.Error("No MCP tools registered")
	}

	if len(handlers) != len(tools) {
		t.Errorf("Tool count mismatch: %d tools, %d handlers", len(tools), len(handlers))
	}

	for _, tool := range tools {
		if _, ok := handlers[tool.Name]; !ok {
			t.Errorf("No handler for tool: %s", tool.Name)
		}
	}

	t.Logf("Registered %d MCP tools", len(tools))
}

func TestMCPToolGetTeamStats(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	handlers := BuildMCPToolHandlers(analyzer, store)

	handler := handlers["get_team_stats"]
	result, err := handler(map[string]interface{}{
		"team": "Palmeiras",
	})
	if err != nil {
		t.Fatalf("get_team_stats returned error: %v", err)
	}

	r, ok := result.(map[string]interface{})
	if !ok {
		t.Fatalf("get_team_stats returned non-map: %T", result)
	}

	if r["matches"].(int) == 0 {
		t.Error("Palmeiras has 0 matches")
	}

	t.Logf("Palmeiras stats: %+v", r)
}

func TestMCPToolSearchPlayersByName(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	handlers := BuildMCPToolHandlers(analyzer, store)

	handler := handlers["search_players_by_name"]
	result, err := handler(map[string]interface{}{
		"name":  "Neymar",
		"limit": 5,
	})
	if err != nil {
		t.Fatalf("search_players_by_name returned error: %v", err)
	}

	r, ok := result.(map[string]interface{})
	if !ok {
		t.Fatalf("search_players_by_name returned non-map: %T", result)
	}

	count := r["count"].(int)
	t.Logf("Search for Neymar: %d results", count)
}

func TestMCPToolSearchMatchesByTeam(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	handlers := BuildMCPToolHandlers(analyzer, store)

	handler := handlers["search_matches_by_team"]
	result, err := handler(map[string]interface{}{
		"team": "Flamengo",
	})
	if err != nil {
		t.Fatalf("search_matches_by_team returned error: %v", err)
	}

	r, ok := result.(map[string]interface{})
	if !ok {
		t.Fatalf("search_matches_by_team returned non-map: %T", result)
	}

	total := r["total_matches"].(int)
	t.Logf("Flamengo matches found: %d", total)
}

func TestMCPToolGetHeadToHead(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	handlers := BuildMCPToolHandlers(analyzer, store)

	handler := handlers["get_head_to_head"]
	result, err := handler(map[string]interface{}{
		"team1": "Palmeiras",
		"team2": "Corinthians",
	})
	if err != nil {
		t.Fatalf("get_head_to_head returned error: %v", err)
	}

	r, ok := result.(map[string]interface{})
	if !ok {
		t.Fatalf("get_head_to_head returned non-map: %T", result)
	}

	t.Logf("H2H result: %+v", r)
}

func TestMCPToolGetBiggestWins(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	handlers := BuildMCPToolHandlers(analyzer, store)

	handler := handlers["get_biggest_wins"]
	result, err := handler(map[string]interface{}{
		"limit": 10,
	})
	if err != nil {
		t.Fatalf("get_biggest_wins returned error: %v", err)
	}

	r, ok := result.(map[string]interface{})
	if !ok {
		t.Fatalf("get_biggest_wins returned non-map: %T", result)
	}

	wins := r["wins"].([]BigWin)
	t.Logf("Found %d big wins", len(wins))

	for _, w := range wins {
		t.Logf("%s %d-%d %s (%s)", w.HomeTeam, w.HomeScore, w.AwayScore, w.AwayTeam, w.Competition)
	}
}

func TestMCPToolGetStatsByCompetition(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	handlers := BuildMCPToolHandlers(analyzer, store)

	handler := handlers["get_stats_by_competition"]
	result, err := handler(nil)
	if err != nil {
		t.Fatalf("get_stats_by_competition returned error: %v", err)
	}

	r, ok := result.(map[string]interface{})
	if !ok {
		t.Fatalf("get_stats_by_competition returned non-map: %T", result)
	}

	for comp, stats := range r {
		t.Logf("%s: %+v", comp, stats)
	}
}

func TestMCPToolGetPlayersByClub(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	handlers := BuildMCPToolHandlers(analyzer, store)

	handler := handlers["get_players_by_club"]
	result, err := handler(map[string]interface{}{
		"club":  "Flamengo",
		"limit": 20,
	})
	if err != nil {
		t.Fatalf("get_players_by_club returned error: %v", err)
	}

	r, ok := result.(map[string]interface{})
	if !ok {
		t.Fatalf("get_players_by_club returned non-map: %T", result)
	}

	count := r["count"].(int)
	players := r["players"].([]PlayerResult)
	t.Logf("Flamengo: %d players found", count)
	for _, p := range players {
		t.Logf("  %s - %s (%d) at %s", p.Name, p.Position, p.Overall, p.Club)
	}
}

func TestMCPToolGetBrazilianPlayers(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	handlers := BuildMCPToolHandlers(analyzer, store)

	handler := handlers["get_brazilian_players"]
	result, err := handler(map[string]interface{}{
		"limit": 20,
	})
	if err != nil {
		t.Fatalf("get_brazilian_players returned error: %v", err)
	}

	r, ok := result.(map[string]interface{})
	if !ok {
		t.Fatalf("get_brazilian_players returned non-map: %T", result)
	}

	count := r["count"].(int)
	players := r["players"].([]PlayerResult)
	t.Logf("Found %d Brazilian players", count)
	for _, p := range players {
		t.Logf("  %s - %d overall, %s at %s", p.Name, p.Overall, p.Nationality, p.Club)
	}
}

func TestBDDFindMatchesBetweenTwoTeams(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	matches := analyzer.SearchMatchesByTeams("Flamengo", "Fluminense")

	for _, m := range matches {
		if m.Date == "" {
			t.Error("Match has empty date")
		}
		if m.HomeTeam == "" || m.AwayTeam == "" {
			t.Error("Match has empty team names")
		}
		if m.Competition == "" {
			t.Error("Match has empty competition")
		}
		t.Logf("  %s: %s %d-%d %s (%s)", m.Date, m.HomeTeam, m.HomeScore, m.AwayScore, m.AwayTeam, m.Competition)
	}

	t.Logf("Total Flamengo vs Fluminense matches: %d", len(matches))
}

func TestBDDGetTeamStatistics(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	stats := analyzer.GetTeamStats("Palmeiras", "", "")

	if stats.Wins+stats.Draws+stats.Losses == 0 {
		t.Error("Team has no matches")
	}

	if stats.GoalsFor < 0 || stats.GoalsAgainst < 0 {
		t.Error("Invalid goal counts")
	}

	t.Logf("Palmeiras stats: %d matches, %dW %dD %dL, %d:%d goals, %.1f%% win rate",
		stats.Matches, stats.Wins, stats.Draws, stats.Losses,
		stats.GoalsFor, stats.GoalsAgainst, stats.WinRate)
}

func TestMCPToolSearchMatchesByTeamWithCompetitionFilter(t *testing.T) {
	store := NewDataStore()
	if err := store.LoadAll("data/kaggle"); err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	analyzer := NewQueryAnalyzer(store)
	handlers := BuildMCPToolHandlers(analyzer, store)

	handler := handlers["search_matches_by_team"]
	result, err := handler(map[string]interface{}{
		"team":        "Palmeiras",
		"competition": "Brasileirao",
	})
	if err != nil {
		t.Fatalf("search_matches_by_team with filter returned error: %v", err)
	}

	r, ok := result.(map[string]interface{})
	if !ok {
		t.Fatalf("search_matches_by_team returned non-map: %T", result)
	}

	matches := r["matches"].([]MatchResult)
	t.Logf("Palmeiras Brasileirao matches: %d", len(matches))

	for _, m := range matches {
		if m.Competition != "Brasileirao" {
			t.Errorf("Unexpected competition: %s", m.Competition)
		}
	}
}

func TestTeamNameVariations(t *testing.T) {
	tests := []struct {
		name1 string
		name2 string
		want  bool
	}{
		{"Palmeiras-SP", "Palmeiras", true},
		{"Flamengo-RJ", "Flamengo", true},
		{"Sao Paulo-SP", "Sao Paulo", true},
		{"Corinthians-SP", "Corinthians", true},
		{"Gremio-RS", "Gremio", true},
		{"Internacional-RS", "Internacional", true},
	}

	for _, tt := range tests {
		got := SimilarName(tt.name1, tt.name2)
		if got != tt.want {
			t.Errorf("SimilarName(%q, %q) = %v, want %v", tt.name1, tt.name2, got, tt.want)
		}
	}
}

func TestContainsIgnoreCase(t *testing.T) {
	if !ContainsIgnoreCase("Flamengo", "fla") {
		t.Error("ContainsIgnoreCase should be case-insensitive")
	}
	if ContainsIgnoreCase("Flamengo", "xyz") {
		t.Error("ContainsIgnoreCase should return false for non-match")
	}
	if ContainsIgnoreCase("", "test") {
		t.Error("ContainsIgnoreCase should return false for empty string")
	}
}

// ContainsIgnoreCase checks if s contains substr case-insensitively
func ContainsIgnoreCase(s, substr string) bool {
	return strings.Contains(strings.ToLower(s), strings.ToLower(substr))
}
