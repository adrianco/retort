package server

import (
	"fmt"
	"testing"
)

// TestNormalizeTeamName tests the team name normalization function
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

// TestMatchResult tests the match result formatting
func TestMatchResult(t *testing.T) {
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
		result := GetMatchResult(match)
		if result != tt.expected {
			t.Errorf("GetMatchResult(home=%d, away=%d) = %q, want %q",
				tt.homeGoal, tt.awayGoal, result, tt.expected)
		}
	}
}

// GetMatchResult is a helper function for testing
func GetMatchResult(match Match) string {
	if match.HomeGoal > match.AwayGoal {
		return fmt.Sprintf("%d-%d", match.HomeGoal, match.AwayGoal)
	} else if match.HomeGoal < match.AwayGoal {
		return fmt.Sprintf("%d-%d", match.HomeGoal, match.AwayGoal)
	}
	return fmt.Sprintf("%d-%d", match.HomeGoal, match.AwayGoal)
}

// TestIntAbs tests the integer absolute value function
func TestIntAbs(t *testing.T) {
	tests := []struct {
		input    int
		expected int
	}{
		{5, 5},
		{-5, 5},
		{0, 0},
		{100, 100},
		{-100, 100},
	}

	for _, tt := range tests {
		result := intAbs(tt.input)
		if result != tt.expected {
			t.Errorf("intAbs(%d) = %d, want %d", tt.input, result, tt.expected)
		}
	}
}

// TestSeasonExtraction tests season extraction from queries
func TestSeasonExtraction(t *testing.T) {
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

// TestCompetitionExtraction tests competition extraction from queries
func TestCompetitionExtraction(t *testing.T) {
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

// TestTeamExtraction tests team name extraction from queries
func TestTeamExtraction(t *testing.T) {
	tests := []struct {
		query    string
		expected string
	}{
		{"What is Palmeiras' record?", "Palmeiras"},
		{"Show Flamengo stats", "Flamengo"},
		{"Corinthians home record", "Corinthians"},
		{"No team name here", ""},
	}

	for _, tt := range tests {
		result := extractTeamName(tt.query)
		if result != tt.expected {
			t.Errorf("extractTeamName(%q) = %q, want %q", tt.query, result, tt.expected)
		}
	}
}

// TestPlayerNameExtraction tests player name extraction from queries
func TestPlayerNameExtraction(t *testing.T) {
	tests := []struct {
		query    string
		expected string
	}{
		{"Who is Neymar?", "neymar"},
		{"Tell me about Cristiano Ronaldo", "ronaldo"},
		{"Who is Casemiro?", "casemiro"},
		{"No player name here", ""},
	}

	for _, tt := range tests {
		result := extractPlayerName(tt.query)
		if result != tt.expected {
			t.Errorf("extractPlayerName(%q) = %q, want %q", tt.query, result, tt.expected)
		}
	}
}

// TestGetTeamList tests getting team list
func TestGetTeamList(t *testing.T) {
	ds := &DataStore{}
	teams := ds.GetTeamList()
	fmt.Printf("Found %d unique teams\n", len(teams))
	if len(teams) < 10 {
		t.Errorf("Expected at least 10 teams, got %d", len(teams))
	}
}

// TestGetBrasileiraoTable tests getting Brasileirão table
func TestGetBrasileiraoTable(t *testing.T) {
	ds := &DataStore{}
	table := ds.calculateLeagueTable("Brasileirão", 2019)
	fmt.Printf("2019 Brasileirão table:\n")
	for i, standing := range table.Teams {
		if i < 5 {
			fmt.Printf("  %d. %s - %d pts\n", i+1, standing.Team, standing.Points)
		}
	}
}

// TestGetBiggestWins tests getting biggest wins
func TestGetBiggestWins(t *testing.T) {
	ds := &DataStore{}
	result := ds.getBiggestWins()
	fmt.Printf("Biggest wins:\n%s\n", result.Message)
}

// getBiggestWins is a helper function for testing
func (ds *DataStore) getBiggestWins() QueryResult {
	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	if len(allMatches) == 0 {
		return QueryResult{
			Message: "No matches found in the dataset",
			Count:   0,
		}
	}

	// Calculate goal difference for each match
	type matchDiff struct {
		match Match
		diff  int
	}

	var diffs []matchDiff
	for _, match := range allMatches {
		diff := intAbs(match.HomeGoal - match.AwayGoal)
		diffs = append(diffs, matchDiff{match: match, diff: diff})
	}

	// Sort by goal difference descending
	sort.Slice(diffs, func(i, j int) bool {
		return diffs[i].diff > diffs[j].diff
	})

	message := "Biggest victories in dataset:\n"
	count := 0
	for _, d := range diffs {
		if d.diff > 0 {
			message += fmt.Sprintf("- %s: %s %d-%d %s (%s)\n",
				d.match.Datetime.Format("2006-01-02"),
				d.match.HomeTeam, d.match.HomeGoal, d.match.AwayGoal, d.match.AwayTeam,
				getCompetitionName(&d.match))
			count++
			if count >= 10 {
				break
			}
		}
	}

	return QueryResult{
		Message: message,
		Count:   count,
	}
}

// TestGetBestHomeRecord tests getting best home record
func TestGetBestHomeRecord(t *testing.T) {
	ds := &DataStore{}
	result := ds.getBestHomeRecord()
	fmt.Printf("Best home records:\n%s\n", result.Message)
}

// getBestHomeRecord is a helper function for testing
func (ds *DataStore) getBestHomeRecord() QueryResult {
	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	teamStats := make(map[string]*TeamStats)

	for _, match := range allMatches {
		homeTeam := NormalizeTeamName(match.HomeTeam)

		if _, exists := teamStats[homeTeam]; !exists {
			teamStats[homeTeam] = &TeamStats{TeamName: homeTeam}
		}

		stats := teamStats[homeTeam]
		stats.HomeMatches++
		stats.HomeGF += match.HomeGoal
		stats.HomeGA += match.AwayGoal

		if match.HomeGoal > match.AwayGoal {
			stats.HomeWins++
			stats.Points += 3
		} else if match.HomeGoal == match.AwayGoal {
			stats.HomeDraws++
			stats.Points += 1
		} else {
			stats.HomeLosses++
		}
	}

	// Convert to slice and sort
	var teams []TeamStats
	for _, stats := range teamStats {
		teams = append(teams, *stats)
	}

	sort.Slice(teams, func(i, j int) bool {
		return float64(teams[i].HomeWins)/float64(teams[i].HomeMatches) >
			float64(teams[j].HomeWins)/float64(teams[j].HomeMatches)
	})

	message := "Teams with best home records:\n"
	count := 0
	for _, stats := range teams {
		if stats.HomeMatches > 0 {
			winRate := float64(stats.HomeWins) / float64(stats.HomeMatches) * 100
			message += fmt.Sprintf("- %s: %d wins in %d home matches (%.1f%% win rate)\n",
				stats.TeamName, stats.HomeWins, stats.HomeMatches, winRate)
			count++
			if count >= 10 {
				break
			}
		}
	}

	return QueryResult{
		Message: message,
		Count:   count,
	}
}

// TestGetStatisticalAnalysis tests getting statistical analysis
func TestGetStatisticalAnalysis(t *testing.T) {
	ds := &DataStore{}
	result := ds.getStatisticalAnalysis()
	fmt.Printf("Statistical analysis:\n%s\n", result.Message)
}

// getStatisticalAnalysis is a helper function for testing
func (ds *DataStore) getStatisticalAnalysis() QueryResult {
	// Calculate average goals
	allMatches := append(append(append(append(
		ds.BrasileiraoMatches,
		ds.CopaDoBrasilMatches...),
		ds.CopaLibertadoresMatches...),
		ds.BRFootballMatches...),
		ds.NovoCampeonatoMatches...)

	if len(allMatches) == 0 {
		return QueryResult{
			Message: "No matches found in the dataset",
			Count:   0,
		}
	}

	totalGoals := 0
	for _, match := range allMatches {
		totalGoals += match.HomeGoal + match.AwayGoal
	}

	avgGoals := float64(totalGoals) / float64(len(allMatches))

	// Count home wins, away wins, draws
	homeWins := 0
	awayWins := 0
	draws := 0
	for _, match := range allMatches {
		if match.HomeGoal > match.AwayGoal {
			homeWins++
		} else if match.HomeGoal < match.AwayGoal {
			awayWins++
		} else {
			draws++
		}
	}

	homeWinRate := float64(homeWins) / float64(len(allMatches)) * 100

	message := "Statistical Analysis:\n"
	message += fmt.Sprintf("- Average goals per match: %.2f\n", avgGoals)
	message += fmt.Sprintf("- Home wins: %d (%.1f%%)\n", homeWins, homeWinRate)
	message += fmt.Sprintf("- Draws: %d\n", draws)
	message += fmt.Sprintf("- Away wins: %d\n", awayWins)

	return QueryResult{
		Message: message,
		Count:   1,
	}
}

// TestFindTeamByName tests finding teams by name
func TestFindTeamByName(t *testing.T) {
	ds := &DataStore{}
	teams := ds.FindTeamByName("Palmeiras")
	fmt.Printf("Found %d teams matching 'Palmeiras'\n", len(teams))
}

// TestGetPlayerByName tests getting players by name
func TestGetPlayerByName(t *testing.T) {
	ds := &DataStore{}
	players := ds.GetPlayerByName("Neymar", 5)
	fmt.Printf("Found %d players matching 'Neymar'\n", len(players))
}

// TestGetPlayersByClub tests getting players by club
func TestGetPlayersByClub(t *testing.T) {
	ds := &DataStore{}
	players := ds.GetPlayersByClub("Flamengo")
	fmt.Printf("Found %d players at Flamengo\n", len(players))
}

// TestGetPlayersByNationality tests getting players by nationality
func TestGetPlayersByNationality(t *testing.T) {
	ds := &DataStore{}
	players := ds.GetPlayersByNationality("Brazil")
	fmt.Printf("Found %d Brazilian players\n", len(players))
}

// TestGetPlayersByPosition tests getting players by position
func TestGetPlayersByPosition(t *testing.T) {
	ds := &DataStore{}
	forwards := ds.GetPlayersByPosition("FW")
	fmt.Printf("Found %d forwards\n", len(forwards))
}

// TestGetTeamMatchHistory tests getting team match history
func TestGetTeamMatchHistory(t *testing.T) {
	ds := &DataStore{}
	matches := ds.GetTeamMatchHistory("Palmeiras", 10)
	fmt.Printf("Found %d matches for Palmeiras\n", len(matches))
}

// TestGetTeamStats tests getting team stats
func TestGetTeamStats(t *testing.T) {
	ds := &DataStore{}
	stats := ds.GetTeamStats("Palmeiras", 2023, "")
	fmt.Printf("Palmeiras stats for 2023:\n")
	fmt.Printf("  Matches: %d\n", stats.Matches)
	fmt.Printf("  Wins: %d\n", stats.Wins)
	fmt.Printf("  Points: %d\n", stats.Points)
}

// TestServerInitialize tests server initialization
func TestServerInitialize(t *testing.T) {
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

// TestServerGetTeamStats tests server GetTeamStats
func TestServerGetTeamStats(t *testing.T) {
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

// TestServerGetBrasileiraoTable tests server GetBrasileiraoTable
func TestServerGetBrasileiraoTable(t *testing.T) {
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

// TestServerGetBiggestWins tests server GetBiggestWins
func TestServerGetBiggestWins(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting biggest wins
	result := s.GetBiggestWins()
	fmt.Printf("Biggest wins:\n%s\n", result.Message)
}

// TestServerGetBestHomeRecord tests server GetBestHomeRecord
func TestServerGetBestHomeRecord(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting best home record
	result := s.GetBestHomeRecord()
	fmt.Printf("Best home records:\n%s\n", result.Message)
}

// TestServerGetStatisticalAnalysis tests server GetStatisticalAnalysis
func TestServerGetStatisticalAnalysis(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting statistical analysis
	result := s.GetStatisticalAnalysis()
	fmt.Printf("Statistical analysis:\n%s\n", result.Message)
}

// TestServerGetTeamList tests server GetTeamList
func TestServerGetTeamList(t *testing.T) {
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

// TestServerGetPlayerByName tests server GetPlayerByName
func TestServerGetPlayerByName(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting players by name
	players := s.GetPlayerByName("Neymar")
	fmt.Printf("Found %d players matching 'Neymar'\n", len(players))
}

// TestServerGetPlayersByClub tests server GetPlayersByClub
func TestServerGetPlayersByClub(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting players by club
	players := s.GetPlayersByClub("Flamengo")
	fmt.Printf("Found %d players at Flamengo\n", len(players))
}

// TestServerGetPlayersByNationality tests server GetPlayersByNationality
func TestServerGetPlayersByNationality(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting players by nationality
	players := s.GetPlayersByNationality("Brazil")
	fmt.Printf("Found %d Brazilian players\n", len(players))
}

// TestServerGetTopBrazilianPlayers tests server GetTopBrazilianPlayers
func TestServerGetTopBrazilianPlayers(t *testing.T) {
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

// TestServerGetPlayersByPosition tests server GetPlayersByPosition
func TestServerGetPlayersByPosition(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting players by position
	forwards := s.GetPlayersByPosition("FW")
	fmt.Printf("Found %d forwards\n", len(forwards))
}

// TestServerGetTopPlayersByClub tests server GetTopPlayersByClub
func TestServerGetTopPlayersByClub(t *testing.T) {
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

// TestServerFindTeamByName tests server FindTeamByName
func TestServerFindTeamByName(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test finding teams by name
	teams := s.FindTeamByName("Palmeiras")
	fmt.Printf("Found %d teams matching 'Palmeiras'\n", len(teams))
}

// TestServerGetMatchHistory tests server GetMatchHistory
func TestServerGetMatchHistory(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting match history
	matches := s.GetMatchHistory("Palmeiras")
	fmt.Printf("Found %d matches for Palmeiras\n", len(matches))
}

// TestServerGetHeadToHead tests server GetHeadToHead
func TestServerGetHeadToHead(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test head-to-head
	team1Wins, team2Wins, draws := s.GetHeadToHead("Flamengo", "Fluminense")
	fmt.Printf("Flamengo vs Fluminense: Flamengo %d, Fluminense %d, Draws %d\n",
		team1Wins, team2Wins, draws)
}

// TestServerGetPlayersByNationalityCount tests server GetPlayersByNationalityCount
func TestServerGetPlayersByNationalityCount(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting players by nationality count
	count := s.GetPlayersByNationalityCount("Brazil")
	fmt.Printf("Found %d Brazilian players\n", count)
}

// TestServerGetPlayersByClubCount tests server GetPlayersByClubCount
func TestServerGetPlayersByClubCount(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting players by club count
	count := s.GetPlayersByClubCount("Flamengo")
	fmt.Printf("Found %d players at Flamengo\n", count)
}

// TestServerGetMatchCount tests server GetMatchCount
func TestServerGetMatchCount(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting match count
	count := s.GetMatchCount()
	fmt.Printf("Found %d matches\n", count)

	if count == 0 {
		t.Error("Expected matches to be loaded")
	}
}

// TestServerGetTeamCount tests server GetTeamCount
func TestServerGetTeamCount(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting team count
	count := s.GetTeamCount()
	fmt.Printf("Found %d unique teams\n", count)

	if count < 10 {
		t.Errorf("Expected at least 10 teams, got %d", count)
	}
}

// TestServerGetPlayerCount tests server GetPlayerCount
func TestServerGetPlayerCount(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting player count
	count := s.GetPlayerCount()
	fmt.Printf("Found %d players\n", count)

	if count == 0 {
		t.Error("Expected players to be loaded")
	}
}

// TestServerGetTeamStatsForSeason tests server GetTeamStatsForSeason
func TestServerGetTeamStatsForSeason(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting team stats for season
	stats := s.GetTeamStatsForSeason("Palmeiras", 2023)
	fmt.Printf("Palmeiras stats for 2023:\n")
	fmt.Printf("  Matches: %d\n", stats.Matches)
	fmt.Printf("  Wins: %d\n", stats.Wins)
	fmt.Printf("  Points: %d\n", stats.Points)
}

// TestServerGetTeamStatsForCompetition tests server GetTeamStatsForCompetition
func TestServerGetTeamStatsForCompetition(t *testing.T) {
	s := NewServer()
	err := s.Initialize()
	if err != nil {
		t.Fatalf("Failed to initialize server: %v", err)
	}

	// Test getting team stats for competition
	stats := s.GetTeamStatsForCompetition("Palmeiras", "Brasileirão")
	fmt.Printf("Palmeiras Brasileirão stats:\n")
	fmt.Printf("  Matches: %d\n", stats.Matches)
	fmt.Printf("  Wins: %d\n", stats.Wins)
	fmt.Printf("  Points: %d\n", stats.Points)
}
