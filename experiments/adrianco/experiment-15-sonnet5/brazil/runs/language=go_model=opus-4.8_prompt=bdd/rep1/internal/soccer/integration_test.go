package soccer

import (
	"os"
	"path/filepath"
	"testing"
)

// dataDir locates the bundled Kaggle datasets relative to the repository root,
// skipping the integration tests when they are not present.
func dataDir(t *testing.T) string {
	t.Helper()
	dir := filepath.Join("..", "..", "data", "kaggle")
	if _, err := os.Stat(filepath.Join(dir, FileBrasileirao)); err != nil {
		t.Skipf("data directory not available: %v", err)
	}
	return dir
}

// Behaviour: the full pipeline loads every dataset and answers the spec's
// headline questions correctly against real data.

func Test_given_real_data_when_loaded_then_all_datasets_present(t *testing.T) {
	// Given the bundled datasets
	dir := dataDir(t)
	// When they are loaded
	s, err := LoadDir(dir)
	if err != nil {
		t.Fatalf("load error: %v", err)
	}
	// Then matches, players and all named competitions are present
	if len(s.Matches) < 10000 {
		t.Errorf("expected many matches, got %d", len(s.Matches))
	}
	if len(s.Players) < 18000 {
		t.Errorf("expected ~18k players, got %d", len(s.Players))
	}
	for _, want := range []string{CompBrasileirao, CompCopaBrasil, CompLibertadores} {
		found := false
		for _, c := range s.Competitions() {
			if c == want {
				found = true
			}
		}
		if !found {
			t.Errorf("expected competition %q to be present", want)
		}
	}
}

func Test_given_real_data_when_standings_2019_then_flamengo_champion_with_90_points(t *testing.T) {
	// Given the loaded datasets
	s, err := LoadDir(dataDir(t))
	if err != nil {
		t.Fatalf("load error: %v", err)
	}
	// When computing the 2019 Brasileirão standings
	table := s.Standings("Brasileir", 2019)
	if len(table) == 0 {
		t.Fatal("expected a table")
	}
	// Then Flamengo are champions with 90 points from 38 games (per the spec)
	champ := table[0]
	if champ.Team != "Flamengo" {
		t.Fatalf("expected Flamengo champion, got %q", champ.Team)
	}
	if champ.Points != 90 {
		t.Errorf("expected 90 points, got %d", champ.Points)
	}
	played := champ.Wins + champ.Draws + champ.Losses
	if played != 38 {
		t.Errorf("expected 38 games played, got %d", played)
	}
}

func Test_given_real_data_when_head_to_head_flamengo_fluminense_then_plausible(t *testing.T) {
	// Given the loaded datasets
	s, err := LoadDir(dataDir(t))
	if err != nil {
		t.Fatalf("load error: %v", err)
	}
	// When computing the Fla-Flu head-to-head
	h := s.HeadToHead("Flamengo", "Fluminense")
	// Then a substantial rivalry history is found and totals are consistent
	if h.Matches < 20 {
		t.Errorf("expected a long rivalry history, got %d matches", h.Matches)
	}
	if h.WinsA+h.WinsB+h.Draws != h.Matches {
		t.Errorf("results %d/%d/%d do not sum to %d matches", h.WinsA, h.WinsB, h.Draws, h.Matches)
	}
}

func Test_given_real_data_when_searching_top_brazilian_player_then_neymar(t *testing.T) {
	// Given the loaded datasets
	s, err := LoadDir(dataDir(t))
	if err != nil {
		t.Fatalf("load error: %v", err)
	}
	// When searching for the highest-rated Brazilian
	got := s.FindPlayers(PlayerFilter{Nationality: "Brazil", Limit: 1})
	// Then Neymar tops the list
	if len(got) != 1 {
		t.Fatalf("expected 1 player, got %d", len(got))
	}
	if got[0].Overall < 90 {
		t.Errorf("expected a 90+ rated player, got %d", got[0].Overall)
	}
}
