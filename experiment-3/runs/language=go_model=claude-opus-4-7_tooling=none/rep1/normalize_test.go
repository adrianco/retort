// BDD scenarios for name, competition and date normalization.
package main

import "testing"

// Feature: Team name normalization
//
// Scenario: A team written with a state suffix normalizes to its base name.
func TestScenario_StateSuffixIsStripped(t *testing.T) {
	cases := []struct {
		raw  string
		want string
	}{
		// Given various ways of writing the same club
		{"Palmeiras-SP", "Palmeiras"},
		{"América - MG", "América"},
		{"Sport-PE", "Sport"},
		{"Vasco da Gama RJ", "Vasco da Gama"},
		{"Nacional (URU)", "Nacional"},
	}
	for _, c := range cases {
		// When the name is cleaned for display
		got := cleanTeamName(c.raw)
		// Then the state/country suffix is removed
		if got != c.want {
			t.Errorf("cleanTeamName(%q) = %q, want %q", c.raw, got, c.want)
		}
	}
}

// Scenario: Accented and unaccented spellings compare equal.
func TestScenario_AccentsAreFoldedForMatching(t *testing.T) {
	// Given the same club spelled with and without accents
	withAccent := parseTeamIdentity("São Paulo")
	without := parseTeamIdentity("Sao Paulo-SP")
	// Then their normalized base names are identical
	if withAccent.base != without.base {
		t.Fatalf("expected equal base, got %q and %q", withAccent.base, without.base)
	}
	// And a query in either spelling matches the other
	if !identityMatches(withAccent, "Sao Paulo") {
		t.Error("expected 'Sao Paulo' query to match 'São Paulo'")
	}
}

// Scenario: Clubs that share a base name but play in different states stay
// distinct so they are never merged.
func TestScenario_AmbiguousClubsStayDistinct(t *testing.T) {
	// Given the three Atlético clubs
	mg := parseTeamIdentity("Atlético-MG")
	pr := parseTeamIdentity("Athletico-PR")
	go_ := parseTeamIdentity("Atlético-GO")
	// Then each has a distinct group key
	keys := map[string]bool{mg.groupKey(): true, pr.groupKey(): true, go_.groupKey(): true}
	if len(keys) != 3 {
		t.Fatalf("expected 3 distinct group keys, got %v", keys)
	}
	// And a query naming one state does not match a club in another state
	if identityMatches(pr, "Atlético Mineiro") {
		t.Error("'Atlético Mineiro' must not match the Paranaense club")
	}
	// And the full name does match the suffixed form of the same club
	if !identityMatches(mg, "Atlético Mineiro") {
		t.Error("'Atlético Mineiro' should match 'Atlético-MG'")
	}
}

// Scenario: A short name matches a club's full official name.
func TestScenario_ShortNameMatchesFullName(t *testing.T) {
	// Given a club stored under its full official name
	full := parseTeamIdentity("Sport Club Corinthians Paulista")
	// When queried by the common short name
	// Then it matches
	if !identityMatches(full, "Corinthians") {
		t.Error("'Corinthians' should match 'Sport Club Corinthians Paulista'")
	}
}

// Feature: Competition normalization
//
// Scenario: Free-text competition queries resolve to one canonical league.
func TestScenario_CompetitionResolution(t *testing.T) {
	cases := map[string]string{
		"Brasileirão":    "Brasileirão Série A",
		"brasileirao":    "Brasileirão Série A",
		"Serie A":        "Brasileirão Série A",
		"Serie B":        "Brasileirão Série B",
		"Libertadores":   "Copa Libertadores",
		"copa do brasil": "Copa do Brasil",
	}
	for query, want := range cases {
		// When a competition query is resolved
		got := resolveCompetition(query)
		// Then it maps to the canonical competition name
		if got != want {
			t.Errorf("resolveCompetition(%q) = %q, want %q", query, got, want)
		}
	}
}

// Feature: Date parsing
//
// Scenario: Dates in any of the dataset formats are parsed.
func TestScenario_MultipleDateFormats(t *testing.T) {
	cases := []string{
		"2012-05-19 18:30:00", // ISO with time
		"2023-09-24",          // ISO date
		"29/03/2003",          // Brazilian DD/MM/YYYY
	}
	for _, in := range cases {
		// When the date string is parsed
		_, ok := parseDate(in)
		// Then parsing succeeds
		if !ok {
			t.Errorf("parseDate(%q) failed", in)
		}
	}
	// And an unparseable string is reported as such
	if _, ok := parseDate("not a date"); ok {
		t.Error("parseDate should fail on garbage input")
	}
}
