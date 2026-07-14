// Context: Brazilian Soccer MCP Server.
// File: integration_test.go
// Purpose: End-to-end test that loads the real bundled CSV datasets and
// sanity-checks row counts and representative queries. Skipped automatically
// when the data directory is not present.
package soccer

import (
	"os"
	"path/filepath"
	"testing"
)

func dataDir(t *testing.T) string {
	t.Helper()
	dir := filepath.Join("..", "..", "data", "kaggle")
	if _, err := os.Stat(filepath.Join(dir, "fifa_data.csv")); err != nil {
		t.Skipf("data directory not available: %v", err)
	}
	return dir
}

func TestLoadRealData(t *testing.T) {
	db, err := Load(dataDir(t))
	if err != nil {
		t.Fatal(err)
	}
	// Raw sum across the five files is ~23954, but heavy overlap between them
	// (the same fixture in multiple files) is deduplicated on load, so the
	// distinct total is lower. Confirm a substantial corpus survived.
	if len(db.Matches) < 15000 {
		t.Errorf("loaded %d matches, want >= 15000", len(db.Matches))
	}
	if len(db.Matches) >= 23954 {
		t.Errorf("loaded %d matches; expected deduplication to remove overlap", len(db.Matches))
	}
	if len(db.Players) < 18000 {
		t.Errorf("loaded %d players, want >= 18000", len(db.Players))
	}
}

func TestRealDataQueries(t *testing.T) {
	db, err := Load(dataDir(t))
	if err != nil {
		t.Fatal(err)
	}

	// Player lookup across the FIFA dataset.
	if got := db.FindPlayers(PlayerFilter{Name: "Neymar"}); len(got) == 0 {
		t.Errorf("expected to find Neymar")
	}
	brazilians := db.FindPlayers(PlayerFilter{Nationality: "Brazil"})
	if len(brazilians) < 500 {
		t.Errorf("Brazilian players = %d, want many", len(brazilians))
	}

	// Match search by team should find plenty of Flamengo games.
	fla := db.FindMatches(MatchFilter{Team: "Flamengo"})
	if len(fla) < 100 {
		t.Errorf("Flamengo matches = %d, want many", len(fla))
	}

	// Standings for a historical Brasileirão season should have ~20 teams and a
	// champion with a sensible points total.
	table := db.Standings(2019, "Brasileirão")
	if len(table) < 16 {
		t.Errorf("2019 standings teams = %d, want ~20", len(table))
	}
	if len(table) > 0 && table[0].Points() < 50 {
		t.Errorf("2019 champion points = %d, want a large total", table[0].Points())
	}

	// Average goals across the league should be in a plausible football range.
	avg := db.AverageGoals(MatchFilter{Competition: "Brasileirão"})
	if avg < 1.5 || avg > 4 {
		t.Errorf("avg goals = %f, want plausible range", avg)
	}
}
