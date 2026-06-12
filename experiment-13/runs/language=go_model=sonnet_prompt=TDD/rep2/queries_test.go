package main

import (
	"testing"
	"time"
)

var testDB = &Database{
	Brasileirao: []Match{
		{HomeTeam: "Palmeiras-SP", AwayTeam: "Flamengo-RJ", HomeGoals: 2, AwayGoals: 1, Season: 2020, Competition: CompBrasileirao},
		{HomeTeam: "Flamengo-RJ", AwayTeam: "Palmeiras-SP", HomeGoals: 1, AwayGoals: 0, Season: 2020, Competition: CompBrasileirao},
		{HomeTeam: "São Paulo-SP", AwayTeam: "Corinthians-SP", HomeGoals: 0, AwayGoals: 0, Season: 2021, Competition: CompBrasileirao},
		{HomeTeam: "Palmeiras-SP", AwayTeam: "São Paulo-SP", HomeGoals: 3, AwayGoals: 1, Season: 2021, Competition: CompBrasileirao},
	},
	Copa: []Match{
		{HomeTeam: "Flamengo", AwayTeam: "Palmeiras", HomeGoals: 2, AwayGoals: 0, Season: 2020, Competition: CompCopa},
	},
}

func TestSearchMatches_ByTeam(t *testing.T) {
	results := SearchMatches(testDB, "Palmeiras", "", "", "", 0, time.Time{}, time.Time{}, 100)
	// Brasileirao: rows 1,2,4 (Palmeiras home or away) + Copa row = 4 total
	if len(results) != 4 {
		t.Errorf("expected 4 matches for Palmeiras (3 in Brasileirao + 1 in Copa), got %d", len(results))
	}
}

func TestSearchMatches_ByCompetition(t *testing.T) {
	results := SearchMatches(testDB, "", "", "", "brasileirao", 0, time.Time{}, time.Time{}, 100)
	for _, m := range results {
		if m.Competition != CompBrasileirao {
			t.Errorf("expected only brasileirao matches, got %q", m.Competition)
		}
	}
	if len(results) != 4 {
		t.Errorf("expected 4 brasileirao matches, got %d", len(results))
	}
}

func TestSearchMatches_BySeason(t *testing.T) {
	results := SearchMatches(testDB, "", "", "", "", 2020, time.Time{}, time.Time{}, 100)
	for _, m := range results {
		if m.Season != 2020 {
			t.Errorf("expected only 2020 matches, got season %d", m.Season)
		}
	}
	if len(results) != 3 {
		t.Errorf("expected 3 matches in 2020, got %d", len(results))
	}
}

func TestHeadToHead_ReturnsCorrectStats(t *testing.T) {
	// Palmeiras vs Flamengo across all competitions:
	// Brasileirao row1: Palmeiras 2-1 Flamengo -> Palmeiras WIN
	// Brasileirao row2: Flamengo 1-0 Palmeiras -> Palmeiras LOSS
	// Copa row: Flamengo 2-0 Palmeiras -> Palmeiras LOSS
	h2h := HeadToHead(testDB, "Palmeiras", "Flamengo", "", 0)
	wins, _ := h2h["wins"].(int)
	losses, _ := h2h["losses"].(int)
	draws, _ := h2h["draws"].(int)
	if wins != 1 {
		t.Errorf("expected 1 win for Palmeiras vs Flamengo, got %d", wins)
	}
	if losses != 2 {
		t.Errorf("expected 2 losses for Palmeiras vs Flamengo (1 Brasileirao + 1 Copa), got %d", losses)
	}
	if draws != 0 {
		t.Errorf("expected 0 draws, got %d", draws)
	}
}

func TestHeadToHead_FilteredByCompetition(t *testing.T) {
	// Only Brasileirao: Palmeiras W1 L1
	h2h := HeadToHead(testDB, "Palmeiras", "Flamengo", "brasileirao", 0)
	wins, _ := h2h["wins"].(int)
	losses, _ := h2h["losses"].(int)
	if wins != 1 {
		t.Errorf("expected 1 win (brasileirao only), got %d", wins)
	}
	if losses != 1 {
		t.Errorf("expected 1 loss (brasileirao only), got %d", losses)
	}
}

func TestGetTeamStats_ComputesCorrectly(t *testing.T) {
	stats := GetTeamStats(testDB, "Palmeiras", "brasileirao", 2020)
	if stats == nil {
		t.Fatal("expected non-nil stats")
	}
	if stats.Wins != 1 {
		t.Errorf("expected 1 win, got %d", stats.Wins)
	}
	if stats.Losses != 1 {
		t.Errorf("expected 1 loss, got %d", stats.Losses)
	}
	if stats.GoalsFor != 2 {
		t.Errorf("expected 2 goals for, got %d", stats.GoalsFor)
	}
	if stats.GoalsAgainst != 2 {
		t.Errorf("expected 2 goals against, got %d", stats.GoalsAgainst)
	}
}

func TestGetStandings_CalculatesPoints(t *testing.T) {
	standings := GetStandings(testDB, 2020, "brasileirao")
	if len(standings) == 0 {
		t.Fatal("expected non-empty standings")
	}
	// Check that points = wins*3 + draws*1
	for _, s := range standings {
		expected := s.Wins*3 + s.Draws
		if s.Points != expected {
			t.Errorf("team %s: expected %d points (W=%d D=%d), got %d", s.Team, expected, s.Wins, s.Draws, s.Points)
		}
	}
	// Standings should be sorted descending by points
	for i := 1; i < len(standings); i++ {
		if standings[i].Points > standings[i-1].Points {
			t.Errorf("standings not sorted: pos %d (%d pts) > pos %d (%d pts)",
				i+1, standings[i].Points, i, standings[i-1].Points)
		}
	}
}
