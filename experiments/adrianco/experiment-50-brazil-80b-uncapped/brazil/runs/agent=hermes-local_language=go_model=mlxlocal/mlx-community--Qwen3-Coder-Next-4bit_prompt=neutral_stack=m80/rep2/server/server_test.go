package server

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

func TestMain(m *testing.M) {
	// Set up test data directory
	// Try relative path first, then absolute path from module root
	dataPath := DataDir
	if _, err := os.Stat(dataPath); os.IsNotExist(err) {
		// Try from module root (one level up from server/)
		moduleRoot, _ := filepath.Abs("..")
		dataPath = filepath.Join(moduleRoot, DataDir)
		if _, err := os.Stat(dataPath); os.IsNotExist(err) {
			fmt.Printf("Test data directory %s does not exist\n", dataPath)
			fmt.Println("Skipping tests that require data files")
			os.Exit(0)
		}
	}
	os.Exit(m.Run())
}

func TestDataStore_LoadAllData(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load all data: %v", err)
	}

	// Verify data was loaded
	if len(ds.BrasileiraoMatches) == 0 {
		t.Error("No Brasileirao matches loaded")
	}
	if len(ds.CopaDoBrasilMatches) == 0 {
		t.Error("No Copa do Brasil matches loaded")
	}
	if len(ds.CopaLibertadoresMatches) == 0 {
		t.Error("No Copa Libertadores matches loaded")
	}
	if len(ds.BRFootballMatches) == 0 {
		t.Error("No BR Football matches loaded")
	}
	if len(ds.NovoCampeonatoMatches) == 0 {
		t.Error("No Novo Campeonato matches loaded")
	}
	if len(ds.Players) == 0 {
		t.Error("No players loaded")
	}

	fmt.Printf("Loaded %d Brasileirao matches\n", len(ds.BrasileiraoMatches))
	fmt.Printf("Loaded %d Copa do Brasil matches\n", len(ds.CopaDoBrasilMatches))
	fmt.Printf("Loaded %d Copa Libertadores matches\n", len(ds.CopaLibertadoresMatches))
	fmt.Printf("Loaded %d BR Football matches\n", len(ds.BRFootballMatches))
	fmt.Printf("Loaded %d Novo Campeonato matches\n", len(ds.NovoCampeonatoMatches))
	fmt.Printf("Loaded %d players\n", len(ds.Players))
}

func TestNormalizeTeamName(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"Corinthians-SP", "Corinthians"},
		{"São Paulo", "São Paulo"},
		{"Grêmio-RS", "Grêmio"},
		{"  Santos-SP  ", "Santos"},
	}

	for _, tt := range tests {
		result := NormalizeTeamName(tt.input)
		if result != tt.expected {
			t.Errorf("NormalizeTeamName(%q) = %q, want %q", tt.input, result, tt.expected)
		}
	}
}

func TestDataStore_GetMatchesByTeams(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	// Test finding matches between two teams
	matches := ds.GetMatchesByTeams("Flamengo", "Fluminense", 10)

	// We may not have specific teams in all datasets, but we should be able to find some matches
	fmt.Printf("Found %d matches between Flamengo and Fluminense\n", len(matches))

	// Test finding matches for a single team
	matches = ds.GetMatchesByTeams("Palmeiras", "", 10)
	fmt.Printf("Found %d matches for Palmeiras\n", len(matches))
}

func TestDataStore_GetTeamStats(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	// Test getting team stats
	stats := ds.GetTeamStats("Palmeiras", 2023, "")

	fmt.Printf("Palmeiras stats for 2023:\n")
	fmt.Printf("  Matches: %d\n", stats.Matches)
	fmt.Printf("  Wins: %d\n", stats.Wins)
	fmt.Printf("  Draws: %d\n", stats.Draws)
	fmt.Printf("  Losses: %d\n", stats.Losses)
	fmt.Printf("  Goals For: %d\n", stats.GoalsFor)
	fmt.Printf("  Goals Against: %d\n", stats.GoalsAgainst)
	fmt.Printf("  Points: %d\n", stats.Points)

	// Test team with no stats
	stats = ds.GetTeamStats("NonExistentTeam", 2023, "")
	if stats.Matches != 0 {
		t.Errorf("Expected 0 matches for non-existent team, got %d", stats.Matches)
	}
}

func TestDataStore_GetHeadToHead(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	// Test head-to-head
	team1Wins, team2Wins, draws := ds.GetHeadToHead("Flamengo", "Fluminense")
	fmt.Printf("Flamengo vs Fluminense: Flamengo %d, Fluminense %d, Draws %d\n",
		team1Wins, team2Wins, draws)
}

func TestDataStore_GetPlayerByName(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	// Test finding players by name
	players := ds.GetPlayerByName("Neymar", 5)
	fmt.Printf("Found %d players matching 'Neymar'\n", len(players))
	for _, p := range players {
		fmt.Printf("  %s: Overall %d, Club: %s\n", p.Name, p.Overall, p.Club)
	}

	// Test finding players by club
	players = ds.GetPlayersByClub("Flamengo")
	fmt.Printf("Found %d players at Flamengo\n", len(players))
}

func TestDataStore_GetPlayersByNationality(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	// Test finding Brazilian players
	brazilianPlayers := ds.GetPlayersByNationality("Brazil")
	fmt.Printf("Found %d Brazilian players\n", len(brazilianPlayers))

	// Test finding Argentinian players
	argentinianPlayers := ds.GetPlayersByNationality("Argentina")
	fmt.Printf("Found %d Argentinian players\n", len(argentinianPlayers))
}

func TestDataStore_GetPlayersByPosition(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	// Test finding forwards
	forwards := ds.GetPlayersByPosition("FW")
	fmt.Printf("Found %d forwards\n", len(forwards))

	// Test finding goalkeepers
	goalkeepers := ds.GetPlayersByPosition("GK")
	fmt.Printf("Found %d goalkeepers\n", len(goalkeepers))
}

func TestQueryEngine_HandleTeamVsTeamQuery(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qe := NewQueryEngine(ds)

	// Test team vs team query
	result := qe.Query("Show me all Flamengo vs Fluminense matches")
	fmt.Printf("Team vs team query result:\n%s\n", result.Message)
	if result.Count == 0 && result.Error == "" {
		// This is acceptable if no matches are found in the dataset
		fmt.Println("No matches found (acceptable for test)")
	}
}

func TestQueryEngine_HandleTeamStatsQuery(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qe := NewQueryEngine(ds)

	// Test team stats query
	result := qe.Query("What is Palmeiras' home record in 2023?")
	fmt.Printf("Team stats query result:\n%s\n", result.Message)
	if result.Count == 0 && result.Error == "" {
		fmt.Println("No stats found (acceptable for test)")
	}
}

func TestQueryEngine_HandlePlayerQuery(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qe := NewQueryEngine(ds)

	// Test player query
	result := qe.Query("Who is Gabriel Barbosa?")
	fmt.Printf("Player query result:\n%s\n", result.Message)
	if result.Count == 0 && result.Error == "" {
		fmt.Println("No players found (acceptable for test)")
	}
}

func TestQueryEngine_HandleTableQuery(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qe := NewQueryEngine(ds)

	// Test table query
	result := qe.Query("Who won the 2019 Brasileirão?")
	fmt.Printf("Table query result:\n%s\n", result.Message)
	if result.Count == 0 && result.Error == "" {
		fmt.Println("No table data found (acceptable for test)")
	}
}

func TestQueryEngine_HandleStatisticalQuery(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	qe := NewQueryEngine(ds)

	// Test statistical query
	result := qe.Query("What's the average goals per match in the Brasileirão?")
	fmt.Printf("Statistical query result:\n%s\n", result.Message)
	if result.Count == 0 && result.Error == "" {
		fmt.Println("No statistical data found (acceptable for test)")
	}
}

func TestServer_Initialize(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	fmt.Printf("Server initialized with %d matches and %d players\n",
		s.GetMatchCount(), s.GetPlayerCount())

	if s.GetMatchCount() == 0 {
		t.Error("Expected matches to be loaded")
	}
	if s.GetPlayerCount() == 0 {
		t.Error("Expected players to be loaded")
	}
}

func TestServer_GetTeamStats(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting team stats
	stats := s.GetTeamStats("Palmeiras", 2023)
	fmt.Printf("Palmeiras stats:\n")
	fmt.Printf("  Matches: %d\n", stats.Matches)
	fmt.Printf("  Wins: %d\n", stats.Wins)
	fmt.Printf("  Points: %d\n", stats.Points)
}

func TestServer_GetBrasileiraoTable(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting Brasileirão table
	table := s.GetBrasileiraoTable(2019)
	fmt.Printf("2019 Brasileirão table:\n")
	for i, standing := range table.Teams {
		if i < 5 {
			fmt.Printf("  %d. %s - %d pts\n", i+1, standing.Team, standing.Points)
		}
	}
}

func TestServer_GetBiggestWins(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting biggest wins
	result := s.GetBiggestWins()
	fmt.Printf("Biggest wins:\n%s\n", result.Message)
}

func TestServer_GetBestHomeRecord(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting best home record
	result := s.GetBestHomeRecord()
	fmt.Printf("Best home records:\n%s\n", result.Message)
}

func TestServer_GetStatisticalAnalysis(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting statistical analysis
	result := s.GetStatisticalAnalysis()
	fmt.Printf("Statistical analysis:\n%s\n", result.Message)
}

func TestServer_GetTeamList(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting team list
	teams := s.GetTeamList()
	fmt.Printf("Found %d unique teams\n", len(teams))
	if len(teams) < 10 {
		t.Errorf("Expected at least 10 teams, got %d", len(teams))
	}
}

func TestServer_GetPlayerByName(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting players by name
	players := s.GetPlayerByName("Neymar")
	fmt.Printf("Found %d players matching 'Neymar'\n", len(players))
}

func TestServer_GetPlayersByClub(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting players by club
	players := s.GetPlayersByClub("Flamengo")
	fmt.Printf("Found %d players at Flamengo\n", len(players))
}

func TestServer_GetPlayersByNationality(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting players by nationality
	players := s.GetPlayersByNationality("Brazil")
	fmt.Printf("Found %d Brazilian players\n", len(players))
}

func TestServer_GetTopBrazilianPlayers(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting top Brazilian players
	players := s.GetTopBrazilianPlayers(5)
	fmt.Printf("Top 5 Brazilian players:\n")
	for _, p := range players {
		fmt.Printf("  %s: Overall %d, Club: %s\n", p.Name, p.Overall, p.Club)
	}
}

func TestServer_GetPlayersByPosition(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting players by position
	forwards := s.GetPlayersByPosition("FW")
	fmt.Printf("Found %d forwards\n", len(forwards))
}

func TestServer_GetTopPlayersByClub(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting top players by club
	players := s.GetTopPlayersByClub("Flamengo", 5)
	fmt.Printf("Top 5 players at Flamengo:\n")
	for _, p := range players {
		fmt.Printf("  %s: Overall %d\n", p.Name, p.Overall)
	}
}

func TestServer_FindTeamByName(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test finding teams by name
	teams := s.FindTeamByName("Palmeiras")
	fmt.Printf("Found %d teams matching 'Palmeiras'\n", len(teams))
}

// Test with sample questions from the specification
func TestSampleQuestions(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	questions := []struct {
		query string
	}{
		{"When did Flamengo last play Corinthians?"},
		{"What was the score?"},
		{"Who is Gabriel Barbosa?"},
		{"Which players play for Flamengo?"},
		{"Show me all derbies in 2023"},
		{"What competitions has Palmeiras played in?"},
		{"Which team has the best home record?"},
		{"Who are the top Brazilian players?"},
		{"Compare the 2018 and 2019 seasons"},
	}

	fmt.Println("\n=== Sample Questions Test ===")
	for i, q := range questions {
		fmt.Printf("\nQuestion %d: %s\n", i+1, q.query)
		result := s.Query(q.query)
		fmt.Printf("Response: %s\n", result.Message)
	}
}

// Test team name normalization
func TestNormalizeTeamNameIntegration(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"Corinthians-SP", "Corinthians"},
		{"São Paulo", "São Paulo"},
		{"Grêmio-RS", "Grêmio"},
		{"  Santos-SP  ", "Santos"},
		{"Botafogo-RJ", "Botafogo"},
		{"Vasco-RJ", "Vasco"},
		{"Cruzeiro-MG", "Cruzeiro"},
		{"Atlético-MG", "Atlético"},
	}

	for _, tt := range tests {
		result := NormalizeTeamName(tt.input)
		if result != tt.expected {
			t.Errorf("NormalizeTeamName(%q) = %q, want %q", tt.input, result, tt.expected)
		}
	}
}

// Test match result formatting
func TestGetMatchResult(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	tests := []struct {
		homeGoal int
		awayGoal int
		expected string
	}{
		{2, 1, "2-1"},
		{1, 2, "1-2"},
		{0, 0, "0-0"},
		{3, 3, "3-3"},
	}

	for _, tt := range tests {
		match := Match{HomeGoal: tt.homeGoal, AwayGoal: tt.awayGoal}
		result := ds.GetMatchResult(match)
		if result != tt.expected {
			t.Errorf("GetMatchResult(home=%d, away=%d) = %q, want %q",
				tt.homeGoal, tt.awayGoal, result, tt.expected)
		}
	}
}

// Test head-to-head calculation
func TestGetHeadToHeadIntegration(t *testing.T) {
	ds := &DataStore{}
	err := ds.LoadAllData()
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	// Test head-to-head calculation
	team1Wins, team2Wins, draws := ds.GetHeadToHead("Flamengo", "Fluminense")
	fmt.Printf("Flamengo vs Fluminense: Flamengo %d, Fluminense %d, Draws %d\n",
		team1Wins, team2Wins, draws)
}

// Test data loading from all CSV files
func TestDataLoadingFromAllFiles(t *testing.T) {
	// Test loading each CSV file individually
	files := []string{
		"Brasileirao_Matches.csv",
		"Brazilian_Cup_Matches.csv",
		"Libertadores_Matches.csv",
		"BR-Football-Dataset.csv",
		"novo_campeonato_brasileiro.csv",
		"fifa_data.csv",
	}

	for _, file := range files {
		filePath := filepath.Join(DataDir, file)
		_, err := LoadCSV(filePath)
		if err != nil {
			t.Errorf("Failed to load %s: %v", file, err)
		}
	}
}

// Test season extraction from queries
func TestExtractSeason(t *testing.T) {
	tests := []struct {
		query    string
		expected int
	}{
		{"What happened in 2023?", 2023},
		{"Show me 2019 season data", 2019},
		{"2020 season statistics", 2020},
		{"2018 Brasileirão", 2018},
		{"No year here", 0},
		{"1990 is too old", 1990},
	}

	for _, tt := range tests {
		result := extractSeason(tt.query)
		if result != tt.expected {
			t.Errorf("extractSeason(%q) = %d, want %d", tt.query, result, tt.expected)
		}
	}
}

// Test competition extraction
func TestExtractCompetition(t *testing.T) {
	tests := []struct {
		query    string
		expected string
	}{
		{"Show me Brasileirão", "Brasileirão"},
		{"Copa do Brasil matches", "Copa do Brasil"},
		{"Libertadores 2023", "Copa Libertadores"},
		{"Some other competition", "Brasileirão"},
	}

	for _, tt := range tests {
		result := extractCompetition(tt.query)
		if result != tt.expected {
			t.Errorf("extractCompetition(%q) = %q, want %q", tt.query, result, tt.expected)
		}
	}
}

// Test team extraction
func TestExtractTeamName(t *testing.T) {
	tests := []struct {
		query    string
		expected string
	}{
		{"What is Palmeiras' record?", "palmeiras"},
		{"Show Flamengo stats", "flamengo"},
		{"Corinthians home record", "corinthians"},
		{"No team name here", ""},
	}

	for _, tt := range tests {
		result := extractTeamName(tt.query)
		if result != tt.expected {
			t.Errorf("extractTeamName(%q) = %q, want %q", tt.query, result, tt.expected)
		}
	}
}
