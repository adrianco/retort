package soccer

import "testing"

// TestLoadStoreFromDir loads the real datasets shipped in data/kaggle,
// verifying that every provided CSV file is loadable, as required by the
// project's data coverage success criteria.
func TestLoadStoreFromDir(t *testing.T) {
	s, err := LoadStoreFromDir("../../data/kaggle")
	if err != nil {
		t.Fatalf("LoadStoreFromDir returned error: %v", err)
	}

	wantMinMatches := 4180 + 1337 + 1250 + 10296 + 6886 // Libertadores has 1 malformed row skipped.
	if len(s.Matches) < wantMinMatches {
		t.Errorf("got %d matches, want at least %d", len(s.Matches), wantMinMatches)
	}
	if len(s.Players) < 18000 {
		t.Errorf("got %d players, want at least 18000", len(s.Players))
	}

	// Spot-check that data from each source is queryable.
	if got := s.FindMatches(MatchFilter{Team: "Flamengo", Competition: "Brasileirao"}); len(got) == 0 {
		t.Error("expected to find Brasileirao matches for Flamengo")
	}
	if got := s.SearchPlayers(PlayerFilter{Name: "Neymar"}); len(got) == 0 {
		t.Error("expected to find a player named Neymar")
	}
}
