// BDD (Given/When/Then) tests for the query engine.
//
// Context: exercises the five query categories required by TASK.md —
// match search, team statistics, player queries, competition standings
// and statistical analysis — against the real Kaggle datasets, including
// the documented example queries (Flamengo vs Fluminense, Corinthians'
// 2022 home record, the 2019 Brasileirão champion) and the query
// performance criteria (<2s simple lookups, <5s aggregates).
package query

import (
	"strings"
	"sync"
	"testing"
	"time"

	"brazilian-soccer-mcp/internal/data"
)

var (
	testOnce sync.Once
	testEng  *Engine
	testErr  error
)

func engine(t *testing.T) *Engine {
	t.Helper()
	testOnce.Do(func() {
		var dir string
		dir, testErr = data.FindDataDir(".")
		if testErr != nil {
			return
		}
		var ds *data.Dataset
		ds, testErr = data.LoadDataset(dir)
		if testErr == nil {
			testEng = New(ds)
		}
	})
	if testErr != nil {
		t.Fatalf("loading datasets: %v", testErr)
	}
	return testEng
}

func TestScenarioFindMatchesBetweenTwoTeams(t *testing.T) {
	// Given the match data is loaded
	e := engine(t)

	// When I search for matches between "Flamengo" and "Fluminense"
	matches := e.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})

	// Then I should receive a list of matches
	if len(matches) < 20 {
		t.Fatalf("expected at least 20 Fla-Flu derbies, got %d", len(matches))
	}
	// And each match should have date, scores, and competition
	flamengo, fluminense := data.NormalizeTeam("Flamengo"), data.NormalizeTeam("Fluminense")
	for _, m := range matches {
		if m.Date.IsZero() || m.Competition == "" {
			t.Fatalf("match missing date or competition: %+v", m)
		}
		if !m.Involves(flamengo) || !m.Involves(fluminense) {
			t.Fatalf("match does not involve both teams: %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
	// And results are sorted newest first
	for i := 1; i < len(matches); i++ {
		if matches[i].Date.After(matches[i-1].Date) {
			t.Fatal("matches not sorted newest first")
		}
	}
}

func TestScenarioMatchesByTeamNameVariant(t *testing.T) {
	// Given the match data is loaded
	e := engine(t)

	// When I search using different spellings of the same team
	bySuffix := e.FindMatches(MatchFilter{Team: "Palmeiras-SP", Season: 2019, Competition: "serie a"})
	byPlain := e.FindMatches(MatchFilter{Team: "Palmeiras", Season: 2019, Competition: "serie a"})
	byAccent := e.FindMatches(MatchFilter{Team: "São Paulo", Season: 2019, Competition: "serie a"})
	byFolded := e.FindMatches(MatchFilter{Team: "Sao Paulo", Season: 2019, Competition: "serie a"})

	// Then every variant returns the same fixtures
	if len(bySuffix) == 0 || len(bySuffix) != len(byPlain) {
		t.Errorf("Palmeiras-SP returned %d matches, Palmeiras returned %d", len(bySuffix), len(byPlain))
	}
	if len(byAccent) == 0 || len(byAccent) != len(byFolded) {
		t.Errorf("São Paulo returned %d matches, Sao Paulo returned %d", len(byAccent), len(byFolded))
	}
	// And a 38-round Série A season has exactly 38 matches per team
	if len(byPlain) != 38 {
		t.Errorf("Palmeiras 2019 Série A: got %d matches, want 38", len(byPlain))
	}
}

func TestScenarioMatchesByDateRange(t *testing.T) {
	// Given the match data is loaded
	e := engine(t)
	from, _ := data.ParseDate("2019-06-01")
	to, _ := data.ParseDate("2019-06-30")

	// When I search for Flamengo matches in June 2019
	matches := e.FindMatches(MatchFilter{Team: "Flamengo", DateFrom: from, DateTo: to})

	// Then every match falls inside the range
	if len(matches) == 0 {
		t.Fatal("expected matches in June 2019")
	}
	for _, m := range matches {
		if m.Date.Before(from) || m.Date.After(to) {
			t.Errorf("match on %s outside requested range", m.Date.Format("2006-01-02"))
		}
	}
}

func TestScenarioTeamSeasonStatistics(t *testing.T) {
	// Given the match data is loaded
	e := engine(t)

	// When I request statistics for "Palmeiras" in season 2023
	rec, _, err := e.TeamStats("Palmeiras", 2023, "", "all")
	if err != nil {
		t.Fatal(err)
	}

	// Then I should receive wins, losses, draws, and goals
	if rec.Matches == 0 {
		t.Fatal("expected Palmeiras matches in 2023")
	}
	if rec.Wins+rec.Draws+rec.Losses != rec.Matches {
		t.Errorf("W+D+L = %d, want %d", rec.Wins+rec.Draws+rec.Losses, rec.Matches)
	}
	if rec.GoalsFor == 0 {
		t.Error("expected Palmeiras to have scored in 2023")
	}
}

func TestScenarioHomeRecord(t *testing.T) {
	// Given the match data is loaded
	e := engine(t)

	// When I request Corinthians' home record for the 2022 Brasileirão
	rec, _, err := e.TeamStats("Corinthians", 2022, "serie a", "home")
	if err != nil {
		t.Fatal(err)
	}

	// Then it covers the 19 home rounds of a 38-round season
	if rec.Matches != 19 {
		t.Errorf("Corinthians 2022 home matches = %d, want 19", rec.Matches)
	}
	if rec.Wins+rec.Draws+rec.Losses != rec.Matches {
		t.Errorf("W+D+L = %d, want %d", rec.Wins+rec.Draws+rec.Losses, rec.Matches)
	}
}

func TestScenarioHeadToHead(t *testing.T) {
	// Given the match data is loaded
	e := engine(t)

	// When I compare Palmeiras and Santos head-to-head
	h, err := e.HeadToHead("Palmeiras", "Santos", "")
	if err != nil {
		t.Fatal(err)
	}

	// Then wins, draws and matches are consistent
	if len(h.Matches) == 0 {
		t.Fatal("expected Palmeiras vs Santos matches")
	}
	if h.Team1Wins+h.Team2Wins+h.Draws != len(h.Matches) {
		t.Errorf("wins+draws = %d, want %d", h.Team1Wins+h.Team2Wins+h.Draws, len(h.Matches))
	}
}

func TestScenario2019BrasileiraoChampion(t *testing.T) {
	// Given the match data is loaded
	e := engine(t)

	// When I calculate the 2019 Brasileirão standings from match results
	table := e.Standings(2019, "")

	// Then 20 teams played 38 matches each
	if len(table) != 20 {
		t.Fatalf("2019 Série A table has %d teams, want 20", len(table))
	}
	for _, r := range table {
		if r.Matches != 38 {
			t.Errorf("%s played %d matches, want 38 (duplicate fixtures not merged?)", r.Team, r.Matches)
		}
	}
	// And Flamengo are champions with 90 points (28W 6D 4L), the real
	// final table for 2019
	top := table[0]
	if data.NormalizeTeam(top.Team) != "flamengo" {
		t.Errorf("2019 champion = %s, want Flamengo", top.Team)
	}
	if top.Points() != 90 || top.Wins != 28 || top.Draws != 6 || top.Losses != 4 {
		t.Errorf("Flamengo 2019 = %d pts (%dW %dD %dL), want 90 pts (28W 6D 4L)",
			top.Points(), top.Wins, top.Draws, top.Losses)
	}
}

func TestScenarioSearchPlayersByName(t *testing.T) {
	// Given the FIFA player data is loaded
	e := engine(t)

	// When I search for "Neymar"
	players := e.FindPlayers(PlayerFilter{Name: "Neymar"})

	// Then the Brazilian superstar is found with his attributes
	if len(players) == 0 {
		t.Fatal("Neymar not found")
	}
	p := players[0]
	if p.Nationality != "Brazil" {
		t.Errorf("Neymar nationality = %q, want Brazil", p.Nationality)
	}
	if p.Overall < 90 {
		t.Errorf("Neymar overall = %d, want >= 90", p.Overall)
	}
}

func TestScenarioFilterPlayersByNationalityAndClub(t *testing.T) {
	// Given the FIFA player data is loaded
	e := engine(t)

	// When I filter players by nationality "Brazil"
	brazilians := e.FindPlayers(PlayerFilter{Nationality: "Brazil"})

	// Then all 827 Brazilian players in the dataset are returned
	if len(brazilians) != 827 {
		t.Errorf("Brazilian players = %d, want 827", len(brazilians))
	}
	// And they are sorted by overall rating, highest first
	for i := 1; i < len(brazilians); i++ {
		if brazilians[i].Overall > brazilians[i-1].Overall {
			t.Fatal("players not sorted by overall rating")
		}
	}

	// When I filter by a Brazilian club (cross-file query: club names are
	// normalized with the same logic as match team names)
	santos := e.FindPlayers(PlayerFilter{Club: "Santos"})

	// Then only players of that club are returned
	if len(santos) == 0 {
		t.Fatal("expected Santos players in FIFA data")
	}
	for _, p := range santos {
		if !strings.Contains(p.ClubNorm, "santos") {
			t.Errorf("player %s club = %q, not Santos", p.Name, p.Club)
		}
	}
}

func TestScenarioAverageGoalsAndHomeAdvantage(t *testing.T) {
	// Given the match data is loaded
	e := engine(t)

	// When I compute Série A aggregate statistics
	st := e.CompetitionStats("serie a", 0)

	// Then the averages are in a plausible football range
	if st.Matches < 8000 {
		t.Errorf("Série A matches = %d, want >= 8000", st.Matches)
	}
	if avg := st.AvgGoals(); avg < 2.0 || avg > 3.2 {
		t.Errorf("average goals per match = %.2f, want between 2.0 and 3.2", avg)
	}
	// And home advantage exists (home win rate above away win rate)
	if st.HomeWins <= st.AwayWins {
		t.Errorf("home wins %d <= away wins %d; home advantage missing", st.HomeWins, st.AwayWins)
	}
}

func TestScenarioBiggestWins(t *testing.T) {
	// Given the match data is loaded
	e := engine(t)

	// When I ask for the biggest wins across all competitions
	wins := e.BiggestWins("", 0, 10)

	// Then ten decisive results are returned in descending margin order
	if len(wins) != 10 {
		t.Fatalf("got %d results, want 10", len(wins))
	}
	margin := func(m *data.Match) int {
		d := m.HomeGoals - m.AwayGoals
		if d < 0 {
			d = -d
		}
		return d
	}
	for i := 1; i < len(wins); i++ {
		if margin(wins[i]) > margin(wins[i-1]) {
			t.Fatal("biggest wins not sorted by margin")
		}
	}
	if margin(wins[0]) < 6 {
		t.Errorf("largest margin = %d, expected a blowout of 6+ goals", margin(wins[0]))
	}
}

func TestScenarioQueryPerformance(t *testing.T) {
	// Given the dataset is fully loaded (load time excluded by warming up)
	e := engine(t)

	// When I run a simple lookup
	start := time.Now()
	e.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Corinthians"})
	simple := time.Since(start)

	// Then it responds in under 2 seconds
	if simple > 2*time.Second {
		t.Errorf("simple lookup took %v, want < 2s", simple)
	}

	// When I run aggregate queries (standings + competition stats)
	start = time.Now()
	e.Standings(2019, "")
	e.CompetitionStats("", 0)
	e.BiggestWins("", 0, 10)
	aggregate := time.Since(start)

	// Then they respond in under 5 seconds
	if aggregate > 5*time.Second {
		t.Errorf("aggregate queries took %v, want < 5s", aggregate)
	}
}

func TestScenarioFormattedResponses(t *testing.T) {
	// Given query results
	e := engine(t)

	// When I format a head-to-head answer
	h, err := e.HeadToHead("Flamengo", "Fluminense", "")
	if err != nil {
		t.Fatal(err)
	}
	text := FormatHeadToHead(h, 5)

	// Then the response includes both team names, win counts and matches
	for _, want := range []string{"head-to-head", "wins", "Draws", "-"} {
		if !strings.Contains(text, want) {
			t.Errorf("formatted head-to-head missing %q:\n%s", want, text)
		}
	}

	// When I format standings
	standings := FormatStandings(e.Standings(2019, ""), 2019, data.CompSerieA)

	// Then the champion is marked and points are shown
	if !strings.Contains(standings, "Champion") || !strings.Contains(standings, "pts") {
		t.Errorf("formatted standings missing champion/points:\n%s", standings)
	}
}
