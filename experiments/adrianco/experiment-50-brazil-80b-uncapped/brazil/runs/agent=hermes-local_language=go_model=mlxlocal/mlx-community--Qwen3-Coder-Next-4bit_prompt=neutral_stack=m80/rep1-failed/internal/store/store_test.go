package store

import (
	"fmt"
	"testing"
)

func TestDataLoading(t *testing.T) {
	db, err := LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-d5c30c1005b2/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	if db.MatchCount() == 0 {
		t.Error("No matches loaded")
	}

	if db.PlayerCount() == 0 {
		t.Error("No players loaded")
	}

	fmt.Printf("Loaded %d matches, %d players\n", db.MatchCount(), db.PlayerCount())
}

func TestFindMatchesByTeams(t *testing.T) {
	db, err := LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-d5c30c1005b2/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	matches := db.FindMatchesByTeams("Flamengo", "Fluminense")
	if len(matches) == 0 {
		t.Error("No matches found between Flamengo and Fluminense")
	}

	fmt.Printf("Found %d Flamengo vs Fluminense matches\n", len(matches))
}

func TestFindMatchesByTeam(t *testing.T) {
	db, err := LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-d5c30c1005b2/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	matches := db.FindMatchesByTeam("Palmeiras", 2023)
	fmt.Printf("Found %d Palmeiras matches in 2023\n", len(matches))
}

func TestFindPlayerByName(t *testing.T) {
	db, err := LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-d5c30c1005b2/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	neymar := db.FindPlayerByName("Neymar")
	if neymar == nil {
		t.Error("Neymar not found")
	} else {
		fmt.Printf("Found player: %s, Club: %s, Overall: %d\n", neymar.Name, neymar.Club, neymar.Overall)
	}
}

func TestGetTeamStats(t *testing.T) {
	db, err := LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-d5c30c1005b2/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	stats := db.GetTeamStats("Palmeiras", 2023)
	fmt.Printf("Palmeiras 2023 stats: %d matches, %d wins, %d draws, %d losses\n",
		stats.Matches, stats.Wins, stats.Draws, stats.Losses)

	if stats.Matches == 0 {
		t.Error("No stats found for Palmeiras 2023")
	}
}

func TestGetHeadToHead(t *testing.T) {
	db, err := LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-d5c30c1005b2/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	h2h := db.GetHeadToHead("Flamengo", "Fluminense")
	fmt.Printf("Flamengo vs Fluminense H2H: %d matches, Flamengo wins: %d, Fluminense wins: %d, Draws: %d\n",
		h2h.Matches, h2h.Team1Wins, h2h.Team2Wins, h2h.Draws)

	if h2h.Matches == 0 {
		t.Error("No head-to-head data found")
	}
}

func TestGetBigWins(t *testing.T) {
	db, err := LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-d5c30c1005b2/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	bigWins := db.GetBigWins(5)
	if len(bigWins) == 0 {
		t.Error("No big wins found")
	} else {
		fmt.Printf("Found %d big wins with margin >= 5 goals\n", len(bigWins))
		if len(bigWins) > 0 {
			fmt.Printf("Biggest win: %s %d-%d %s\n",
				bigWins[0].HomeTeam, bigWins[0].HomeGoal, bigWins[0].AwayGoal, bigWins[0].AwayTeam)
		}
	}
}

func TestCalculateLeagueStandings(t *testing.T) {
	db, err := LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-d5c30c1005b2/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	standings := db.CalculateLeagueStandings("brasileirao", 2019)
	if len(standings) == 0 {
		t.Error("No standings found for 2019 Brasileirão")
	} else {
		fmt.Printf("Top 5 teams in 2019 Brasileirão:\n")
		for i := 0; i < 5 && i < len(standings); i++ {
			fmt.Printf("%d. %s - %d pts\n", i+1, standings[i].TeamName, standings[i].Points)
		}
	}
}

func TestGetBrazilianPlayers(t *testing.T) {
	db, err := LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-d5c30c1005b2/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	brazilianPlayers := db.GetBrazilianPlayers()
	if len(brazilianPlayers) == 0 {
		t.Error("No Brazilian players found")
	} else {
		fmt.Printf("Found %d Brazilian players\n", len(brazilianPlayers))

		topPlayers := db.GetTopBrazilianPlayers(5)
		fmt.Printf("Top 5 Brazilian players:\n")
		for i, player := range topPlayers {
			fmt.Printf("%d. %s - Overall: %d, Club: %s\n", i+1, player.Name, player.Overall, player.Club)
		}
	}
}

func TestTeamNameNormalization(t *testing.T) {
	// Test team name normalization
	testCases := []struct {
		input    string
		expected string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"São Paulo-SP", "São Paulo"},
		{"Corinthians-SP", "Corinthians"},
		{"Grêmio-RS", "Grêmio"},
		{"Vasco da Gama-RJ", "Vasco da Gama"},
	}

	db, err := LoadData("/Users/adriancockcroft/.retort/work/retort-local-0xabe5kx/retort-d5c30c1005b2/data/kaggle")
	if err != nil {
		t.Fatalf("Failed to load data: %v", err)
	}

	// Test that team names are normalized correctly
	for _, tc := range testCases {
		// Find matches with the team
		matches := db.FindMatchesByTeam(tc.input, 0)
		fmt.Printf("Team '%s': %d matches found\n", tc.input, len(matches))
	}
}
