// Package store tests — team-name normalization (BDD Given/When/Then).
package store

import "testing"

// Scenario: State and country suffixes are stripped for matching.
func TestScenario_NormalizeTeamSuffixes(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP":   "palmeiras",
		"Flamengo-RJ":    "flamengo",
		"América - MG":   "america",
		"Nacional (URU)": "nacional",
		"Barcelona-EQU":  "barcelona",
		"São Paulo":      "sao paulo",
		"Grêmio":         "gremio",
		"Atlético-MG":    "atletico",
	}
	for input, want := range cases {
		// Given a raw team name
		// When it is normalized
		got := NormalizeTeam(input)
		// Then accents/suffixes are removed
		if got != want {
			t.Errorf("NormalizeTeam(%q) = %q; want %q", input, got, want)
		}
	}
}

// Scenario: Queries match dataset spellings regardless of suffix or accent.
func TestScenario_TeamMatches(t *testing.T) {
	matches := []struct{ team, query string }{
		{"Palmeiras-SP", "Palmeiras"},
		{"Sport Club Corinthians Paulista", "Corinthians"},
		{"São Paulo", "Sao Paulo"},
		{"Grêmio", "gremio"},
		{"Flamengo-RJ", "flamengo"},
	}
	for _, c := range matches {
		if !TeamMatches(c.team, c.query) {
			t.Errorf("TeamMatches(%q, %q) = false; want true", c.team, c.query)
		}
	}
	// And distinct teams do not match
	nonMatches := []struct{ team, query string }{
		{"Palmeiras-SP", "Santos"},
		{"Flamengo-RJ", "Fluminense"},
	}
	for _, c := range nonMatches {
		if TeamMatches(c.team, c.query) {
			t.Errorf("TeamMatches(%q, %q) = true; want false", c.team, c.query)
		}
	}
}

// Scenario: Free-text fields match accent-insensitively.
func TestScenario_ContainsFold(t *testing.T) {
	if !containsFold("São Paulo FC", "sao paulo") {
		t.Error("Then accent-folded substring should match")
	}
	if !containsFold("Brazil", "brazil") {
		t.Error("Then case-insensitive substring should match")
	}
	if containsFold("Argentina", "brazil") {
		t.Error("Then unrelated text should not match")
	}
}
