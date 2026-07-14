package soccer

import "testing"

func TestNormalizeTeamName(t *testing.T) {
	cases := []struct {
		input string
		want  string
	}{
		{"Flamengo-RJ", "flamengo"},
		{"Palmeiras-SP", "palmeiras"},
		{"Atlético-MG", "atlético"},
		{"Nacional (URU)", "nacional (uru)"},
		{"Barcelona-EQU", "barcelona-equ"}, // 3-letter suffix, not stripped
		{"Flamengo", "flamengo"},
		{"América - MG", "américa"},
		{"Sport-PE", "sport"},
	}
	for _, c := range cases {
		got := NormalizeTeamName(c.input)
		if got != c.want {
			t.Errorf("NormalizeTeamName(%q) = %q, want %q", c.input, got, c.want)
		}
	}
}

func TestTeamsMatch(t *testing.T) {
	cases := []struct {
		a, b string
		want bool
	}{
		{"Flamengo-RJ", "Flamengo", true},
		{"Palmeiras-SP", "Palmeiras", true},
		{"Flamengo", "Fluminense", false},
		{"Corinthians-SP", "Corinthians", true},
	}
	for _, c := range cases {
		got := TeamsMatch(c.a, c.b)
		if got != c.want {
			t.Errorf("TeamsMatch(%q, %q) = %v, want %v", c.a, c.b, got, c.want)
		}
	}
}
