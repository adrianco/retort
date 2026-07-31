// normalize_test.go covers the team-name normaliser in isolation: the region
// suffix parser, the club-type token stripper and the alias tables. These are
// the cases the specification calls out under "Team Name Variations" and
// "Character Encoding".
package soccer

import "testing"

func TestFoldASCII(t *testing.T) {
	cases := map[string]string{
		"São Paulo": "Sao Paulo",
		"Grêmio":    "Gremio",
		"Avaí":      "Avai",
		"Náutico":   "Nautico",
		"Atlético":  "Atletico",
		"Peñarol":   "Penarol",
		"Criciúma":  "Criciuma",
		"Fortaleza": "Fortaleza",
		"Ji-paraná": "Ji-parana",
	}
	for in, want := range cases {
		if got := FoldASCII(in); got != want {
			t.Errorf("FoldASCII(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestParseTeamNameRegionSuffixes(t *testing.T) {
	cases := []struct {
		raw        string
		wantBase   string
		wantRegion string
	}{
		// The three suffix styles used across the datasets.
		{"Palmeiras-SP", "palmeiras", "SP"},
		{"América - MG", "america", "MG"},
		{"America MG", "america", "MG"},
		{"Vasco Da Gama RJ", "vascogama", "RJ"},
		{"Nacional (URU)", "nacional", "URU"},
		{"Barcelona-EQU", "barcelona", "EQU"},
		{"Guaraní (PAR)", "guarani", "PAR"},
		{"River (PI)", "river", "PI"},
		// Names that merely look like they carry a suffix.
		{"Colo-Colo", "colocolo", ""},
		{"Sport Boys", "sportboys", ""},
		{"O'Higgins", "ohiggins", ""},
		// Club-type words and initials are noise. "Sport Club do Recife" carries
		// no region in the name; its state arrives via the curated default,
		// which TestParseTeamNameDefaultRegions covers.
		{"Sport Club do Recife", "sport", ""},
		{"Fc Cascavel - PR", "cascavel", "PR"},
		{"Parnahyba S.c - PI", "parnahyba", "PI"},
		{"Serra F. C. - ES", "serra", "ES"},
		{"A.b.c. - RN", "abc", "RN"},
		{"C.r.b. - AL", "crb", "AL"},
		// Parentheticals that are not region codes are dropped.
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista", "RJ"},
		// Aliases collapse historical and colloquial spellings.
		{"Atletico Mineiro", "atletico", ""},
		{"Athletico Paranaense", "atletico", ""},
		{"Red Bull Bragantino", "bragantino", ""},
		{"Nautico Capibaribe", "nautico", ""},
	}
	for _, c := range cases {
		got := ParseTeamName(c.raw)
		if got.Base != c.wantBase {
			t.Errorf("ParseTeamName(%q).Base = %q, want %q", c.raw, got.Base, c.wantBase)
		}
		if got.Region != c.wantRegion {
			t.Errorf("ParseTeamName(%q).Region = %q, want %q", c.raw, got.Region, c.wantRegion)
		}
	}
}

func TestParseTeamNameDefaultRegions(t *testing.T) {
	// Bare club names that exist in several states resolve to the top-flight
	// club through the curated default, not through the state column.
	cases := map[string]string{
		"Flamengo":      "RJ",
		"Santos":        "SP",
		"Internacional": "RS",
		"Vitória":       "BA",
		"Guarani":       "SP",
		"Santa Cruz":    "PE",
		"Athletico":     "PR",
	}
	for raw, want := range cases {
		got := ParseTeamName(raw)
		if got.Region != "" {
			t.Errorf("ParseTeamName(%q).Region = %q, want it to come from the default", raw, got.Region)
		}
		if got.DefaultRegion != want {
			t.Errorf("ParseTeamName(%q).DefaultRegion = %q, want %q", raw, got.DefaultRegion, want)
		}
	}
}

func TestRawNameOverrides(t *testing.T) {
	// "Central SC" is Central Sport Club of Pernambuco, not a Santa Catarina
	// club; "River AC" is River Atlético Clube of Piauí.
	for raw, want := range map[string]struct{ base, region string }{
		"Central SC":     {"central", "PE"},
		"River AC":       {"river", "PI"},
		"Sao Jose - POA": {"saojose", "RS"},
	} {
		got := ParseTeamName(raw)
		if got.Base != want.base || got.Region != want.region {
			t.Errorf("ParseTeamName(%q) = (%q,%q), want (%q,%q)", raw, got.Base, got.Region, want.base, want.region)
		}
	}
}

func TestTeamIDComposition(t *testing.T) {
	if got := TeamID("flamengo", "RJ"); got != "flamengo-rj" {
		t.Errorf("TeamID = %q", got)
	}
	if got := TeamID("bocajuniors", ""); got != "bocajuniors" {
		t.Errorf("TeamID = %q", got)
	}
}
