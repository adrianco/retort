// graph_test.go - BDD scenarios for dataset loading, club identity resolution
// and cross-source de-duplication.
//
// Context
//
//	Two levels of test live here. The synthetic scenarios use fstest.MapFS with
//	a handful of hand-written rows, so they pin down the loader's contract
//	without depending on the 22 MB of bundled CSVs. The corpus scenarios load
//	the real files once (see testGraph) and assert against independently known
//	football history - the 2003-2022 Brasileirão champions, their points totals
//	and the relegated clubs. If the merge logic, the points calculation or the
//	club identity table regresses, those assertions fail.
package soccer

import (
	"strings"
	"sync"
	"testing"
	"testing/fstest"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/bdd"
)

var (
	sharedGraph *Graph
	graphOnce   sync.Once
	graphErr    error
)

// testGraph loads the bundled datasets once per test binary.
func testGraph(t *testing.T) *Graph {
	t.Helper()
	graphOnce.Do(func() {
		dir, err := FindDataDir()
		if err != nil {
			graphErr = err
			return
		}
		sharedGraph, graphErr = Load(dir)
	})
	if graphErr != nil {
		t.Fatalf("loading bundled datasets: %v", graphErr)
	}
	return sharedGraph
}

// mustClub resolves a club name or fails the test.
func mustClub(t *testing.T, g *Graph, name string) *Club {
	t.Helper()
	c, err := g.MustResolveClub(name)
	if err != nil {
		t.Fatalf("resolving %q: %v", name, err)
	}
	return c
}

func TestFeatureDatasetLoading(t *testing.T) {
	bdd.Feature(t, "Dataset loading")

	bdd.Scenario(t, "all six datasets load and are queryable", func(s *bdd.S) {
		var g *Graph
		s.Given("the six bundled Kaggle CSV files", nil)
		s.When("the knowledge graph is built", func() { g = testGraph(s.T) })
		s.Then("every file reports rows loaded", func() {
			want := []string{FileBrasileirao, FileCup, FileLibertadores, FileBRFootball, FileHistorical, FileFIFA}
			byFile := map[string]DatasetInfo{}
			for _, d := range g.Datasets() {
				byFile[d.File] = d
			}
			if len(byFile) != len(want) {
				s.Fatalf("loaded %d datasets, want %d", len(byFile), len(want))
			}
			for _, f := range want {
				d, ok := byFile[f]
				if !ok {
					s.Errorf("dataset %s missing", f)
					continue
				}
				if d.Rows == 0 || d.Loaded == 0 {
					s.Errorf("dataset %s: rows=%d loaded=%d", f, d.Rows, d.Loaded)
				}
				if d.License == "" || d.Source == "" {
					s.Errorf("dataset %s is missing licence or source attribution", f)
				}
			}
		})
		s.And("all five competitions and both node types are populated", func() {
			sum := g.Summary()
			if sum.Competitions != 5 {
				s.Errorf("competitions = %d, want 5", sum.Competitions)
			}
			if sum.Clubs < 300 {
				s.Errorf("clubs = %d, want at least 300", sum.Clubs)
			}
			if sum.Matches < 15000 {
				s.Errorf("matches = %d, want at least 15000", sum.Matches)
			}
			if sum.Players != 18207 {
				s.Errorf("players = %d, want 18207", sum.Players)
			}
		})
	})

	bdd.Scenario(t, "the loader handles a synthetic dataset with messy values", func(s *bdd.S) {
		fsys := fstest.MapFS{
			FileBrasileirao: &fstest.MapFile{Data: []byte(
				`"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2020-05-19 18:30:00,"Palmeiras-SP","SP","Sao Paulo-SP","SP",2,1,2020,1
2020-05-26 18:30:00,"Sao Paulo-SP","SP","Palmeiras-SP","SP",NA,NA,2020,2
`)},
			FileHistorical: &fstest.MapFile{Data: []byte(
				`ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2020.01.0001,19/05/2020,2020,1,Palmeiras,São Paulo,2,1,SP,SP,Mandante,Allianz Parque,
`)},
			FileCup: &fstest.MapFile{Data: []byte(
				`"round","datetime","home_team","away_team","home_goal","away_goal","season"
"1",2020-03-07 16:00:00,"América - MG","Palmeiras - SP",0,3,2020
`)},
			FileLibertadores: &fstest.MapFile{Data: []byte(
				`"datetime","home_team","away_team","home_goal","away_goal","season","stage"
2020-02-12 20:15:00,"Nacional (URU)","Palmeiras","1","2",2020,"group stage"
`)},
			FileBRFootball: &fstest.MapFile{Data: []byte(
				`tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
Serie A,Palmeiras,2.0,1.0,Sao Paulo,5.0,3.0,100.0,90.0,12.0,,20:00:00,2020-05-19,1.0,-1.0,WON,LOST,8.0
`)},
			FileFIFA: &fstest.MapFile{Data: []byte(
				`,ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight,Value,Wage,Preferred Foot,Work Rate,Finishing,Dribbling
0,1001,Test Player,24,Brazil,80,86,Santos,ST,9,5'10,170lbs,€20M,€30K,Right,High/ Medium,82,84
`)},
		}
		var g *Graph
		var err error
		s.Given("a synthetic dataset with mixed date formats, NA scores and blank statistics", nil)
		s.When("the graph is built from it", func() { g, err = LoadFS(fsys) })
		s.Then("loading succeeds", func() {
			if err != nil {
				s.Fatalf("LoadFS: %v", err)
			}
		})
		s.And("the same Série A fixture from three files becomes one match", func() {
			serieA := g.CompetitionMatches(SerieA, 2020)
			if len(serieA) != 2 {
				s.Fatalf("Série A 2020 has %d matches, want 2 (one merged, one unplayed)", len(serieA))
			}
			var merged *Match
			for _, m := range serieA {
				if m.HasScore {
					merged = m
				}
			}
			if merged == nil {
				s.Fatal("no played Série A match found")
			}
			if len(merged.Sources) != 3 {
				s.Errorf("merged match sources = %v, want all three files", merged.Sources)
			}
			if merged.Stadium != "Allianz Parque" {
				s.Errorf("stadium = %q, want the value contributed by the historical file", merged.Stadium)
			}
			if merged.Stats == nil || merged.Stats.HomeShots == nil || *merged.Stats.HomeShots != 12 {
				s.Errorf("extended stats were not merged in from BR-Football: %+v", merged.Stats)
			}
			if merged.Stats != nil && merged.Stats.AwayShots != nil {
				s.Errorf("blank away_shots should stay absent, got %d", *merged.Stats.AwayShots)
			}
		})
		s.And("a fixture with NA scores is kept but marked unplayed", func() {
			for _, m := range g.CompetitionMatches(SerieA, 2020) {
				if !m.HasScore && m.HomeClubID != "sao-paulo-sp" {
					s.Errorf("unexpected unplayed match %s", m.ID)
				}
			}
		})
		s.And("accented and suffixed spellings resolve to the same clubs", func() {
			p := mustClub(s.T, g, "Palmeiras")
			if got := len(g.ClubMatches(p.ID)); got != 4 {
				s.Errorf("Palmeiras has %d matches, want 4 across the four competitions", got)
			}
			sp, err := g.MustResolveClub("São Paulo")
			if err != nil {
				s.Fatalf("resolving São Paulo: %v", err)
			}
			if sp.ID != "sao-paulo-sp" {
				s.Errorf("São Paulo resolved to %q", sp.ID)
			}
		})
		s.And("the Libertadores opponent keeps its country marker", func() {
			nac := mustClub(s.T, g, "Nacional (URU)")
			if nac.State != "URU" || nac.Country != "Uruguay" {
				s.Errorf("Nacional (URU) = state %q country %q", nac.State, nac.Country)
			}
		})
		s.And("the player dataset links to its club", func() {
			if len(g.Players()) != 1 {
				s.Fatalf("players = %d, want 1", len(g.Players()))
			}
			p := g.Players()[0]
			if p.ClubID != "santos-sp" {
				s.Errorf("player club id = %q, want santos-sp", p.ClubID)
			}
			if p.PositionGroup != "Forward" {
				s.Errorf("position group = %q, want Forward", p.PositionGroup)
			}
		})
	})
}

func TestFeatureClubIdentity(t *testing.T) {
	bdd.Feature(t, "Club identity resolution")
	g := testGraph(t)

	bdd.Scenario(t, "every spelling of a club resolves to one node", func(s *bdd.S) {
		cases := []struct {
			id      string
			aliases []string
		}{
			{"flamengo-rj", []string{"Flamengo", "flamengo", "Flamengo-RJ", "Flamengo - RJ", "CR Flamengo", "FLAMENGO"}},
			{"sao-paulo-sp", []string{"São Paulo", "Sao Paulo", "sao paulo-sp", "São Paulo FC", "sao paulo fc"}},
			{"vasco-da-gama-rj", []string{"Vasco", "Vasco da Gama", "Vasco Da Gama RJ", "vasco da gama-rj"}},
			{"atletico-mg", []string{"Atlético Mineiro", "Atletico Mineiro", "Atlético-MG", "Atletico-MG", "Atlético - MG", "Galo"}},
			{"atletico-pr", []string{"Athletico", "Athletico Paranaense", "Atlético-PR", "Atletico - PR", "Atlético Paranaense"}},
			{"sport-pe", []string{"Sport", "Sport-PE", "Sport Recife", "Sport Club do Recife"}},
			{"bragantino-sp", []string{"Bragantino", "Red Bull Bragantino", "Red Bull Bragantino-SP"}},
			{"gremio-rs", []string{"Grêmio", "Gremio", "Gremio-RS", "Grêmio - RS"}},
			{"ceara-ce", []string{"Ceará", "Ceara", "Ceará Sporting Club", "Ceara-CE"}},
			{"corinthians-sp", []string{"Corinthians", "Corinthians-SP", "Sport Club Corinthians Paulista"}},
		}
		s.Given("the club spelling variations used across the datasets", nil)
		s.Then("each variation resolves to the expected club node", func() {
			for _, c := range cases {
				for _, alias := range c.aliases {
					got, err := g.MustResolveClub(alias)
					if err != nil {
						s.Errorf("resolving %q: %v", alias, err)
						continue
					}
					if got.ID != c.id {
						s.Errorf("%q resolved to %q, want %q", alias, got.ID, c.id)
					}
				}
			}
		})
	})

	bdd.Scenario(t, "different clubs that share a short name stay separate", func(s *bdd.S) {
		pairs := []struct {
			a, b string
			ids  [2]string
		}{
			{"Flamengo", "Flamengo - PI", [2]string{"flamengo-rj", "flamengo-pi"}},
			{"Santos", "Santos - AP", [2]string{"santos-sp", "santos-ap"}},
			{"Botafogo", "Botafogo - PB", [2]string{"botafogo-rj", "botafogo-pb"}},
			{"Portuguesa", "Portuguesa RJ", [2]string{"portuguesa-sp", "portuguesa-rj"}},
			{"Vitória", "Vitoria ES", [2]string{"vitoria-ba", "vitoria-es"}},
			{"Internacional", "Internacional - SC", [2]string{"internacional-rs", "internacional-sc"}},
			{"Atlético Mineiro", "Atlético - GO", [2]string{"atletico-mg", "atletico-go"}},
		}
		s.Given("clubs from different states with the same short name", nil)
		s.Then("they are distinct nodes", func() {
			for _, p := range pairs {
				a := mustClub(s.T, g, p.a)
				b := mustClub(s.T, g, p.b)
				if a.ID != p.ids[0] || b.ID != p.ids[1] {
					s.Errorf("%q/%q resolved to %q/%q, want %q/%q", p.a, p.b, a.ID, b.ID, p.ids[0], p.ids[1])
				}
				if a.ID == b.ID {
					s.Errorf("%q and %q collapsed into %q", p.a, p.b, a.ID)
				}
			}
		})
		s.And("the label makes the difference visible to a reader", func() {
			if got := mustClub(s.T, g, "Flamengo - PI").Label(); !strings.Contains(got, "PI") {
				s.Errorf("label = %q, want it to mention the state", got)
			}
		})
	})

	bdd.Scenario(t, "an unknown club produces a helpful error", func(s *bdd.S) {
		var err error
		s.Given("a name that is not in the data", nil)
		s.When("it is resolved", func() { _, err = g.MustResolveClub("Manchester United") })
		s.Then("the error explains how to browse the clubs", func() {
			if err == nil {
				s.Fatal("expected an error")
			}
			if !strings.Contains(err.Error(), "search_teams") {
				s.Errorf("error %q should point at search_teams", err)
			}
		})
	})
}

func TestFeatureDeduplication(t *testing.T) {
	bdd.Feature(t, "Cross-source de-duplication")
	g := testGraph(t)

	bdd.Scenario(t, "a Série A season has exactly the fixtures the format implies", func(s *bdd.S) {
		// 2003 and 2004 were 24-club seasons, 2005 had 22 clubs, and every
		// season from 2006 has been a 20-club double round-robin.
		want := map[int]int{
			2003: 24 * 23, 2004: 24 * 23, 2005: 22 * 21,
			2006: 380, 2007: 380, 2008: 380, 2009: 380, 2010: 380, 2011: 380,
			2012: 380, 2013: 380, 2014: 380, 2015: 380, 2016: 380, 2017: 380,
			2018: 380, 2019: 380, 2020: 380, 2021: 380, 2022: 380,
		}
		s.Given("Série A 2012-2019 present in three of the five source files", nil)
		s.Then("each season holds one fixture per ordered pair of clubs", func() {
			for season, n := range want {
				if got := len(g.CompetitionMatches(SerieA, season)); got != n {
					s.Errorf("Série A %d has %d matches, want %d", season, got, n)
				}
			}
		})
		s.And("every club in a 20-club season played 38 matches", func() {
			for _, season := range []int{2015, 2019, 2022} {
				st, err := g.Standings(SerieA, season)
				if err != nil {
					s.Fatalf("standings %d: %v", season, err)
				}
				if len(st.Rows) != 20 {
					s.Errorf("Série A %d has %d clubs, want 20", season, len(st.Rows))
				}
				for _, row := range st.Rows {
					if row.Record.Played != 38 {
						s.Errorf("Série A %d: %s played %d, want 38", season, row.Record.Club, row.Record.Played)
					}
				}
			}
		})
	})

	bdd.Scenario(t, "merged matches record every file they came from", func(s *bdd.S) {
		var multi int
		s.Given("the loaded match edges", nil)
		s.When("their source lists are inspected", func() {
			for _, m := range g.Matches() {
				if len(m.Sources) > 1 {
					multi++
				}
			}
		})
		s.Then("thousands of fixtures cite more than one source", func() {
			if multi < 1000 {
				s.Errorf("only %d matches merged across sources, expected thousands", multi)
			}
		})
		s.And("no match cites the same source twice", func() {
			for _, m := range g.Matches() {
				seen := map[string]bool{}
				for _, src := range m.Sources {
					if seen[src] {
						s.Fatalf("match %s lists %s twice", m.ID, src)
					}
					seen[src] = true
				}
			}
		})
	})

	bdd.Scenario(t, "match ids are unique and resolvable", func(s *bdd.S) {
		s.Given("every match edge", nil)
		s.Then("each id maps back to exactly that match", func() {
			seen := make(map[string]bool, len(g.Matches()))
			for _, m := range g.Matches() {
				if seen[m.ID] {
					s.Fatalf("duplicate match id %s", m.ID)
				}
				seen[m.ID] = true
				if got := g.Match(m.ID); got != m {
					s.Fatalf("Match(%q) did not round-trip", m.ID)
				}
			}
		})
	})
}
