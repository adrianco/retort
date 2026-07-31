// names_test.go covers the name normalisation rules in isolation: accent
// folding, state and country suffixes, generic club words, the alias table and
// the argument parsers used by the MCP tools.
package soccer

import "testing"

func TestFoldKey(t *testing.T) {
	cases := map[string]string{
		"São Paulo":               "sao paulo",
		"Grêmio":                  "gremio",
		"Avaí":                    "avai",
		"Atlético-MG":             "atletico mg",
		"A.b.c. - RN":             "a b c rn",
		"  Vasco  da Gama":        "vasco da gama",
		"Fortaleza Esporte Clube": "fortaleza esporte clube",
		"":                        "",
	}
	for in, want := range cases {
		if got := foldKey(in); got != want {
			t.Errorf("foldKey(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestParseTeamName(t *testing.T) {
	cases := []struct {
		raw     string
		base    string
		state   string
		country string
		pretty  string
	}{
		{"Palmeiras-SP", "palmeiras", "SP", "", "Palmeiras"},
		{"Palmeiras", "palmeiras", "", "", "Palmeiras"},
		{"América - MG", "america", "MG", "", "América"},
		{"America MG", "america", "MG", "", "America"},
		{"América FC (Minas Gerais)", "america", "MG", "", "América"},
		{"Nacional (URU)", "nacional", "", "URU", "Nacional"},
		{"Barcelona-EQU", "barcelona", "", "EQU", "Barcelona"},
		{"Guaraní-PAR", "guarani", "", "PAR", "Guaraní"},
		{"Athletico Paranaense - PR", "atletico", "PR", "", "Athletico Paranaense"},
		{"Atlético-PR", "atletico", "PR", "", "Atlético"},
		{"Athletico", "atletico", "PR", "", "Athletico"},
		{"Atlético Mineiro", "atletico", "MG", "", "Atlético Mineiro"},
		{"Vasco da Gama-RJ", "vasco da gama", "RJ", "", "Vasco da Gama"},
		{"Vasco", "vasco da gama", "RJ", "", "Vasco"},
		{"Sport Club do Recife", "sport", "PE", "", "Sport Club do Recife"},
		{"Sport-PE", "sport", "PE", "", "Sport"},
		{"Ceará Sporting Club", "ceara", "", "", "Ceará"},
		{"Fortaleza EC", "fortaleza", "", "", "Fortaleza"},
		{"EC Vitoria", "vitoria", "BA", "", "Vitoria"},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista", "RJ", "", "Boavista"},
		{"Red Bull Bragantino-SP", "bragantino", "SP", "", "Red Bull Bragantino"},
		{"Colo-Colo", "colo colo", "", "", "Colo-Colo"},
		{"River Plate", "river plate", "", "ARG", "River Plate"},
		{"River Plate - SE", "river plate", "SE", "", "River Plate"},
		{"Flamengo", "flamengo", "RJ", "", "Flamengo"},
		{"Flamengo - PI", "flamengo", "PI", "", "Flamengo"},
		{"Aquidauanense Futebol Clube - MS", "aquidauanense", "MS", "", "Aquidauanense"},
	}
	for _, c := range cases {
		got := parseTeamName(c.raw)
		if got.Base != c.base || got.State != c.state || got.Country != c.country {
			t.Errorf("parseTeamName(%q) = base %q state %q country %q; want %q / %q / %q",
				c.raw, got.Base, got.State, got.Country, c.base, c.state, c.country)
		}
		if got.Pretty != c.pretty {
			t.Errorf("parseTeamName(%q).Pretty = %q, want %q", c.raw, got.Pretty, c.pretty)
		}
	}
}

// TestParseTeamNameKeepsRivalsApart guards against the normaliser being so
// aggressive that two different clubs collapse into one.
func TestParseTeamNameKeepsRivalsApart(t *testing.T) {
	pairs := [][2]string{
		{"Atlético-MG", "Atlético-PR"},
		{"América - MG", "América - RN"},
		{"Botafogo - RJ", "Botafogo - PB"},
		{"Grêmio", "Grêmio Prudente"},
		{"Santos-SP", "Santos - AP"},
		{"River Plate", "River Plate - SE"},
		{"Sport-PE", "Sport Club do Recife - PE"},
		{"Atlético Nacional", "Atlético-MG"},
		{"Nacional (URU)", "Atlético Nacional"},
	}
	for _, p := range pairs {
		a, b := parseTeamName(p[0]), parseTeamName(p[1])
		if a.groupKey() == b.groupKey() && p[0] != "Sport-PE" {
			t.Errorf("%q and %q collapsed onto the same identity %q", p[0], p[1], a.groupKey())
		}
	}
	// The exception above is intentional: "Sport Club do Recife" really is the
	// same club as "Sport-PE" and must merge.
	if parseTeamName("Sport-PE").groupKey() != parseTeamName("Sport Club do Recife - PE").groupKey() {
		t.Error("Sport-PE and Sport Club do Recife should be the same club")
	}
}

func TestParseCompetition(t *testing.T) {
	cases := map[string]Competition{
		"":                      "",
		"serie a":               SerieA,
		"Série A":               SerieA,
		"brasileirao":           SerieA,
		"Campeonato Brasileiro": SerieA,
		"Serie B":               SerieB,
		"serie c":               SerieC,
		"copa do brasil":        CopaDoBrasil,
		"Brazilian Cup":         CopaDoBrasil,
		"libertadores":          Libertadores,
		"Copa Libertadores":     Libertadores,
	}
	for in, want := range cases {
		got, err := ParseCompetition(in)
		if err != nil {
			t.Errorf("ParseCompetition(%q): %v", in, err)
			continue
		}
		if got != want {
			t.Errorf("ParseCompetition(%q) = %q, want %q", in, got, want)
		}
	}
	if _, err := ParseCompetition("Premier League"); err == nil {
		t.Error("expected an error for an unknown competition")
	}
}

func TestParseVenueAndMetric(t *testing.T) {
	for _, in := range []string{"", "all", "home", "away"} {
		if _, err := ParseVenue(in); err != nil {
			t.Errorf("ParseVenue(%q): %v", in, err)
		}
	}
	if _, err := ParseVenue("neutral"); err == nil {
		t.Error("expected an error for an unknown venue")
	}
	for _, in := range []string{"", "most_wins", "best win rate", "goals", "best defense", "clean_sheets"} {
		if _, err := ParseMetric(in); err != nil {
			t.Errorf("ParseMetric(%q): %v", in, err)
		}
	}
	if _, err := ParseMetric("most_headers"); err == nil {
		t.Error("expected an error for an unknown metric")
	}
}

func TestParseDateFormats(t *testing.T) {
	cases := map[string]string{
		"2012-05-19 18:30:00": "2012-05-19",
		"2023-09-24":          "2023-09-24",
		"29/03/2003":          "2003-03-29",
	}
	for in, want := range cases {
		got, ok := parseDate(in)
		if !ok {
			t.Errorf("parseDate(%q) failed", in)
			continue
		}
		if got.Format("2006-01-02") != want {
			t.Errorf("parseDate(%q) = %s, want %s", in, got.Format("2006-01-02"), want)
		}
	}
	for _, in := range []string{"", "NA", "-", "not a date"} {
		if _, ok := parseDate(in); ok {
			t.Errorf("parseDate(%q) should have failed", in)
		}
	}
}

func TestParseMoney(t *testing.T) {
	cases := map[string]int64{
		"€110.5M": 110_500_000,
		"€565K":   565_000,
		"€0":      0,
		"":        0,
		"€1.1M":   1_100_000,
	}
	for in, want := range cases {
		if got := parseMoney(in); got != want {
			t.Errorf("parseMoney(%q) = %d, want %d", in, got, want)
		}
	}
}

func TestPositionGroup(t *testing.T) {
	cases := map[string]string{
		"GK": "goalkeeper", "CB": "defender", "LB": "defender",
		"CDM": "midfielder", "CAM": "midfielder", "RM": "midfielder",
		"ST": "forward", "LW": "forward", "CF": "forward", "": "",
	}
	for in, want := range cases {
		if got := positionGroup(in); got != want {
			t.Errorf("positionGroup(%q) = %q, want %q", in, got, want)
		}
	}
}
