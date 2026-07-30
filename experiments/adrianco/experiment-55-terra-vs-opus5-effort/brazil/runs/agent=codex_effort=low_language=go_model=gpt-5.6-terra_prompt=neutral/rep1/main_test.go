package main

import (
	"testing"
	"time"
)

func TestNormalization(t *testing.T) {
	if !teamMatch("São Paulo-SP", "Sao Paulo") {
		t.Fatal("accent/state normalization failed")
	}
	if !teamMatch("Flamengo-RJ", "Flamengo") {
		t.Fatal("suffix normalization failed")
	}
}
func TestQueries(t *testing.T) {
	d := &Database{Matches: []Match{{Date: time.Date(2023, 1, 1, 0, 0, 0, 0, time.UTC), Home: "Flamengo-RJ", Away: "Fluminense-RJ", HomeGoals: 2, AwayGoals: 1, Season: 2023, Competition: "Brasileirão"}, {Date: time.Date(2023, 1, 2, 0, 0, 0, 0, time.UTC), Home: "São Paulo-SP", Away: "Flamengo-RJ", HomeGoals: 0, AwayGoals: 0, Season: 2023, Competition: "Brasileirão"}}, Players: []Player{{Name: "Gabriel Barbosa", Nationality: "Brazil", Club: "Flamengo", Position: "ST", Overall: 82}}}
	r := searchMatches(d, map[string]any{"team": "Flamengo", "opponent": "Fluminense"}).(map[string]any)
	if r["count"].(int) != 1 {
		t.Fatal("match search")
	}
	v, e := teamStats(d, map[string]any{"team": "Flamengo", "season": float64(2023)})
	if e != nil || v.(map[string]any)["record"].(record).Matches != 2 {
		t.Fatal("stats")
	}
	p := players(d, map[string]any{"club": "Flamengo"}).(map[string]any)
	if p["count"].(int) != 1 {
		t.Fatal("players")
	}
}
