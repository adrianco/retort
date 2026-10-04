package soccer

import "testing"

func TestParseTeamNameUnderstandsEveryNamingStyle(t *testing.T) {
	cases := []struct{ raw, base, qualifier string }{
		{"Palmeiras-SP", "palmeiras", "SP"},
		{"Palmeiras - SP", "palmeiras", "SP"},
		{"Botafogo RJ", "botafogo", "RJ"},
		{"São Paulo", "sao paulo", ""},
		{"Nacional (URU)", "nacional", "URU"},
		{"Nacional-URU", "nacional", "URU"},
		{"Barcelona-EQU", "barcelona", "ECU"},
		{"Sport Club Corinthians Paulista", "corinthians", "SP"},
		{"Atletico-MG", "atletico mineiro", "MG"},
		{"Atlético Mineiro - MG", "atletico mineiro", "MG"},
		{"Athletico-PR", "athletico paranaense", "PR"},
		{"Atletico-PR", "athletico paranaense", "PR"},
		{"Athletico", "athletico paranaense", "PR"},
		{"Atlético Paranaense", "athletico paranaense", "PR"},
		{"Atletico Goianiense", "atletico goianiense", "GO"},
		{"America FC Natal", "america", "RN"},
		{"América FC (Minas Gerais)", "america", "MG"},
		{"Club América", "club america", ""},
		{"Fortaleza EC", "fortaleza", ""},
		{"EC Bahia", "bahia", ""},
		{"EC Internacional SC", "internacional", "SC"},
		{"C. R. B. - AL", "crb", "AL"},
		{"A.b.c. - RN", "abc", "RN"},
		{"Vasco", "vasco da gama", ""},
		{"Vasco Da Gama RJ", "vasco da gama", "RJ"},
		{"Sport Recife", "sport", "PE"},
		{"Sport Club do Recife", "sport", "PE"},
		{"Red Bull Bragantino-SP", "bragantino", "SP"},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista", "RJ"},
		{"Colo-Colo", "colo colo", ""},
		{"Paris Saint-Germain", "paris saint germain", ""},
	}
	for _, c := range cases {
		tn := ParseTeamName(c.raw)
		if tn.Base != c.base || tn.Qualifier != c.qualifier {
			t.Errorf("ParseTeamName(%q) = %q|%q, want %q|%q", c.raw, tn.Base, tn.Qualifier, c.base, c.qualifier)
		}
	}
}

func TestUnqualifiedNamesTakeTheirMostCommonState(t *testing.T) {
	teams := NewTeams()
	for _, raw := range []string{"Flamengo-RJ", "Flamengo-RJ", "Flamengo - PI", "Flamengo", "River Plate", "River Plate-URU"} {
		teams.Observe(ParseTeamName(raw))
	}
	teams.Settle()
	ids := map[string]TeamID{}
	for _, raw := range []string{"Flamengo-RJ", "Flamengo - PI", "Flamengo", "River Plate", "River Plate-URU"} {
		ids[raw] = teams.Register(ParseTeamName(raw))
	}
	if ids["Flamengo"] != ids["Flamengo-RJ"] {
		t.Errorf("plain Flamengo should be Flamengo-RJ, got %s", ids["Flamengo"])
	}
	if ids["Flamengo - PI"] == ids["Flamengo-RJ"] {
		t.Errorf("Flamengo-PI is a different club")
	}
	if ids["River Plate"] == ids["River Plate-URU"] {
		t.Errorf("a country qualifier must not become the default for an unqualified foreign club")
	}
	if got := teams.Name(ids["Flamengo"]); got != "Flamengo" {
		t.Errorf("display %q", got)
	}
	if got := teams.Name(ids["Flamengo - PI"]); got != "Flamengo-PI" {
		t.Errorf("display %q", got)
	}
	if got := teams.Name(ids["River Plate-URU"]); got != "River Plate (URU)" {
		t.Errorf("display %q", got)
	}
}

func TestResolveFindsClubsHoweverTheFanNamesThem(t *testing.T) {
	teams := NewTeams()
	for _, raw := range []string{"Sao Paulo-SP", "São Paulo", "Corinthians-SP", "Athletico-PR"} {
		teams.Observe(ParseTeamName(raw))
	}
	teams.Settle()
	for _, raw := range []string{"Sao Paulo-SP", "São Paulo", "Corinthians-SP", "Athletico-PR"} {
		teams.Register(ParseTeamName(raw))
	}
	for query, want := range map[string]TeamID{
		"sao paulo": "sao paulo|SP", "SÃO PAULO": "sao paulo|SP", "Corinthians Paulista": "corinthians|SP",
		"Paranaense": "athletico paranaense|PR", "Atlético-PR": "athletico paranaense|PR",
	} {
		if got, ok := teams.Resolve(query); !ok || got != want {
			t.Errorf("Resolve(%q) = %q, want %q", query, got, want)
		}
	}
	if _, ok := teams.Resolve("Real Madrid"); ok {
		t.Errorf("Real Madrid is not in the match data")
	}
}

func TestParseDateUnderstandsTheDatasetFormats(t *testing.T) {
	for _, s := range []string{"2023-09-24", "29/03/2003", "2012-05-19 18:30:00"} {
		if _, ok := ParseDate(s); !ok {
			t.Errorf("could not parse %q", s)
		}
	}
	d, _ := ParseDate("29/03/2003")
	if d.Day() != 29 || d.Month() != 3 || d.Year() != 2003 {
		t.Errorf("Brazilian dates are day first: %v", d)
	}
	if _, ok := ParseDate("NA"); ok {
		t.Errorf("NA is not a date")
	}
}

func TestParseCompetition(t *testing.T) {
	for in, want := range map[string]string{
		"Brasileirão": SerieA, "serie a": SerieA, "Série B": SerieB, "Serie C": SerieC,
		"Copa do Brasil": CopaDoBrasil, "libertadores": Libertadores, "Copa Libertadores": Libertadores, "nonsense": "",
	} {
		if got := ParseCompetition(in); got != want {
			t.Errorf("ParseCompetition(%q) = %q, want %q", in, got, want)
		}
	}
}
