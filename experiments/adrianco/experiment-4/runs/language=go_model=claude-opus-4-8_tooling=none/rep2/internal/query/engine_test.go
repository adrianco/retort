// Context:
//   - Project: Brazilian Soccer MCP Server (see TASK.md).
//   - Role of this file: BDD (Given/When/Then) tests for the query engine. Most
//     scenarios run against a small, hand-built synthetic database for
//     determinism; a final group runs against the real Kaggle data and asserts
//     well-known facts (e.g. Flamengo won the 2019 Brasileirão with 90 points).
package query

import (
	"path/filepath"
	"strings"
	"testing"
	"time"

	"brazilian-soccer-mcp/internal/data"
)

// mkMatch builds a Match with the derived display/state fields populated the way
// the loader would, so synthetic fixtures behave like loaded ones.
func mkMatch(comp string, season int, date, home, away string, hg, ag int) data.Match {
	d, _ := time.Parse("2006-01-02", date)
	return data.Match{
		Competition: comp,
		Season:      season,
		Date:        d,
		HasDate:     date != "",
		HomeRaw:     home,
		AwayRaw:     away,
		HomeTeam:    data.DisplayTeam(home),
		AwayTeam:    data.DisplayTeam(away),
		HomeState:   data.TeamState(home),
		AwayState:   data.TeamState(away),
		HomeGoal:    hg,
		AwayGoal:    ag,
		Source:      "synthetic",
	}
}

// syntheticEngine builds a tiny, fully-known dataset:
//   - A round-robin-ish set of 2023 Série A games among 3 clubs.
//   - One Libertadores game.
//   - A handful of FIFA players.
func syntheticEngine() *Engine {
	const A = data.CompSerieA
	db := &data.Database{
		Matches: []data.Match{
			mkMatch(A, 2023, "2023-09-03", "Flamengo-RJ", "Fluminense-RJ", 2, 1),
			mkMatch(A, 2023, "2023-05-28", "Fluminense-RJ", "Flamengo-RJ", 0, 1),
			mkMatch(A, 2023, "2023-07-10", "Flamengo-RJ", "Palmeiras-SP", 1, 1),
			mkMatch(A, 2023, "2023-08-01", "Palmeiras-SP", "Flamengo-RJ", 3, 0),
			mkMatch(A, 2023, "2023-06-15", "Palmeiras-SP", "Fluminense-RJ", 2, 0),
			mkMatch(A, 2023, "2023-09-20", "Fluminense-RJ", "Palmeiras-SP", 2, 2),
			mkMatch(data.CompLibertadores, 2023, "2023-11-04", "Fluminense-RJ", "Boca Juniors", 2, 1),
		},
		Players: []data.Player{
			{ID: 1, Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Potential: 92, Position: "LW", Club: "Paris Saint-Germain", Age: 31},
			{ID: 2, Name: "Alisson", Nationality: "Brazil", Overall: 89, Potential: 90, Position: "GK", Club: "Liverpool", Age: 28},
			{ID: 3, Name: "Gabriel Barbosa", Nationality: "Brazil", Overall: 83, Potential: 85, Position: "ST", Club: "Flamengo", Age: 26},
			{ID: 4, Name: "Pedro", Nationality: "Brazil", Overall: 80, Potential: 84, Position: "ST", Club: "Flamengo", Age: 25},
			{ID: 5, Name: "L. Messi", Nationality: "Argentina", Overall: 94, Potential: 94, Position: "RW", Club: "Paris Saint-Germain", Age: 34},
		},
	}
	return New(db)
}

func TestSearchMatches_BetweenTwoTeams(t *testing.T) {
	// Feature: Match Queries
	// Scenario: Find matches between two teams
	e := syntheticEngine()

	// Given the match data is loaded
	// When I search for matches between "Flamengo" and "Fluminense"
	got := e.SearchMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})

	// Then I should receive the two Fla-Flu matches
	if len(got) != 2 {
		t.Fatalf("got %d matches; want 2", len(got))
	}
	// And each match should have date, scores, and competition
	for _, m := range got {
		if !m.HasDate || m.Competition == "" {
			t.Fatalf("match missing date/competition: %+v", m)
		}
		// And the pairing is always Flamengo vs Fluminense
		if !(data.TeamMatches("Flamengo", m.HomeRaw) || data.TeamMatches("Flamengo", m.AwayRaw)) {
			t.Fatalf("unexpected match without Flamengo: %+v", m)
		}
	}
	// And results are sorted most-recent first
	if got[0].Date.Before(got[1].Date) {
		t.Fatalf("results not sorted most-recent first")
	}
}

func TestSearchMatches_FilterByCompetitionAndSeason(t *testing.T) {
	// Scenario: Filter matches by competition and season
	e := syntheticEngine()
	// When I restrict to the Libertadores
	got := e.SearchMatches(MatchFilter{Competition: "Libertadores"})
	if len(got) != 1 {
		t.Fatalf("Libertadores matches = %d; want 1", len(got))
	}
	// And to Série A 2023 by team
	got = e.SearchMatches(MatchFilter{Team: "Fluminense", Competition: "Brasileirão", Season: 2023})
	for _, m := range got {
		if m.Competition != data.CompSerieA || m.Season != 2023 {
			t.Fatalf("filter leaked non-matching record: %+v", m)
		}
	}
}

func TestSearchMatches_VenueFilter(t *testing.T) {
	// Scenario: Restrict to home games only
	e := syntheticEngine()
	got := e.SearchMatches(MatchFilter{Team: "Flamengo", Venue: "home"})
	for _, m := range got {
		if !data.TeamMatches("Flamengo", m.HomeRaw) {
			t.Fatalf("away game leaked into home filter: %+v", m)
		}
	}
	if len(got) != 2 { // Flamengo home vs Flu and vs Palmeiras
		t.Fatalf("Flamengo home games = %d; want 2", len(got))
	}
}

func TestHeadToHead_Record(t *testing.T) {
	// Feature: Statistical Analysis — head-to-head records
	// Scenario: Compute Flamengo vs Fluminense record
	e := syntheticEngine()
	// When I request the head-to-head
	h := e.HeadToHead("Flamengo", "Fluminense")
	// Then Flamengo has won both meetings (2-1 and 1-0 away)
	if h.AWins != 2 || h.BWins != 0 || h.Draws != 0 {
		t.Fatalf("h2h = A%d B%d D%d; want A2 B0 D0", h.AWins, h.BWins, h.Draws)
	}
	// And goal tallies are oriented to each team
	if h.AGoals != 3 || h.BGoals != 1 {
		t.Fatalf("h2h goals = A%d B%d; want A3 B1", h.AGoals, h.BGoals)
	}
}

func TestTeamStats_SeasonRecord(t *testing.T) {
	// Feature: Team Queries
	// Scenario: Get team statistics
	e := syntheticEngine()
	// When I request statistics for Flamengo in 2023 Série A
	st := e.TeamStats("Flamengo", 2023, "Brasileirão", "")
	// Then I receive wins, losses, draws and goals.
	// Flamengo games: 2-1 W, 1-0 W, 1-1 D, 0-3 L  => P4 W2 D1 L1
	if st.Played != 4 || st.Wins != 2 || st.Draws != 1 || st.Losses != 1 {
		t.Fatalf("stats = P%d W%d D%d L%d; want P4 W2 D1 L1", st.Played, st.Wins, st.Draws, st.Losses)
	}
	if st.GoalsFor != 4 || st.GoalsAgainst != 5 {
		t.Fatalf("goals = GF%d GA%d; want GF4 GA5", st.GoalsFor, st.GoalsAgainst)
	}
	if st.Points() != 7 {
		t.Fatalf("points = %d; want 7", st.Points())
	}
}

func TestStandings_OrderAndPoints(t *testing.T) {
	// Feature: Competition Queries
	// Scenario: Compute standings from match results
	e := syntheticEngine()
	table := e.Standings("Brasileirão", 2023)
	if len(table) != 3 {
		t.Fatalf("standings teams = %d; want 3", len(table))
	}
	// Palmeiras: vs Fla 1-1 D, 3-0 W, vs Flu 2-0 W, 2-2 D => 8 pts, top.
	if table[0].Team != "Palmeiras" || table[0].Points() != 8 {
		t.Fatalf("leader = %s %dpts; want Palmeiras 8", table[0].Team, table[0].Points())
	}
	// And the table is sorted by points descending.
	for i := 1; i < len(table); i++ {
		if table[i-1].Points() < table[i].Points() {
			t.Fatalf("standings not sorted by points: %+v", table)
		}
	}
}

func TestCompetitionStats_Aggregates(t *testing.T) {
	// Feature: Statistical Analysis
	// Scenario: Average goals and biggest wins
	e := syntheticEngine()
	cs := e.CompetitionStats("Brasileirão", 2023, 3)
	if cs.Matches != 6 {
		t.Fatalf("matches = %d; want 6", cs.Matches)
	}
	// Total goals in the 6 Série A games: 3+1+2+3+2+4 = 15 -> avg 2.50
	if cs.AvgGoalsPerGame < 2.49 || cs.AvgGoalsPerGame > 2.51 {
		t.Fatalf("avg goals = %.2f; want 2.50", cs.AvgGoalsPerGame)
	}
	// Biggest win is the 3-0 (margin 3).
	if len(cs.BiggestWins) == 0 || cs.BiggestWins[0].GoalDiff() != 3 {
		t.Fatalf("biggest win not first: %+v", cs.BiggestWins)
	}
}

func TestSearchPlayers_FilterAndSort(t *testing.T) {
	// Feature: Player Queries
	// Scenario: Filter by nationality and club, sorted by rating
	e := syntheticEngine()

	// Brazilian players, sorted by overall descending.
	br := e.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
	if len(br) != 4 {
		t.Fatalf("Brazilian players = %d; want 4", len(br))
	}
	if br[0].Name != "Neymar Jr" {
		t.Fatalf("top Brazilian = %s; want Neymar Jr", br[0].Name)
	}
	for i := 1; i < len(br); i++ {
		if br[i-1].Overall < br[i].Overall {
			t.Fatalf("players not sorted by overall")
		}
	}

	// Players at Flamengo.
	fla := e.SearchPlayers(PlayerFilter{Club: "Flamengo"})
	if len(fla) != 2 {
		t.Fatalf("Flamengo players = %d; want 2", len(fla))
	}

	// Forwards only, with a minimum rating.
	st := e.SearchPlayers(PlayerFilter{Position: "ST", MinOverall: 82})
	if len(st) != 1 || st[0].Name != "Gabriel Barbosa" {
		t.Fatalf("filtered forwards = %+v; want only Gabriel Barbosa", st)
	}
}

func TestSearchPlayers_ByName(t *testing.T) {
	// Scenario: Simple lookup "Who is Gabriel Barbosa?"
	e := syntheticEngine()
	got := e.SearchPlayers(PlayerFilter{Name: "gabriel"})
	if len(got) != 1 || got[0].Name != "Gabriel Barbosa" {
		t.Fatalf("name search = %+v; want Gabriel Barbosa", got)
	}
}

// --- Integration tests against the real datasets ---------------------------

func realEngine(t *testing.T) *Engine {
	t.Helper()
	dir := filepath.Join("..", "..", "data", "kaggle")
	db, err := data.Load(dir)
	if err != nil {
		t.Skipf("real data unavailable: %v", err)
	}
	return New(db)
}

func TestIntegration_Brasileirao2019Champion(t *testing.T) {
	// Scenario: "Who won the 2019 Brasileirão?"
	e := realEngine(t)
	table := e.Standings("Brasileirão", 2019)
	if len(table) == 0 {
		t.Skip("no 2019 data")
	}
	// Then Flamengo are champions with 90 points (well-known result).
	champ := table[0]
	if !strings.Contains(strings.ToLower(champ.Team), "flamengo") {
		t.Fatalf("2019 champion = %q; want Flamengo", champ.Team)
	}
	if champ.Points() != 90 {
		t.Fatalf("2019 Flamengo points = %d; want 90", champ.Points())
	}
}

func TestIntegration_BrazilianPlayersExist(t *testing.T) {
	// Scenario: "Find all Brazilian players in the dataset"
	e := realEngine(t)
	br := e.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: 5})
	if len(br) == 0 {
		t.Fatal("expected Brazilian players")
	}
	// Sorted by overall, the top Brazilian should be highly rated.
	if br[0].Overall < 85 {
		t.Fatalf("top Brazilian overall = %d; expected >= 85", br[0].Overall)
	}
}

func TestIntegration_AverageGoalsReasonable(t *testing.T) {
	// Scenario: "What's the average goals per match in the Brasileirão?"
	e := realEngine(t)
	cs := e.CompetitionStats("Brasileirão", 0, 5)
	if cs.Matches == 0 {
		t.Skip("no Brasileirão data")
	}
	// Brazilian league football averages roughly 2.2–2.8 goals/game.
	if cs.AvgGoalsPerGame < 2.0 || cs.AvgGoalsPerGame > 3.0 {
		t.Fatalf("avg goals/game = %.2f; outside plausible range", cs.AvgGoalsPerGame)
	}
}
