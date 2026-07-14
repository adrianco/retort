package loader

import (
	"os"
	"path/filepath"
	"testing"
)

// dataDir returns the path to test data relative to this file's location.
func dataDir(t *testing.T) string {
	t.Helper()
	// go up one level from loader/ to find data/
	wd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	return filepath.Join(wd, "..", "data", "kaggle")
}

func TestLoadBrasileiraoMatches(t *testing.T) {
	matches, err := LoadBrasileiraoMatches(filepath.Join(dataDir(t), "Brasileirao_Matches.csv"))
	if err != nil {
		t.Fatalf("LoadBrasileiraoMatches: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("expected matches, got none")
	}
	// Verify first match fields are populated
	m := matches[0]
	if m.HomeTeam == "" {
		t.Error("HomeTeam is empty")
	}
	if m.Season == 0 {
		t.Error("Season is zero")
	}
	// Team names should still include state suffix (raw)
	// but we can normalize them
	norm := NormalizeTeamName(m.HomeTeam)
	if norm == "" {
		t.Error("normalized HomeTeam is empty")
	}
}

func TestLoadCupMatches(t *testing.T) {
	matches, err := LoadCupMatches(filepath.Join(dataDir(t), "Brazilian_Cup_Matches.csv"))
	if err != nil {
		t.Fatalf("LoadCupMatches: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("expected matches, got none")
	}
	m := matches[0]
	if m.HomeTeam == "" {
		t.Error("HomeTeam is empty")
	}
}

func TestLoadLibertadoresMatches(t *testing.T) {
	matches, err := LoadLibertadoresMatches(filepath.Join(dataDir(t), "Libertadores_Matches.csv"))
	if err != nil {
		t.Fatalf("LoadLibertadoresMatches: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("expected matches, got none")
	}
	m := matches[0]
	if m.Stage == "" {
		t.Error("Stage is empty")
	}
}

func TestLoadExtendedMatches(t *testing.T) {
	matches, err := LoadExtendedMatches(filepath.Join(dataDir(t), "BR-Football-Dataset.csv"))
	if err != nil {
		t.Fatalf("LoadExtendedMatches: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("expected matches, got none")
	}
	m := matches[0]
	if m.Tournament == "" {
		t.Error("Tournament is empty")
	}
}

func TestLoadHistoricalMatches(t *testing.T) {
	matches, err := LoadHistoricalMatches(filepath.Join(dataDir(t), "novo_campeonato_brasileiro.csv"))
	if err != nil {
		t.Fatalf("LoadHistoricalMatches: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("expected matches, got none")
	}
	m := matches[0]
	if m.HomeTeam == "" {
		t.Error("HomeTeam is empty")
	}
	if m.Year == 0 {
		t.Error("Year is zero")
	}
}

func TestLoadPlayers(t *testing.T) {
	players, err := LoadPlayers(filepath.Join(dataDir(t), "fifa_data.csv"))
	if err != nil {
		t.Fatalf("LoadPlayers: %v", err)
	}
	if len(players) == 0 {
		t.Fatal("expected players, got none")
	}
	p := players[0]
	if p.Name == "" {
		t.Error("Name is empty")
	}
	if p.Nationality == "" {
		t.Error("Nationality is empty")
	}
}
