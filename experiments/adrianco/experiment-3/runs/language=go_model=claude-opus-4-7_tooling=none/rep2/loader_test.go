// loader_test.go verifies that all six provided CSV datasets load correctly
// and that overlapping fixtures are de-duplicated.
package main

import (
	"path/filepath"
	"testing"
)

func TestRawDatasetCounts(t *testing.T) {
	// Given each provided CSV file
	// When it is loaded by its dedicated loader
	// Then the row count matches the specification
	cases := []struct {
		file   string
		loader func(string) ([]Match, error)
		want   int
	}{
		{"Brasileirao_Matches.csv", loadBrasileirao, 4180},
		{"Brazilian_Cup_Matches.csv", loadCup, 1337},
		{"Libertadores_Matches.csv", loadLibertadores, 1255},
		{"BR-Football-Dataset.csv", loadBRFootball, 10296},
		{"novo_campeonato_brasileiro.csv", loadNovo, 6886},
	}
	for _, c := range cases {
		t.Run(c.file, func(t *testing.T) {
			matches, err := c.loader(filepath.Join(testDataDir, c.file))
			if err != nil {
				t.Fatalf("loader failed: %v", err)
			}
			if len(matches) != c.want {
				t.Errorf("%s loaded %d matches, want %d", c.file, len(matches), c.want)
			}
		})
	}
}

func TestLoadPlayers(t *testing.T) {
	// Given the FIFA player CSV
	// When it is loaded
	players, err := loadPlayers(filepath.Join(testDataDir, "fifa_data.csv"))
	if err != nil {
		t.Fatalf("loadPlayers failed: %v", err)
	}
	// Then the player count is close to the documented 18,207
	if len(players) < 18000 {
		t.Errorf("loaded %d players, want >= 18000", len(players))
	}
	// And the first player (Messi) parsed his core fields
	var messi *Player
	for i := range players {
		if players[i].Name == "L. Messi" {
			messi = &players[i]
			break
		}
	}
	if messi == nil {
		t.Fatal("expected to find L. Messi in player data")
	}
	if messi.Overall != 94 || messi.Nationality != "Argentina" {
		t.Errorf("Messi parsed as overall=%d nationality=%q, want 94/Argentina",
			messi.Overall, messi.Nationality)
	}
}

func TestLoadAllAndDedupe(t *testing.T) {
	store := loadedStore(t)

	rawTotal := 4180 + 1337 + 1255 + 10296 + 6886

	// When all datasets are merged
	// Then de-duplication removes the cross-dataset overlap
	if len(store.Matches) >= rawTotal {
		t.Errorf("store has %d matches; expected fewer than raw total %d after dedupe",
			len(store.Matches), rawTotal)
	}
	if len(store.Matches) < 15000 {
		t.Errorf("store has only %d matches; expected a substantial dataset", len(store.Matches))
	}
	if len(store.Players) < 18000 {
		t.Errorf("store has %d players, want >= 18000", len(store.Players))
	}
}

func TestParsedMatchFields(t *testing.T) {
	store := loadedStore(t)

	dated, scored, withRound := 0, 0, 0
	for _, m := range store.Matches {
		if m.HasDate {
			dated++
		}
		if m.HasScore {
			scored++
		}
		if m.Round != "" {
			withRound++
		}
	}
	// Then the bulk of matches have dates, scores and round/stage metadata
	if dated < len(store.Matches)/2 {
		t.Errorf("only %d/%d matches have parsed dates", dated, len(store.Matches))
	}
	if scored < len(store.Matches)/2 {
		t.Errorf("only %d/%d matches have parsed scores", scored, len(store.Matches))
	}
	if withRound == 0 {
		t.Error("no matches have round information")
	}
}

func TestDateFormatParsing(t *testing.T) {
	// Given the multiple date formats described in the spec
	cases := []string{
		"2012-05-19 18:30:00", // ISO with time
		"2023-09-24",          // ISO date
		"29/03/2003",          // Brazilian DD/MM/YYYY
	}
	for _, in := range cases {
		// When parsed
		// Then a valid date is produced
		if _, ok := parseDate(in); !ok {
			t.Errorf("parseDate(%q) failed", in)
		}
	}
}

func TestGoalParsing(t *testing.T) {
	// Goals appear as plain ints and as floats across datasets.
	cases := map[string]int{"2": 2, "2.0": 2, "0": 0, "3.0": 3}
	for in, want := range cases {
		if got, ok := parseGoal(in); !ok || got != want {
			t.Errorf("parseGoal(%q) = %d,%v want %d,true", in, got, ok, want)
		}
	}
	if _, ok := parseGoal(""); ok {
		t.Error("parseGoal(\"\") should report not-ok")
	}
}
