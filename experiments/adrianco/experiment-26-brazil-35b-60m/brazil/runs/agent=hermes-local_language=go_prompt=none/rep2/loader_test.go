package main

import (
	"testing"
)

func TestLoadBrasileirao(t *testing.T) {
	matches, err := LoadBrasileirao("data/kaggle/Brasileirao_Matches.csv")
	if err != nil {
		t.Fatalf("LoadBrasileirao error: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("Expected non-empty Brasileirao matches")
	}
	// Check normalization: team names should not have state suffix
	m := matches[0]
	if len(m.HomeTeam) == 0 {
		t.Error("Expected non-empty home team")
	}
	if len(m.AwayTeam) == 0 {
		t.Error("Expected non-empty away team")
	}
	if m.HomeScore < 0 || m.AwayScore < 0 {
		t.Errorf("Expected non-negative scores, got %d-%d", m.HomeScore, m.AwayScore)
	}
	if m.Competition != "Brasileirao Serie A" {
		t.Errorf("Wrong competition: %s", m.Competition)
	}
	if m.Source != "Brasileirao_Matches.csv" {
		t.Errorf("Wrong source: %s", m.Source)
	}
	t.Logf("Loaded %d Brasileirao matches, first: %s %d-%d %s",
		len(matches), m.HomeTeam, m.HomeScore, m.AwayScore, m.AwayTeam)
}

func TestLoadCopaBrasil(t *testing.T) {
	matches, err := LoadCopaBrasil("data/kaggle/Brazilian_Cup_Matches.csv")
	if err != nil {
		t.Fatalf("LoadCopaBrasil error: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("Expected non-empty Copa Brasil matches")
	}
	m := matches[0]
	if m.Competition != "Copa do Brasil" {
		t.Errorf("Wrong competition: %s", m.Competition)
	}
	if m.Source != "Brazilian_Cup_Matches.csv" {
		t.Errorf("Wrong source: %s", m.Source)
	}
	t.Logf("Loaded %d Copa Brasil matches, first: %s %d-%d %s",
		len(matches), m.HomeTeam, m.HomeScore, m.AwayScore, m.AwayTeam)
}

func TestLoadLibertadores(t *testing.T) {
	matches, err := LoadLibertadores("data/kaggle/Libertadores_Matches.csv")
	if err != nil {
		t.Fatalf("LoadLibertadores error: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("Expected non-empty Libertadores matches")
	}
	m := matches[0]
	if m.Competition != "Copa Libertadores" {
		t.Errorf("Wrong competition: %s", m.Competition)
	}
	if m.Source != "Libertadores_Matches.csv" {
		t.Errorf("Wrong source: %s", m.Source)
	}
	t.Logf("Loaded %d Libertadores matches, first: %s %d-%d %s",
		len(matches), m.HomeTeam, m.HomeScore, m.AwayScore, m.AwayTeam)
}

func TestLoadBRFootball(t *testing.T) {
	matches, err := LoadBRFootball("data/kaggle/BR-Football-Dataset.csv")
	if err != nil {
		t.Fatalf("LoadBRFootball error: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("Expected non-empty BR Football matches")
	}
	m := matches[0]
	if m.Competition == "" {
		t.Error("Expected non-empty competition")
	}
	if m.Source != "BR-Football-Dataset.csv" {
		t.Errorf("Wrong source: %s", m.Source)
	}
	t.Logf("Loaded %d BR Football matches, first: %s %d-%d %s (%s)",
		len(matches), m.HomeTeam, m.HomeScore, m.AwayScore, m.AwayTeam, m.Competition)
}

func TestLoadNovoCampeonato(t *testing.T) {
	matches, err := LoadNovoCampeonato("data/kaggle/novo_campeonato_brasileiro.csv")
	if err != nil {
		t.Fatalf("LoadNovoCampeonato error: %v", err)
	}
	if len(matches) == 0 {
		t.Fatal("Expected non-empty Novo Campeonato matches")
	}
	m := matches[0]
	if m.Competition != "Campeonato Brasileiro" {
		t.Errorf("Wrong competition: %s", m.Competition)
	}
	if m.Source != "novo_campeonato_brasileiro.csv" {
		t.Errorf("Wrong source: %s", m.Source)
	}
	t.Logf("Loaded %d Novo Campeonato matches, first: %s %d-%d %s (year: %d)",
		len(matches), m.HomeTeam, m.HomeScore, m.AwayScore, m.AwayTeam, m.Season)
}

func TestLoadFIFAPlayers(t *testing.T) {
	players, err := LoadFIFAPlayers("data/kaggle/fifa_data.csv")
	if err != nil {
		t.Fatalf("LoadFIFAPlayers error: %v", err)
	}
	if len(players) == 0 {
		t.Fatal("Expected non-empty FIFA players")
	}
	p := players[0]
	if p.Name == "" {
		t.Error("Expected non-empty player name")
	}
	if p.Overall <= 0 {
		t.Errorf("Expected positive overall rating, got %d", p.Overall)
	}
	t.Logf("Loaded %d FIFA players, first: %s (Overall: %d, Club: %s)",
		len(players), p.Name, p.Overall, p.Club)
}

func TestNormalizeTeamName(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"Atletico-MG", "Atletico"},
		{"Sao Paulo-SP", "Sao Paulo"},
		{"Corinthians-SP", "Corinthians"},
		{"Gremio-RS", "Gremio"},
		{"Botafogo-RJ", "Botafogo"},
		{"Real Madrid", "Real Madrid"},        // No suffix
		{"Barcelona", "Barcelona"},             // No suffix
	}
	for _, tt := range tests {
		got := normalizeTeamName(tt.input)
		if got != tt.expected {
			t.Errorf("normalizeTeamName(%q) = %q, want %q", tt.input, got, tt.expected)
		}
	}
}

func TestParseInt(t *testing.T) {
	tests := []struct {
		input    string
		expected int
	}{
		{"2023", 2023},
		{"0", 0},
		{"abc", 0},
		{"", 0},
		{" 5 ", 5},
	}
	for _, tt := range tests {
		got := parseInt(tt.input)
		if got != tt.expected {
			t.Errorf("parseInt(%q) = %d, want %d", tt.input, got, tt.expected)
		}
	}
}
