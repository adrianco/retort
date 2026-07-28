package server

import (
	"fmt"
	"testing"

	"brazilian-soccer-mcp/internal/store"
)

func TestSoccerServerFindMatchesByTeam(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test finding matches for a team
	matches := soccerServer.FindMatchesByTeam("Flamengo", 2023)
	fmt.Printf("Found %d matches for Flamengo in 2023\n", len(matches))

	// Test with season=0 (all seasons)
	allMatches := soccerServer.FindMatchesByTeam("Flamengo", 0)
	fmt.Printf("Found %d matches for Flamengo (all seasons)\n", len(allMatches))
}

func TestSoccerServerFindMatchesByTeams(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test finding matches between two teams
	matches := soccerServer.FindMatchesByTeams("Flamengo", "Fluminense")
	fmt.Printf("Found %d matches between Flamengo and Fluminense\n", len(matches))

	if len(matches) == 0 {
		t.Error("Expected to find matches between Flamengo and Fluminense")
	}
}

func TestSoccerServerFindPlayerByName(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test finding a player by name
	player := soccerServer.FindPlayerByName("Neymar")
	if player == nil {
		t.Error("Expected to find player Neymar")
	} else {
		fmt.Printf("Found player: %s, Club: %s, Overall: %d\n", player.Name, player.Club, player.Overall)
	}
}

func TestSoccerServerGetTeamStats(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test getting team stats
	stats := soccerServer.GetTeamStats("Palmeiras", 2023)
	fmt.Printf("Palmeiras 2023 stats: %d matches, %d wins, %d draws, %d losses\n",
		stats.Matches, stats.Wins, stats.Draws, stats.Losses)

	if stats.Matches == 0 {
		t.Error("Expected Palmeiras to have matches in 2023")
	}
}

func TestSoccerServerGetHeadToHead(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test getting head-to-head
	h2h := soccerServer.GetHeadToHead("Flamengo", "Fluminense")
	fmt.Printf("Flamengo vs Fluminense H2H: %d matches, Flamengo wins: %d, Fluminense wins: %d, Draws: %d\n",
		h2h.Matches, h2h.Team1Wins, h2h.Team2Wins, h2h.Draws)

	if h2h.Matches == 0 {
		t.Error("Expected Flamengo vs Fluminense to have matches")
	}
}

func TestSoccerServerGetBigWins(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test getting big wins
	wins := soccerServer.GetBigWins(5)
	fmt.Printf("Found %d big wins with margin >= 5 goals\n", len(wins))

	if len(wins) == 0 {
		t.Error("Expected to find big wins")
	}
}

func TestSoccerServerCalculateLeagueStandings(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test getting league standings
	standings := soccerServer.CalculateLeagueStandings("brasileirao", 2019)
	fmt.Printf("Top 5 teams in 2019 Brasileirão:\n")
	for i, team := range standings {
		if i >= 5 {
			break
		}
		fmt.Printf("%d. %s - %d pts\n", i+1, team.TeamName, team.Points)
	}

	if len(standings) == 0 {
		t.Error("Expected to find standings for 2019 Brasileirão")
	}
}

func TestSoccerServerGetAverageGoalsPerMatch(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test getting average goals
	avgGoals := soccerServer.GetAverageGoalsPerMatch("", 0)
	fmt.Printf("Average goals per match: %.2f\n", avgGoals)
}

func TestSoccerServerGetHomeWinRate(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test getting home win rate
	homeWinRate := soccerServer.GetHomeWinRate("", 0)
	fmt.Printf("Home win rate: %.1f%%\n", homeWinRate)
}

func TestSoccerServerGetTopBrazilianPlayers(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test getting top Brazilian players
	players := soccerServer.GetTopBrazilianPlayers(5)
	fmt.Printf("Top 5 Brazilian players:\n")
	for i, player := range players {
		fmt.Printf("%d. %s - Overall: %d, Club: %s\n", i+1, player.Name, player.Overall, player.Club)
	}

	if len(players) == 0 {
		t.Error("Expected to find Brazilian players")
	}
}

func TestSoccerServerGetPlayersByClub(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test getting players by club
	players := soccerServer.FindPlayersByClub("Flamengo")
	fmt.Printf("Found %d players for Flamengo\n", len(players))
}

func TestSoccerServerCompareTeams(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test comparing teams
	result := soccerServer.CompareTeams("Flamengo", "Palmeiras")
	fmt.Printf("Flamengo vs Palmeiras comparison:\n")
	fmt.Printf("  Team 1: %s\n", result["team_1"].(map[string]interface{})["name"])
	fmt.Printf("  Team 2: %s\n", result["team_2"].(map[string]interface{})["name"])
}

func TestFormatMatchesText(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test formatting matches
	matches := soccerServer.FindMatchesByTeams("Flamengo", "Fluminense")
	text := formatMatchesText(matches)
	fmt.Printf("Flamengo vs Fluminense matches:\n%s\n", text)

	if len(text) == 0 {
		t.Error("Expected formatted match text")
	}
}

func TestFormatPlayersText(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test formatting players
	players := soccerServer.FindPlayersByNationality("Brazil")
	text := formatPlayersText(players)
	fmt.Printf("Brazilian players (first 10):\n%s\n", text)

	if len(text) == 0 {
		t.Error("Expected formatted player text")
	}
}

func TestFormatStandingsText(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test formatting standings
	standings := soccerServer.CalculateLeagueStandings("brasileirao", 2019)
	text := formatStandingsText(standings)
	fmt.Printf("2019 Brasileirão Standings:\n%s\n", text)

	if len(text) == 0 {
		t.Error("Expected formatted standings text")
	}
}

func TestFormatBigWinsText(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test formatting big wins
	wins := soccerServer.GetBigWins(5)
	text := formatBigWinsText(wins)
	fmt.Printf("Big wins:\n%s\n", text)

	if len(text) == 0 {
		t.Error("Expected formatted big wins text")
	}
}

func TestFormatPlayerText(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test formatting a single player
	player := soccerServer.FindPlayerByName("Neymar")
	if player == nil {
		t.Skip("Player not found")
	}
	text := formatPlayerText(player)
	fmt.Printf("Player text: %s\n", text)

	if len(text) == 0 {
		t.Error("Expected formatted player text")
	}
}

func TestFormatCompareTeamsText(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test formatting team comparison
	result := soccerServer.CompareTeams("Flamengo", "Palmeiras")
	text := formatCompareTeamsText(result)
	fmt.Printf("Team comparison:\n%s\n", text)

	if len(text) == 0 {
		t.Error("Expected formatted comparison text")
	}
}

func TestSoccerServerFindMatchesBySeason(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test finding matches by season
	matches := soccerServer.FindMatchesBySeason(2023)
	fmt.Printf("Found %d matches in 2023\n", len(matches))
}

func TestSoccerServerFindMatchesByCompetition(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test finding matches by competition
	matches := soccerServer.FindMatchesByCompetition("brasileirao")
	fmt.Printf("Found %d matches in Brasileirão\n", len(matches))
}

func TestSoccerServerFindPlayersByNationality(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test finding players by nationality
	players := soccerServer.FindPlayersByNationality("Brazil")
	fmt.Printf("Found %d Brazilian players\n", len(players))
}

func TestSoccerServerGetTopScorers(t *testing.T) {
	db, err := store.LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-7ef53393b892/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	soccerServer := NewSoccerServer(db)

	// Test getting top scorers
	players := soccerServer.GetTopScorers(5)
	fmt.Printf("Top 5 players by rating:\n")
	for i, player := range players {
		fmt.Printf("%d. %s - Overall: %d\n", i+1, player.Name, player.Overall)
	}
}
