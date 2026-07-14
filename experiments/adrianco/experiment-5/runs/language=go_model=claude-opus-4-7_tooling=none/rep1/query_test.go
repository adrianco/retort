package main

import (
	"strings"
	"testing"
	"time"
)

// Helper: build a tiny in-memory store for unit testing the query layer
// without depending on the on-disk CSVs.
func miniStore() *DataStore {
	ds := NewDataStore()
	mk := func(date, home, away string, hg, ag int, comp string, season int) Match {
		t, _ := time.Parse("2006-01-02", date)
		return Match{
			Competition: comp,
			Date:        t,
			HomeTeam:    home,
			AwayTeam:    away,
			HomeKey:     NormalizeTeam(home),
			AwayKey:     NormalizeTeam(away),
			HomeGoals:   hg,
			AwayGoals:   ag,
			Season:      season,
		}
	}
	ds.Matches = []Match{
		mk("2023-09-03", "Flamengo", "Fluminense", 2, 1, "Brasileirão", 2023),
		mk("2023-05-28", "Fluminense", "Flamengo", 1, 0, "Brasileirão", 2023),
		mk("2023-02-10", "Flamengo", "Palmeiras", 3, 0, "Brasileirão", 2023),
		mk("2022-08-01", "Palmeiras", "Flamengo", 1, 1, "Brasileirão", 2022),
		mk("2019-12-01", "Flamengo", "Santos", 6, 1, "Brasileirão", 2019),
	}
	ds.Players = []Player{
		{ID: 1, Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Club: "Paris Saint-Germain", ClubKey: NormalizeTeam("Paris Saint-Germain"), Position: "LW"},
		{ID: 2, Name: "Gabriel Barbosa", Nationality: "Brazil", Overall: 85, Club: "Flamengo", ClubKey: NormalizeTeam("Flamengo"), Position: "ST"},
		{ID: 3, Name: "Lionel Messi", Nationality: "Argentina", Overall: 94, Club: "FC Barcelona", ClubKey: NormalizeTeam("FC Barcelona"), Position: "RW"},
	}
	ds.buildIndexes()
	return ds
}

// Feature: find matches between two teams.
func TestFindMatches_HeadToHead(t *testing.T) {
	ds := miniStore()
	matches := ds.FindMatches(MatchFilter{Team1: "Flamengo", Team2: "Fluminense"})
	if len(matches) != 2 {
		t.Fatalf("expected 2 Fla-Flu matches, got %d", len(matches))
	}
	// Newest first.
	if matches[0].Date.Before(matches[1].Date) {
		t.Errorf("results not sorted newest first")
	}
}

// Feature: filter by season.
func TestFindMatches_BySeason(t *testing.T) {
	ds := miniStore()
	matches := ds.FindMatches(MatchFilter{Team1: "Flamengo", Season: 2023})
	for _, m := range matches {
		if m.Season != 2023 {
			t.Errorf("expected season 2023, got %d", m.Season)
		}
	}
	if len(matches) != 3 {
		t.Errorf("expected 3 Flamengo 2023 matches, got %d", len(matches))
	}
}

// Feature: team stats aggregation.
func TestComputeTeamStats(t *testing.T) {
	ds := miniStore()
	matches := ds.FindMatches(MatchFilter{Team1: "Flamengo"})
	stats := ComputeTeamStats("Flamengo", matches)
	if stats.Matches != 5 {
		t.Errorf("matches = %d, want 5", stats.Matches)
	}
	// 2-1, 0-1 (away loss), 3-0, 1-1, 6-1 → 3W, 1D, 1L
	if stats.Wins != 3 || stats.Draws != 1 || stats.Losses != 1 {
		t.Errorf("W/D/L = %d/%d/%d, want 3/1/1", stats.Wins, stats.Draws, stats.Losses)
	}
	if stats.Points != 3*3+1 {
		t.Errorf("points = %d, want 10", stats.Points)
	}
	// Goals: 2+0+3+1+6=12 for, 1+1+0+1+1=4 against.
	if stats.GoalsFor != 12 || stats.GoalsAgst != 4 {
		t.Errorf("goals %d/%d, want 12/4", stats.GoalsFor, stats.GoalsAgst)
	}
}

// Feature: head-to-head.
func TestComputeHeadToHead(t *testing.T) {
	ds := miniStore()
	matches := ds.FindMatches(MatchFilter{Team1: "Flamengo", Team2: "Fluminense"})
	h := ComputeHeadToHead("Flamengo", "Fluminense", matches)
	if h.Matches != 2 {
		t.Errorf("matches = %d, want 2", h.Matches)
	}
	if h.Team1Wins != 1 || h.Team2Wins != 1 || h.Draws != 0 {
		t.Errorf("h2h = %d/%d/%d, want 1/1/0",
			h.Team1Wins, h.Team2Wins, h.Draws)
	}
}

// Feature: standings.
func TestStandings(t *testing.T) {
	ds := miniStore()
	rows := ds.Standings("Brasileirão", 2023)
	if len(rows) == 0 {
		t.Fatal("expected standings rows")
	}
	// Flamengo: W vs Fluminense (3pt), L vs Fluminense (0), W vs Palmeiras (3) = 6 pts
	// Fluminense: L (0), W (3) = 3 pts
	// Palmeiras: L (0) = 0 pts
	flaPos := -1
	for i, r := range rows {
		if NormalizeTeam(r.Team) == "flamengo" {
			flaPos = i
			if r.Points != 6 {
				t.Errorf("Flamengo points = %d, want 6", r.Points)
			}
		}
	}
	if flaPos != 0 {
		t.Errorf("Flamengo not in 1st place, got pos %d", flaPos)
	}
}

// Feature: player search by nationality.
func TestFindPlayers_Nationality(t *testing.T) {
	ds := miniStore()
	br := ds.FindPlayers(PlayerFilter{Nationality: "Brazil"})
	if len(br) != 2 {
		t.Errorf("Brazilian players = %d, want 2", len(br))
	}
	// Sorted by overall desc.
	if br[0].Name != "Neymar Jr" {
		t.Errorf("top Brazilian = %q, want Neymar Jr", br[0].Name)
	}
}

// Feature: player search by name substring.
func TestFindPlayers_Name(t *testing.T) {
	ds := miniStore()
	res := ds.FindPlayers(PlayerFilter{Name: "Barbosa"})
	if len(res) != 1 || res[0].Name != "Gabriel Barbosa" {
		t.Errorf("Barbosa search = %v", res)
	}
}

// Feature: aggregate stats.
func TestComputeAggregate(t *testing.T) {
	ds := miniStore()
	a := ComputeAggregate(ds.Matches)
	if a.Matches != 5 {
		t.Errorf("matches %d, want 5", a.Matches)
	}
	// goals: 3, 1, 3, 2, 7 = 16
	if a.TotalGoals != 16 {
		t.Errorf("goals = %d, want 16", a.TotalGoals)
	}
}

// Feature: biggest wins (sorted by goal diff).
func TestBiggestWins(t *testing.T) {
	ds := miniStore()
	bw := BiggestWins(ds.Matches, 1)
	if len(bw) != 1 {
		t.Fatalf("len = %d", len(bw))
	}
	if !strings.Contains(bw[0].HomeTeam, "Flamengo") || bw[0].HomeGoals-bw[0].AwayGoals != 5 {
		t.Errorf("biggest win = %s %d-%d %s", bw[0].HomeTeam, bw[0].HomeGoals, bw[0].AwayGoals, bw[0].AwayTeam)
	}
}
