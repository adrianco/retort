package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthHandler(t *testing.T) {
	// Initialize server
	server = NewSoccerServer()
	
	req := httptest.NewRequest("GET", "/health", nil)
	rec := httptest.NewRecorder()
	healthHandler(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rec.Code)
	}

	var response map[string]interface{}
	if err := json.NewDecoder(rec.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if response["status"] != "ok" {
		t.Errorf("Expected status 'ok', got '%v'", response["status"])
	}
}

func TestTeamStatsHandler(t *testing.T) {
	// Initialize server with test data
	server = NewSoccerServer()
	
	// Add a test match
	match := Match{
		Tournament: "Brasileirão",
		Date:       "2023-01-01",
		HomeTeam:   "Flamengo",
		AwayTeam:   "Fluminense",
		HomeGoal:   3,
		AwayGoal:   1,
		Season:     2023,
	}
	server.matches = append(server.matches, match)

	req := httptest.NewRequest("GET", "/api/team-stats?team=Flamengo", nil)
	rec := httptest.NewRecorder()
	teamStatsHandler(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rec.Code)
	}

	var stats TeamStats
	if err := json.NewDecoder(rec.Body).Decode(&stats); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if stats.TeamName != "Flamengo" {
		t.Errorf("Expected team name 'Flamengo', got '%v'", stats.TeamName)
	}
	
	if stats.Matches != 1 {
		t.Errorf("Expected 1 match, got %d", stats.Matches)
	}
}

func TestPlayersHandler(t *testing.T) {
	// Initialize server with test data
	server = NewSoccerServer()
	
	// Add a test player
	player := Player{
		Name:      "Neymar",
		Club:      "Flamengo",
		Overall:   91,
		Position:  "Forward",
	}
	server.players = append(server.players, player)

	req := httptest.NewRequest("GET", "/api/players?name=ney", nil)
	rec := httptest.NewRecorder()
	playersHandler(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rec.Code)
	}

	var players []Player
	if err := json.NewDecoder(rec.Body).Decode(&players); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(players) != 1 {
		t.Errorf("Expected 1 player, got %d", len(players))
	}
}

func TestMatchesHandler(t *testing.T) {
	// Initialize server with test data
	server = NewSoccerServer()
	
	// Add test matches
	match1 := Match{
		Tournament: "Brasileirão",
		Date:       "2023-01-01",
		HomeTeam:   "Flamengo",
		AwayTeam:   "Fluminense",
		HomeGoal:   3,
		AwayGoal:   1,
		Season:     2023,
	}
	match2 := Match{
		Tournament: "Brasileirão",
		Date:       "2023-02-01",
		HomeTeam:   "Fluminense",
		AwayTeam:   "Flamengo",
		HomeGoal:   1,
		AwayGoal:   0,
		Season:     2023,
	}
	server.matches = append(server.matches, match1, match2)

	req := httptest.NewRequest("GET", "/api/matches?team1=Flamengo&team2=Fluminense&season=2023", nil)
	rec := httptest.NewRecorder()
	matchesHandler(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rec.Code)
	}

	var matches []Match
	if err := json.NewDecoder(rec.Body).Decode(&matches); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if len(matches) != 2 {
		t.Errorf("Expected 2 matches, got %d", len(matches))
	}
}

func TestHeadToHeadHandler(t *testing.T) {
	// Initialize server with test data
	server = NewSoccerServer()
	
	// Add test matches
	match1 := Match{
		Tournament: "Brasileirão",
		Date:       "2023-01-01",
		HomeTeam:   "Flamengo",
		AwayTeam:   "Fluminense",
		HomeGoal:   3,
		AwayGoal:   1,
		Season:     2023,
	}
	match2 := Match{
		Tournament: "Brasileirão",
		Date:       "2023-02-01",
		HomeTeam:   "Fluminense",
		AwayTeam:   "Flamengo",
		HomeGoal:   1,
		AwayGoal:   0,
		Season:     2023,
	}
	match3 := Match{
		Tournament: "Brasileirão",
		Date:       "2023-03-01",
		HomeTeam:   "Flamengo",
		AwayTeam:   "Fluminense",
		HomeGoal:   1,
		AwayGoal:   1,
		Season:     2023,
	}
	server.matches = append(server.matches, match1, match2, match3)

	req := httptest.NewRequest("GET", "/api/head-to-head?team1=Flamengo&team2=Fluminense", nil)
	rec := httptest.NewRecorder()
	headToHeadHandler(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rec.Code)
	}

	var response map[string]interface{}
	if err := json.NewDecoder(rec.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	// Flamengo: 1 win (match1), Fluminense: 1 win (match2), Draw: 1 (match3)
	// JSON numbers come back as float64
	if v, ok := response["team1_wins"].(float64); !ok || int(v) != 1 {
		t.Errorf("Expected Flamengo 1 win, got %v", response["team1_wins"])
	}
	if v, ok := response["team2_wins"].(float64); !ok || int(v) != 1 {
		t.Errorf("Expected Fluminense 1 win, got %v", response["team2_wins"])
	}
	if v, ok := response["draws"].(float64); !ok || int(v) != 1 {
		t.Errorf("Expected 1 draw, got %v", response["draws"])
	}
}

func TestGetMatchesByTeams(t *testing.T) {
	server = NewSoccerServer()
	
	match := Match{
		Tournament: "Brasileirão",
		Date:       "2023-01-01",
		HomeTeam:   "Flamengo",
		AwayTeam:   "Fluminense",
		HomeGoal:   3,
		AwayGoal:   1,
		Season:     2023,
	}
	server.matches = append(server.matches, match)

	matches := server.GetMatchesByTeams("Flamengo", "Fluminense")
	if len(matches) != 1 {
		t.Errorf("Expected 1 match, got %d", len(matches))
	}
}

func TestGetTeamStats(t *testing.T) {
	server = NewSoccerServer()
	
	match := Match{
		Tournament: "Brasileirão",
		Date:       "2023-01-01",
		HomeTeam:   "Flamengo",
		AwayTeam:   "Fluminense",
		HomeGoal:   3,
		AwayGoal:   1,
		Season:     2023,
	}
	server.matches = append(server.matches, match)

	stats := server.GetTeamStats("Flamengo", 2023)
	if stats.TeamName != "Flamengo" {
		t.Errorf("Expected team name 'Flamengo', got '%v'", stats.TeamName)
	}
	if stats.Matches != 1 {
		t.Errorf("Expected 1 match, got %d", stats.Matches)
	}
	if stats.Wins != 1 {
		t.Errorf("Expected 1 win, got %d", stats.Wins)
	}
	if stats.Points != 3 {
		t.Errorf("Expected 3 points, got %d", stats.Points)
	}
}

func TestGetHeadToHead(t *testing.T) {
	server = NewSoccerServer()
	
	match1 := Match{
		Tournament: "Brasileirão",
		Date:       "2023-01-01",
		HomeTeam:   "Flamengo",
		AwayTeam:   "Fluminense",
		HomeGoal:   3,
		AwayGoal:   1,
		Season:     2023,
	}
	match2 := Match{
		Tournament: "Brasileirão",
		Date:       "2023-02-01",
		HomeTeam:   "Fluminense",
		AwayTeam:   "Flamengo",
		HomeGoal:   1,
		AwayGoal:   0,
		Season:     2023,
	}
	match3 := Match{
		Tournament: "Brasileirão",
		Date:       "2023-03-01",
		HomeTeam:   "Flamengo",
		AwayTeam:   "Fluminense",
		HomeGoal:   1,
		AwayGoal:   1,
		Season:     2023,
	}
	server.matches = append(server.matches, match1, match2, match3)

	t1Wins, t2Wins, draws := server.GetHeadToHead("Flamengo", "Fluminense")
	if t1Wins != 1 {
		t.Errorf("Expected Flamengo 1 win, got %d", t1Wins)
	}
	if t2Wins != 1 {
		t.Errorf("Expected Fluminense 1 win, got %d", t2Wins)
	}
	if draws != 1 {
		t.Errorf("Expected 1 draw, got %d", draws)
	}
}

func TestGetBrazilianPlayers(t *testing.T) {
	server = NewSoccerServer()
	
	brazilianPlayer := Player{
		Name:        "Neymar",
		Nationality: "Brazil",
		Club:        "Flamengo",
		Overall:     91,
	}
	nonBrazilianPlayer := Player{
		Name:        "Messi",
		Nationality: "Argentina",
		Club:        "Inter Miami",
		Overall:     95,
	}
	server.players = append(server.players, brazilianPlayer, nonBrazilianPlayer)

	players := server.GetBrazilianPlayers()
	if len(players) != 1 {
		t.Errorf("Expected 1 Brazilian player, got %d", len(players))
	}
	if players[0].Name != "Neymar" {
		t.Errorf("Expected Neymar, got %v", players[0].Name)
	}
}

func TestGetSeasonStandings(t *testing.T) {
	server = NewSoccerServer()
	
	match1 := Match{
		Tournament: "Brasileirão",
		Date:       "2023-01-01",
		HomeTeam:   "Flamengo",
		AwayTeam:   "Fluminense",
		HomeGoal:   3,
		AwayGoal:   1,
		Season:     2023,
	}
	match2 := Match{
		Tournament: "Brasileirão",
		Date:       "2023-01-02",
		HomeTeam:   "Fluminense",
		AwayTeam:   "Palmeiras",
		HomeGoal:   0,
		AwayGoal:   2,
		Season:     2023,
	}
	match3 := Match{
		Tournament: "Brasileirão",
		Date:       "2023-01-03",
		HomeTeam:   "Palmeiras",
		AwayTeam:   "Flamengo",
		HomeGoal:   1,
		AwayGoal:   1,
		Season:     2023,
	}
	server.matches = append(server.matches, match1, match2, match3)

	standings := server.GetSeasonStandings(2023)
	if len(standings) != 3 {
		t.Errorf("Expected 3 teams in standings, got %d", len(standings))
	}
	
	// Check that standings are sorted correctly (by points)
	if standings[0].TeamName != "Flamengo" {
		t.Errorf("Expected Flamengo at top, got %v", standings[0].TeamName)
	}
}

func TestExtractTeamName(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Flamengo-RJ", "Flamengo"},
		{"Palmeiras-SP", "Palmeiras"},
		{"São Paulo-SP", "São Paulo"},
		{"Fluminense-RJ", "Fluminense"},
		{"Inter", "Inter"},
		{"Real Madrid", "Real Madrid"},
	}
	
	for _, test := range tests {
		result := extractTeamName(test.input)
		if result != test.expected {
			t.Errorf("extractTeamName(%q) = %q, want %q", test.input, result, test.expected)
		}
	}
}

func TestAbs(t *testing.T) {
	tests := []struct {
		input    int
		expected int
	}{
		{5, 5},
		{-5, 5},
		{0, 0},
		{-100, 100},
		{100, 100},
	}
	
	for _, test := range tests {
		result := abs(test.input)
		if result != test.expected {
			t.Errorf("abs(%d) = %d, want %d", test.input, result, test.expected)
		}
	}
}

func TestMin(t *testing.T) {
	tests := []struct {
		input1   int
		input2   int
		expected int
	}{
		{5, 10, 5},
		{10, 5, 5},
		{0, 0, 0},
		{-5, -10, -10},
	}
	
	for _, test := range tests {
		result := min(test.input1, test.input2)
		if result != test.expected {
			t.Errorf("min(%d, %d) = %d, want %d", test.input1, test.input2, result, test.expected)
		}
	}
}

func TestParseSkill(t *testing.T) {
	tests := []struct {
		input    string
		expected int
	}{
		{"88", 88},
		{"88+2", 90},
		{" 90 ", 90},
		{"92+1", 93},
	}
	
	for _, test := range tests {
		result := parseSkill(test.input)
		if result != test.expected {
			t.Errorf("parseSkill(%q) = %d, want %d", test.input, result, test.expected)
		}
	}
}

// Test helper to set server for handlers
func setTestServer(s *SoccerServer) {
	server = s
}

func TestGetBiggestWins(t *testing.T) {
	server = NewSoccerServer()
	
	matches := []Match{
		{HomeTeam: "Flamengo", AwayTeam: "Fluminense", HomeGoal: 5, AwayGoal: 0, Season: 2023},
		{HomeTeam: "Fluminense", AwayTeam: "Flamengo", HomeGoal: 4, AwayGoal: 1, Season: 2023},
		{HomeTeam: "Palmeiras", AwayTeam: "São Paulo", HomeGoal: 2, AwayGoal: 1, Season: 2023},
	}
	server.matches = matches
	
	wins := server.GetBiggestWins(10)
	if len(wins) != 2 {
		t.Errorf("Expected 2 big wins, got %d", len(wins))
	}
	
	// Check that the first result has the largest margin
	if wins[0].HomeGoal-wins[0].AwayGoal != 5 {
		t.Errorf("Expected largest win to be 5-0, got %d-%d", wins[0].HomeGoal, wins[0].AwayGoal)
	}
}

func TestGetPlayersByClub(t *testing.T) {
	server = NewSoccerServer()
	
	players := []Player{
		{Name: "Neymar", Club: "Flamengo", Overall: 91},
		{Name: "Pastore", Club: "Flamengo", Overall: 85},
		{Name: "Messi", Club: "Inter Miami", Overall: 95},
	}
	server.players = players
	
	result := server.GetPlayersByClub("Flamengo")
	if len(result) != 2 {
		t.Errorf("Expected 2 Flamengo players, got %d", len(result))
	}
}

func TestGetPlayersByPosition(t *testing.T) {
	server = NewSoccerServer()
	
	players := []Player{
		{Name: "Neymar", Position: "Forward", Overall: 91},
		{Name: "Casemiro", Position: "Defender", Overall: 88},
		{Name: "Casemiro2", Position: "Midfielder", Overall: 87},
	}
	server.players = players
	
	result := server.GetPlayersByPosition("Forward")
	if len(result) != 1 {
		t.Errorf("Expected 1 Forward, got %d", len(result))
	}
}

func TestGetPlayerByName(t *testing.T) {
	server = NewSoccerServer()
	
	players := []Player{
		{Name: "Neymar Jr", Overall: 91},
		{Name: "Neymar Silva", Overall: 85},
		{Name: "Messi", Overall: 95},
	}
	server.players = players
	
	result := server.GetPlayerByName("ney")
	if len(result) != 2 {
		t.Errorf("Expected 2 players with 'ney', got %d", len(result))
	}
}

func TestGetMatchesBySeason(t *testing.T) {
	server = NewSoccerServer()
	
	matches := []Match{
		{HomeTeam: "Flamengo", AwayTeam: "Fluminense", Season: 2023},
		{HomeTeam: "Flamengo", AwayTeam: "Palmeiras", Season: 2022},
		{HomeTeam: "São Paulo", AwayTeam: "Corinthians", Season: 2023},
	}
	server.matches = matches
	
	result := server.GetMatchesBySeason(2023)
	if len(result) != 2 {
		t.Errorf("Expected 2 matches in 2023, got %d", len(result))
	}
}

func TestGetMatchesByTournament(t *testing.T) {
	server = NewSoccerServer()
	
	matches := []Match{
		{HomeTeam: "Flamengo", AwayTeam: "Fluminense", Tournament: "Brasileirão"},
		{HomeTeam: "Flamengo", AwayTeam: "Palmeiras", Tournament: "Copa do Brasil"},
		{HomeTeam: "São Paulo", AwayTeam: "Corinthians", Tournament: "Brasileirão"},
	}
	server.matches = matches
	
	result := server.GetMatchesByTournament("Brasileirão")
	if len(result) != 2 {
		t.Errorf("Expected 2 Brasileirão matches, got %d", len(result))
	}
}

func TestGetMatchesByTeam(t *testing.T) {
	server = NewSoccerServer()
	
	matches := []Match{
		{HomeTeam: "Flamengo", AwayTeam: "Fluminense", Season: 2023},
		{HomeTeam: "Fluminense", AwayTeam: "Flamengo", Season: 2023},
		{HomeTeam: "Palmeiras", AwayTeam: "São Paulo", Season: 2023},
	}
	server.matches = matches
	
	result := server.GetMatchesByTeam("Flamengo")
	if len(result) != 2 {
		t.Errorf("Expected 2 Flamengo matches, got %d", len(result))
	}
}

func TestGetTeamRecordByCompetition(t *testing.T) {
	server = NewSoccerServer()
	
	matches := []Match{
		{HomeTeam: "Flamengo", AwayTeam: "Fluminense", Tournament: "Brasileirão", HomeGoal: 3, AwayGoal: 1},
		{HomeTeam: "Fluminense", AwayTeam: "Flamengo", Tournament: "Brasileirão", HomeGoal: 1, AwayGoal: 0},
		{HomeTeam: "Flamengo", AwayTeam: "Palmeiras", Tournament: "Copa do Brasil", HomeGoal: 2, AwayGoal: 0},
	}
	server.matches = matches
	
	record := server.GetTeamRecordByCompetition("Flamengo", "Brasileirão")
	if record.Matches != 2 {
		t.Errorf("Expected 2 Brasileirão matches, got %d", record.Matches)
	}
	if record.Wins != 1 {
		t.Errorf("Expected 1 win in Brasileirão, got %d", record.Wins)
	}
	if record.GoalsFor != 4 {
		t.Errorf("Expected 4 goals for in Brasileirão, got %d", record.GoalsFor)
	}
}

func TestGetMatchesByDateRange(t *testing.T) {
	server = NewSoccerServer()
	
	matches := []Match{
		{HomeTeam: "Flamengo", AwayTeam: "Fluminense", Date: "2023-01-01", Season: 2023},
		{HomeTeam: "Fluminense", AwayTeam: "Flamengo", Date: "2023-01-15", Season: 2023},
		{HomeTeam: "Palmeiras", AwayTeam: "São Paulo", Date: "2023-02-01", Season: 2023},
	}
	server.matches = matches
	
	result := server.GetMatchesByDateRange("2023-01-01", "2023-01-31")
	if len(result) != 2 {
		t.Errorf("Expected 2 matches in January 2023, got %d", len(result))
	}
}
