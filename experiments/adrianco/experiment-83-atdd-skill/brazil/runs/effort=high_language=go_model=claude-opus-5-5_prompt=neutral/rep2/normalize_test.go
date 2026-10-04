package main

import (
	"testing"
)

func TestFoldText(t *testing.T) {
	cases := map[string]string{
		"São Paulo":         "sao paulo",
		"Grêmio":            "gremio",
		"Avaí":              "avai",
		"Criciúma":          "criciuma",
		"Sampaio Corrêa":    "sampaio correa",
		"Confiança":         "confianca",
		"ATLÉTICO-MG":       "atletico-mg",
		"Peñarol":           "penarol",
		"Vélez Sarsfield":   "velez sarsfield",
		"Ødegaard":          "odegaard",
		"plain ascii stays": "plain ascii stays",
	}
	for in, want := range cases {
		if got := foldText(in); got != want {
			t.Errorf("foldText(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestParseTeamName(t *testing.T) {
	cases := []struct {
		raw          string
		base, region string
		country      bool
	}{
		{"Palmeiras-SP", "palmeiras", "sp", false},
		{"Palmeiras - SP", "palmeiras", "sp", false},
		{"Palmeiras", "palmeiras", "", false},
		{"Sociedade Esportiva Palmeiras", "palmeiras", "sp", false},
		{"Sport Club Corinthians Paulista", "corinthians", "sp", false},
		{"Sao Paulo-SP", "sao paulo", "sp", false},
		{"São Paulo FC", "sao paulo", "", false},
		{"Atletico-PR", "atletico", "pr", false},
		{"Athletico Paranaense - PR", "atletico", "pr", false},
		{"Athletico", "atletico", "pr", false},
		{"Atlético Mineiro - MG", "atletico", "mg", false},
		{"Atletico Goianiense", "atletico", "go", false},
		{"Vasco da Gama-RJ", "vasco", "rj", false},
		{"Vasco", "vasco", "", false},
		{"Red Bull Bragantino-SP", "bragantino", "sp", false},
		{"Bragantino PA", "bragantino", "pa", false},
		{"Sport Recife", "sport", "pe", false},
		{"Nautico Capibaribe", "nautico", "pe", false},
		{"Fortaleza EC", "fortaleza", "", false},
		{"EC Bahia", "bahia", "", false},
		{"C. R. B. - AL", "crb", "al", false},
		{"A.b.c. - RN", "abc", "rn", false},
		{"Parnahyba S.c - PI", "parnahyba", "pi", false},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista", "rj", false},
		{"Flamengo - PI", "flamengo", "pi", false},
		{"Nacional (URU)", "nacional", "uru", true},
		{"Nacional-URU", "nacional", "uru", true},
		{"Guaraní (PAR)", "guarani", "par", true},
		{"Barcelona-EQU", "barcelona", "equ", true},
		{"River Plate", "river plate", "", false},
		{"América FC (Minas Gerais)", "america", "mg", false},
		{"Ceará Sporting Club", "ceara", "", false},
		{"Clube Do Remo", "remo", "", false},
	}
	for _, c := range cases {
		p := parseTeamName(c.raw)
		if p.Base != c.base || p.Region != c.region || p.Country != c.country {
			t.Errorf("parseTeamName(%q) = %+v, want base=%q region=%q country=%v", c.raw, p, c.base, c.region, c.country)
		}
	}
}

func TestDisplayBase(t *testing.T) {
	cases := map[string]string{
		"Grêmio - RS":    "Grêmio",
		"Palmeiras-SP":   "Palmeiras",
		"Nacional (URU)": "Nacional",
		"Barcelona-EQU":  "Barcelona",
		"Ponte Preta":    "Ponte Preta",
		"Santos AP":      "Santos",
		"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ": "Boavista Sport Club",
	}
	for in, want := range cases {
		if got := displayBase(in); got != want {
			t.Errorf("displayBase(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestNormalizeCompetition(t *testing.T) {
	cases := map[string]string{
		"":                      "",
		"all":                   "",
		"Brasileirão":           CompSerieA,
		"brasileirao":           CompSerieA,
		"Serie A":               CompSerieA,
		"Série A":               CompSerieA,
		"Campeonato Brasileiro": CompSerieA,
		"Serie B":               CompSerieB,
		"serie-c":               CompSerieC,
		"Copa do Brasil":        CompCopaBrasil,
		"Brazilian Cup":         CompCopaBrasil,
		"Libertadores":          CompLibertadores,
		"Copa Libertadores":     CompLibertadores,
	}
	for in, want := range cases {
		got, err := normalizeCompetition(in)
		if err != nil || got != want {
			t.Errorf("normalizeCompetition(%q) = %q, %v; want %q", in, got, err, want)
		}
	}
	if _, err := normalizeCompetition("Premier League"); err == nil {
		t.Error("expected error for unknown competition")
	}
}

func TestParseDate(t *testing.T) {
	cases := []struct {
		in      string
		want    string
		hasTime bool
	}{
		{"2023-09-24", "2023-09-24 00:00", false},
		{"29/03/2003", "2003-03-29 00:00", false},
		{"2012-05-19 18:30:00", "2012-05-19 18:30", true},
	}
	for _, c := range cases {
		d, hasTime, err := parseDate(c.in)
		if err != nil {
			t.Fatalf("parseDate(%q): %v", c.in, err)
		}
		if got := d.Format("2006-01-02 15:04"); got != c.want || hasTime != c.hasTime {
			t.Errorf("parseDate(%q) = %s (time %v), want %s (time %v)", c.in, got, hasTime, c.want, c.hasTime)
		}
	}
	if _, _, err := parseDate("yesterday"); err == nil {
		t.Error("expected error for invalid date")
	}
}

func TestNormalizeStage(t *testing.T) {
	cases := map[string]string{
		"final": "final", "Finals": "final", "semi-final": "semifinals", "Semifinals": "semifinals",
		"quarter finals": "quarterfinals", "round of 16": "round of 16", "group": "group stage", "": "",
	}
	for in, want := range cases {
		if got := normalizeStage(in); got != want {
			t.Errorf("normalizeStage(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestCompactYears(t *testing.T) {
	if got := compactYears([]int{2012, 2013, 2014, 2016, 2018, 2019}); got != "2012-2014, 2016, 2018-2019" {
		t.Errorf("compactYears = %q", got)
	}
}
