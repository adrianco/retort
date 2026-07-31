package soccer

import (
	"fmt"
	"os"
	"strings"
	"sync"
	"testing"
	"time"
)

// ---------------------------------------------------------------------------
// A tiny Given/When/Then harness.
//
// The specification asks for Gherkin-style scenarios. Rather than pull in a
// Cucumber runner, each scenario is a Go subtest whose steps are recorded and
// printed on failure, so a failing scenario reads like the feature file it was
// written from.
// ---------------------------------------------------------------------------

type scenario struct {
	t     *testing.T
	steps []string
	g     *Graph
}

func feature(t *testing.T, name string, fn func(*scenario)) {
	t.Helper()
	t.Run(name, func(t *testing.T) {
		s := &scenario{t: t, g: testGraph(t)}
		defer func() {
			if t.Failed() {
				t.Logf("Scenario: %s\n  %s", name, strings.Join(s.steps, "\n  "))
			}
		}()
		fn(s)
	})
}

func (s *scenario) step(kind, format string, args ...any) {
	s.steps = append(s.steps, kind+" "+fmt.Sprintf(format, args...))
}

func (s *scenario) Given(format string, args ...any) { s.step("Given", format, args...) }
func (s *scenario) When(format string, args ...any)  { s.step("When", format, args...) }
func (s *scenario) Then(format string, args ...any)  { s.step("Then", format, args...) }
func (s *scenario) And(format string, args ...any)   { s.step("And", format, args...) }

func (s *scenario) must(err error) {
	s.t.Helper()
	if err != nil {
		s.t.Fatalf("step failed: %v\n  %s", err, strings.Join(s.steps, "\n  "))
	}
}

func (s *scenario) assert(cond bool, format string, args ...any) {
	s.t.Helper()
	if !cond {
		s.t.Errorf(format+"\n  %s", append(args, strings.Join(s.steps, "\n  "))...)
	}
}

// require aborts the scenario when a later step would panic without it.
func (s *scenario) require(cond bool, format string, args ...any) {
	s.t.Helper()
	if !cond {
		s.t.Fatalf(format+"\n  %s", append(args, strings.Join(s.steps, "\n  "))...)
	}
}

func (s *scenario) equal(got, want any, what string) {
	s.t.Helper()
	if got != want {
		s.t.Errorf("%s = %v, want %v\n  %s", what, got, want, strings.Join(s.steps, "\n  "))
	}
}

// testGraph loads the real datasets once and shares them across every test.
var (
	graphOnce sync.Once
	sharedG   *Graph
	graphErr  error
)

const testDataDir = "../../data/kaggle"

func testGraph(t *testing.T) *Graph {
	t.Helper()
	graphOnce.Do(func() {
		if _, err := os.Stat(testDataDir); err != nil {
			graphErr = err
			return
		}
		sharedG, graphErr = Load(testDataDir)
	})
	if graphErr != nil {
		t.Fatalf("loading %s: %v", testDataDir, graphErr)
	}
	return sharedG
}

// ---------------------------------------------------------------------------
// Feature: Data loading
// ---------------------------------------------------------------------------

func TestFeatureDataLoading(t *testing.T) {
	feature(t, "all six CSV files are loadable and queryable", func(s *scenario) {
		s.Given("the data directory %s", testDataDir)
		s.When("the knowledge graph is loaded")
		st := s.g.Stats()

		s.Then("every match file contributes fixtures")
		for _, f := range MatchFiles {
			s.assert(st.FileRows[f] > 0, "file %s contributed %d matches, want > 0", f, st.FileRows[f])
		}
		s.And("the FIFA player file contributes 18207 players")
		s.equal(st.Players, 18207, "player count")

		s.And("duplicate fixtures across files are merged")
		s.assert(st.Duplicates > 0, "expected duplicates to be detected, got %d", st.Duplicates)
		s.assert(st.Matches < st.RawMatches, "unique (%d) should be below raw (%d)", st.Matches, st.RawMatches)

		s.And("all five competitions are present")
		for _, comp := range []string{SerieA, SerieB, SerieC, CopaDoBrasil, Libertadores} {
			seasons := s.g.Competitions()[comp]
			s.assert(len(seasons) > 0, "competition %q has no seasons", comp)
		}
	})

	feature(t, "unplayable fixtures are skipped rather than counted as 0-0", func(s *scenario) {
		s.Given("Brasileirao_Matches.csv contains rows with NA scores")
		s.When("the file is loaded")
		st := s.g.Stats()
		s.Then("those rows are reported as skipped")
		s.assert(st.SkippedRows[FileBrasileirao] > 0,
			"expected skipped rows in %s, got %d", FileBrasileirao, st.SkippedRows[FileBrasileirao])
		s.And("no match in the graph came from an NA row")
		// A skipped row would otherwise appear as a 0-0 with no source merge.
		s.assert(st.Matches > 15000, "expected >15000 unique matches, got %d", st.Matches)
	})

	feature(t, "UTF-8 club names survive loading", func(s *scenario) {
		s.Given("the datasets contain accented club names")
		s.When("clubs are looked up by their accented name")
		for _, name := range []string{"Grêmio", "São Paulo", "Avaí", "Goiás", "Náutico", "Ceará"} {
			t, err := s.g.ResolveTeam(name)
			s.must(err)
			s.Then("%q resolves to %q", name, t.Name)
			s.assert(t.MatchCount > 0, "%s has no matches", t.Name)
		}
	})
}

// ---------------------------------------------------------------------------
// Feature: Match Queries
// ---------------------------------------------------------------------------

func TestFeatureMatchQueries(t *testing.T) {
	feature(t, "find matches between two teams", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When(`I search for matches between "Flamengo" and "Fluminense"`)
		res, err := s.g.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense", Limit: 5})
		s.must(err)

		s.Then("I should receive a list of matches")
		s.assert(res.Total > 20, "expected many Fla-Flu meetings, got %d", res.Total)
		s.assert(res.Returned == 5, "expected 5 returned under limit, got %d", res.Returned)

		s.And("each match should have date, scores, and competition")
		for _, m := range res.Matches {
			s.assert(!m.Date.IsZero(), "match has no date: %+v", m)
			s.assert(m.Competition != "", "match has no competition: %+v", m)
			s.assert(m.Home.ID == "flamengo" || m.Away.ID == "flamengo", "Flamengo missing from %+v", m)
			s.assert(m.Home.ID == "fluminense" || m.Away.ID == "fluminense", "Fluminense missing from %+v", m)
		}

		s.And("a head-to-head record is included")
		h := res.HeadToHead
		s.assert(h != nil, "expected head-to-head record")
		s.equal(h.WinsA+h.WinsB+h.Draws, h.Matches, "h2h outcomes")
		s.equal(h.Matches, res.Total, "h2h meetings vs total matches")
	})

	feature(t, "what matches did Palmeiras play in 2023", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When(`I search for Palmeiras matches in season 2023`)
		res, err := s.g.FindMatches(MatchFilter{Team: "Palmeiras", Season: 2023, Limit: 100})
		s.must(err)
		s.Then("every returned match is from 2023 and involves Palmeiras")
		s.assert(res.Total > 30, "expected a full 2023 campaign, got %d matches", res.Total)
		for _, m := range res.Matches {
			s.equal(m.Season, 2023, "season")
			s.assert(m.Involves("palmeiras"), "Palmeiras missing from %s", describeMatch(m))
		}
	})

	feature(t, "find all Copa do Brasil finals", func(s *scenario) {
		s.Given("the cup data is loaded")
		s.When(`I search Copa do Brasil matches with round "final"`)
		res, err := s.g.FindMatches(MatchFilter{Competition: "Copa do Brasil", Round: "final", Limit: 200})
		s.must(err)
		s.Then("only final and semi-final ties come back")
		s.assert(res.Total > 0, "expected some finals")
		for _, m := range res.Matches {
			s.equal(m.Competition, CopaDoBrasil, "competition")
			s.assert(strings.Contains(strings.ToLower(m.Stage), "final"),
				"unexpected stage %q", m.Stage)
		}

		s.And("an exact stage filter isolates the finals themselves")
		exact, err := s.g.FindMatches(MatchFilter{Competition: "Copa do Brasil", Round: "Final", Limit: 200})
		s.must(err)
		finals := 0
		for _, m := range exact.Matches {
			if m.Stage == "Final" {
				finals++
			}
		}
		s.assert(finals > 0, "expected at least one match staged as Final")
	})

	feature(t, "when did Flamengo last play Corinthians and what was the score", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I ask for the most recent Flamengo vs Corinthians match")
		res, err := s.g.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Corinthians", Limit: 1})
		s.must(err)
		s.Then("exactly one match is returned, the latest one")
		s.equal(res.Returned, 1, "returned")
		latest := res.Matches[0]
		s.And("it is later than every other meeting")
		all, err := s.g.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Corinthians", Limit: 1000})
		s.must(err)
		for _, m := range all.Matches {
			s.assert(!m.Date.After(latest.Date), "%s is later than the 'latest' %s",
				describeMatch(m), describeMatch(latest))
		}
		s.And("the score is available: %s %d-%d %s",
			latest.Home.Name, latest.HomeGoals, latest.AwayGoals, latest.Away.Name)
		s.assert(latest.HomeGoals >= 0 && latest.AwayGoals >= 0, "scores must be non-negative")
	})

	feature(t, "matches can be filtered by date range", func(s *scenario) {
		s.Given("the match data is loaded")
		from := time.Date(2019, 1, 1, 0, 0, 0, 0, time.UTC)
		to := time.Date(2019, 6, 30, 0, 0, 0, 0, time.UTC)
		s.When("I search for matches between %s and %s", from.Format("2006-01-02"), to.Format("2006-01-02"))
		res, err := s.g.FindMatches(MatchFilter{From: from, To: to, Limit: 500})
		s.must(err)
		s.Then("every returned match falls inside the range")
		s.assert(res.Total > 100, "expected a busy half-season, got %d", res.Total)
		for _, m := range res.Matches {
			s.assert(!m.Date.Before(from) && !m.Date.After(to), "%s outside range", describeMatch(m))
		}
	})

	feature(t, "unknown clubs produce a helpful error", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I search for a club that does not exist")
		_, err := s.g.FindMatches(MatchFilter{Team: "Manchester United"})
		s.Then("an ErrTeamNotFound is returned")
		s.assert(err != nil, "expected an error")
		var notFound *ErrTeamNotFound
		s.assert(asErr(err, &notFound), "expected ErrTeamNotFound, got %T", err)
	})
}

func asErr[T error](err error, target *T) bool {
	if t, ok := err.(T); ok {
		*target = t
		return true
	}
	return false
}

// ---------------------------------------------------------------------------
// Feature: Team Queries
// ---------------------------------------------------------------------------

func TestFeatureTeamQueries(t *testing.T) {
	feature(t, "get team statistics", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When(`I request statistics for "Palmeiras" in season "2023"`)
		st, err := s.g.TeamStatistics(TeamStatsFilter{Team: "Palmeiras", Season: 2023})
		s.must(err)

		s.Then("I should receive wins, losses, draws, and goals")
		s.equal(st.Overall.Wins+st.Overall.Draws+st.Overall.Losses, st.Overall.Matches, "W+D+L")
		s.assert(st.Overall.GoalsFor > 0, "expected goals scored")
		s.assert(st.Overall.GoalsAgainst >= 0, "goals against must be set")
		s.And("home and away splits add up to the overall record")
		s.equal(st.Home.Matches+st.Away.Matches, st.Overall.Matches, "home+away")
		s.equal(st.Home.GoalsFor+st.Away.GoalsFor, st.Overall.GoalsFor, "home+away goals")
		s.And("points follow the three-point rule")
		s.equal(st.Overall.Points, st.Overall.Wins*3+st.Overall.Draws, "points")
	})

	feature(t, "Corinthians home record in the 2022 Brasileirao", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When(`I request the Corinthians 2022 Serie A home record`)
		st, err := s.g.TeamStatistics(TeamStatsFilter{
			Team: "Corinthians", Season: 2022, Competition: "Serie A", Venue: "home"})
		s.must(err)
		s.Then("a 19-match home campaign is reported")
		s.equal(st.Overall.Matches, 19, "home matches in a 20-team league")
		s.equal(st.Away.Matches, 0, "away matches under a home-only filter")
		s.And("the win rate is derived from those 19 matches")
		s.equal(st.Overall.Wins+st.Overall.Draws+st.Overall.Losses, 19, "W+D+L")
	})

	feature(t, "compare Palmeiras and Santos head-to-head", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I compare Palmeiras and Santos")
		c, err := s.g.Compare("Palmeiras", "Santos", 0, "")
		s.must(err)
		s.Then("both clubs have a full record and a shared head-to-head")
		s.assert(c.A.Overall.Matches > 100, "Palmeiras should have many matches")
		s.assert(c.B.Overall.Matches > 100, "Santos should have many matches")
		s.equal(c.HeadToHead.WinsA+c.HeadToHead.WinsB+c.HeadToHead.Draws,
			c.HeadToHead.Matches, "h2h outcomes")
		s.And("the head-to-head goal totals are symmetric with the meetings")
		s.assert(c.HeadToHead.Matches > 20, "expected many Palmeiras-Santos meetings")
	})

	feature(t, "head-to-head is direction independent", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I ask for Gremio vs Internacional and then the reverse")
		ab, err := s.g.HeadToHead("Gremio", "Internacional", "", 0)
		s.must(err)
		ba, err := s.g.HeadToHead("Internacional", "Gremio", "", 0)
		s.must(err)
		s.Then("the two records mirror each other exactly")
		s.equal(ab.Matches, ba.Matches, "meetings")
		s.equal(ab.WinsA, ba.WinsB, "wins A vs wins B")
		s.equal(ab.WinsB, ba.WinsA, "wins B vs wins A")
		s.equal(ab.Draws, ba.Draws, "draws")
		s.equal(ab.GoalsA, ba.GoalsB, "goals")
	})

	feature(t, "search clubs by partial name and state", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When(`I search clubs matching "atletico"`)
		found := s.g.SearchTeams("atletico", "", 20)
		s.Then("several distinct Atletico clubs are returned")
		s.assert(len(found) >= 3, "expected several Atleticos, got %d", len(found))
		s.When("I list clubs from the state of RS")
		rs := s.g.SearchTeams("", "RS", 50)
		s.Then("Gremio and Internacional are among them")
		names := map[string]bool{}
		for _, t := range rs {
			names[t.ID] = true
		}
		s.assert(names["gremio"] && names["internacional"], "expected the Grenal clubs in RS, got %v", names)
	})

	feature(t, "what competitions has Palmeiras played in", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I look up the Palmeiras club node")
		t, err := s.g.ResolveTeam("Palmeiras")
		s.must(err)
		s.Then("the club lists every competition it appears in")
		s.assert(len(t.Competitions) >= 3, "expected 3+ competitions, got %v", t.Competitions)
		s.And("Serie A, Copa do Brasil and Libertadores are all present")
		set := map[string]bool{}
		for _, c := range t.Competitions {
			set[c] = true
		}
		for _, want := range []string{SerieA, CopaDoBrasil, Libertadores} {
			s.assert(set[want], "expected %s in %v", want, t.Competitions)
		}
	})
}

// ---------------------------------------------------------------------------
// Feature: Player Queries
// ---------------------------------------------------------------------------

func TestFeaturePlayerQueries(t *testing.T) {
	feature(t, "find all Brazilian players in the dataset", func(s *scenario) {
		s.Given("the FIFA player data is loaded")
		s.When(`I filter players by nationality "Brazil"`)
		res := s.g.FindPlayers(PlayerFilter{Nationality: "Brazil", Limit: 10})
		s.Then("a large set of Brazilians is returned, best rated first")
		s.assert(res.Total > 500, "expected many Brazilians, got %d", res.Total)
		s.equal(res.Returned, 10, "returned under limit")
		for i := 1; i < len(res.Players); i++ {
			s.assert(res.Players[i-1].Overall >= res.Players[i].Overall,
				"ratings out of order at %d", i)
		}
		s.And("every returned player is Brazilian")
		for _, p := range res.Players {
			s.equal(p.Nationality, "Brazil", "nationality of "+p.Name)
		}
		s.And("the highest rated is Neymar")
		s.assert(strings.Contains(res.Players[0].Name, "Neymar"),
			"expected Neymar top-rated, got %s (%d)", res.Players[0].Name, res.Players[0].Overall)
	})

	feature(t, "who is a named player", func(s *scenario) {
		s.Given("the FIFA player data is loaded")
		s.When(`I search players by name "Gabriel Jesus"`)
		res := s.g.FindPlayers(PlayerFilter{Name: "Gabriel Jesus"})
		s.Then("the player is found with a club, rating and nationality")
		s.require(res.Total >= 1, "expected to find Gabriel Jesus")
		p := res.Players[0]
		s.assert(p.Overall > 0, "expected an overall rating for %s", p.Name)
		s.equal(p.Nationality, "Brazil", "nationality")
		s.assert(p.Club != "", "expected a club")

		s.And("accented and unaccented spellings both work")
		for _, q := range []string{"Alisson", "Casemiro", "Thiago Silva", "Éder Militão", "Eder Militao"} {
			r := s.g.FindPlayers(PlayerFilter{Name: q})
			s.assert(r.Total >= 1, "expected to find %q", q)
		}
	})

	feature(t, "a player absent from the snapshot returns an honest empty result", func(s *scenario) {
		s.Given("the FIFA 19 snapshot predates some careers")
		s.When(`I search for "Gabriel Barbosa", who is not in this dataset`)
		res := s.g.FindPlayers(PlayerFilter{Name: "Gabriel Barbosa"})
		s.Then("zero players are returned rather than a wrong guess")
		s.equal(res.Total, 0, "matches for an absent player")
		s.equal(res.Returned, 0, "returned")
	})

	feature(t, "which players play for a Brazilian club", func(s *scenario) {
		s.Given("the FIFA player data is loaded")
		s.When(`I ask for the squad of "Gremio"`)
		sq, err := s.g.Squad("Gremio", true)
		s.must(err)
		s.Then("a squad with an average rating is returned")
		s.assert(sq.Players >= 10, "expected a full squad, got %d", sq.Players)
		s.assert(sq.AvgOverall > 0, "expected an average rating")
		s.And("the squad is ordered by rating and the top player is named")
		s.equal(sq.Squad[0].Name, sq.TopPlayer, "top player")
		s.And("the club is cross-referenced with the match graph")
		s.equal(sq.ClubID, "gremio", "canonical club id")
		s.assert(strings.Contains(sq.Summary, "fixture data"),
			"expected a cross-reference to the fixture data in %q", sq.Summary)
	})

	feature(t, "show me all forwards from a club", func(s *scenario) {
		s.Given("the FIFA player data is loaded")
		s.When(`I filter by club "Santos" and position "ST"`)
		res := s.g.FindPlayers(PlayerFilter{Club: "Santos", Position: "ST"})
		s.Then("only strikers at that club come back")
		s.require(res.Total > 0, "expected strikers at Santos")
		for _, p := range res.Players {
			s.equal(p.Position, "ST", "position of "+p.Name)
			s.equal(p.ClubID, "santos", "club of "+p.Name)
		}
		s.And("a club whose name is a prefix of another is not confused with it")
		for _, p := range res.Players {
			s.assert(p.Club != "Santos Laguna", "Santos Laguna leaked into a Santos search")
		}
	})

	feature(t, "clubs missing from the FIFA snapshot fail loudly", func(s *scenario) {
		s.Given("the FIFA 19 snapshot omits several unlicensed Brazilian clubs")
		for _, club := range []string{"Flamengo", "Palmeiras", "Corinthians", "Sao Paulo"} {
			s.When("I ask for the %s squad", club)
			_, err := s.g.Squad(club, false)
			s.Then("an explicit no-data error is returned rather than a wrong squad")
			s.assert(err != nil, "expected no FIFA squad for %s", club)
		}
		s.And("clubs that are present still work")
		for _, club := range []string{"Gremio", "Santos", "Internacional", "Cruzeiro"} {
			sq, err := s.g.Squad(club, false)
			s.must(err)
			s.assert(sq.Players > 0, "expected a squad for %s", club)
		}
	})

	feature(t, "Brazilian players at Brazilian clubs", func(s *scenario) {
		s.Given("both the player and the match data are loaded")
		s.When("I cross-reference Brazilian players against clubs in the fixture data")
		rows := s.g.BrazilianClubRatings("Brazil", 0, 20)
		s.Then("only clubs present in both datasets are listed")
		s.assert(len(rows) >= 10, "expected 10+ clubs in both datasets, got %d", len(rows))
		for _, r := range rows {
			_, inGraph := s.g.TeamByID(r.ClubID)
			s.assert(inGraph, "club %s (%s) is not in the match graph", r.Club, r.ClubID)
			s.assert(r.MatchCount > 0, "club %s has no fixtures", r.Club)
			s.assert(r.Players > 0 && r.AvgOverall > 0, "club %s has no rated players", r.Club)
		}
		s.And("clubs are ordered by average rating")
		for i := 1; i < len(rows); i++ {
			s.assert(rows[i-1].AvgOverall >= rows[i].AvgOverall, "ratings out of order at %d", i)
		}
	})

	feature(t, "player filters compose", func(s *scenario) {
		s.Given("the FIFA player data is loaded")
		s.When("I ask for Brazilian goalkeepers rated 80 or better")
		res := s.g.FindPlayers(PlayerFilter{Nationality: "Brazil", Position: "GK", MinOverall: 80})
		s.Then("every result satisfies all three constraints")
		s.assert(res.Total > 0, "expected some highly rated Brazilian keepers")
		for _, p := range res.Players {
			s.equal(p.Nationality, "Brazil", "nationality")
			s.equal(p.Position, "GK", "position")
			s.assert(p.Overall >= 80, "%s rated %d, want >= 80", p.Name, p.Overall)
		}
	})
}

// ---------------------------------------------------------------------------
// Feature: Competition Queries
// ---------------------------------------------------------------------------

func TestFeatureCompetitionQueries(t *testing.T) {
	feature(t, "who won the 2019 Brasileirao", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I calculate the 2019 Brasileirao standings")
		st, err := s.g.LeagueStandings("brasileirao", 2019, 0)
		s.must(err)

		s.Then("the season is complete: 20 teams and 380 matches")
		s.equal(len(st.Table), 20, "teams")
		s.equal(st.Matches, 380, "matches counted")
		s.assert(st.Complete, "expected a complete season")

		s.And("Flamengo are champions on 90 points")
		s.equal(st.Champion, "Flamengo", "champion")
		s.equal(st.Table[0].Points, 90, "champion points")
		s.equal(st.Table[0].Wins, 28, "champion wins")
		s.equal(st.Table[0].Draws, 6, "champion draws")
		s.equal(st.Table[0].Losses, 4, "champion losses")
		s.equal(st.Table[0].GoalsFor, 86, "champion goals for")

		s.And("Santos and Palmeiras follow on 74 points")
		s.equal(st.Table[1].Team, "Santos", "runner-up")
		s.equal(st.Table[1].Points, 74, "runner-up points")
		s.equal(st.Table[2].Team, "Palmeiras", "third")
		s.equal(st.Table[2].Points, 74, "third points")

		s.And("every club played 38 matches")
		for _, r := range st.Table {
			s.equal(r.Played, 38, "matches played by "+r.Team)
			s.equal(r.Points, r.Wins*3+r.Draws, "points for "+r.Team)
			s.equal(r.Wins+r.Draws+r.Losses, 38, "W+D+L for "+r.Team)
		}
	})

	feature(t, "which teams were relegated in 2020", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I calculate the 2020 Brasileirao standings")
		st, err := s.g.LeagueStandings("brasileirao", 2020, 0)
		s.must(err)
		s.Then("four clubs are marked relegated")
		s.equal(len(st.Relegated), 4, "relegated count")
		s.And("they are the bottom four of the table")
		for i, name := range st.Relegated {
			s.equal(st.Table[len(st.Table)-4+i].Team, name, "relegated position")
		}
		s.And("the actual 2020 relegated clubs are Coritiba, Botafogo, Goias and Vasco da Gama")
		got := map[string]bool{}
		for _, n := range st.Relegated {
			got[n] = true
		}
		for _, want := range []string{"Coritiba", "Botafogo", "Goiás", "Vasco da Gama"} {
			s.assert(got[want], "expected %s among relegated %v", want, st.Relegated)
		}
	})

	feature(t, "standings totals reconcile with the matches", func(s *scenario) {
		s.Given("the match data is loaded")
		for _, season := range []int{2014, 2017, 2021, 2022} {
			s.When("I calculate the %d Brasileirao standings", season)
			st, err := s.g.LeagueStandings("Brasileirão Série A", season, 0)
			s.must(err)
			s.Then("goals for across the table equal goals against")
			gf, ga, played := 0, 0, 0
			for _, r := range st.Table {
				gf += r.GoalsFor
				ga += r.GoalsAgainst
				played += r.Played
			}
			s.equal(gf, ga, fmt.Sprintf("%d goals scored vs conceded", season))
			s.equal(played, st.Matches*2, fmt.Sprintf("%d appearances", season))
		}
	})

	feature(t, "a knockout competition refuses to produce a league table", func(s *scenario) {
		s.Given("the cup data is loaded")
		s.When("I ask for Copa do Brasil standings")
		_, err := s.g.LeagueStandings("copa do brasil", 2019, 0)
		s.Then("the query is rejected with an explanation")
		s.assert(err != nil, "expected an error for a knockout competition")
		s.assert(strings.Contains(err.Error(), "find_matches"),
			"expected the error to point at find_matches, got %q", err)
	})

	feature(t, "Libertadores stages are queryable", func(s *scenario) {
		s.Given("the Libertadores data is loaded")
		s.When("I search the 2018 Libertadores by stage")
		res, err := s.g.FindMatches(MatchFilter{Competition: "Libertadores", Season: 2018, Limit: 200})
		s.must(err)
		s.Then("matches carry a tournament stage")
		s.assert(res.Total > 100, "expected a full Libertadores season, got %d", res.Total)
		stages := map[string]int{}
		for _, m := range res.Matches {
			stages[m.Stage]++
		}
		s.assert(len(stages) > 1, "expected several stages, got %v", stages)
		s.assert(stages["group stage"] > 0, "expected group stage matches, got %v", stages)
	})
}

// ---------------------------------------------------------------------------
// Feature: Statistical Analysis
// ---------------------------------------------------------------------------

func TestFeatureStatisticalAnalysis(t *testing.T) {
	feature(t, "average goals per match in the Brasileirao", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I aggregate Brasileirao Serie A statistics")
		st, err := s.g.AggregateStats(StatsFilter{Competition: "brasileirao"})
		s.must(err)
		s.Then("the average goals per match is a plausible football number")
		s.assert(st.AvgGoals > 2.0 && st.AvgGoals < 3.2,
			"average goals %.2f outside the plausible 2.0-3.2 range", st.AvgGoals)
		s.And("home, away and draw rates sum to 100%%")
		total := st.HomeWinPct + st.AwayWinPct + st.DrawPct
		s.assert(total > 99.9 && total < 100.1, "outcome rates sum to %.2f, want 100", total)
		s.And("home advantage is visible")
		s.assert(st.HomeWinPct > st.AwayWinPct, "expected home advantage, got %.1f vs %.1f",
			st.HomeWinPct, st.AwayWinPct)
		s.And("the goal totals reconcile")
		s.equal(st.HomeGoals+st.AwayGoals, st.Goals, "home+away goals")
		s.equal(st.HomeWins+st.AwayWins+st.Draws, st.Matches, "outcomes")
	})

	feature(t, "show me the biggest wins in the dataset", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I ask for the biggest victories")
		st, err := s.g.AggregateStats(StatsFilter{TopN: 5})
		s.must(err)
		s.Then("five results are listed, by descending margin")
		s.equal(len(st.BiggestWins), 5, "biggest wins listed")
		s.And("the top result has a margin of at least six goals")
		s.assert(strings.Contains(st.BiggestWins[0], "-"), "expected a scoreline in %q", st.BiggestWins[0])
		s.And("the highest scoring list is also populated")
		s.equal(len(st.HighestScoring), 5, "highest scoring listed")
	})

	feature(t, "which team has the best home record", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I rank clubs by home win rate in the Brasileirao")
		rows, err := s.g.Leaderboard(LeaderboardFilter{
			Metric: "win_rate", Competition: "brasileirao", Venue: "home", MinMatches: 50, Limit: 5})
		s.must(err)
		s.Then("clubs are ranked from best to worst")
		s.assert(len(rows) == 5, "expected 5 rows, got %d", len(rows))
		for i := 1; i < len(rows); i++ {
			s.assert(rows[i-1].Value >= rows[i].Value, "rows out of order at %d", i)
			s.equal(rows[i].Rank, i+1, "rank")
		}
		s.And("the home win rate beats the same clubs' away win rate on average")
		away, err := s.g.Leaderboard(LeaderboardFilter{
			Metric: "win_rate", Competition: "brasileirao", Venue: "away", MinMatches: 50, Limit: 5})
		s.must(err)
		s.assert(rows[0].Value > away[0].Value,
			"best home rate %.1f should beat best away rate %.1f", rows[0].Value, away[0].Value)
	})

	feature(t, "which team scored the most goals in Serie A 2023", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I rank clubs by goals scored in the 2023 Serie A")
		rows, err := s.g.Leaderboard(LeaderboardFilter{
			Metric: "goals_for", Competition: "serie a", Season: 2023, Limit: 3})
		s.must(err)
		s.Then("a top scorer club is identified")
		s.assert(len(rows) == 3, "expected 3 rows, got %d", len(rows))
		s.assert(rows[0].Value > 0, "expected goals")
		s.And("the ranking agrees with the calculated standings")
		st, err := s.g.LeagueStandings("serie a", 2023, 0)
		s.must(err)
		best := 0
		for _, r := range st.Table {
			if r.GoalsFor > best {
				best = r.GoalsFor
			}
		}
		s.equal(int(rows[0].Value), best, "top goals scored")
	})

	feature(t, "compare the 2018 and 2019 seasons", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I compare the 2018 and 2019 Brasileirao seasons")
		c, err := s.g.CompareSeasons("brasileirao", 2018, 2019)
		s.must(err)
		s.Then("both seasons are summarised with deltas between them")
		s.equal(c.Seasons["2018"].Matches, 380, "2018 matches")
		s.equal(c.Seasons["2019"].Matches, 380, "2019 matches")
		s.assert(c.Deltas["avg_goals_per_match"] != 0 || c.Seasons["2018"].AvgGoals == c.Seasons["2019"].AvgGoals,
			"delta should reflect the difference")
	})

	feature(t, "show me all derbies in a season", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I ask for derby matches in 2019")
		derbies, err := s.g.DerbyMatches(2019, 10)
		s.must(err)
		s.Then("classic rivalries are listed with their fixtures")
		s.assert(len(derbies) >= 5, "expected several derbies in 2019, got %d", len(derbies))
		for name, lines := range derbies {
			s.assert(len(lines) > 0, "derby %s has no matches", name)
			for _, l := range lines {
				s.assert(strings.HasPrefix(l, "2019-"), "derby %s has non-2019 match %q", name, l)
			}
		}
		s.And("the Fla-Flu and the Grenal are among them")
		s.assert(derbies["Fla-Flu"] != nil, "expected Fla-Flu in %v", keysOf(derbies))
		s.assert(derbies["Grenal"] != nil, "expected Grenal in %v", keysOf(derbies))
	})

	feature(t, "statistics can be scoped to one club", func(s *scenario) {
		s.Given("the match data is loaded")
		s.When("I aggregate statistics for matches involving Flamengo")
		st, err := s.g.AggregateStats(StatsFilter{Team: "Flamengo"})
		s.must(err)
		s.Then("only Flamengo matches are counted")
		t, err := s.g.ResolveTeam("Flamengo")
		s.must(err)
		s.equal(st.Matches, t.MatchCount, "Flamengo matches")
	})
}

func keysOf[V any](m map[string]V) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}

// ---------------------------------------------------------------------------
// Feature: Query performance
// ---------------------------------------------------------------------------

func TestFeatureQueryPerformance(t *testing.T) {
	feature(t, "simple lookups respond in under 2 seconds", func(s *scenario) {
		s.Given("the knowledge graph is loaded")
		lookups := map[string]func(){
			"find_matches by team": func() { s.g.FindMatches(MatchFilter{Team: "Flamengo"}) },
			"head_to_head":         func() { s.g.HeadToHead("Flamengo", "Fluminense", "", 0) },
			"find_players by name": func() { s.g.FindPlayers(PlayerFilter{Name: "Neymar"}) },
			"find_players by club": func() { s.g.FindPlayers(PlayerFilter{Club: "Santos"}) },
			"team_statistics":      func() { s.g.TeamStatistics(TeamStatsFilter{Team: "Palmeiras"}) },
			"search_teams":         func() { s.g.SearchTeams("atletico", "", 25) },
		}
		for name, fn := range lookups {
			s.When("I run %s", name)
			start := time.Now()
			fn()
			elapsed := time.Since(start)
			s.Then("%s completes in %s", name, elapsed)
			s.assert(elapsed < 2*time.Second, "%s took %s, budget is 2s", name, elapsed)
		}
	})

	feature(t, "aggregate queries respond in under 5 seconds", func(s *scenario) {
		s.Given("the knowledge graph is loaded")
		aggregates := map[string]func(){
			"standings":      func() { s.g.LeagueStandings("brasileirao", 2019, 0) },
			"all-time stats": func() { s.g.AggregateStats(StatsFilter{}) },
			"leaderboard":    func() { s.g.Leaderboard(LeaderboardFilter{Metric: "points"}) },
			"club ratings":   func() { s.g.BrazilianClubRatings("Brazil", 0, 50) },
			"derbies":        func() { s.g.DerbyMatches(0, 10) },
			"season compare": func() { s.g.CompareSeasons("brasileirao", 2018, 2019) },
		}
		for name, fn := range aggregates {
			s.When("I run %s", name)
			start := time.Now()
			fn()
			elapsed := time.Since(start)
			s.Then("%s completes in %s", name, elapsed)
			s.assert(elapsed < 5*time.Second, "%s took %s, budget is 5s", name, elapsed)
		}
	})

	feature(t, "the whole dataset loads quickly enough for start-up", func(s *scenario) {
		s.Given("all six CSV files")
		s.When("the graph is loaded from scratch")
		start := time.Now()
		_, err := Load(testDataDir)
		s.must(err)
		elapsed := time.Since(start)
		s.Then("loading completes in %s", elapsed)
		s.assert(elapsed < 30*time.Second, "cold load took %s", elapsed)
	})
}

// ---------------------------------------------------------------------------
// Feature: Concurrency
// ---------------------------------------------------------------------------

func TestFeatureConcurrentQueries(t *testing.T) {
	feature(t, "the graph serves concurrent queries safely", func(s *scenario) {
		s.Given("the knowledge graph is loaded")
		s.When("50 goroutines query it at once")
		var wg sync.WaitGroup
		errs := make(chan error, 50)
		for i := 0; i < 50; i++ {
			wg.Add(1)
			go func(i int) {
				defer wg.Done()
				if _, err := s.g.FindMatches(MatchFilter{Team: "Flamengo", Season: 2015 + i%8}); err != nil {
					errs <- err
				}
				if _, err := s.g.LeagueStandings("brasileirao", 2015+i%8, 0); err != nil {
					errs <- err
				}
				s.g.FindPlayers(PlayerFilter{Nationality: "Brazil", Limit: 5})
			}(i)
		}
		wg.Wait()
		close(errs)
		s.Then("no query fails")
		for err := range errs {
			s.t.Errorf("concurrent query failed: %v", err)
		}
	})
}
