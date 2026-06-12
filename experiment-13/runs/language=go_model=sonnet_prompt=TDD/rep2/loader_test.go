package main

import (
	"testing"
)

const dataDir = "data/kaggle"

func TestLoadBrasileirao_LoadsCorrectRowCount(t *testing.T) {
	matches, err := LoadBrasileirao(dataDir + "/Brasileirao_Matches.csv")
	if err != nil {
		t.Fatalf("LoadBrasileirao failed: %v", err)
	}
	if len(matches) < 4000 {
		t.Errorf("expected at least 4000 matches, got %d", len(matches))
	}
}

func TestLoadCopa_LoadsCorrectRowCount(t *testing.T) {
	matches, err := LoadCopa(dataDir + "/Brazilian_Cup_Matches.csv")
	if err != nil {
		t.Fatalf("LoadCopa failed: %v", err)
	}
	if len(matches) < 1000 {
		t.Errorf("expected at least 1000 matches, got %d", len(matches))
	}
}

func TestLoadLibertadores_LoadsCorrectRowCount(t *testing.T) {
	matches, err := LoadLibertadores(dataDir + "/Libertadores_Matches.csv")
	if err != nil {
		t.Fatalf("LoadLibertadores failed: %v", err)
	}
	if len(matches) < 1000 {
		t.Errorf("expected at least 1000 matches, got %d", len(matches))
	}
}

func TestLoadBRFootball_LoadsCorrectRowCount(t *testing.T) {
	matches, err := LoadBRFootball(dataDir + "/BR-Football-Dataset.csv")
	if err != nil {
		t.Fatalf("LoadBRFootball failed: %v", err)
	}
	if len(matches) < 10000 {
		t.Errorf("expected at least 10000 matches, got %d", len(matches))
	}
}

func TestLoadHistorico_LoadsCorrectRowCount(t *testing.T) {
	matches, err := LoadHistorico(dataDir + "/novo_campeonato_brasileiro.csv")
	if err != nil {
		t.Fatalf("LoadHistorico failed: %v", err)
	}
	if len(matches) < 6000 {
		t.Errorf("expected at least 6000 matches, got %d", len(matches))
	}
}

func TestLoadFIFA_LoadsCorrectRowCount(t *testing.T) {
	players, err := LoadFIFA(dataDir + "/fifa_data.csv")
	if err != nil {
		t.Fatalf("LoadFIFA failed: %v", err)
	}
	if len(players) < 18000 {
		t.Errorf("expected at least 18000 players, got %d", len(players))
	}
}

func TestLoadBrasileirao_ParsesTeamNames(t *testing.T) {
	matches, err := LoadBrasileirao(dataDir + "/Brasileirao_Matches.csv")
	if err != nil {
		t.Fatalf("LoadBrasileirao failed: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("no matches loaded")
	}
	first := matches[0]
	if first.HomeTeam == "" {
		t.Error("HomeTeam should not be empty")
	}
	if first.AwayTeam == "" {
		t.Error("AwayTeam should not be empty")
	}
	if first.Season == 0 {
		t.Error("Season should not be zero")
	}
}

func TestLoadBrasileirao_ParsesDates(t *testing.T) {
	matches, err := LoadBrasileirao(dataDir + "/Brasileirao_Matches.csv")
	if err != nil {
		t.Fatalf("LoadBrasileirao failed: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("no matches loaded")
	}
	first := matches[0]
	if first.DateTime.IsZero() {
		t.Error("DateTime should not be zero")
	}
	if first.DateTime.Year() < 2000 {
		t.Errorf("DateTime year should be >= 2000, got %d", first.DateTime.Year())
	}
}

func TestLoadFIFA_ParsesPlayerData(t *testing.T) {
	players, err := LoadFIFA(dataDir + "/fifa_data.csv")
	if err != nil {
		t.Fatalf("LoadFIFA failed: %v", err)
	}
	if len(players) == 0 {
		t.Fatal("no players loaded")
	}
	first := players[0]
	if first.Name == "" {
		t.Error("Name should not be empty")
	}
	if first.Overall == 0 {
		t.Error("Overall should not be zero")
	}
}
