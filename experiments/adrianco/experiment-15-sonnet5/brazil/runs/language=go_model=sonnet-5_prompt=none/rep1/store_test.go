package main

import (
	"os"
	"path/filepath"
	"testing"
)

func repoDataDir(t *testing.T) string {
	t.Helper()
	wd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	dir := filepath.Join(wd, "data", "kaggle")
	if _, err := os.Stat(dir); err != nil {
		t.Skipf("data directory not available: %v", err)
	}
	return dir
}

func TestLoadStoreRealData(t *testing.T) {
	store, err := LoadStore(repoDataDir(t))
	if err != nil {
		t.Fatalf("LoadStore: %v", err)
	}

	// Note: total is well below the sum of each file's row count because
	// overlapping real-world matches recorded in more than one source
	// (novo_campeonato_brasileiro.csv vs. Brasileirao_Matches.csv, and
	// BR-Football-Dataset.csv's extended stats vs. both Brasileirao_Matches
	// and Brazilian_Cup_Matches) are deduplicated during loading.
	if len(store.Matches) < 15000 {
		t.Errorf("got %d matches, want at least 15000 across all sources", len(store.Matches))
	}
	if len(store.Players) < 18000 {
		t.Errorf("got %d players, want at least 18000", len(store.Players))
	}

	// Skip/warning rate should be small relative to total rows processed.
	totalRows := len(store.Matches) + len(store.LoadWarnings)
	if float64(len(store.LoadWarnings))/float64(totalRows) > 0.05 {
		t.Errorf("too many load warnings: %d out of ~%d rows: %v", len(store.LoadWarnings), totalRows, store.LoadWarnings)
	}

	seenCompetitions := map[string]bool{}
	for _, m := range store.Matches {
		seenCompetitions[m.Competition] = true
	}
	for _, want := range []string{"Brasileirão", "Copa do Brasil", "Copa Libertadores"} {
		if !seenCompetitions[want] {
			t.Errorf("expected competition %q to be present in loaded matches", want)
		}
	}
}

func TestResolveTeamAmbiguousStateVariants(t *testing.T) {
	store := newStore()
	store.addMatch(Match{HomeTeam: "América-MG", AwayTeam: "Cruzeiro-MG", Season: 2015, HomeGoals: 1, AwayGoals: 1, HasGoals: true})
	store.addMatch(Match{HomeTeam: "América-RN", AwayTeam: "Ceará-CE", Season: 2015, HomeGoals: 2, AwayGoals: 0, HasGoals: true})

	keys := store.resolveTeam("America")
	if len(keys) != 2 {
		t.Fatalf("resolveTeam(\"America\") = %v, want 2 distinct state variants", keys)
	}

	exact := store.resolveTeam("América-MG")
	if len(exact) != 1 || exact[0] != "america|MG" {
		t.Fatalf("resolveTeam(\"América-MG\") = %v, want exactly [america|MG]", exact)
	}
}

func TestResolveTeamUnknownReturnsEmpty(t *testing.T) {
	store := newStore()
	store.addMatch(Match{HomeTeam: "Flamengo-RJ", AwayTeam: "Vasco-RJ", Season: 2020, HomeGoals: 1, AwayGoals: 0, HasGoals: true})
	if keys := store.resolveTeam("Real Madrid"); len(keys) != 0 {
		t.Fatalf("resolveTeam(\"Real Madrid\") = %v, want empty", keys)
	}
}
