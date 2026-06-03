package main

import "testing"

// BDD-style: Given two team names, When they refer to the same team, Then
// TeamMatches returns true.
func TestTeamMatches_Variations(t *testing.T) {
	cases := []struct {
		a, b string
		want bool
	}{
		{"Palmeiras", "Palmeiras-SP", true},
		{"Flamengo", "Flamengo-RJ", true},
		{"São Paulo", "Sao Paulo", true},
		{"Grêmio", "Gremio-RS", true},
		{"Corinthians", "SC Corinthians Paulista", true},
		{"Flamengo", "Fluminense", false},
		{"Palmeiras", "Santos", false},
		{"", "Anything", false},
	}
	for _, c := range cases {
		got := TeamMatches(c.a, c.b)
		if got != c.want {
			t.Errorf("TeamMatches(%q, %q) = %v, want %v", c.a, c.b, got, c.want)
		}
	}
}

func TestNormalizeTeam_DropsStateSuffix(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP":       "palmeiras",
		"Flamengo - RJ":      "flamengo",
		"São Paulo":          "sao paulo",
		"Grêmio":             "gremio",
		"Nacional (URU)":     "nacional",
	}
	for in, want := range cases {
		got := NormalizeTeam(in)
		if got != want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestContainsFold_IgnoresAccentsAndCase(t *testing.T) {
	if !ContainsFold("São Paulo FC", "sao paulo") {
		t.Errorf("expected accent-insensitive match")
	}
	if !ContainsFold("Grêmio", "gremio") {
		t.Errorf("expected accent-insensitive match")
	}
	if ContainsFold("Santos", "Palmeiras") {
		t.Errorf("expected no match")
	}
}
