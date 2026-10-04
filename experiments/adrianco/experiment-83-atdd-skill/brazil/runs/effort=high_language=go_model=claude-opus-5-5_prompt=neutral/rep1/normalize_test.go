// normalize_test.go — unit tests for accent folding and team-name handling.
package main

import "testing"

func TestFold(t *testing.T) {
	cases := map[string]string{
		"São Paulo":                "sao paulo",
		"Grêmio":                   "gremio",
		"Avaí":                     "avai",
		"Fortaleza Esporte Clube":  "fortaleza esporte clube",
		"Confiança":                "confianca",
		"C.R.B.":                   "crb",
		"  Atlético-MG ":           "atletico mg",
		"O'Higgins":                "ohiggins",
		"Boavista Sport Club (RJ)": "boavista sport club rj",
	}
	for in, want := range cases {
		if got := Fold(in); got != want {
			t.Errorf("Fold(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestSplitTeamName(t *testing.T) {
	cases := []struct{ in, base, qual string }{
		{"Palmeiras-SP", "palmeiras", "SP"},
		{"Palmeiras - SP", "palmeiras", "SP"},
		{"Palmeiras", "palmeiras", ""},
		{"Botafogo PB", "botafogo", "PB"},
		{"Nacional (URU)", "nacional", "URU"},
		{"Nacional-URU", "nacional", "URU"},
		{"Barcelona-EQU", "barcelona", "EQU"},
		{"EC Bahia", "bahia", ""},
		{"Nova Mutum EC", "nova mutum", ""},
		{"Operario FC MS", "operario", "MS"},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista sport club", "RJ"},
		{"Vitoria F. C. - ES", "vitoria", "ES"},
		{"River AC", "river", "PI"}, // explicit alias: River Atlético Clube of Piauí
		{"Colo-Colo", "colo colo", ""},
	}
	for _, c := range cases {
		b, q := SplitTeamName(c.in)
		if b != c.base || q != c.qual {
			t.Errorf("SplitTeamName(%q) = (%q,%q), want (%q,%q)", c.in, b, q, c.base, c.qual)
		}
	}
}

func TestRegistryMergesVariants(t *testing.T) {
	r := NewTeamRegistry()
	raws := []struct{ raw, hint string }{
		{"Palmeiras-SP", "SP"}, {"Palmeiras - SP", ""}, {"Palmeiras", ""},
		{"Atletico-MG", "MG"}, {"Atlético Mineiro", ""}, {"Atlético - MG", ""},
		{"Athletico-PR", "PR"}, {"Atletico Paranaense", ""}, {"Athletico", ""}, {"Atlético Paranaense - PR", ""},
		{"Botafogo-RJ", "RJ"}, {"Botafogo", ""}, {"Botafogo PB", ""},
		{"Vitória", "ES"}, // wrong state column in the historical file
		{"Vitoria", ""},
		{"Ponte Preta", ""}, {"Ponte Preta-SP", "SP"},
		{"Mirassol", ""}, {"Mirassol - SP", ""},
		{"Libertad", ""}, {"Libertad-PAR", ""},
		{"River Plate", ""}, {"River Plate-URU", ""},
	}
	for _, x := range raws {
		r.Register(x.raw, x.hint)
	}
	r.Finalize()
	same := func(a, ah, b, bh string) {
		t.Helper()
		ta, tb := r.Lookup(a, ah), r.Lookup(b, bh)
		if ta == nil || tb == nil || ta != tb {
			t.Errorf("%q and %q should be the same team (%v, %v)", a, b, ta, tb)
		}
	}
	differ := func(a, ah, b, bh string) {
		t.Helper()
		if r.Lookup(a, ah) == r.Lookup(b, bh) {
			t.Errorf("%q and %q should be different teams", a, b)
		}
	}
	same("Palmeiras-SP", "SP", "Palmeiras", "")
	same("Palmeiras - SP", "", "Palmeiras", "")
	same("Atletico-MG", "MG", "Atlético Mineiro", "")
	same("Athletico-PR", "PR", "Atletico Paranaense", "")
	same("Athletico", "", "Atlético Paranaense - PR", "")
	differ("Atletico-MG", "MG", "Athletico-PR", "PR")
	same("Botafogo-RJ", "RJ", "Botafogo", "")
	differ("Botafogo", "", "Botafogo PB", "")
	same("Vitória", "ES", "Vitoria", "")
	same("Ponte Preta", "", "Ponte Preta-SP", "SP")
	same("Mirassol", "", "Mirassol - SP", "")
	same("Libertad", "", "Libertad-PAR", "")
	differ("River Plate", "", "River Plate-URU", "")

	if got := r.Lookup("Palmeiras", "").Name; got != "Palmeiras" {
		t.Errorf("display name = %q", got)
	}
	if got := r.Lookup("Atletico-MG", "MG").Name; got != "Atlético-MG" {
		t.Errorf("display name = %q", got)
	}
}

func TestResolveUserQueries(t *testing.T) {
	s := testStore(t)
	cases := map[string]string{
		"Flamengo":                        "flamengo|RJ",
		"flamengo-rj":                     "flamengo|RJ",
		"Sao Paulo":                       "sao paulo|SP",
		"São Paulo FC":                    "sao paulo|SP",
		"Sport Club Corinthians Paulista": "corinthians|SP",
		"Atlético Mineiro":                "atletico|MG",
		"Athletico Paranaense":            "athletico|PR",
		"Gremio":                          "gremio|RS",
		"Grêmio":                          "gremio|RS",
		"Vasco":                           "vasco|RJ",
		"Vasco da Gama":                   "vasco|RJ",
		"Red Bull Bragantino":             "bragantino|SP",
		"Avaí":                            "avai|SC",
		"Ceará":                           "ceara|CE",
		"Nacional (URU)":                  "nacional|URU",
		"Boca":                            "boca juniors|",
		"Botafogo-PB":                     "botafogo|PB",
	}
	for q, want := range cases {
		got, _ := s.ResolveTeam(q)
		if got == nil || got.Key != want {
			t.Errorf("ResolveTeam(%q) = %v, want %s", q, got, want)
		}
	}
	if got, _ := s.ResolveTeam("Xyzzy United"); got != nil {
		t.Errorf("nonsense query resolved to %s", got.Key)
	}
}
