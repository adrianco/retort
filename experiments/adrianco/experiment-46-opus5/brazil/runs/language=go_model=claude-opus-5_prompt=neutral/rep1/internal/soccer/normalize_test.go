// normalize_test.go - BDD scenarios for the data quality rules in the spec:
// team name variations, multiple date formats and UTF-8 handling.
package soccer

import (
	"testing"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/bdd"
)

func TestFeatureTeamNameNormalization(t *testing.T) {
	bdd.Feature(t, "Team name normalization")

	bdd.Scenario(t, "state suffixes are separated from the club name", func(s *bdd.S) {
		cases := []struct {
			raw, base, region string
		}{
			{"Palmeiras-SP", "palmeiras", "SP"},
			{"Palmeiras - SP", "palmeiras", "SP"},
			{"Palmeiras", "palmeiras", ""},
			{"Ponte Preta-SP", "ponte preta", "SP"},
			{"Vasco da Gama-RJ", "vasco gama", "RJ"},
			{"Red Bull Bragantino-SP", "red bull bragantino", "SP"},
			{"Santos AP", "santos", "AP"},
		}
		var got []NameParts
		s.Given("raw team spellings from different source files", nil)
		s.When("each spelling is parsed", func() {
			for _, c := range cases {
				got = append(got, ParseTeamName(c.raw))
			}
		})
		s.Then("the base name and the state are separated", func() {
			for i, c := range cases {
				if got[i].Base != c.base || got[i].Region != c.region {
					s.Errorf("ParseTeamName(%q) = base %q region %q, want base %q region %q",
						c.raw, got[i].Base, got[i].Region, c.base, c.region)
				}
			}
		})
	})

	bdd.Scenario(t, "Portuguese accents and cedillas are folded for matching", func(s *bdd.S) {
		pairs := [][2]string{
			{"São Paulo", "Sao Paulo"},
			{"Grêmio", "Gremio"},
			{"Avaí - SC", "Avai-SC"},
			{"Atlético Mineiro", "Atletico Mineiro"},
			{"Criciúma", "Criciuma"},
			{"Náutico", "Nautico"},
			{"Goiás", "Goias"},
			{"Confiança", "Confianca"},
		}
		s.Given("accented and unaccented spellings of the same club", nil)
		s.Then("both reduce to the same base name", func() {
			for _, p := range pairs {
				a, b := ParseTeamName(p[0]), ParseTeamName(p[1])
				if a.Base != b.Base {
					s.Errorf("%q -> %q but %q -> %q", p[0], a.Base, p[1], b.Base)
				}
			}
		})
	})

	bdd.Scenario(t, "abbreviations, corporate suffixes and parentheses are removed", func(s *bdd.S) {
		cases := []struct{ raw, base string }{
			{"A.b.c. - RN", "abc"},
			{"C. R. B. - AL", "crb"},
			{"C.s.a. - AL", "csa"},
			{"Vitoria F. C. - ES", "vitoria"},
			{"Fortaleza Esporte Clube", "fortaleza"},
			{"Sport Club Corinthians Paulista", "sport corinthians paulista"},
			{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista sport"},
			{"XV de Piracicaba - SP", "xv piracicaba"},
			{"Clube Do Remo", "remo"},
			{"EC Bahia", "bahia"},
			{"AD Confianca", "confianca"},
		}
		s.Given("verbose legal club names", nil)
		s.Then("only the identifying words remain", func() {
			for _, c := range cases {
				if got := ParseTeamName(c.raw); got.Base != c.base {
					s.Errorf("ParseTeamName(%q).Base = %q, want %q", c.raw, got.Base, c.base)
				}
			}
		})
	})

	bdd.Scenario(t, "country markers on Libertadores clubs become regions", func(s *bdd.S) {
		cases := []struct{ raw, base, region string }{
			{"Nacional (URU)", "nacional", "URU"},
			{"Nacional-URU", "nacional", "URU"},
			{"Guaraní (PAR)", "guarani", "PAR"},
			{"Barcelona-EQU", "barcelona", "EQU"},
			{"Colo-Colo", "colo colo", ""},
			{"Boca Juniors", "boca juniors", ""},
		}
		s.Given("CONMEBOL club spellings", nil)
		s.Then("the country code is extracted without damaging hyphenated names", func() {
			for _, c := range cases {
				got := ParseTeamName(c.raw)
				if got.Base != c.base || got.Region != c.region {
					s.Errorf("ParseTeamName(%q) = %q/%q, want %q/%q", c.raw, got.Base, got.Region, c.base, c.region)
				}
			}
		})
	})
}

func TestFeatureDateParsing(t *testing.T) {
	bdd.Feature(t, "Date format handling")

	bdd.Scenario(t, "every date format used by the datasets parses", func(s *bdd.S) {
		cases := []struct {
			in      string
			want    time.Time
			hasTime bool
		}{
			{"2012-05-19 18:30:00", time.Date(2012, 5, 19, 18, 30, 0, 0, time.UTC), true},
			{"2023-09-24", time.Date(2023, 9, 24, 0, 0, 0, 0, time.UTC), false},
			{"29/03/2003", time.Date(2003, 3, 29, 0, 0, 0, 0, time.UTC), false},
			{"31/12/2019", time.Date(2019, 12, 31, 0, 0, 0, 0, time.UTC), false},
		}
		s.Given("ISO timestamps, ISO dates and Brazilian DD/MM/YYYY dates", nil)
		s.Then("each parses to the correct instant", func() {
			for _, c := range cases {
				got, ok, hasTime := parseDate(c.in)
				if !ok {
					s.Errorf("parseDate(%q) failed", c.in)
					continue
				}
				if !got.Equal(c.want) {
					s.Errorf("parseDate(%q) = %v, want %v", c.in, got, c.want)
				}
				if hasTime != c.hasTime {
					s.Errorf("parseDate(%q) hasTime = %v, want %v", c.in, hasTime, c.hasTime)
				}
			}
		})
	})

	bdd.Scenario(t, "missing values are rejected rather than defaulting to zero", func(s *bdd.S) {
		s.Given("the placeholder values that appear in the source files", nil)
		s.Then("dates and scores report that they are absent", func() {
			for _, v := range []string{"", "NA", "-", "   "} {
				if _, ok, _ := parseDate(v); ok {
					s.Errorf("parseDate(%q) unexpectedly succeeded", v)
				}
				if _, ok := parseInt(v); ok {
					s.Errorf("parseInt(%q) unexpectedly succeeded", v)
				}
			}
		})
		s.And("float-formatted goal counts still parse", func() {
			if v, ok := parseInt("3.0"); !ok || v != 3 {
				s.Errorf("parseInt(\"3.0\") = %d, %v; want 3, true", v, ok)
			}
		})
	})
}

func TestFeatureCompetitionParsing(t *testing.T) {
	bdd.Feature(t, "Competition name handling")

	bdd.Scenario(t, "users can name competitions in several ways", func(s *bdd.S) {
		cases := map[string]Competition{
			"Serie A":               SerieA,
			"serie a":               SerieA,
			"Brasileirão":           SerieA,
			"brasileirao":           SerieA,
			"campeonato brasileiro": SerieA,
			"Brasileirão Série A":   SerieA,
			"Serie B":               SerieB,
			"Copa do Brasil":        CopaDoBrasil,
			"brazilian cup":         CopaDoBrasil,
			"libertadores":          Libertadores,
			"Copa Libertadores":     Libertadores,
		}
		s.Given("competition names as a user would type them", nil)
		s.Then("each maps to the canonical competition", func() {
			for in, want := range cases {
				got, ok := ParseCompetition(in)
				if !ok || got != want {
					s.Errorf("ParseCompetition(%q) = %q, %v; want %q", in, got, ok, want)
				}
			}
		})
		s.And("an unknown competition is reported as unknown", func() {
			if _, ok := ParseCompetition("Premier League"); ok {
				s.Error("ParseCompetition(\"Premier League\") should not match")
			}
		})
	})
}
