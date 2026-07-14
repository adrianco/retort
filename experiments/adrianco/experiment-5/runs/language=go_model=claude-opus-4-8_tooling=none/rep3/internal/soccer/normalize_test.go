// Context: tests for the team-name normalization that lets the same club be
// matched across datasets despite state suffixes, country codes, accents and
// parenthetical notes (the "Data Quality Notes" in TASK.md).
package soccer

import "testing"

// Feature: team-name normalization.
func TestScenario_NormalizationUnifiesVariants(t *testing.T) {
	cases := []struct{ a, b string }{
		{"Palmeiras-SP", "Palmeiras"},       // state suffix
		{"Flamengo-RJ", "Flamengo"},         // state suffix
		{"São Paulo", "Sao Paulo"},          // accents
		{"Grêmio", "Gremio"},                // accents
		{"Nacional (URU)", "Nacional"},      // country code in parens
		{"América - MG", "America"},         // spaced suffix + accent
		{"Atlético-MG", "Atletico Mineiro"}, // alias
		{"Vasco da Gama", "Vasco"},          // alias
		{"São Paulo FC", "Sao Paulo"},       // alias + accents
	}
	for _, c := range cases {
		// Given two spellings of the same club
		// When normalized
		// Then they produce the same key
		if normKey(c.a) != normKey(c.b) {
			t.Errorf("normKey(%q)=%q != normKey(%q)=%q", c.a, normKey(c.a), c.b, normKey(c.b))
		}
	}
}

func TestScenario_NormalizationKeepsDistinctTeams(t *testing.T) {
	// Distinct clubs must NOT collide.
	pairs := []struct{ a, b string }{
		{"Flamengo", "Fluminense"},
		{"Palmeiras", "Santos"},
		{"São Paulo", "Santos"},
	}
	for _, p := range pairs {
		if normKey(p.a) == normKey(p.b) {
			t.Errorf("distinct teams collided: %q and %q -> %q", p.a, p.b, normKey(p.a))
		}
	}
}

func TestScenario_CleanTeamNameExtractsState(t *testing.T) {
	display, state := cleanTeamName("Palmeiras-SP")
	if display != "Palmeiras" {
		t.Errorf("display = %q, want Palmeiras", display)
	}
	if state != "SP" {
		t.Errorf("state = %q, want SP", state)
	}
}

func TestScenario_MatchesQueryPartial(t *testing.T) {
	key := normKey("Flamengo-RJ")
	if !matchesQuery(key, "Flamengo") {
		t.Error("expected partial query 'Flamengo' to match 'Flamengo-RJ'")
	}
	if matchesQuery(key, "Santos") {
		t.Error("did not expect 'Santos' to match Flamengo")
	}
	// Empty query matches anything.
	if !matchesQuery(key, "") {
		t.Error("empty query should match")
	}
}
