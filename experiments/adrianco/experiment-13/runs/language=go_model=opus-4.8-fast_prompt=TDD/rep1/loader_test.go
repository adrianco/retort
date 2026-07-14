// Package main — Brazilian Soccer MCP Server.
//
// loader_test.go: Tests that every provided CSV loads into the in-memory
// Dataset with the expected row counts, correct competition tagging, and
// well-formed parsed fields (goals, seasons, dates, normalized team keys).
package main

import (
	"testing"
)

const dataDir = "data/kaggle"

// loadOnce caches the dataset so the many query tests don't re-parse ~40k rows.
var sharedDataset *Dataset

func testDataset(t *testing.T) *Dataset {
	t.Helper()
	if sharedDataset == nil {
		ds, err := LoadDataset(dataDir)
		if err != nil {
			t.Fatalf("LoadDataset: %v", err)
		}
		sharedDataset = ds
	}
	return sharedDataset
}

func TestLoadDatasetCounts(t *testing.T) {
	ds := testDataset(t)

	// Per-file (Source) match counts — header rows excluded. Counting by Source
	// rather than Competition keeps files distinct (e.g. BR-Football also has
	// "Copa do Brasil" tagged rows).
	wantBySource := map[string]int{
		"Brasileirao":  4180,
		"Cup":          1337,
		"Libertadores": 1255,
		"Historico":    6886,
		"BR-Football":  10296,
	}
	got := map[string]int{}
	for _, m := range ds.Matches {
		got[m.Source]++
	}
	for src, want := range wantBySource {
		if got[src] != want {
			t.Errorf("source %q: got %d matches, want %d", src, got[src], want)
		}
	}

	if len(ds.Players) != 18207 {
		t.Errorf("players: got %d, want 18207", len(ds.Players))
	}
}

func TestLoadDatasetFields(t *testing.T) {
	ds := testDataset(t)

	// Find the known first Brasileirao row: Palmeiras-SP 1-1 Portuguesa-SP, 2012 round 1.
	var found bool
	for _, m := range ds.Matches {
		if m.Source == "Brasileirao" && m.Season == 2012 &&
			m.HomeTeamKey == "palmeiras" && m.AwayTeamKey == "portuguesa" {
			found = true
			if m.HomeGoals != 1 || m.AwayGoals != 1 {
				t.Errorf("Palmeiras-Portuguesa score = %d-%d, want 1-1", m.HomeGoals, m.AwayGoals)
			}
			if !m.HasDate || m.Date.Year() != 2012 {
				t.Errorf("expected parsed 2012 date, got %v (has=%v)", m.Date, m.HasDate)
			}
			break
		}
	}
	if !found {
		t.Error("did not find the seeded Palmeiras vs Portuguesa 2012 match")
	}
}

func TestLoadPlayersBrazilian(t *testing.T) {
	ds := testDataset(t)
	brazilians := 0
	var neymar *Player
	for i := range ds.Players {
		p := &ds.Players[i]
		if NormalizeTeam(p.Nationality) == "brazil" {
			brazilians++
		}
		if p.Name == "Neymar Jr" {
			neymar = p
		}
	}
	if brazilians < 500 {
		t.Errorf("expected many Brazilian players, got %d", brazilians)
	}
	if neymar == nil {
		t.Fatal("expected to find Neymar Jr")
	}
	if neymar.Overall < 80 {
		t.Errorf("Neymar overall = %d, want >= 80", neymar.Overall)
	}
}
