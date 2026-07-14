package loader

import "testing"

func TestNormalizeTeamName(t *testing.T) {
	cases := []struct {
		input string
		want  string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"Flamengo", "Flamengo"},
		{"América - MG", "América"},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "Boavista Sport Club (antigo Esporte Clube Barreira)"},
	}
	for _, c := range cases {
		got := NormalizeTeamName(c.input)
		if got != c.want {
			t.Errorf("NormalizeTeamName(%q) = %q, want %q", c.input, got, c.want)
		}
	}
}
