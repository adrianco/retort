package main

import (
	"testing"
)

func TestNormalizeTeam_StripsSuffix(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Palmeiras-SP", "Palmeiras"},
		{"Sport-PE", "Sport"},
		{"Flamengo", "Flamengo"},
		{"Flamengo-RJ", "Flamengo"},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "Boavista Sport Club (antigo Esporte Clube Barreira)"},
		{"América - MG", "América"},
		{"Nacional (URU)", "Nacional (URU)"},
	}
	for _, tc := range tests {
		got := NormalizeTeam(tc.input)
		if got != tc.expected {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", tc.input, got, tc.expected)
		}
	}
}

func TestTeamMatches_CaseInsensitive(t *testing.T) {
	if !TeamMatches("Palmeiras", "Palmeiras-SP") {
		t.Error("expected Palmeiras to match Palmeiras-SP")
	}
	if !TeamMatches("palmeiras", "Palmeiras-SP") {
		t.Error("expected palmeiras (lowercase) to match Palmeiras-SP")
	}
	if !TeamMatches("Flamengo", "Flamengo-RJ") {
		t.Error("expected Flamengo to match Flamengo-RJ")
	}
}

func TestTeamMatches_SubstringMatch(t *testing.T) {
	if !TeamMatches("Boavista", "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ") {
		t.Error("expected Boavista to match Boavista Sport Club...")
	}
	if !TeamMatches("sport", "Sport-PE") {
		t.Error("expected sport (lowercase) to match Sport-PE")
	}
}

func TestTeamMatches_NoFalsePositive(t *testing.T) {
	if TeamMatches("São Paulo", "Sao Paulo") {
		t.Error("São Paulo should NOT match Sao Paulo (accent difference, exact match required after normalize)")
	}
}

func TestParseDate_ISOFormat(t *testing.T) {
	dt, err := ParseDate("2023-09-24")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if dt.IsZero() {
		t.Error("expected non-zero time for ISO date")
	}
	if dt.Year() != 2023 || dt.Month() != 9 || dt.Day() != 24 {
		t.Errorf("expected 2023-09-24, got %v", dt)
	}
}

func TestParseDate_DatetimeFormat(t *testing.T) {
	dt, err := ParseDate("2012-05-19 18:30:00")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if dt.Year() != 2012 || dt.Month() != 5 || dt.Day() != 19 {
		t.Errorf("expected 2012-05-19, got %v", dt)
	}
}

func TestParseDate_BrazilianFormat(t *testing.T) {
	dt, err := ParseDate("29/03/2003")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if dt.Year() != 2003 || dt.Month() != 3 || dt.Day() != 29 {
		t.Errorf("expected 29/03/2003, got %v", dt)
	}
}
