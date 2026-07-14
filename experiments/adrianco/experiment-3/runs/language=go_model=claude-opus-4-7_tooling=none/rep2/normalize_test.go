// normalize_test.go covers team-name normalization: the data-quality concern
// called out in the specification (state suffixes, country codes, accents).
package main

import "testing"

func TestNormalizeTeamKey(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{"state suffix becomes token", "Palmeiras-SP", "palmeiras sp"},
		{"spaced state suffix", "América - MG", "america mg"},
		{"drops country code in parens", "Nacional (URU)", "nacional"},
		{"folds accents", "Grêmio", "gremio"},
		{"folds accents and case", "São Paulo", "sao paulo"},
		{"plain name unchanged", "Flamengo", "flamengo"},
		{"drops parenthetical qualifier", "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista sport club rj"},
		{"collapses whitespace", "  Vasco   da Gama ", "vasco da gama"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			// When the team name is normalized
			got := normalizeTeamKey(c.in)
			// Then it matches the expected canonical key
			if got != c.want {
				t.Errorf("normalizeTeamKey(%q) = %q, want %q", c.in, got, c.want)
			}
		})
	}
}

func TestKeyContainsHandlesVariations(t *testing.T) {
	// Given the same club written several ways
	variations := []string{"Palmeiras", "Palmeiras-SP", "palmeiras", "PALMEIRAS", "Palmeiras - SP"}
	// When a bare query is matched against each normalized key
	// Then the query finds every variation
	for _, v := range variations {
		key := normalizeTeamKey(v)
		if !keyContains(key, "Palmeiras") {
			t.Errorf("query 'Palmeiras' did not match variation %q (key %q)", v, key)
		}
	}
}

func TestNormalizeKeepsStateDisambiguation(t *testing.T) {
	// Clubs sharing a base name must remain distinct keys.
	mg := normalizeTeamKey("Atlético-MG")
	pr := normalizeTeamKey("Atlético-PR")
	if mg == pr {
		t.Errorf("Atlético-MG and Atlético-PR collapsed to the same key %q", mg)
	}
}

func TestStripAccents(t *testing.T) {
	cases := map[string]string{
		"São Paulo": "Sao Paulo",
		"Grêmio":    "Gremio",
		"Avaí":      "Avai",
		"Atlético":  "Atletico",
		"Fortaleza": "Fortaleza",
		"Ceará":     "Ceara",
	}
	for in, want := range cases {
		if got := stripAccents(in); got != want {
			t.Errorf("stripAccents(%q) = %q, want %q", in, got, want)
		}
	}
}
