package main

import (
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

var (
	loadOnce sync.Once
	loaded   *Dataset
)

// sharedDataset loads the full dataset once for reuse across tests.
func sharedDataset(t *testing.T) *Dataset {
	t.Helper()
	loadOnce.Do(func() {
		dir := filepath.Join("data", "kaggle")
		if _, err := os.Stat(dir); err != nil {
			t.Skipf("data directory missing: %v", err)
			return
		}
		ds, err := LoadDataset(dir)
		if err != nil {
			t.Fatalf("LoadDataset: %v", err)
		}
		loaded = ds
	})
	if loaded == nil {
		t.SkipNow()
	}
	return loaded
}

// Feature: Match Queries
// Scenario: Find matches between two teams.
func TestMatchQuery_FlamengoVsFluminense(t *testing.T) {
	// Given the match data is loaded
	ds := sharedDataset(t)
	// When I search for matches between Flamengo and Fluminense
	matches := ds.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
	// Then I should receive at least one match
	if len(matches) == 0 {
		t.Fatalf("expected at least one Fla-Flu match")
	}
	// And every returned match must involve both teams
	for _, m := range matches {
		flaOk := TeamMatches("Flamengo", m.HomeTeam) || TeamMatches("Flamengo", m.AwayTeam)
		fluOk := TeamMatches("Fluminense", m.HomeTeam) || TeamMatches("Fluminense", m.AwayTeam)
		if !flaOk || !fluOk {
			t.Errorf("match does not involve both teams: %s", FormatMatch(m))
		}
	}
}

// Scenario: Filter by season.
func TestMatchQuery_PalmeirasInSeason(t *testing.T) {
	ds := sharedDataset(t)
	matches := ds.FindMatches(MatchFilter{Team: "Palmeiras", Season: 2019})
	if len(matches) == 0 {
		t.Skip("no Palmeiras 2019 matches in dataset")
	}
	for _, m := range matches {
		if m.Season != 2019 {
			t.Errorf("expected season 2019, got %d", m.Season)
		}
	}
}

// Feature: Team Queries
// Scenario: Compute home record for Corinthians.
func TestTeamStats_CorinthiansHomeRecord(t *testing.T) {
	ds := sharedDataset(t)
	matches := ds.FindMatches(MatchFilter{Team: "Corinthians", Season: 2019, Competition: "Brasileirão"})
	if len(matches) == 0 {
		t.Skip("no Corinthians 2019 matches")
	}
	stats := ComputeTeamStats("Corinthians", matches, true, false)
	if stats.Matches == 0 {
		t.Fatalf("expected at least one home match")
	}
	if stats.Wins+stats.Draws+stats.Losses != stats.Matches {
		t.Errorf("W+D+L (%d) != Matches (%d)", stats.Wins+stats.Draws+stats.Losses, stats.Matches)
	}
}

// Feature: Player Queries
// Scenario: Find Brazilian players.
func TestPlayerQuery_BrazilianPlayers(t *testing.T) {
	ds := sharedDataset(t)
	if len(ds.Players) == 0 {
		t.Skip("no players loaded")
	}
	players := ds.FindPlayers(PlayerFilter{Nationality: "Brazil", Limit: 10})
	if len(players) == 0 {
		t.Fatalf("expected Brazilian players")
	}
	for _, p := range players {
		if !ContainsFold(p.Nationality, "Brazil") {
			t.Errorf("expected Brazil nationality, got %q", p.Nationality)
		}
	}
	// And: results are sorted by Overall descending.
	for i := 1; i < len(players); i++ {
		if players[i-1].Overall < players[i].Overall {
			t.Errorf("players not sorted: %d < %d", players[i-1].Overall, players[i].Overall)
		}
	}
}

// Feature: Competition Queries
// Scenario: Compute standings for a season.
func TestStandings_BrasileiraoComputable(t *testing.T) {
	ds := sharedDataset(t)
	matches := ds.FindMatches(MatchFilter{Competition: "Brasileirão", Season: 2019})
	if len(matches) == 0 {
		t.Skip("no Brasileirão 2019 matches")
	}
	table := Standings(matches)
	if len(table) == 0 {
		t.Fatalf("expected non-empty standings")
	}
	// And: top team has at least as many points as any other.
	top := table[0].Points
	for _, row := range table {
		if row.Points > top {
			t.Errorf("standings out of order: %s has %d > %d", row.Team, row.Points, top)
		}
	}
}

// Feature: Statistical Analysis
// Scenario: Average goals per match are within a sensible range.
func TestStats_AverageGoals(t *testing.T) {
	ds := sharedDataset(t)
	avg := AverageGoals(ds.Matches)
	if avg < 1.0 || avg > 5.0 {
		t.Errorf("average goals %.2f outside sensible range", avg)
	}
	hwr := HomeWinRate(ds.Matches)
	if hwr < 30 || hwr > 70 {
		t.Errorf("home win rate %.2f outside sensible range", hwr)
	}
}

// Scenario: Biggest wins sorted by margin desc.
func TestStats_BiggestWinsSorted(t *testing.T) {
	ds := sharedDataset(t)
	wins := ds.BiggestWins("", 0, 5)
	if len(wins) < 2 {
		t.Skip("not enough matches")
	}
	prev := abs(wins[0].HomeGoals - wins[0].AwayGoals)
	for _, m := range wins[1:] {
		cur := abs(m.HomeGoals - m.AwayGoals)
		if cur > prev {
			t.Errorf("biggest wins not sorted: %d after %d", cur, prev)
		}
		prev = cur
	}
}

// Scenario: Date filter excludes out-of-range matches.
func TestMatchQuery_DateFilter(t *testing.T) {
	ds := sharedDataset(t)
	from := time.Date(2019, 1, 1, 0, 0, 0, 0, time.UTC)
	to := time.Date(2019, 12, 31, 23, 59, 59, 0, time.UTC)
	matches := ds.FindMatches(MatchFilter{From: from, To: to})
	if len(matches) == 0 {
		t.Skip("no 2019 matches")
	}
	for _, m := range matches {
		if m.Date.Before(from) || m.Date.After(to) {
			t.Errorf("match outside range: %s", m.Date)
		}
	}
}

// Scenario: Head-to-head conservation: A wins + B wins + draws = matches.
func TestHeadToHead_Consistency(t *testing.T) {
	ds := sharedDataset(t)
	matches := ds.FindMatches(MatchFilter{Team: "Palmeiras", Opponent: "Santos"})
	if len(matches) == 0 {
		t.Skip("no Palmeiras vs Santos matches")
	}
	h := ComputeHeadToHead("Palmeiras", "Santos", matches)
	if h.AWins+h.BWins+h.Draws != h.Matches {
		t.Errorf("inconsistency: %d+%d+%d != %d", h.AWins, h.BWins, h.Draws, h.Matches)
	}
}

// Scenario: Search players by club.
func TestPlayerQuery_ClubFilter(t *testing.T) {
	ds := sharedDataset(t)
	if len(ds.Players) == 0 {
		t.Skip("no players loaded")
	}
	players := ds.FindPlayers(PlayerFilter{Club: "Flamengo"})
	if len(players) == 0 {
		t.Skip("no Flamengo players in FIFA dataset")
	}
	for _, p := range players {
		if !ContainsFold(p.Club, "Flamengo") {
			t.Errorf("player %s has club %s, expected Flamengo", p.Name, p.Club)
		}
	}
}
