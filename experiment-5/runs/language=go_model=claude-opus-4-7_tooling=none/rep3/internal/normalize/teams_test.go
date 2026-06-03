package normalize

import "testing"

func TestKey(t *testing.T) {
	cases := []struct {
		in, want string
	}{
		{"Palmeiras-SP", "palmeiras"},
		{"Palmeiras - SP", "palmeiras"},
		{"Flamengo-RJ", "flamengo"},
		{"Grêmio", "gremio"},
		{"São Paulo", "sao paulo"},
		{"Nacional (URU)", "nacional"},
		{"", ""},
		{"  Botafogo-RJ  ", "botafogo"},
	}
	for _, c := range cases {
		got := Key(c.in)
		if got != c.want {
			t.Errorf("Key(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

func TestMatches(t *testing.T) {
	// Given two ways of writing the same team
	// When I compare them via Matches
	// Then the result should be true
	yes := [][2]string{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"Grêmio", "Gremio"},
		{"São Paulo", "Sao Paulo"},
		{"SE Palmeiras", "Palmeiras"},
	}
	for _, p := range yes {
		if !Matches(p[0], p[1]) {
			t.Errorf("Matches(%q, %q) = false, want true", p[0], p[1])
		}
	}
	no := [][2]string{
		{"Palmeiras", "Santos"},
		{"Flamengo", "Corinthians"},
	}
	for _, p := range no {
		if Matches(p[0], p[1]) {
			t.Errorf("Matches(%q, %q) = true, want false", p[0], p[1])
		}
	}
}
