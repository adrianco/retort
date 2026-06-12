// Context: Brazilian Soccer MCP Server.
// File: normalize_test.go
// Purpose: Tests for team-name normalization, which underpins consistent
// matching across datasets that use different naming conventions (state
// suffixes, country codes, accents, full club names).
package soccer

import "testing"

func TestNormalizeTeamName(t *testing.T) {
	cases := []struct {
		raw  string
		want string
	}{
		{"Palmeiras-SP", "palmeiras"},
		{"Flamengo-RJ", "flamengo"},
		{"América - MG", "america"},
		{"Barcelona-EQU", "barcelona"},
		{"Nacional (URU)", "nacional"},
		{"São Paulo", "sao paulo"},
		{"Grêmio", "gremio"},
		{"  Santos  ", "santos"},
		{"Atlético-MG", "atletico"},
		{"Sport Club Corinthians Paulista", "sport club corinthians paulista"},
	}
	for _, c := range cases {
		if got := NormalizeTeamName(c.raw); got != c.want {
			t.Errorf("NormalizeTeamName(%q) = %q, want %q", c.raw, got, c.want)
		}
	}
}

// CleanTeamName keeps accents and proper casing for display but strips the
// state/country suffix noise.
func TestCleanTeamName(t *testing.T) {
	cases := []struct {
		raw  string
		want string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"América - MG", "América"},
		{"Nacional (URU)", "Nacional"},
		{"  Grêmio  ", "Grêmio"},
		// Only uppercase state/country codes are suffixes; a hyphenated club
		// name like "Colo-Colo" must be left intact.
		{"Colo-Colo", "Colo-Colo"},
	}
	for _, c := range cases {
		if got := CleanTeamName(c.raw); got != c.want {
			t.Errorf("CleanTeamName(%q) = %q, want %q", c.raw, got, c.want)
		}
	}
}

// TeamMatches reports whether a free-text query refers to a given team name,
// tolerating partial / full-name variations.
func TestTeamMatches(t *testing.T) {
	cases := []struct {
		query string
		team  string
		want  bool
	}{
		{"Corinthians", "Sport Club Corinthians Paulista", true},
		{"Palmeiras", "Palmeiras-SP", true},
		{"flamengo", "Flamengo-RJ", true},
		{"São Paulo", "Sao Paulo", true},
		{"Santos", "Palmeiras-SP", false},
		{"", "Palmeiras-SP", false},
	}
	for _, c := range cases {
		if got := TeamMatches(c.query, c.team); got != c.want {
			t.Errorf("TeamMatches(%q, %q) = %v, want %v", c.query, c.team, got, c.want)
		}
	}
}
