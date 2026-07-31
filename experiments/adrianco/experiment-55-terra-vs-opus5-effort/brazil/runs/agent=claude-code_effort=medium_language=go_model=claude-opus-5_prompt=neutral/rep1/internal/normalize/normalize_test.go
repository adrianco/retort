package normalize

import "testing"

// TestResolveCollapsesSpellings covers the "team name variations" requirement:
// every spelling of a club that appears anywhere in the datasets must land on
// the same canonical ID.
func TestResolveCollapsesSpellings(t *testing.T) {
	groups := []struct {
		want     string
		spelling []string
	}{
		{"flamengo", []string{"Flamengo", "Flamengo-RJ", "Flamengo - RJ", "CR Flamengo",
			"Clube de Regatas do Flamengo", `"Flamengo-RJ"`}},
		{"gremio", []string{"Grêmio", "Gremio", "Gremio RS", "Grêmio - RS", "Gremio-RS"}},
		{"sao-paulo", []string{"São Paulo", "Sao Paulo", "Sao Paulo-SP", "São Paulo - SP"}},
		{"sport-recife", []string{"Sport", "Sport - PE", "Sport Recife", "Sport Club do Recife"}},
		{"vasco-da-gama", []string{"Vasco", "Vasco da Gama", "Vasco Da Gama RJ", "Vasco da Gama - RJ"}},
		{"athletico-paranaense", []string{"Athletico", "Atletico-PR", "Atlético - PR",
			"Athletico Paranaense", "Atletico Paranaense"}},
		{"atletico-mineiro", []string{"Atlético-MG", "Atletico-MG", "Atlético Mineiro",
			"Atletico Mineiro", "Atlético - MG"}},
		{"america-mineiro", []string{"América-MG", "America MG", "América FC (Minas Gerais)",
			"América - MG", "America - MG"}},
		{"ceara", []string{"Ceará", "Ceara", "Ceará - CE", "Ceará Sporting Club"}},
		{"corinthians", []string{"Corinthians", "Corinthians - SP", "Corinthians-SP",
			"Sport Corinthians Paulista"}},
		{"nautico", []string{"Náutico", "Nautico Capibaribe", "Náutico - PE"}},
		{"csa", []string{"CSA", "Csa - AL", "C.s.a. - AL", "CS Alagoano"}},
		{"abc", []string{"ABC", "Abc - RN", "A.b.c. - RN"}},
		{"red-bull-bragantino", []string{"Bragantino", "Bragantino - SP", "Red Bull Bragantino",
			"Red Bull Bragantino-SP"}},
		{"volta-redonda", []string{"Volta Redonda", "Volta Redonda - RJ"}},
		{"nacional-uru", []string{"Nacional (URU)", "Nacional-URU"}},
		{"barcelona-equ", []string{"Barcelona-EQU"}},
	}
	for _, g := range groups {
		for _, s := range g.spelling {
			if got := Resolve(s).ID; got != g.want {
				t.Errorf("Resolve(%q).ID = %q, want %q", s, got, g.want)
			}
		}
	}
}

// TestResolveKeepsDistinctClubsApart guards the opposite failure: over-eager
// normalisation must not merge different clubs that share a base name.
func TestResolveKeepsDistinctClubsApart(t *testing.T) {
	pairs := [][2]string{
		{"Atlético-MG", "Atlético-PR"},
		{"Atlético-MG", "Atlético - GO"},
		{"Flamengo - RJ", "Flamengo - PI"},
		{"Botafogo - RJ", "Botafogo - PB"},
		{"América - MG", "América - RN"},
		{"Internacional - RS", "Internacional - SC"},
		{"Santos - SP", "Santos - AP"},
		{"Guarani - SP", "Guarani - CE"},
		{"Red Bull Bragantino", "Red Bull Brasil"},
		{"Bragantino - SP", "Bragantino - PA"},
		{"Fluminense - RJ", "Fluminense de Feira - BA"},
		{"Grêmio - RS", "Grêmio Barueri - SP"},
		{"River Plate", "River Plate-URU"},
	}
	for _, p := range pairs {
		a, b := Resolve(p[0]), Resolve(p[1])
		if a.ID == b.ID {
			t.Errorf("Resolve(%q) and Resolve(%q) both give %q; they are different clubs",
				p[0], p[1], a.ID)
		}
	}
}

func TestSplitState(t *testing.T) {
	cases := []struct{ in, name, state string }{
		{"Palmeiras-SP", "Palmeiras", "SP"},
		{"América - MG", "América", "MG"},
		{"Nacional (URU)", "Nacional", "URU"},
		{"América FC (Minas Gerais)", "América FC", "MG"},
		{"Colo-Colo", "Colo-Colo", ""},           // hyphen is part of the name
		{"Sao Jose - POA", "Sao Jose - POA", ""}, // POA is not a state code
		{"Boca Juniors", "Boca Juniors", ""},
		{"Rio Branco - Vn - ES", "Rio Branco - Vn", "ES"},
	}
	for _, c := range cases {
		name, state := splitState(c.in)
		if name != c.name || state != c.state {
			t.Errorf("splitState(%q) = (%q, %q), want (%q, %q)", c.in, name, state, c.name, c.state)
		}
	}
}

func TestDeaccentHandlesPortuguese(t *testing.T) {
	cases := map[string]string{
		"São Paulo": "sao paulo",
		"Grêmio":    "gremio",
		"Avaí":      "avai",
		"Confiança": "confianca",
		"Goiás":     "goias",
		"Náutico":   "nautico",
		"Peñarol":   "penarol",
	}
	for in, want := range cases {
		if got := Deaccent(in); got != want {
			t.Errorf("Deaccent(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestResolveBlank(t *testing.T) {
	for _, s := range []string{"", "   ", `""`, "-", "  -  "} {
		if got := Resolve(s); got.ID != "" {
			t.Errorf("Resolve(%q) = %+v, want zero Team", s, got)
		}
	}
}

func TestStateName(t *testing.T) {
	if got := StateName("SP"); got != "São Paulo" {
		t.Errorf("StateName(SP) = %q", got)
	}
	if got := StateName("ZZ"); got != "ZZ" {
		t.Errorf("StateName(ZZ) = %q, want passthrough", got)
	}
}
