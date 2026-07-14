package soccer

import (
	"os"
	"path/filepath"
	"testing"
)

// dataDir is the path to the bundled datasets relative to this package.
const dataDir = "../../data/kaggle"

// loadRealKB loads the bundled datasets, skipping the test if they are absent.
func loadRealKB(t *testing.T) *KB {
	t.Helper()
	if _, err := os.Stat(filepath.Join(dataDir, "fifa_data.csv")); err != nil {
		t.Skipf("datasets not available: %v", err)
	}
	kb, err := LoadDir(dataDir)
	if err != nil {
		t.Fatalf("LoadDir: %v", err)
	}
	return kb
}

func TestLoadDirCounts(t *testing.T) {
	kb := loadRealKB(t)

	// Expected data-row counts per the specification (file line count - header).
	const (
		wantPlayers = 18207
		wantMatches = 4180 + 1337 + 1255 + 10296 + 6886
	)
	if len(kb.Players) != wantPlayers {
		t.Errorf("players = %d, want %d", len(kb.Players), wantPlayers)
	}
	if len(kb.Matches) != wantMatches {
		t.Errorf("matches = %d, want %d", len(kb.Matches), wantMatches)
	}

	// Spot-check that scores and dates parsed for the bulk of matches.
	withScore, withDate := 0, 0
	for _, m := range kb.Matches {
		if m.HasScore {
			withScore++
		}
		if m.HasDate {
			withDate++
		}
	}
	if withScore < wantMatches*9/10 {
		t.Errorf("only %d/%d matches have scores", withScore, wantMatches)
	}
	if withDate < wantMatches*9/10 {
		t.Errorf("only %d/%d matches have dates", withDate, wantMatches)
	}
}
