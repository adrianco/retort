package soccer

import "testing"

func TestNormalizeTeamGivesEverySpellingOfATeamTheSameKey(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP":                    "palmeiras",
		"Palmeiras - SP":                  "palmeiras",
		"Sociedade Esportiva Palmeiras":   "palmeiras",
		"São Paulo":                       "sao paulo",
		"Sao Paulo-SP":                    "sao paulo",
		"São Paulo FC":                    "sao paulo",
		"Sport Club Corinthians Paulista": "corinthians",
		"Athletico Paranaense - PR":       "athletico-pr",
		"Atletico-PR":                     "athletico-pr",
		"Athletico":                       "athletico-pr",
		"Atlético Mineiro - MG":           "atletico-mg",
		"Atletico-MG":                     "atletico-mg",
		"Atletico Goianiense":             "atletico-go",
		"Vasco da Gama-RJ":                "vasco",
		"Red Bull Bragantino-SP":          "bragantino",
		"América FC (Minas Gerais)":       "america-mg",
		"Ceara SC":                        "ceara",
		"Ceará Sporting Club":             "ceara",
		"Sport Club do Recife":            "sport",
		"Grêmio":                          "gremio",
		"C. R. B. - AL":                   "crb",
		"CRB":                             "crb",
		"AD Confianca":                    "confianca",
		"Confiança - SE":                  "confianca",
		"Nautico Capibaribe":              "nautico",
		"XV de Piracicaba - SP":           "xv piracicaba",
		"XV Piracicaba":                   "xv piracicaba",
		"Nacional (URU)":                  "nacional-uru",
		"Nacional-URU":                    "nacional-uru",
		"Guaraní (PAR)":                   "guarani-par",
		"O'Higgins":                       "ohiggins",
		"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ": "boavista",
	}
	for raw, want := range cases {
		if got := NormalizeTeam(raw).Key; got != want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", raw, got, want)
		}
	}
}

func TestNormalizeTeamKeepsApartClubsThatShareANameButNotAState(t *testing.T) {
	cases := map[string]string{
		"Botafogo PB":        "botafogo-pb",
		"Botafogo - RJ":      "botafogo-rj",
		"Santos - AP":        "santos-ap",
		"Vitoria F. C. - ES": "vitoria-es",
		"Vitória - BA":       "vitoria",
		"América - RN":       "america-rn",
		"Bragantino - PA":    "bragantino-pa",
		"Santos Laguna":      "santos laguna",
	}
	for raw, want := range cases {
		if got := NormalizeTeam(raw).Key; got != want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", raw, got, want)
		}
	}
}

func TestResolveCompetitionUnderstandsCommonNames(t *testing.T) {
	cases := map[string]Competition{
		"Brasileirão": SerieA, "Serie A": SerieA, "brasileirao serie a": SerieA, "Série B": SerieB,
		"Copa do Brasil": CopaDoBrasil, "Libertadores": Libertadores, "Copa Libertadores": Libertadores,
	}
	for name, want := range cases {
		if got, ok := ResolveCompetition(name); !ok || got != want {
			t.Errorf("ResolveCompetition(%q) = %q, want %q", name, got, want)
		}
	}
}

func TestParseDateUnderstandsEveryFormatInTheData(t *testing.T) {
	for _, s := range []string{"2023-09-24", "29/03/2003", "2012-05-19 18:30:00"} {
		if _, ok := ParseDate(s); !ok {
			t.Errorf("could not parse %q", s)
		}
	}
}
