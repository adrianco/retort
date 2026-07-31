package soccer

import (
	"errors"
	"testing"
)

// TestTeamNameVariations is the specification's "handles team name variations
// correctly" requirement: every spelling of a club in the six files must land
// on one canonical club.
func TestTeamNameVariations(t *testing.T) {
	s := testStore(t)
	groups := map[string][]string{
		"flamengo-rj":   {"Flamengo", "Flamengo-RJ", "flamengo", "FLAMENGO", "Clube de Regatas do Flamengo", "flamengo-rj"},
		"sao-paulo-sp":  {"São Paulo", "Sao Paulo", "sao paulo", "São Paulo FC", "Sao Paulo-SP", "SÃO PAULO"},
		"athletico-pr":  {"Athletico-PR", "Atletico-PR", "Atlético-PR", "Athletico Paranaense", "Atletico Paranaense", "Athletico"},
		"atletico-mg":   {"Atlético-MG", "Atletico-MG", "Atletico Mineiro", "Atlético Mineiro", "atletico-mg"},
		"gremio-rs":     {"Grêmio", "Gremio", "GREMIO", "Gremio-RS", "Grêmio - RS"},
		"vasco-rj":      {"Vasco", "Vasco da Gama", "Vasco Da Gama RJ", "Vasco da Gama-RJ"},
		"bragantino-sp": {"Bragantino", "Red Bull Bragantino", "RB Bragantino", "Red Bull Bragantino-SP"},
		"sport-pe":      {"Sport", "Sport Recife", "Sport Club do Recife", "Sport-PE"},
		"america-mg":    {"América-MG", "America MG", "América - MG", "América Mineiro"},
		"nautico-pe":    {"Náutico", "Nautico", "Nautico Capibaribe", "Náutico - PE"},
		"ceara-ce":      {"Ceará", "Ceara", "Ceará Sporting Club", "Ceara-CE"},
		"vitoria-ba":    {"Vitória", "Vitoria", "EC Vitoria", "Vitória - BA"},
	}
	for wantID, spellings := range groups {
		for _, spelling := range spellings {
			team, _, err := s.Teams.Lookup(spelling)
			if err != nil {
				t.Errorf("Lookup(%q): %v", spelling, err)
				continue
			}
			if team.ID != wantID {
				t.Errorf("Lookup(%q) = %s, want %s", spelling, team.ID, wantID)
			}
		}
	}
}

// TestDistinctClubsStayApart guards the other half of normalisation: clubs
// that share a name must not be merged.
func TestDistinctClubsStayApart(t *testing.T) {
	s := testStore(t)
	pairs := [][2]string{
		{"america-mg", "america-rn"},
		{"botafogo-rj", "botafogo-pb"},
		{"vila-nova-go", "villa-nova-mg"},
		{"guarani-sp", "guarani-par"},
		{"nacional-uru", "nacional-par"},
		{"river-plate-arg", "river-plate-uru"},
		{"atletico-mg", "atletico-go"},
		{"athletico-pr", "athletic-mg"},
	}
	for _, p := range pairs {
		a, b := s.Teams.Team(p[0]), s.Teams.Team(p[1])
		if a == nil {
			t.Errorf("club %s is missing from the registry", p[0])
			continue
		}
		if b == nil {
			t.Errorf("club %s is missing from the registry", p[1])
			continue
		}
		if a.ID == b.ID {
			t.Errorf("%s and %s were merged", p[0], p[1])
		}
		if a.Name == b.Name {
			t.Errorf("%s and %s share the display name %q", a.ID, b.ID, a.Name)
		}
	}
}

// A club named after a big club but from another state keeps its own identity:
// Flamengo-PI plays the Copa do Brasil and is not Flamengo of Rio.
func TestStateQualifierBeatsFamousName(t *testing.T) {
	s := testStore(t)
	rio := s.Teams.Team("flamengo-rj")
	if rio == nil {
		t.Fatal("flamengo-rj missing")
	}
	for _, alias := range rio.Aliases {
		n := NormalizeTeamName(alias)
		if n.IsState && n.Qualifier != "RJ" {
			t.Errorf("flamengo-rj absorbed %q, which is from %s", alias, n.Qualifier)
		}
	}
}

func TestLookupAmbiguity(t *testing.T) {
	s := testStore(t)
	if _, _, err := s.Teams.Lookup("América"); err == nil {
		t.Error(`Lookup("América") should be ambiguous between América-MG and América-RN`)
	} else {
		var amb *AmbiguousError
		if !errors.As(err, &amb) {
			t.Errorf("expected AmbiguousError, got %T: %v", err, err)
		} else if len(amb.Candidates) < 2 {
			t.Errorf("ambiguity should list the candidates, got %v", amb.Candidates)
		}
	}
}

func TestLookupNotFoundSuggests(t *testing.T) {
	s := testStore(t)
	_, _, err := s.Teams.Lookup("Flamengoo")
	if err != nil {
		var nf *NotFoundError
		if errors.As(err, &nf) && len(nf.Suggestions) == 0 {
			t.Error("a near miss should come back with suggestions")
		}
		return
	}
	// A near miss may also resolve outright, which is equally acceptable.
}

func TestLookupUnknownTeam(t *testing.T) {
	s := testStore(t)
	if team, _, err := s.Teams.Lookup("Manchester United"); err == nil {
		t.Errorf("Manchester United should not resolve, got %s", team.ID)
	}
}

func TestLinkClubIsStrict(t *testing.T) {
	s := testStore(t)
	// FIFA club names that must link to the match data.
	links := map[string]string{
		"Atlético Mineiro":          "atletico-mg",
		"Grêmio":                    "gremio-rs",
		"América FC (Minas Gerais)": "america-mg",
		"Ceará Sporting Club":       "ceara-ce",
		"Sport Club do Recife":      "sport-pe",
		"Atlético Paranaense":       "athletico-pr",
		"Botafogo":                  "botafogo-rj",
	}
	for club, want := range links {
		team := s.Teams.LinkClub(club)
		if team == nil {
			t.Errorf("LinkClub(%q) found nothing, want %s", club, want)
			continue
		}
		if team.ID != want {
			t.Errorf("LinkClub(%q) = %s, want %s", club, team.ID, want)
		}
	}
	// European clubs must not be attached to a same-named South American club.
	for _, club := range []string{"FC Barcelona", "Real Madrid", "Juventus", "Liverpool", "Sporting CP"} {
		if team := s.Teams.LinkClub(club); team != nil {
			t.Errorf("LinkClub(%q) wrongly linked to %s", club, team.ID)
		}
	}
}

func TestTeamsHaveStateAndAliases(t *testing.T) {
	s := testStore(t)
	for _, id := range []string{"flamengo-rj", "palmeiras-sp", "gremio-rs", "bahia-ba"} {
		team := s.Teams.Team(id)
		if team == nil {
			t.Fatalf("%s missing", id)
		}
		if team.State == "" {
			t.Errorf("%s has no state", id)
		}
		if len(team.Aliases) == 0 {
			t.Errorf("%s records no spellings", id)
		}
		if team.Matches == 0 {
			t.Errorf("%s has no matches", id)
		}
	}
}

func TestSuggestTeams(t *testing.T) {
	s := testStore(t)
	got := s.Teams.Suggest("Palmieras", 5)
	if len(got) == 0 {
		t.Fatal("no suggestions for a misspelt club")
	}
	found := false
	for _, name := range got {
		if name == "Palmeiras" {
			found = true
		}
	}
	if !found {
		t.Errorf("Suggest(\"Palmieras\") = %v, want it to include Palmeiras", got)
	}
}
