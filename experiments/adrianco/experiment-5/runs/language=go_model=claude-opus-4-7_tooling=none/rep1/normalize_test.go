package main

import "testing"

// Feature: team name normalization across CSV naming conventions.

func TestNormalizeTeam_StripsStateSuffix(t *testing.T) {
	// Given a team name with a state suffix
	// When NormalizeTeam is called
	// Then the suffix is stripped, accents removed, lower-cased
	cases := map[string]string{
		"Palmeiras-SP":     "palmeiras",
		"Flamengo-RJ":      "flamengo",
		"Grêmio-RS":        "gremio",
		"Avaí-SC":          "avai",
		"Internacional-RS": "internacional",
	}
	for in, want := range cases {
		if got := NormalizeTeam(in); got != want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestNormalizeTeam_PreservesDisambiguatorForAmbiguousNames(t *testing.T) {
	// Given two clubs sharing a base name (Atlético MG vs Atlético PR)
	// When normalized, they must NOT collide.
	mg := NormalizeTeam("Atletico-MG")
	pr := NormalizeTeam("Atletico-PR")
	if mg == pr {
		t.Fatalf("Atletico-MG and Atletico-PR collided: both → %q", mg)
	}
	if mg != "atletico mineiro" {
		t.Errorf("Atletico-MG = %q, want atletico mineiro", mg)
	}
	if pr != "athletico paranaense" {
		t.Errorf("Atletico-PR = %q, want athletico paranaense", pr)
	}
}

func TestNormalizeTeam_LongFormAlias(t *testing.T) {
	// Given a long-form team name
	// When normalized, it maps to the canonical short key
	if got := NormalizeTeam("Sport Club Corinthians Paulista"); got != "corinthians" {
		t.Errorf("long-form Corinthians = %q", got)
	}
	if got := NormalizeTeam("Clube de Regatas do Flamengo"); got != "flamengo" {
		t.Errorf("long-form Flamengo = %q", got)
	}
}

func TestNormalizeTeam_StripsParenSuffix(t *testing.T) {
	// Given a Libertadores team with a country code in parens
	// When normalized, the paren block is removed
	if got := NormalizeTeam("Nacional (URU)"); got != "nacional" {
		t.Errorf("Nacional (URU) = %q", got)
	}
}

func TestNormalizeTeam_HandlesEmpty(t *testing.T) {
	if got := NormalizeTeam(""); got != "" {
		t.Errorf("empty = %q", got)
	}
}
