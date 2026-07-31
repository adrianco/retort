package soccer

import (
	"testing"
	"time"
)

func TestFold(t *testing.T) {
	cases := map[string]string{
		"São Paulo":       "sao paulo",
		"Grêmio":          "gremio",
		"Avaí":            "avai",
		"Atlético-MG":     "atletico-mg",
		"Fortaleza":       "fortaleza",
		"CRICIÚMA":        "criciuma",
		"Peñarol":         "penarol",
		"Nacional (URU)":  "nacional (uru)",
		"\ufeffColumn":    "column",
		"Coritiba  F.B.C": "coritiba  f.b.c",
	}
	for in, want := range cases {
		if got := Fold(in); got != want {
			t.Errorf("Fold(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestNormalizeTeamName(t *testing.T) {
	cases := []struct {
		raw       string
		base      string
		qualifier string
		isState   bool
	}{
		{"Palmeiras-SP", "palmeiras", "SP", true},
		{"Palmeiras", "palmeiras", "", false},
		{"América - MG", "america", "MG", true},
		{"América-RN", "america", "RN", true},
		{"Vasco da Gama-RJ", "vasco da gama", "RJ", true},
		{"Vasco Da Gama RJ", "vasco da gama", "RJ", true},
		{"Sport Club Corinthians Paulista", "sport club corinthians paulista", "", false}, // resolved by the alias table
		{"Arapongas Esporte Clube - PR", "arapongas", "PR", true},
		{"Aquidauanense Futebol Clube - MS", "aquidauanense", "MS", true},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista", "RJ", true},
		{"A.b.c. - RN", "abc", "RN", true},
		{"A.s.a. - AL", "asa", "AL", true},
		{"EC Bahia", "bahia", "", false},
		{"Clube Do Remo", "remo", "", false},
		{"GE Bage", "bage", "", false},
		{"Nacional (URU)", "nacional", "URU", false},
		{"Nacional-URU", "nacional", "URU", false},
		{"Guaraní (PAR)", "guarani", "PAR", false},
		{"Barcelona-EQU", "barcelona", "ECU", false},
		{"América FC (Minas Gerais)", "america", "MG", true},
		{"Ceará Sporting Club", "ceara", "", false},
		{"Sport Club do Recife", "sport club do recife", "", false},
		{"Newells Old Boys", "newells old boys", "", false},
		{"O'Higgins", "o higgins", "", false},
		{"4 de Julho - PI", "4 de julho", "PI", true},
		{"Rentistas ", "rentistas", "", false},
	}
	for _, c := range cases {
		got := NormalizeTeamName(c.raw)
		if got.Base != c.base || got.Qualifier != c.qualifier || got.IsState != c.isState {
			t.Errorf("NormalizeTeamName(%q) = {base:%q qualifier:%q state:%v}, want {%q %q %v}",
				c.raw, got.Base, got.Qualifier, got.IsState, c.base, c.qualifier, c.isState)
		}
	}
}

func TestTeamNameKey(t *testing.T) {
	if got := NormalizeTeamName("Vasco da Gama-RJ").Key(); got != "vasco-da-gama-rj" {
		t.Errorf("Key() = %q", got)
	}
	if got := NormalizeTeamName("Santos").Key(); got != "santos" {
		t.Errorf("Key() = %q", got)
	}
}

func TestParseDate(t *testing.T) {
	cases := []struct {
		in      string
		want    string
		hasTime bool
		ok      bool
	}{
		{"2012-05-19 18:30:00", "2012-05-19", true, true},
		{"2023-09-24", "2023-09-24", false, true},
		{"29/03/2003", "2003-03-29", false, true},
		{"01/12/2019", "2019-12-01", false, true},
		{"2012-05-19T18:30:00", "2012-05-19", true, true},
		{"", "", false, false},
		{"not a date", "", false, false},
	}
	for _, c := range cases {
		got, hasTime, ok := ParseDate(c.in)
		if ok != c.ok {
			t.Errorf("ParseDate(%q) ok = %v, want %v", c.in, ok, c.ok)
			continue
		}
		if !ok {
			continue
		}
		if got.Format("2006-01-02") != c.want || hasTime != c.hasTime {
			t.Errorf("ParseDate(%q) = %s (hasTime %v), want %s (hasTime %v)",
				c.in, got.Format("2006-01-02"), hasTime, c.want, c.hasTime)
		}
	}
}

func TestParseDateTime(t *testing.T) {
	got, hasTime, ok := ParseDateTime("2023-09-24", "20:00:00")
	if !ok || !hasTime {
		t.Fatalf("ParseDateTime failed: ok=%v hasTime=%v", ok, hasTime)
	}
	want := time.Date(2023, 9, 24, 20, 0, 0, 0, time.UTC)
	if !got.Equal(want) {
		t.Errorf("ParseDateTime = %s, want %s", got, want)
	}
	if _, _, ok := ParseDateTime("", "20:00:00"); ok {
		t.Error("ParseDateTime with no date should fail")
	}
}

func TestParseIntLoose(t *testing.T) {
	cases := []struct {
		in   string
		want int
		ok   bool
	}{
		{"3", 3, true},
		{"1.0", 1, true},
		{`"2"`, 2, true},
		{" 4 ", 4, true},
		{"", 0, false},
		{"n/a", 0, false},
	}
	for _, c := range cases {
		got, ok := ParseIntLoose(c.in)
		if got != c.want || ok != c.ok {
			t.Errorf("ParseIntLoose(%q) = %d,%v want %d,%v", c.in, got, ok, c.want, c.ok)
		}
	}
}

func TestStageMatches(t *testing.T) {
	cases := []struct {
		stage, want string
		match       bool
	}{
		{"final", "final", true},
		{"final (inferred)", "final", true},
		{"quarterfinals", "final", false},
		{"semifinals", "final", false},
		{"semifinals", "semi", true},
		{"quarterfinals", "quarter", true},
		{"group stage", "group stage", true},
		{"group stage", "group", true},
		{"round of 16", "round of 16", true},
		{"", "final", false},
		{"final", "", true},
	}
	for _, c := range cases {
		if got := StageMatches(c.stage, c.want); got != c.match {
			t.Errorf("StageMatches(%q, %q) = %v, want %v", c.stage, c.want, got, c.match)
		}
	}
}

func TestLevenshtein(t *testing.T) {
	cases := []struct {
		a, b string
		want int
	}{
		{"vila nova", "villa nova", 1},
		{"america", "america", 0},
		{"flamengo", "fluminense", 5},
		{"", "abc", 3},
	}
	for _, c := range cases {
		if got := Levenshtein(c.a, c.b); got != c.want {
			t.Errorf("Levenshtein(%q, %q) = %d, want %d", c.a, c.b, got, c.want)
		}
	}
}

func TestSlug(t *testing.T) {
	if got := Slug("Estádio do Maracanã"); got != "estadio-do-maracana" {
		t.Errorf("Slug = %q", got)
	}
}

func TestResolveCompetition(t *testing.T) {
	cases := map[string]string{
		"brasileirao":           CompBrasileirao,
		"Brasileirão":           CompBrasileirao,
		"Serie A":               CompBrasileirao,
		"campeonato brasileiro": CompBrasileirao,
		"serie b":               CompSerieB,
		"Copa do Brasil":        CompCopaDoBrasil,
		"libertadores":          CompLibertadores,
		"Copa Libertadores":     CompLibertadores,
	}
	for in, want := range cases {
		got, ok := ResolveCompetition(in)
		if !ok || got != want {
			t.Errorf("ResolveCompetition(%q) = %q,%v want %q", in, got, ok, want)
		}
	}
	if _, ok := ResolveCompetition("Premier League"); ok {
		t.Error("Premier League should not resolve")
	}
}
