package main

import (
	"os"
	"testing"
)

// Feature: load all 6 CSVs from data/kaggle and verify basic counts.
// Skipped if the data directory is not present.

func TestLoadAll_RealData(t *testing.T) {
	if _, err := os.Stat("data/kaggle"); os.IsNotExist(err) {
		t.Skip("data/kaggle not present, skipping integration test")
	}
	ds := NewDataStore()
	if err := ds.LoadAll("data"); err != nil {
		t.Fatalf("LoadAll: %v", err)
	}
	// Expect tens of thousands of matches and tens of thousands of players.
	if len(ds.Matches) < 10000 {
		t.Errorf("matches = %d, want > 10000", len(ds.Matches))
	}
	if len(ds.Players) < 10000 {
		t.Errorf("players = %d, want > 10000", len(ds.Players))
	}

	// Flamengo should have plenty of matches.
	fla := ds.FindMatches(MatchFilter{Team1: "Flamengo"})
	if len(fla) < 100 {
		t.Errorf("Flamengo matches = %d, want > 100", len(fla))
	}

	// 2019 Brasileirão standings should show Flamengo on top with ~38 games.
	st := ds.Standings("Brasileirão", 2019)
	if len(st) == 0 {
		t.Fatal("no standings for 2019 Brasileirão")
	}
	if NormalizeTeam(st[0].Team) != "flamengo" {
		t.Errorf("2019 champion = %q, want flamengo", st[0].Team)
	}
	if st[0].Played < 35 || st[0].Played > 42 {
		t.Errorf("Flamengo 2019 played = %d, want ~38", st[0].Played)
	}
}
