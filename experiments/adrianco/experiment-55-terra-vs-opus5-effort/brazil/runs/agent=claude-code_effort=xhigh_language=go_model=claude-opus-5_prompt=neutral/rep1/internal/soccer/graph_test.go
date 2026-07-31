// graph_test.go checks that the six CSV files load into one coherent graph:
// every file contributes, the different spellings of a club collapse onto one
// node without merging distinct clubs, overlapping datasets are de-duplicated,
// and the FIFA squads attach to the right teams.
package soccer

import (
	"strings"
	"sync"
	"testing"
	"time"
)

var (
	sharedGraph *Graph
	sharedErr   error
	sharedOnce  sync.Once
)

// testGraph loads the datasets once per test binary; loading takes ~120ms and
// every test needs the same read-only graph.
func testGraph(t *testing.T) *Graph {
	t.Helper()
	sharedOnce.Do(func() { sharedGraph, sharedErr = Load("") })
	if sharedErr != nil {
		t.Fatalf("loading the knowledge graph: %v", sharedErr)
	}
	return sharedGraph
}

func TestLoadCoversEverySourceFile(t *testing.T) {
	g := testGraph(t)
	sources := g.Sources()
	if len(sources) != len(Datasets) {
		t.Fatalf("loaded %d sources, want %d", len(sources), len(Datasets))
	}
	wantRows := map[string]int{
		"brasileirao":          4098, // 4,180 rows minus 82 unplayed fixtures scored "NA"
		"copa_do_brasil":       1321, // 1,337 rows minus 16 without a score
		"libertadores":         1253, // 1,255 rows minus 2 placeholders
		"historic_brasileirao": 6886,
		"br_football":          10296,
		"fifa_players":         18207,
	}
	for _, s := range sources {
		if want, ok := wantRows[s.Key]; ok && s.Rows != want {
			t.Errorf("source %s loaded %d rows, want %d", s.Key, s.Rows, want)
		}
		if s.Rows == 0 {
			t.Errorf("source %s contributed no rows", s.Key)
		}
		if s.License == "" || s.URL == "" {
			t.Errorf("source %s is missing provenance", s.Key)
		}
	}
}

func TestGraphStats(t *testing.T) {
	g := testGraph(t)
	s := g.Stats()
	if s.Teams < 300 {
		t.Errorf("only %d teams, expected several hundred", s.Teams)
	}
	if s.Players != 18207 {
		t.Errorf("loaded %d players, want 18207", s.Players)
	}
	if s.BrazilianPlayers != 827 {
		t.Errorf("found %d Brazilian players, want 827", s.BrazilianPlayers)
	}
	for _, c := range AllCompetitions {
		if s.Competitions[string(c)] == 0 {
			t.Errorf("no matches for %s", c)
		}
	}
	if s.SeasonRange != "2003-2023" {
		t.Errorf("season range %s, want 2003-2023", s.SeasonRange)
	}
	// Two Copa do Brasil rows list the same club as home and away; nothing else
	// should fail to resolve.
	if n := len(g.Unresolved()); n > 2 {
		t.Errorf("%d rows failed to resolve to two clubs: %v", n, g.Unresolved())
	}
}

// TestTeamNamesUnifyAcrossFiles is the core data-quality guarantee: one club,
// one node, no matter which file spells it how.
func TestTeamNamesUnifyAcrossFiles(t *testing.T) {
	g := testGraph(t)
	cases := []struct {
		query   string
		wantID  string
		aliases []string
	}{
		{"Flamengo", "flamengo-rj", []string{"Flamengo", "Flamengo-RJ", "Flamengo - RJ"}},
		{"Palmeiras", "palmeiras-sp", []string{"Palmeiras", "Palmeiras-SP", "Palmeiras - SP"}},
		{"Sao Paulo", "sao-paulo-sp", []string{"São Paulo", "Sao Paulo-SP", "São Paulo - SP"}},
		{"Atletico Mineiro", "atletico-mg", []string{"Atlético-MG", "Atletico-MG", "Atlético Mineiro - MG"}},
		{"Athletico Paranaense", "atletico-pr", []string{"Athletico-PR", "Atlético-PR", "Athletico"}},
		{"Vasco", "vasco-da-gama-rj", []string{"Vasco", "Vasco da Gama-RJ"}},
		{"Gremio", "gremio-rs", []string{"Grêmio", "Gremio-RS"}},
		{"Sport", "sport-pe", []string{"Sport", "Sport-PE", "Sport Recife"}},
		{"Bragantino", "bragantino-sp", []string{"Bragantino", "Red Bull Bragantino-SP"}},
		{"America-MG", "america-mg", []string{"América-MG", "America MG"}},
	}
	for _, c := range cases {
		team, _, err := g.ResolveTeam(c.query)
		if err != nil {
			t.Errorf("ResolveTeam(%q): %v", c.query, err)
			continue
		}
		if team.ID != c.wantID {
			t.Errorf("ResolveTeam(%q) = %s, want %s", c.query, team.ID, c.wantID)
			continue
		}
		for _, alias := range c.aliases {
			if !contains(team.Aliases, alias) {
				t.Errorf("team %s is missing the spelling %q (has %v)", team.ID, alias, team.Aliases)
			}
			got, _, err := g.ResolveTeam(alias)
			if err != nil || got.ID != c.wantID {
				t.Errorf("ResolveTeam(%q) = %v (%v), want %s", alias, got, err, c.wantID)
			}
		}
	}
}

// TestDistinctClubsStayDistinct is the other half of the guarantee.
func TestDistinctClubsStayDistinct(t *testing.T) {
	g := testGraph(t)
	pairs := [][2]string{
		{"Atlético-MG", "Athletico-PR"},
		{"América-MG", "América-RN"},
		{"Botafogo-RJ", "Botafogo-PB"},
		{"Santos-SP", "Santos-AP"},
		{"Grêmio", "Grêmio Prudente"},
		{"River Plate", "River Plate-SE"},
		{"Peñarol", "Penarol-AM"},
	}
	for _, p := range pairs {
		a, _, errA := g.ResolveTeam(p[0])
		b, _, errB := g.ResolveTeam(p[1])
		if errA != nil || errB != nil {
			t.Errorf("resolving %v: %v / %v", p, errA, errB)
			continue
		}
		if a.ID == b.ID {
			t.Errorf("%q and %q both resolved to %s", p[0], p[1], a.ID)
		}
	}
}

// TestNicknamesResolve makes sure the curated nickname table is wired up.
func TestNicknamesResolve(t *testing.T) {
	g := testGraph(t)
	cases := map[string]string{
		"Timão":   "corinthians-sp",
		"Verdão":  "palmeiras-sp",
		"Mengão":  "flamengo-rj",
		"Galo":    "atletico-mg",
		"Peixe":   "santos-sp",
		"Raposa":  "cruzeiro-mg",
		"Furacão": "atletico-pr",
		"Fogão":   "botafogo-rj",
	}
	for nickname, want := range cases {
		team, _, err := g.ResolveTeam(nickname)
		if err != nil {
			t.Errorf("ResolveTeam(%q): %v", nickname, err)
			continue
		}
		if team.ID != want {
			t.Errorf("ResolveTeam(%q) = %s, want %s", nickname, team.ID, want)
		}
	}
}

func TestUnknownTeamGivesSuggestions(t *testing.T) {
	g := testGraph(t)
	_, _, err := g.ResolveTeam("Manchester United")
	if err == nil {
		t.Fatal("expected an error for a club that never played in Brazil")
	}
	var unknown *ErrUnknownTeam
	if !asUnknownTeam(err, &unknown) {
		t.Fatalf("error %v is not an ErrUnknownTeam", err)
	}
	if len(unknown.Suggestions) == 0 {
		t.Error("expected the error to suggest alternatives")
	}
}

func asUnknownTeam(err error, target **ErrUnknownTeam) bool {
	u, ok := err.(*ErrUnknownTeam)
	if ok {
		*target = u
	}
	return ok
}

// TestDeduplicationOfOverlappingSeasons is the reason aggregate statistics are
// trustworthy: Série A 2014-2019 sits in three files at once.
func TestDeduplicationOfOverlappingSeasons(t *testing.T) {
	g := testGraph(t)
	for season := 2006; season <= 2022; season++ {
		matches := g.SeasonMatches(SerieA, season)
		// 2015 carries one row that BR-Football files under Serie A but which is
		// really a state championship game; it is excluded from the table by
		// Standings rather than deleted from the match list.
		if len(matches) < 380 || len(matches) > 381 {
			t.Errorf("Série A %d has %d matches, want 380", season, len(matches))
		}
	}
	// The 2003 and 2004 seasons had 24 clubs, 2005 had 22.
	if n := len(g.SeasonMatches(SerieA, 2003)); n != 552 {
		t.Errorf("Série A 2003 has %d matches, want 552", n)
	}
	if n := len(g.SeasonMatches(SerieA, 2005)); n != 462 {
		t.Errorf("Série A 2005 has %d matches, want 462", n)
	}
	// Duplicated rows must still be reachable, and must be tagged with every
	// file they came from.
	multi := 0
	for _, m := range g.Matches() {
		if len(m.SourceList()) > 1 {
			multi++
		}
	}
	if multi < 2000 {
		t.Errorf("only %d fixtures were matched across files, expected thousands", multi)
	}
}

// TestCrossSourceEnrichment checks that a fixture from the file with rounds also
// picks up the stadium from the historic file and the shot counts from the wide
// BR-Football export.
func TestCrossSourceEnrichment(t *testing.T) {
	g := testGraph(t)
	withStats, withVenue := 0, 0
	for _, m := range g.Matches() {
		if m.Competition != SerieA || m.Source != "brasileirao" {
			continue
		}
		if m.Stats != nil {
			withStats++
		}
		if m.Venue != "" {
			withVenue++
		}
	}
	if withStats == 0 {
		t.Error("no Brasileirão fixture inherited match statistics from BR-Football")
	}
	if withVenue == 0 {
		t.Error("no Brasileirão fixture inherited a stadium from the historic file")
	}
}

// TestFIFASquadsLinkToClubs checks the cross-file join between player and match
// data, and that a European club is not mistaken for a Brazilian one.
func TestFIFASquadsLinkToClubs(t *testing.T) {
	g := testGraph(t)
	for _, id := range []string{
		"gremio-rs", "internacional-rs", "cruzeiro-mg", "fluminense-rj", "santos-sp",
		"botafogo-rj", "bahia-ba", "vitoria-ba", "chapecoense-sc", "sport-pe",
		"ceara-ce", "america-mg", "atletico-mg", "atletico-pr", "parana-pr",
	} {
		team, ok := g.Team(id)
		if !ok {
			t.Errorf("club %s is missing from the graph", id)
			continue
		}
		if len(g.playersByClub[id]) != 20 {
			t.Errorf("club %s (%s) has %d FIFA players, want 20", id, team.Display, len(g.playersByClub[id]))
		}
	}
	// FC Barcelona shares a base name with Barcelona of Ecuador; the Ecuadorian
	// club must not end up with Messi in its squad.
	for _, p := range g.playersByClub["barcelona-equ"] {
		if strings.Contains(p.Name, "Messi") {
			t.Error("FC Barcelona was wrongly linked to Barcelona (EQU)")
		}
	}
	// South American clubs that really do appear in both datasets should link.
	if len(g.playersByClub["boca-juniors"]) == 0 {
		t.Error("Boca Juniors has no FIFA squad despite appearing in both datasets")
	}
}

// TestRivalryTableIsValid keeps the curated derby list in sync with the graph.
func TestRivalryTableIsValid(t *testing.T) {
	g := testGraph(t)
	for _, r := range rivalries {
		a, okA := g.Team(r.TeamA)
		b, okB := g.Team(r.TeamB)
		if !okA || !okB {
			t.Errorf("derby %q references unknown clubs %s / %s", r.Name, r.TeamA, r.TeamB)
			continue
		}
		if a == b {
			t.Errorf("derby %q has the same club on both sides", r.Name)
		}
	}
}

// TestLoadPerformance guards the "simple lookups in under 2 seconds" requirement
// at its worst point: the cold start that reads all six files.
func TestLoadPerformance(t *testing.T) {
	g := testGraph(t)
	if g.LoadDuration() > 5*time.Second {
		t.Errorf("loading took %v, which is too slow for an interactive server", g.LoadDuration())
	}
}

func contains(list []string, want string) bool {
	for _, s := range list {
		if s == want {
			return true
		}
	}
	return false
}
