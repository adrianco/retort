package main

import (
	"strings"
	"testing"
)

func newTestStore() *Store {
	store := NewStore()

	// Add test matches
	matches := []Match{
		{DateTime: "2023-09-03", HomeTeam: "Flamengo", AwayTeam: "Fluminense", HomeScore: 2, AwayScore: 1, Season: 2023, Round: "22", Competition: "Brasileirao", Source: "test"},
		{DateTime: "2023-05-28", HomeTeam: "Fluminense", AwayTeam: "Flamengo", HomeScore: 1, AwayScore: 0, Season: 2023, Round: "8", Competition: "Brasileirao", Source: "test"},
		{DateTime: "2023-04-15", HomeTeam: "Flamengo", AwayTeam: "Santos", HomeScore: 3, AwayScore: 0, Season: 2023, Round: "5", Competition: "Brasileirao", Source: "test"},
		{DateTime: "2023-06-20", HomeTeam: "Santos", AwayTeam: "Flamengo", HomeScore: 1, AwayScore: 1, Season: 2023, Round: "10", Competition: "Brasileirao", Source: "test"},
		{DateTime: "2022-11-10", HomeTeam: "Palmeiras", AwayTeam: "Sao Paulo", HomeScore: 1, AwayScore: 0, Season: 2022, Round: "1", Competition: "Brasileirao", Source: "test"},
		{DateTime: "2023-07-01", HomeTeam: "Flamengo", AwayTeam: "Corinthians", HomeScore: 5, AwayScore: 0, Season: 2023, Round: "12", Competition: "Brasileirao", Source: "test"},
		{DateTime: "2023-08-15", HomeTeam: "Flamengo", AwayTeam: "Palmeiras", HomeScore: 0, AwayScore: 2, Season: 2023, Round: "18", Competition: "Brasileirao", Source: "test"},
		{DateTime: "2023-10-01", HomeTeam: "Corinthians", AwayTeam: "Palmeiras", HomeScore: 2, AwayScore: 2, Season: 2023, Round: "25", Competition: "Brasileirao", Source: "test"},
	}

	players := []Player{
		{ID: 1, Name: "Neymar Jr", Age: 31, Nationality: "Brazil", Overall: 92, Potential: 92, Club: "Al Hilal", Position: "LW"},
		{ID: 2, Name: "Gabriel Barbosa", Age: 26, Nationality: "Brazil", Overall: 82, Potential: 85, Club: "Flamengo", Position: "ST"},
		{ID: 3, Name: "Ederson", Age: 30, Nationality: "Brazil", Overall: 88, Potential: 88, Club: "Manchester City", Position: "GK"},
		{ID: 4, Name: "Marquinhos", Age: 29, Nationality: "Brazil", Overall: 87, Potential: 88, Club: "Paris Saint-Germain", Position: "CB"},
		{ID: 5, Name: "Bruno Henrique", Age: 33, Nationality: "Brazil", Overall: 78, Potential: 78, Club: "Flamengo", Position: "LW"},
		{ID: 6, Name: "Luis Suarez", Age: 36, Nationality: "Uruguay", Overall: 87, Potential: 87, Club: "Inter Miami", Position: "ST"},
		{ID: 7, Name: "Vinicius Jr", Age: 23, Nationality: "Brazil", Overall: 90, Potential: 95, Club: "Real Madrid", Position: "LW"},
		{ID: 8, Name: "Raphinha", Age: 27, Nationality: "Brazil", Overall: 84, Potential: 86, Club: "Barcelona", Position: "RW"},
	}

	store.AddMatches(matches)
	store.AddPlayers(players)
	return store
}

func TestStore_SearchMatches(t *testing.T) {
	store := newTestStore()

	// Search by team
	matches := store.SearchMatches("Flamengo", "", "", "", "")
	if len(matches) == 0 {
		t.Fatal("Expected Flamengo matches")
	}
	t.Logf("Found %d matches involving Flamengo", len(matches))

	// Verify all matches contain Flamengo
	for _, m := range matches {
		if m.HomeTeam != "Flamengo" && m.AwayTeam != "Flamengo" {
			t.Errorf("Match %s %d-%d %s does not contain Flamengo", m.HomeTeam, m.HomeScore, m.AwayScore, m.AwayTeam)
		}
	}
}

func TestStore_SearchMatches_ByCompetition(t *testing.T) {
	store := newTestStore()

	matches := store.SearchMatches("", "Brasileirao", "", "", "")
	if len(matches) == 0 {
		t.Fatal("Expected Brasileirao matches")
	}
	for _, m := range matches {
		if m.Competition != "Brasileirao" {
			t.Errorf("Wrong competition: %s", m.Competition)
		}
	}
	t.Logf("Found %d Brasileirao matches", len(matches))
}

func TestStore_SearchMatches_BySeason(t *testing.T) {
	store := newTestStore()

	matches := store.SearchMatches("Flamengo", "", "2023", "", "")
	if len(matches) == 0 {
		t.Fatal("Expected Flamengo 2023 matches")
	}
	for _, m := range matches {
		if m.Season != 2023 {
			t.Errorf("Wrong season: %d", m.Season)
		}
	}
	t.Logf("Found %d Flamengo matches in 2023", len(matches))
}

func TestStore_SearchMatches_ByDateRange(t *testing.T) {
	store := newTestStore()

	matches := store.SearchMatches("Flamengo", "", "", "2023-06-01", "2023-09-30")
	if len(matches) == 0 {
		t.Fatal("Expected Flamengo matches in date range")
	}
	for _, m := range matches {
		if m.DateTime < "2023-06-01" || m.DateTime > "2023-09-30" {
			t.Errorf("Match %s outside date range", m.DateTime)
		}
	}
	t.Logf("Found %d Flamengo matches in date range", len(matches))
}

func TestStore_TeamStats(t *testing.T) {
	store := newTestStore()

	stats := store.TeamStats("Flamengo", "Brasileirao", "2023")
	if stats.Matches == 0 {
		t.Fatal("Expected Flamengo Brasileirao 2023 stats")
	}
	if stats.Wins+stats.Draws+stats.Losses != stats.Matches {
		t.Errorf("Wins (%d) + Draws (%d) + Losses (%d) != Matches (%d)",
			stats.Wins, stats.Draws, stats.Losses, stats.Matches)
	}
	t.Logf("Flamengo 2023 Brasileirao: %d matches, %dW-%dD-%dL, %.1f%% win rate",
		stats.Matches, stats.Wins, stats.Draws, stats.Losses, stats.WinRate)
}

func TestStore_HeadToHead(t *testing.T) {
	store := newTestStore()

	record := store.HeadToHead("Flamengo", "Fluminense")
	if record.TotalMatches == 0 {
		t.Fatal("Expected Flamengo vs Fluminense matches")
	}
	if record.Team1Wins+record.Team2Wins+record.Draws != record.TotalMatches {
		t.Errorf("Team1Wins (%d) + Team2Wins (%d) + Draws (%d) != TotalMatches (%d)",
			record.Team1Wins, record.Team2Wins, record.Draws, record.TotalMatches)
	}
	t.Logf("Flamengo vs Fluminense: %d matches, %d W-%d D-%d L",
		record.TotalMatches, record.Team1Wins, record.Draws, record.Team2Wins)
}

func TestStore_SearchPlayers(t *testing.T) {
	store := newTestStore()

	// Search by name
	players := store.SearchPlayers("Gabriel", "", "", "")
	if len(players) == 0 {
		t.Fatal("Expected Gabriel players")
	}
	for _, p := range players {
		if !stringContains(p.Name, "Gabriel") {
			t.Errorf("Player %s does not contain Gabriel", p.Name)
		}
	}
	t.Logf("Found %d players with 'Gabriel' in name", len(players))

	// Search by nationality
	brazilians := store.SearchPlayers("", "Brazil", "", "")
	if len(brazilians) == 0 {
		t.Fatal("Expected Brazilian players")
	}
	t.Logf("Found %d Brazilian players", len(brazilians))

	// Search by club
	flamengoPlayers := store.SearchPlayers("", "", "Flamengo", "")
	if len(flamengoPlayers) == 0 {
		t.Fatal("Expected Flamengo players")
	}
	t.Logf("Found %d Flamengo players", len(flamengoPlayers))

	// Search by position
	forwards := store.SearchPlayers("", "", "", "ST")
	if len(forwards) == 0 {
		t.Fatal("Expected ST players")
	}
	t.Logf("Found %d ST players", len(forwards))
}

func TestStore_CompetitionStandings(t *testing.T) {
	store := newTestStore()

	table := store.CompetitionStandings("Brasileirao", "2023")
	if len(table) == 0 {
		t.Fatal("Expected standings")
	}
	entries := make([]StandingsEntry, 0, len(table))
	for _, e := range table {
		entries = append(entries, *e)
	}
	if len(entries) == 0 {
		t.Fatal("Expected non-empty standings entries")
	}
	// Sort by points
	sortStandings(entries)
	t.Logf("Top team: %s with %d points (%dW-%dD-%dL)",
		entries[0].Team, entries[0].Points, entries[0].Wins, entries[0].Draws, entries[0].Losses)
}

func TestStore_BiggestWins(t *testing.T) {
	store := newTestStore()

	wins := store.BiggestWins("Brasileirao", 10)
	if len(wins) == 0 {
		t.Log("No big wins found (expected for small test set)")
	}
	// Verify all have diff >= 5
	for _, w := range wins {
		diff := w.HomeScore - w.AwayScore
		if diff < 0 {
			diff = -diff
		}
		if diff < 5 {
			t.Errorf("Win %s %d-%d %s has diff %d < 5",
				w.HomeTeam, w.HomeScore, w.AwayScore, w.AwayTeam, diff)
		}
	}
	t.Logf("Found %d big wins", len(wins))
}

func TestStore_StatsAnalysis(t *testing.T) {
	store := newTestStore()

	stats := store.StatsAnalysis("Brasileirao", "2023")
	if stats.TotalMatches == 0 {
		t.Fatal("Expected non-zero stats")
	}
	if stats.TotalGoals == 0 {
		t.Error("Expected non-zero total goals")
	}
	if stats.AvgGoalsPerMatch <= 0 {
		t.Error("Expected positive avg goals per match")
	}

	// Check win rates sum to ~100%
	totalRate := stats.HomeWinRate + stats.DrawRate + stats.AwayWinRate
	if totalRate < 90 || totalRate > 110 {
		t.Errorf("Win rates sum to %.1f%%, expected ~100%%", totalRate)
	}
	t.Logf("Stats: %d matches, %.2f avg goals, H: %.1f%% D: %.1f%% A: %.1f%%",
		stats.TotalMatches, stats.AvgGoalsPerMatch, stats.HomeWinRate, stats.DrawRate, stats.AwayWinRate)
}

func TestStore_NonExistentTeam(t *testing.T) {
	store := newTestStore()

	matches := store.SearchMatches("NonExistentTeam", "", "", "", "")
	if len(matches) != 0 {
		t.Errorf("Expected 0 matches for non-existent team, got %d", len(matches))
	}

	stats := store.TeamStats("NonExistentTeam", "", "")
	if stats.Matches != 0 {
		t.Errorf("Expected 0 matches for non-existent team stats, got %d", stats.Matches)
	}
}

func TestStore_FormattedH2H(t *testing.T) {
	store := newTestStore()
	record := store.HeadToHead("Flamengo", "Fluminense")
	formatted := FormatH2H(record)
	if len(formatted) == 0 {
		t.Error("Expected non-empty formatted H2H")
	}
	t.Logf("Formatted H2H:\n%s", formatted)
}

func TestStore_FormattedStandings(t *testing.T) {
	store := newTestStore()
	table := store.CompetitionStandings("Brasileirao", "2023")
	entries := make([]StandingsEntry, 0, len(table))
	for _, e := range table {
		e.GoalDiff = e.GoalsFor - e.GoalsAgainst
		entries = append(entries, *e)
	}
	sortStandings(entries)
	formatted := FormatStandings(entries)
	if len(formatted) == 0 {
		t.Error("Expected non-empty formatted standings")
	}
	if len(formatted) < 50 {
		t.Error("Formatted standings too short")
	}
	t.Logf("Formatted standings:\n%s", formatted)
}

func TestStore_NilPlayerSearch(t *testing.T) {
	store := newTestStore()
	players := store.SearchPlayers("", "", "", "")
	if len(players) == 0 {
		t.Fatal("Expected all players")
	}
	t.Logf("Returned %d players for nil filter", len(players))
}

func TestMatchFormat(t *testing.T) {
	m := Match{
		DateTime: "2023-09-03",
		HomeTeam: "Flamengo",
		AwayTeam: "Fluminense",
		HomeScore: 2,
		AwayScore: 1,
		Round: "22",
		Competition: "Brasileirao",
	}
	formatted := MatchFormat(m)
	expected := "2023-09-03: Flamengo 2-1 Fluminense (Round 22) (Brasileirao)"
	if formatted != expected {
		t.Errorf("MatchFormat = %q, want %q", formatted, expected)
	}
}

func TestFormatPlayer(t *testing.T) {
	p := Player{Name: "Neymar Jr", Overall: 92, Age: 31, Position: "LW", Club: "Al Hilal"}
	formatted := FormatPlayer(p)
	expected := "Neymar Jr (Overall: 92, Age: 31, Pos: LW, Club: Al Hilal)"
	if formatted != expected {
		t.Errorf("FormatPlayer = %q, want %q", formatted, expected)
	}
}

// Helper functions
func stringContains(s, substr string) bool {
	return strings.Contains(s, substr)
}

