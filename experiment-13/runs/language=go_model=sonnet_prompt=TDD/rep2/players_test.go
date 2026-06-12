package main

import (
	"testing"
)

var testPlayers = []Player{
	{ID: 1, Name: "L. Messi", Age: 31, Nationality: "Argentina", Overall: 94, Club: "FC Barcelona", Position: "RF"},
	{ID: 2, Name: "Neymar Jr", Age: 26, Nationality: "Brazil", Overall: 92, Club: "Paris SG", Position: "LW"},
	{ID: 3, Name: "Philippe Coutinho", Age: 26, Nationality: "Brazil", Overall: 88, Club: "FC Barcelona", Position: "LAM"},
	{ID: 4, Name: "Casemiro", Age: 26, Nationality: "Brazil", Overall: 87, Club: "Real Madrid", Position: "CDM"},
}

func TestSearchPlayers_ByName(t *testing.T) {
	results := SearchPlayers(testPlayers, "Ney", "", "", "", 0, 10)
	if len(results) != 1 {
		t.Fatalf("expected 1 player, got %d", len(results))
	}
	if results[0].Name != "Neymar Jr" {
		t.Errorf("expected Neymar Jr, got %s", results[0].Name)
	}
}

func TestSearchPlayers_ByNationality(t *testing.T) {
	results := SearchPlayers(testPlayers, "", "Brazil", "", "", 0, 10)
	if len(results) != 3 {
		t.Errorf("expected 3 Brazilian players, got %d", len(results))
	}
}

func TestSearchPlayers_ByClub(t *testing.T) {
	results := SearchPlayers(testPlayers, "", "", "FC Barcelona", "", 0, 10)
	if len(results) != 2 {
		t.Fatalf("expected 2 FC Barcelona players, got %d", len(results))
	}
}

func TestSearchPlayers_ByPosition(t *testing.T) {
	results := SearchPlayers(testPlayers, "", "", "", "CDM", 0, 10)
	if len(results) != 1 {
		t.Fatalf("expected 1 CDM player, got %d", len(results))
	}
	if results[0].Name != "Casemiro" {
		t.Errorf("expected Casemiro, got %s", results[0].Name)
	}
}

func TestSearchPlayers_MinOverall(t *testing.T) {
	results := SearchPlayers(testPlayers, "", "", "", "", 90, 10)
	if len(results) != 2 {
		t.Fatalf("expected 2 players with overall >= 90, got %d", len(results))
	}
}

func TestSearchPlayers_Limit(t *testing.T) {
	results := SearchPlayers(testPlayers, "", "", "", "", 0, 2)
	if len(results) != 2 {
		t.Errorf("expected exactly 2 results with limit=2, got %d", len(results))
	}
}
