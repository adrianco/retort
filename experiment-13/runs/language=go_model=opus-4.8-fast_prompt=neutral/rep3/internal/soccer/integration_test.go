package soccer

import (
	"os"
	"path/filepath"
	"testing"
)

// findDataDir walks up from the test's working directory looking for the
// bundled Kaggle dataset, so the integration test works regardless of where
// `go test` is invoked.
func findDataDir() string {
	dir, err := os.Getwd()
	if err != nil {
		return ""
	}
	for i := 0; i < 6; i++ {
		candidate := filepath.Join(dir, "data", "kaggle")
		if _, err := os.Stat(filepath.Join(candidate, "fifa_data.csv")); err == nil {
			return candidate
		}
		dir = filepath.Dir(dir)
	}
	return ""
}

// TestRealData validates against the bundled datasets. It is skipped if the
// data is not present (e.g. when the package is vendored without it).
func TestRealData(t *testing.T) {
	dir := findDataDir()
	if dir == "" {
		t.Skip("bundled Kaggle data not found; skipping integration test")
	}
	db, err := Load(dir)
	if err != nil {
		t.Fatalf("Load(%q): %v", dir, err)
	}

	if len(db.Players) < 18000 {
		t.Errorf("players = %d, want >= 18000", len(db.Players))
	}
	if len(db.Matches) < 10000 {
		t.Errorf("matches = %d, want >= 10000", len(db.Matches))
	}

	// The 2019 Brasileirão Série A had exactly 380 matches and was won by
	// Flamengo with 90 points (28W 6D 4L). This is the canonical check that
	// cross-source de-duplication works.
	stats := db.CompetitionStats(CompBrasileiraoA, 2019, 1)
	if stats.Matches != 380 {
		t.Errorf("2019 Série A matches = %d, want 380", stats.Matches)
	}
	table := db.Standings(CompBrasileiraoA, 2019)
	if len(table) != 20 {
		t.Errorf("2019 Série A teams = %d, want 20", len(table))
	}
	champ := table[0]
	if champ.Team != "Flamengo" {
		t.Errorf("2019 champion = %q, want Flamengo", champ.Team)
	}
	if champ.Points() != 90 {
		t.Errorf("Flamengo 2019 points = %d, want 90", champ.Points())
	}
	if champ.Wins != 28 || champ.Draws != 6 || champ.Losses != 4 {
		t.Errorf("Flamengo 2019 record = %dW %dD %dL, want 28/6/4", champ.Wins, champ.Draws, champ.Losses)
	}

	// Average goals per match in Série A 2019 was ~2.3.
	if g := stats.AvgGoals(); g < 2.0 || g > 2.7 {
		t.Errorf("2019 avg goals = %.2f, want ~2.3", g)
	}

	// 2020 Série A: Flamengo champions on 71 points. This guards against the
	// classic bug where Atlético-MG/PR/GO (distinguished only by state suffix)
	// merge into one 100+ point "Atletico" row.
	t2020 := db.Standings(CompBrasileiraoA, 2020)
	if len(t2020) != 20 {
		t.Errorf("2020 Série A teams = %d, want 20", len(t2020))
	}
	if t2020[0].Team != "Flamengo" || t2020[0].Points() != 71 {
		t.Errorf("2020 champion = %q on %d pts, want Flamengo on 71", t2020[0].Team, t2020[0].Points())
	}
	for _, r := range t2020 {
		if r.Played > 38 {
			t.Errorf("team %q played %d matches in 2020 (>38): teams wrongly merged", r.Team, r.Played)
		}
	}

	// There must be hundreds of Brazilian players.
	br := db.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
	if len(br) < 500 {
		t.Errorf("Brazilian players = %d, want >= 500", len(br))
	}
}
