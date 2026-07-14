// Brazilian Soccer MCP Server
//
// File: loader_test.go
// Responsibility: Integration tests that exercise the loader and query engine
// against the real bundled Kaggle datasets under data/kaggle. These verify that
// every CSV parses, the expected volume of records loads, and that well-known
// real-world answers (e.g. Flamengo winning the 2019 Brasileirão) come out
// correct. If the datasets are absent the tests skip rather than fail, so the
// unit suite still runs anywhere.
package main

import (
	"os"
	"path/filepath"
	"sync"
	"testing"
)

const testDataDir = "data/kaggle"

var (
	loadedStore *Store
	loadOnce    sync.Once
)

// realStore loads the bundled datasets once, skipping the test if they are not
// present in the working tree.
func realStore(t *testing.T) *Store {
	t.Helper()
	if _, err := os.Stat(filepath.Join(testDataDir, "Brasileirao_Matches.csv")); err != nil {
		t.Skipf("datasets not present under %s; skipping integration test", testDataDir)
	}
	loadOnce.Do(func() {
		s, err := LoadAll(testDataDir)
		if err != nil {
			t.Fatalf("LoadAll: %v", err)
		}
		loadedStore = s
	})
	return loadedStore
}

// Scenario: All datasets load.
func TestLoadAllDatasets(t *testing.T) {
	// Given the bundled CSV files
	s := realStore(t)
	// When they are loaded
	// Then a large, plausible number of matches and players is present
	if len(s.Matches) < 20000 {
		t.Errorf("expected >20000 matches, got %d", len(s.Matches))
	}
	if len(s.Players) < 18000 {
		t.Errorf("expected >18000 players, got %d", len(s.Players))
	}
	// And every competition has at least one season
	if len(s.Competitions()) == 0 {
		t.Error("no competitions loaded")
	}
}

// Scenario: Computed 2019 Brasileirão standings match the historical result.
func TestStandings2019Real(t *testing.T) {
	// Given the loaded match data
	s := realStore(t)
	// When I compute the 2019 Brasileirão Série A standings
	table := s.Standings("Brasileirão Série A", 2019)
	// Then Flamengo is champion with 90 points over 38 games
	if len(table) == 0 {
		t.Fatal("empty standings")
	}
	champ := table[0]
	if teamBaseKey(champ.Team) != "flamengo" {
		t.Errorf("2019 champion = %q, want Flamengo", champ.Team)
	}
	if champ.Points() != 90 {
		t.Errorf("2019 champion points = %d, want 90", champ.Points())
	}
	if champ.Matches != 38 {
		t.Errorf("2019 champion games = %d, want 38 (no double counting)", champ.Matches)
	}
}

// Scenario: Find the Fla-Flu derby in the data.
func TestFlaFluReal(t *testing.T) {
	// Given the loaded match data
	s := realStore(t)
	// When I look up Flamengo vs Fluminense
	h := s.HeadToHead("Flamengo", "Fluminense")
	// Then there are many recorded meetings with a decided aggregate
	if len(h.Matches) < 20 {
		t.Errorf("expected many Fla-Flu meetings, got %d", len(h.Matches))
	}
	if h.Team1Wins+h.Team2Wins+h.Draws == 0 {
		t.Error("no decided Fla-Flu results")
	}
}

// Scenario: Brazilian players are searchable.
func TestBrazilianPlayersReal(t *testing.T) {
	// Given the loaded player data
	s := realStore(t)
	// When I search for top Brazilian players
	got := s.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: 3})
	// Then I get three highly-rated players sorted by overall
	if len(got) != 3 {
		t.Fatalf("expected 3 players, got %d", len(got))
	}
	if got[0].Overall < got[1].Overall || got[1].Overall < got[2].Overall {
		t.Errorf("players not sorted by overall: %d, %d, %d", got[0].Overall, got[1].Overall, got[2].Overall)
	}
	for _, p := range got {
		if normKey(p.Nationality) != "brazil" {
			t.Errorf("non-Brazilian leaked in: %s (%s)", p.Name, p.Nationality)
		}
	}
}
