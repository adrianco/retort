package main

import (
	"testing"
	"time"
)

func TestFeature_TeamNameNormalization(t *testing.T) {
	cases := []struct {
		scenario, raw, wantBase, wantState string
	}{
		{"state suffix without space", "Palmeiras-SP", "palmeiras", "SP"},
		{"state suffix with spaces", "Flamengo - RJ", "flamengo", "RJ"},
		{"bare state word", "Botafogo RJ", "botafogo", "RJ"},
		{"three-letter country code", "Nacional (URU)", "nacional", "URU"},
		{"accented name folds", "Atlético-MG", "atletico", "MG"},
		{"full name uses alias", "Sport Club Corinthians Paulista", "corinthians", "SP"},
		{"Portuguese prefix dropped", "EC Bahia", "bahia", ""},
		{"trailing club word dropped", "America FC", "america", ""},
		{"alias for named clubs", "Atletico Mineiro", "atletico", "MG"},
		{"Vasco spelled with da", "Vasco da Gama", "vasco", "RJ"},
		{"non-state parenthetical is dropped", "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavistasport", "RJ"},
	}
	for _, tc := range cases {
		t.Run(tc.scenario, func(t *testing.T) {
			// Given a club name written as in one of the datasets
			// When it is normalized
			got := parseTeamName(tc.raw)
			// Then the base key and state match the expected values
			if got.Base != tc.wantBase || got.State != tc.wantState {
				t.Fatalf("parseTeamName(%q) = base %q state %q; want base %q state %q",
					tc.raw, got.Base, got.State, tc.wantBase, tc.wantState)
			}
		})
	}
}

func TestFeature_AccentInsensitiveMatching(t *testing.T) {
	t.Run("Scenario: São Paulo and Sao Paulo are the same club", func(t *testing.T) {
		// Given two spellings with and without accents
		// When both are folded
		// Then they produce the same key
		if foldKey("São Paulo") != foldKey("Sao Paulo") {
			t.Fatalf("foldKey mismatch: %q vs %q", foldKey("São Paulo"), foldKey("Sao Paulo"))
		}
		if foldKey("Grêmio") != "gremio" {
			t.Fatalf("foldKey(Grêmio) = %q", foldKey("Grêmio"))
		}
	})
}

func TestFeature_DateFormats(t *testing.T) {
	cases := map[string]time.Time{
		"2023-09-24":          time.Date(2023, 9, 24, 0, 0, 0, 0, time.UTC),
		"2012-05-19 18:30:00": time.Date(2012, 5, 19, 18, 30, 0, 0, time.UTC),
		"29/03/2003":          time.Date(2003, 3, 29, 0, 0, 0, 0, time.UTC),
		"2023-09-24T20:00:00": time.Date(2023, 9, 24, 20, 0, 0, 0, time.UTC),
	}
	for input, want := range cases {
		t.Run("Scenario: parse "+input, func(t *testing.T) {
			// Given a date in one of the dataset formats
			// When it is parsed
			got, err := parseDate(input)
			// Then it parses to the expected instant
			if err != nil {
				t.Fatal(err)
			}
			if !got.Equal(want) {
				t.Fatalf("parseDate(%q) = %v; want %v", input, got, want)
			}
		})
	}

	t.Run("Scenario: reject a malformed date", func(t *testing.T) {
		// Given an unrecognized date
		// When it is parsed
		// Then an error is returned
		if _, err := parseDate("not a date"); err == nil {
			t.Fatal("expected an error")
		}
	})
}

func TestFeature_GoalParsing(t *testing.T) {
	t.Run("Scenario: goals stored as floats or quoted strings", func(t *testing.T) {
		for in, want := range map[string]int{"1.0": 1, "2": 2, " 0 ": 0} {
			got, err := parseGoals(in)
			if err != nil || got != want {
				t.Fatalf("parseGoals(%q) = %d, %v; want %d", in, got, err, want)
			}
		}
	})
	t.Run("Scenario: unplayed fixtures have no score", func(t *testing.T) {
		// Given a score of NA, which the 2022 file uses for fixtures not yet played
		// When it is parsed
		// Then parsing fails so the row is skipped
		if _, err := parseGoals("NA"); err == nil {
			t.Fatal("expected an error for NA")
		}
	})
}
