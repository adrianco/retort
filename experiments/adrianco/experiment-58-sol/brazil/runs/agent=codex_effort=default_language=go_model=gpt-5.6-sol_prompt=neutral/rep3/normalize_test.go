package main

import "testing"

func TestNormalizeTeamVariations(t *testing.T) {
	tests := []struct{ a, b string }{
		{"Palmeiras-SP", "palmeiras"},
		{"São Paulo FC", "Sao Paulo"},
		{"Sport Club Corinthians Paulista", "Corinthians"},
		{"Clube Atlético Mineiro", "Atletico-MG"},
		{"Athletico-PR", "Atlético Paranaense"},
	}
	for _, tc := range tests {
		if !fuzzyEqual(tc.a, tc.b) {
			t.Errorf("expected %q and %q to identify the same team (%q != %q)", tc.a, tc.b, normalizeTeam(tc.a), normalizeTeam(tc.b))
		}
	}
	if fuzzyEqual("Atletico-MG", "Atletico-PR") {
		t.Fatal("state-disambiguated Atletico clubs were merged")
	}
}
