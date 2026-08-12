package main

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestLoadAndNormalize(t *testing.T) {
	d := t.TempDir()
	write := func(n, c string) {
		if e := os.WriteFile(filepath.Join(d, n), []byte(c), 0600); e != nil {
			t.Fatal(e)
		}
	}
	write("Brasileirao_Matches.csv", "datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round\n2023-01-01 12:00:00,Flamengo-RJ,RJ,Flu-RJ,RJ,2,1,2023,1\n")
	write("fifa_data.csv", "\ufeff,ID,Name,Age,Nationality,Overall,Potential,Club,Position\n0,7,Test Player,20,Brazil,85,90,Flamengo,ST\n")
	s, e := LoadStore(d)
	if e != nil {
		t.Fatal(e)
	}
	if len(s.Matches) != 1 || s.Matches[0].HomeGoals != 2 || len(s.Players) != 1 || s.Players[0].Name != "Test Player" {
		t.Fatalf("bad normalization: %+v %+v", s.Matches, s.Players)
	}
}
func TestQueries(t *testing.T) {
	s := &Server{Store: &Store{Matches: []Match{{Competition: "Brasileirão", Home: "Palmeiras-SP", Away: "Santos-SP", HomeGoals: 2, AwayGoals: 0, Season: 2022}, {Competition: "Brasileirão", Home: "Santos-SP", Away: "Palmeiras-SP", HomeGoals: 1, AwayGoals: 1, Season: 2022}}, Players: []Player{{Name: "Neymar", Nationality: "Brazil", Club: "Paris", Position: "LW", Overall: 92}}}}
	r := s.Stats("Palmeiras", MatchFilter{Season: 2022})
	if r.Wins != 1 || r.Draws != 1 || r.GoalsFor != 3 {
		t.Fatalf("stats: %+v", r)
	}
	if len(s.Players("ney", "", "", "", 90, 0)) != 1 {
		t.Fatal("player query")
	}
	s.Store.Players = append(s.Store.Players, Player{Name: "Lower Rated", Overall: 50})
	if got := s.Players("", "", "", "", 0, 1); got[0].Overall != 92 {
		t.Fatalf("player limit was applied before ranking: %+v", got)
	}
	if len(s.Standings(2022, "Brasileirão")) != 2 {
		t.Fatal("standings")
	}
}

func TestTeamNormalizationKeepsStatesDistinct(t *testing.T) {
	if !teamMatch("Palmeiras-SP", "Palmeiras") || !teamMatch("Atlético-MG", "Atletico-MG") {
		t.Fatal("expected accent and state-insensitive matching")
	}
	if teamMatch("Atletico-MG", "Atletico-PR") {
		t.Fatal("state-specific clubs must remain distinct")
	}
}

func TestDeduplicateMatchesAllowsOneDayDateDrift(t *testing.T) {
	day := time.Date(2019, 4, 28, 0, 0, 0, 0, time.UTC)
	got := deduplicateMatches([]Match{
		{Date: day, Season: 2019, Home: "Atletico-PR", Away: "Vasco da Gama-RJ", HomeGoals: 4, AwayGoals: 1},
		{Date: day.Add(23 * time.Hour), Season: 2019, Home: "Athletico-PR", Away: "Vasco da Gama", HomeGoals: 4, AwayGoals: 1},
	})
	if len(got) != 1 {
		t.Fatalf("deduplicated matches = %d, want 1", len(got))
	}
}

func TestStandingsCanonicalizeTeamRows(t *testing.T) {
	s := &Server{Store: &Store{Matches: []Match{
		{Season: 2019, Competition: "Brasileirão", Home: "Flamengo-RJ", Away: "Atletico-MG", HomeGoals: 2, AwayGoals: 0},
		{Season: 2019, Competition: "Brasileirão", Home: "Atlético-MG", Away: "Flamengo", HomeGoals: 1, AwayGoals: 1},
	}}}
	rows := s.Standings(2019, "Brasileirao")
	if len(rows) != 2 {
		t.Fatalf("rows = %d, want 2: %+v", len(rows), rows)
	}
	flamengo := s.Stats("Flamengo", MatchFilter{Season: 2019, Competition: "Brasileirao"})
	if flamengo.Matches != 2 || flamengo.Wins != 1 || flamengo.Draws != 1 {
		t.Fatalf("flamengo stats: %+v", flamengo)
	}
}
