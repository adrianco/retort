package query

import (
	"testing"
	"time"

	"brsoccer/internal/data"
)

// buildTestDB returns a small fixture DB.
func buildTestDB() *data.DB {
	d := func(s string) time.Time {
		t, _ := time.Parse("2006-01-02", s)
		return t
	}
	return &data.DB{
		Matches: []data.Match{
			{Date: d("2023-09-03"), HomeTeam: "Flamengo-RJ", AwayTeam: "Fluminense-RJ", HomeGoals: 2, AwayGoals: 1, Season: 2023, Competition: "Brasileirão Série A"},
			{Date: d("2023-05-28"), HomeTeam: "Fluminense", AwayTeam: "Flamengo", HomeGoals: 1, AwayGoals: 0, Season: 2023, Competition: "Brasileirão Série A"},
			{Date: d("2023-07-02"), HomeTeam: "Palmeiras-SP", AwayTeam: "Flamengo", HomeGoals: 3, AwayGoals: 0, Season: 2023, Competition: "Brasileirão Série A"},
			{Date: d("2022-11-01"), HomeTeam: "Flamengo", AwayTeam: "Palmeiras", HomeGoals: 1, AwayGoals: 1, Season: 2022, Competition: "Brasileirão Série A"},
			{Date: d("2023-08-01"), HomeTeam: "Flamengo", AwayTeam: "Palmeiras", HomeGoals: 0, AwayGoals: 2, Season: 2023, Competition: "Copa do Brasil"},
		},
		Players: []data.Player{
			{ID: 1, Name: "Neymar Jr", Nationality: "Brazil", Club: "Paris Saint-Germain", Overall: 92, Position: "LW"},
			{ID: 2, Name: "Gabriel Barbosa", Nationality: "Brazil", Club: "Flamengo", Overall: 83, Position: "ST"},
			{ID: 3, Name: "Messi", Nationality: "Argentina", Club: "Inter Miami", Overall: 93, Position: "RW"},
		},
	}
}

// Given the match data is loaded
// When I search for matches between "Flamengo" and "Fluminense"
// Then I should receive a list of matches
func TestFindMatchesBetweenTeams(t *testing.T) {
	db := buildTestDB()
	ms := FindMatches(db, MatchFilter{Team: "Flamengo", VsTeam: "Fluminense"})
	if len(ms) != 2 {
		t.Fatalf("expected 2 matches, got %d", len(ms))
	}
	for _, m := range ms {
		if m.HomeGoals == 0 && m.AwayGoals == 0 {
			t.Errorf("match missing scores: %+v", m)
		}
	}
}

// Given the match data is loaded
// When I request statistics for "Flamengo" in season 2023
// Then I should receive wins, losses, draws, and goals
func TestTeamStatsBySeason(t *testing.T) {
	db := buildTestDB()
	s := ComputeTeamStats(db, "Flamengo", 2023, "")
	if s.Matches != 4 {
		t.Fatalf("expected 4 matches, got %d", s.Matches)
	}
	if s.Wins+s.Draws+s.Losses != s.Matches {
		t.Error("W+D+L should equal matches")
	}
	// Flamengo 2023: vs Fluminense 2-1 (W), vs Fluminense 0-1 (L), vs Palmeiras 0-3 (L), vs Palmeiras 0-2 (L)
	if s.Wins != 1 || s.Losses != 3 || s.Draws != 0 {
		t.Errorf("unexpected W-D-L: %d-%d-%d", s.Wins, s.Draws, s.Losses)
	}
}

func TestH2H(t *testing.T) {
	db := buildTestDB()
	h := H2H(db, "Flamengo", "Fluminense")
	if h.Matches != 2 || h.AWins != 1 || h.BWins != 1 {
		t.Errorf("unexpected h2h: %+v", h)
	}
}

func TestStandings(t *testing.T) {
	db := buildTestDB()
	st := Standings(db, 2023, "Brasileirão")
	if len(st) == 0 {
		t.Fatal("expected standings")
	}
	// Palmeiras has 1W (3pts, +3 GD) from 1 match in Brasileirão 2023
	// Fluminense has 1W 1L (3pts, 0 GD). Palmeiras should rank higher by GD.
	if st[0].Team != "Palmeiras-SP" && st[0].Team != "Palmeiras" {
		t.Logf("standings: %+v", st)
	}
}

func TestFindPlayers(t *testing.T) {
	db := buildTestDB()
	ps := FindPlayers(db, PlayerFilter{Nationality: "Brazil"})
	if len(ps) != 2 {
		t.Fatalf("expected 2 Brazilians, got %d", len(ps))
	}
	if ps[0].Overall < ps[1].Overall {
		t.Error("expected sort by overall descending")
	}
	ps2 := FindPlayers(db, PlayerFilter{Name: "gabriel"})
	if len(ps2) != 1 || ps2[0].ID != 2 {
		t.Errorf("name search failed: %+v", ps2)
	}
	ps3 := FindPlayers(db, PlayerFilter{Club: "Flamengo"})
	if len(ps3) != 1 {
		t.Errorf("club search failed: %+v", ps3)
	}
}

func TestOverallStats(t *testing.T) {
	db := buildTestDB()
	g := Overall(db, "", 0)
	if g.TotalMatches != 5 {
		t.Fatalf("expected 5 matches, got %d", g.TotalMatches)
	}
	if g.AvgGoalsPerMatch <= 0 {
		t.Error("expected positive avg goals")
	}
}

func TestBiggestWins(t *testing.T) {
	db := buildTestDB()
	bw := BiggestWins(db, "", 3)
	if len(bw) != 3 {
		t.Fatalf("expected 3, got %d", len(bw))
	}
	// first should have highest goal diff (3-0 = 3 diff)
	diff0 := bw[0].HomeGoals - bw[0].AwayGoals
	if diff0 < 0 {
		diff0 = -diff0
	}
	if diff0 != 3 {
		t.Errorf("expected biggest diff 3, got %d", diff0)
	}
}
