package main

import "testing"

func TestParseTeamName(t *testing.T) {
	cases := []struct {
		raw       string
		wantBase  string
		wantState string
	}{
		{"Palmeiras-SP", "palmeiras", "SP"},
		{"Flamengo-RJ", "flamengo", "RJ"},
		{"América - MG", "america", "MG"},
		{"América-RN", "america", "RN"},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista sport club", "RJ"},
		{"Barcelona-EQU", "barcelona", "EQU"},
		{"Nacional (URU)", "nacional", ""},
		{"São Paulo", "sao paulo", ""},
		{"Grêmio", "gremio", ""},
		{"Sport Club Corinthians Paulista", "sport club corinthians paulista", ""},
		{"Csa-AL", "csa", "AL"},
		{"America MG", "america", "MG"},
		{"Operario FC MS", "operario fc", "MS"},
		{"4 de Julho EC", "4 de julho ec", ""},
	}
	for _, c := range cases {
		got := parseTeamName(c.raw)
		if got.Base != c.wantBase {
			t.Errorf("parseTeamName(%q).Base = %q, want %q", c.raw, got.Base, c.wantBase)
		}
		if got.State != c.wantState {
			t.Errorf("parseTeamName(%q).State = %q, want %q", c.raw, got.State, c.wantState)
		}
	}
}

func TestParseTeamNameFullKeyDistinguishesStates(t *testing.T) {
	mg := parseTeamName("América-MG")
	rn := parseTeamName("América-RN")
	if mg.Full == rn.Full {
		t.Fatalf("expected América-MG and América-RN to have distinct full keys, both got %q", mg.Full)
	}
	if mg.Base != rn.Base {
		t.Fatalf("expected América-MG and América-RN to share a base key, got %q vs %q", mg.Base, rn.Base)
	}
}

func TestNormalizeKeyAccentAndCase(t *testing.T) {
	cases := map[string]string{
		"São Paulo":  "sao paulo",
		"CEARÁ":      "ceara",
		"Avaí":       "avai",
		"Fortaleza!": "fortaleza",
	}
	for in, want := range cases {
		if got := normalizeKey(in); got != want {
			t.Errorf("normalizeKey(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestFoldAccentsDoesNotTouchPlainASCII(t *testing.T) {
	if got := foldAccents("Flamengo"); got != "Flamengo" {
		t.Errorf("foldAccents(\"Flamengo\") = %q, want unchanged", got)
	}
}
