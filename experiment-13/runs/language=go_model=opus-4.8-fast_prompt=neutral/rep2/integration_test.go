// Context: integration test against the real Kaggle datasets shipped in
// data/kaggle. It validates the headline example from TASK.md — the computed
// 2019 Brasileirão table must crown Flamengo champions with 90 points — and
// basic cross-file coverage. Skipped automatically if the data is absent.
package main

import (
	"os"
	"testing"

	"brazilian-soccer-mcp/internal/soccer"
)

func TestRealDataBrasileirao2019(t *testing.T) {
	if _, err := os.Stat("data/kaggle/novo_campeonato_brasileiro.csv"); err != nil {
		t.Skip("real dataset not present; skipping integration test")
	}
	db, _ := soccer.Load("data/kaggle")
	if len(db.Matches) == 0 || len(db.Players) == 0 {
		t.Fatalf("expected matches and players, got %d/%d", len(db.Matches), len(db.Players))
	}

	rows := db.Standings(soccer.CompBrasileirao, 2019)
	if len(rows) == 0 {
		t.Fatal("no 2019 standings computed")
	}
	champ := rows[0]
	if champ.Team != "Flamengo" {
		t.Errorf("2019 Brasileirão champion = %q, want Flamengo", champ.Team)
	}
	// The historically correct total: Flamengo finished 2019 on 90 points.
	if champ.Points != 90 {
		t.Errorf("Flamengo 2019 points = %d, want 90", champ.Points)
	}
	if champ.Wins != 28 || champ.Draws != 6 || champ.Losses != 4 {
		t.Errorf("Flamengo 2019 W/D/L = %d/%d/%d, want 28/6/4", champ.Wins, champ.Draws, champ.Losses)
	}

	// Cross-file sanity: many Brazilian players should be present.
	br := db.SearchPlayers(soccer.PlayerQuery{Nationality: "Brazil"})
	if len(br) < 100 {
		t.Errorf("Brazilian players = %d, want >= 100", len(br))
	}
}
