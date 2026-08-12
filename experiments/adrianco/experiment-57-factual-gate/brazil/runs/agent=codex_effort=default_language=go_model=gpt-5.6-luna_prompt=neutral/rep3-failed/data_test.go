package main

import (
	"os"
	"path/filepath"
	"testing"
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
