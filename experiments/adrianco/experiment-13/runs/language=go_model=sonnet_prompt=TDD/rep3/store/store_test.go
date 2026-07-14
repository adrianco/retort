package store

import (
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func testStore(t *testing.T) *Store {
	t.Helper()
	_, file, _, _ := runtime.Caller(0)
	dir := filepath.Dir(filepath.Dir(file))
	dataDir := filepath.Join(dir, "data", "kaggle")

	s, err := New(dataDir)
	if err != nil {
		t.Fatalf("New store: %v", err)
	}
	return s
}

func TestNewStore(t *testing.T) {
	s := testStore(t)
	if len(s.Brasileirao) == 0 {
		t.Error("Brasileirao matches not loaded")
	}
	if len(s.Cup) == 0 {
		t.Error("Cup matches not loaded")
	}
	if len(s.Libertadores) == 0 {
		t.Error("Libertadores matches not loaded")
	}
	if len(s.Extended) == 0 {
		t.Error("Extended matches not loaded")
	}
	if len(s.Historical) == 0 {
		t.Error("Historical matches not loaded")
	}
	if len(s.Players) == 0 {
		t.Error("Players not loaded")
	}
}

func TestFindMatchesByTeam(t *testing.T) {
	s := testStore(t)
	results := s.FindMatchesByTeam("Flamengo")
	if len(results) == 0 {
		t.Fatal("expected Flamengo matches, got none")
	}
	// All results should have "flamengo" as a substring in home or away team (case-insensitive)
	for _, m := range results {
		home := strings.ToLower(m.HomeTeam)
		away := strings.ToLower(m.AwayTeam)
		if !strings.Contains(home, "flamengo") && !strings.Contains(away, "flamengo") {
			t.Errorf("match does not involve Flamengo: %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
}

func TestFindMatchesBySeason(t *testing.T) {
	s := testStore(t)
	results := s.FindMatchesBySeason(2019)
	if len(results) == 0 {
		t.Fatal("expected 2019 matches, got none")
	}
	for _, m := range results {
		if m.Season != 2019 {
			t.Errorf("expected season 2019, got %d", m.Season)
		}
	}
}

func TestFindHeadToHead(t *testing.T) {
	s := testStore(t)
	h2h := s.HeadToHead("Flamengo", "Fluminense")
	if h2h.Total == 0 {
		t.Fatal("expected Flamengo vs Fluminense matches")
	}
	if h2h.Team1Wins+h2h.Team2Wins+h2h.Draws != h2h.Total {
		t.Errorf("wins+draws(%d) != total(%d)", h2h.Team1Wins+h2h.Team2Wins+h2h.Draws, h2h.Total)
	}
}

func TestGetTeamStats(t *testing.T) {
	s := testStore(t)
	stats := s.TeamStats("Palmeiras", 2022) // data goes up to 2022
	if stats.Played == 0 {
		t.Fatal("expected Palmeiras 2022 stats")
	}
	if stats.Wins+stats.Draws+stats.Losses != stats.Played {
		t.Errorf("W+D+L(%d) != played(%d)", stats.Wins+stats.Draws+stats.Losses, stats.Played)
	}
}

func TestFindPlayersByName(t *testing.T) {
	s := testStore(t)
	players := s.FindPlayersByName("Neymar")
	if len(players) == 0 {
		t.Fatal("expected Neymar, got none")
	}
}

func TestFindPlayersByNationality(t *testing.T) {
	s := testStore(t)
	players := s.FindPlayersByNationality("Brazil")
	if len(players) == 0 {
		t.Fatal("expected Brazilian players, got none")
	}
	for _, p := range players {
		if p.Nationality != "Brazil" {
			t.Errorf("expected Brazil, got %q", p.Nationality)
		}
	}
}

func TestFindPlayersByClub(t *testing.T) {
	s := testStore(t)
	// Use Cruzeiro - a Brazilian club present in the FIFA dataset
	players := s.FindPlayersByClub("Cruzeiro")
	if len(players) == 0 {
		t.Fatal("expected Cruzeiro players, got none")
	}
}

func TestLeagueStandings(t *testing.T) {
	s := testStore(t)
	standings := s.LeagueStandings(2019)
	if len(standings) == 0 {
		t.Fatal("expected 2019 standings")
	}
	// First place should have most points
	if standings[0].Points < standings[len(standings)-1].Points {
		t.Error("standings not sorted by points descending")
	}
}

func TestBiggestWins(t *testing.T) {
	s := testStore(t)
	wins := s.BiggestWins(5)
	if len(wins) == 0 {
		t.Fatal("expected biggest wins")
	}
	for i := 0; i < len(wins)-1; i++ {
		diff0 := wins[i].GoalDiff
		diff1 := wins[i+1].GoalDiff
		if diff0 < diff1 {
			t.Errorf("wins[%d].diff(%d) < wins[%d].diff(%d)", i, diff0, i+1, diff1)
		}
	}
}

func TestAverageGoalsPerMatch(t *testing.T) {
	s := testStore(t)
	avg := s.AverageGoalsPerMatch()
	if avg <= 0 || avg > 20 {
		t.Errorf("unreasonable average goals per match: %f", avg)
	}
}
