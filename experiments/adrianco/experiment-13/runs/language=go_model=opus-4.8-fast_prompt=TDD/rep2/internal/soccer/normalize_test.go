package soccer

import "testing"

// NormalizeTeam folds accents, lowercases, and reduces a name to
// space-separated alphanumeric tokens. The state/country code (if any) is
// preserved as a token so that distinct teams that differ only by state
// (Atletico-MG vs Atletico-GO) do not collide.
func TestNormalizeTeam(t *testing.T) {
	cases := []struct {
		in   string
		want string
	}{
		{"Palmeiras-SP", "palmeiras sp"},
		{"Atletico-MG", "atletico mg"},
		{"Flamengo-RJ", "flamengo rj"},
		{"São Paulo", "sao paulo"},
		{"Grêmio-RS", "gremio rs"},
		{"Avaí-SC", "avai sc"},
		{"América - MG", "america mg"},
		{"Nacional (URU)", "nacional uru"},
		{"Barcelona-EQU", "barcelona equ"},
		{"Vasco", "vasco"},
		{"  Corinthians  ", "corinthians"},
		{"Fortaleza Esporte Clube", "fortaleza esporte clube"},
		{"", ""},
	}
	for _, c := range cases {
		if got := NormalizeTeam(c.in); got != c.want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

// TeamsMatch reports whether two raw team names refer to the same team,
// tolerating missing state suffixes and accent/case differences. It matches
// when one name's token set is a subset of the other's.
func TestTeamsMatch(t *testing.T) {
	pairs := []struct {
		a, b string
		want bool
	}{
		{"Palmeiras-SP", "Palmeiras", true},
		{"São Paulo", "Sao Paulo", true},
		{"Grêmio-RS", "Gremio", true},
		{"Nacional (URU)", "Nacional", true},
		{"Flamengo", "Fluminense", false},
		// Same base name, different states must NOT match.
		{"Atletico-MG", "Atletico-GO", false},
		// A bare base name matches any state variant (intentional ambiguity).
		{"Atletico-MG", "Atletico", true},
		{"", "Flamengo", false},
	}
	for _, p := range pairs {
		if got := TeamsMatch(p.a, p.b); got != p.want {
			t.Errorf("TeamsMatch(%q,%q) = %v, want %v", p.a, p.b, got, p.want)
		}
	}
}
