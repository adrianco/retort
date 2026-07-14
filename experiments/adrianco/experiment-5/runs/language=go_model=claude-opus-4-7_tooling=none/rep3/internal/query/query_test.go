package query_test

import (
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/adrian/brazilian-soccer-mcp/internal/data"
	"github.com/adrian/brazilian-soccer-mcp/internal/query"
)

var (
	dsOnce sync.Once
	dsVal  *data.Dataset
	dsErr  error
)

func dataset(t *testing.T) *data.Dataset {
	t.Helper()
	dsOnce.Do(func() {
		abs, err := filepath.Abs("../../data/kaggle")
		if err != nil {
			dsErr = err
			return
		}
		dsVal, dsErr = data.LoadAll(abs)
	})
	if dsErr != nil {
		t.Fatalf("loading dataset: %v", dsErr)
	}
	return dsVal
}

// Feature: Match Queries
// Scenario: Find matches between two teams
//   Given the match data is loaded
//   When I search for matches between Flamengo and Fluminense
//   Then I should receive at least one match and each match references both
func TestFindMatchesBetweenTwoTeams(t *testing.T) {
	ds := dataset(t)
	start := time.Now()
	matches := query.FindMatches(ds, query.MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
	if elapsed := time.Since(start); elapsed > 2*time.Second {
		t.Errorf("query took %v, exceeds 2s budget", elapsed)
	}
	if len(matches) == 0 {
		t.Fatalf("no matches between Flamengo and Fluminense found")
	}
	for _, m := range matches {
		home := strings.ToLower(m.HomeTeam)
		away := strings.ToLower(m.AwayTeam)
		hasFla := strings.Contains(home, "flamengo") || strings.Contains(away, "flamengo")
		hasFlu := strings.Contains(home, "fluminense") || strings.Contains(away, "fluminense")
		if !hasFla || !hasFlu {
			t.Fatalf("unexpected match without both teams: %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
}

// Feature: Match Queries
// Scenario: Filter by season and team
func TestFindMatchesBySeason(t *testing.T) {
	ds := dataset(t)
	matches := query.FindMatches(ds, query.MatchFilter{Team: "Palmeiras", Season: 2018})
	if len(matches) == 0 {
		t.Fatalf("no Palmeiras matches found in 2018")
	}
	for _, m := range matches {
		if m.Season != 2018 {
			t.Fatalf("season filter failed: got %d", m.Season)
		}
	}
}

// Feature: Team Queries
// Scenario: Get team statistics for a season
//   Given the match data is loaded
//   When I request statistics for Palmeiras in season 2018
//   Then I should receive wins, losses, draws, and goals
func TestTeamStatsByCompetitionSeason(t *testing.T) {
	ds := dataset(t)
	r := query.TeamStats(ds, "Palmeiras", "Brasileirão", 2018, "")
	if r.Matches == 0 {
		t.Fatalf("expected Palmeiras matches in 2018")
	}
	if r.Wins+r.Draws+r.Losses != r.Matches {
		t.Fatalf("inconsistent record: W%d D%d L%d but matches=%d", r.Wins, r.Draws, r.Losses, r.Matches)
	}
	if r.WinRate() < 0 || r.WinRate() > 100 {
		t.Fatalf("absurd win rate %.2f", r.WinRate())
	}
}

// Feature: Team Queries
// Scenario: Home record only
func TestTeamStatsHomeOnly(t *testing.T) {
	ds := dataset(t)
	r := query.TeamStats(ds, "Corinthians", "Brasileirão", 2018, "home")
	if r.Matches == 0 {
		t.Fatalf("expected Corinthians home matches in 2018")
	}
}

// Feature: Head-to-Head
// Scenario: Compare Palmeiras and Santos
func TestHeadToHead(t *testing.T) {
	ds := dataset(t)
	h := query.ComputeHeadToHead(ds, "Palmeiras", "Santos")
	if h.TotalGames == 0 {
		t.Fatal("expected at least one Palmeiras-Santos match")
	}
	if h.AWins+h.BWins+h.Draws != h.TotalGames {
		t.Fatalf("h2h totals mismatch: A%d B%d D%d total %d", h.AWins, h.BWins, h.Draws, h.TotalGames)
	}
}

// Feature: Player Queries
// Scenario: Find Brazilian players
func TestPlayersByNationality(t *testing.T) {
	ds := dataset(t)
	players := query.SearchPlayers(ds, query.PlayerFilter{Nationality: "Brazil", Limit: 50})
	if len(players) == 0 {
		t.Fatal("expected Brazilian players")
	}
	for _, p := range players {
		if !strings.EqualFold(p.Nationality, "Brazil") {
			t.Fatalf("nationality filter leaked: %q", p.Nationality)
		}
	}
	// sorted by Overall desc
	for i := 1; i < len(players); i++ {
		if players[i-1].Overall < players[i].Overall {
			t.Fatalf("players not sorted by Overall desc: %d then %d", players[i-1].Overall, players[i].Overall)
		}
	}
}

// Feature: Player Queries
// Scenario: Search by name
func TestPlayersByName(t *testing.T) {
	ds := dataset(t)
	players := query.SearchPlayers(ds, query.PlayerFilter{NameContains: "Neymar", Limit: 5})
	if len(players) == 0 {
		t.Skip("Neymar not present in FIFA dataset shipped with repo")
	}
	for _, p := range players {
		if !strings.Contains(strings.ToLower(p.Name), "neymar") {
			t.Fatalf("name filter leaked: %q", p.Name)
		}
	}
}

// Feature: Competition Queries
// Scenario: Compute standings for a season
func TestStandings(t *testing.T) {
	ds := dataset(t)
	start := time.Now()
	rows := query.Standings(ds, "Brasileirão", 2018)
	if elapsed := time.Since(start); elapsed > 5*time.Second {
		t.Errorf("standings took %v, exceeds 5s budget", elapsed)
	}
	if len(rows) == 0 {
		t.Fatal("no standings produced")
	}
	for i := 1; i < len(rows); i++ {
		if rows[i-1].Points < rows[i].Points {
			t.Fatalf("standings not sorted by points: %d then %d", rows[i-1].Points, rows[i].Points)
		}
	}
	for i, r := range rows {
		if r.Position != i+1 {
			t.Fatalf("standings position %d != %d at index %d", r.Position, i+1, i)
		}
	}
}

// Feature: Statistical Analysis
// Scenario: Average goals across a season
func TestAggregateStats(t *testing.T) {
	ds := dataset(t)
	s := query.AggregateStats(ds, "Brasileirão", 2018)
	if s.Matches == 0 {
		t.Fatal("expected non-zero matches")
	}
	if s.AvgGoals <= 0 || s.AvgGoals > 6 {
		t.Fatalf("unexpected avg goals: %.2f", s.AvgGoals)
	}
	if total := s.HomeWins + s.AwayWins + s.Draws; total != s.Matches {
		t.Fatalf("results don't sum to matches: %d != %d", total, s.Matches)
	}
}

// Feature: Statistical Analysis
// Scenario: Biggest victories
func TestBiggestWins(t *testing.T) {
	ds := dataset(t)
	matches := query.BiggestWins(ds, "", 5)
	if len(matches) != 5 {
		t.Fatalf("expected 5 matches, got %d", len(matches))
	}
	for i := 1; i < len(matches); i++ {
		prev := absInt(matches[i-1].HomeGoal - matches[i-1].AwayGoal)
		cur := absInt(matches[i].HomeGoal - matches[i].AwayGoal)
		if prev < cur {
			t.Fatalf("biggest wins not sorted by margin")
		}
	}
}

func absInt(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
