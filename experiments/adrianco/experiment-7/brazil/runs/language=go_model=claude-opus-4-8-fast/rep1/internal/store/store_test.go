// Package store tests — BDD-style (Given/When/Then) scenarios covering data
// loading and the query/aggregation helpers.
//
// Context:
//   - Tests load the real bundled datasets from ../../data/kaggle once (shared
//     across scenarios via loadOnce) since loading is read-only.
//   - Each test function maps to a Gherkin-style scenario; comments mark the
//     Given/When/Then phases described in TASK.md's "Testing Approach".
package store

import (
	"path/filepath"
	"sync"
	"testing"
	"time"
)

var (
	sharedStore *Store
	loadErr     error
	once        sync.Once
)

// loadOnce loads the bundled datasets a single time for all scenarios.
func loadOnce(t *testing.T) *Store {
	t.Helper()
	once.Do(func() {
		sharedStore, loadErr = Load(filepath.Join("..", "..", "data", "kaggle"))
	})
	if loadErr != nil {
		t.Fatalf("Given the datasets, loading failed: %v", loadErr)
	}
	return sharedStore
}

// Scenario: All six datasets load into queryable collections.
func TestScenario_LoadAllDatasets(t *testing.T) {
	// Given the bundled Kaggle CSV files
	// When the store is loaded
	s := loadOnce(t)
	// Then matches and players are populated (count is post-deduplication)
	if len(s.Matches) < 14000 {
		t.Errorf("Then matches should be loaded; got %d (want >= 14000)", len(s.Matches))
	}
	if len(s.Players) < 18000 {
		t.Errorf("Then players should be loaded; got %d (want >= 18000)", len(s.Players))
	}
	// And every competition label appears
	comps := map[string]bool{}
	for _, m := range s.Matches {
		comps[m.Competition] = true
	}
	for _, want := range []string{CompBrasileirao, CompCopaDoBrasil, CompLibertadores} {
		if !comps[want] {
			t.Errorf("Then competition %q should be present", want)
		}
	}
}

// Scenario: Find matches between two teams (Fla-Flu derby).
func TestScenario_FindMatchesBetweenTwoTeams(t *testing.T) {
	// Given the match data is loaded
	s := loadOnce(t)
	// When I search for matches between Flamengo and Fluminense
	matches := s.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"}, 0)
	// Then I should receive a non-empty list
	if len(matches) == 0 {
		t.Fatal("Then there should be Fla-Flu matches in the dataset")
	}
	// And each match involves both teams
	for _, m := range matches {
		flaInvolved := TeamMatches(m.HomeTeam, "Flamengo") || TeamMatches(m.AwayTeam, "Flamengo")
		fluInvolved := TeamMatches(m.HomeTeam, "Fluminense") || TeamMatches(m.AwayTeam, "Fluminense")
		if !flaInvolved || !fluInvolved {
			t.Errorf("Then each match should involve both teams; got %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
}

// Scenario: Filter matches by season.
func TestScenario_FindMatchesBySeason(t *testing.T) {
	// Given the match data is loaded
	s := loadOnce(t)
	// When I search for Palmeiras matches in 2019
	matches := s.FindMatches(MatchFilter{Team: "Palmeiras", Season: 2019}, 0)
	// Then there should be results, all from 2019
	if len(matches) == 0 {
		t.Fatal("Then Palmeiras should have 2019 matches")
	}
	for _, m := range matches {
		if m.Season != 2019 {
			t.Errorf("Then every match should be from 2019; got %d", m.Season)
		}
	}
}

// Scenario: Matches are returned most-recent first.
func TestScenario_FindMatchesSortedByDate(t *testing.T) {
	// Given the match data is loaded
	s := loadOnce(t)
	// When I list Corinthians matches
	matches := s.FindMatches(MatchFilter{Team: "Corinthians"}, 50)
	// Then dated matches are in descending order
	var prev time.Time
	first := true
	for _, m := range matches {
		if !m.HasDate {
			continue
		}
		if !first && m.Date.After(prev) {
			t.Errorf("Then matches should be newest-first; %s came after %s", m.Date, prev)
		}
		prev = m.Date
		first = false
	}
}

// Scenario: Head-to-head record sums to total meetings.
func TestScenario_HeadToHead(t *testing.T) {
	// Given the match data is loaded
	s := loadOnce(t)
	// When I request the head-to-head between Palmeiras and Santos
	rec, matches := s.HeadToHead("Palmeiras", "Santos")
	// Then there are meetings and the record is internally consistent
	if len(matches) == 0 {
		t.Fatal("Then Palmeiras and Santos should have met")
	}
	if rec.Wins+rec.Draws+rec.Losses != rec.Matches {
		t.Errorf("Then W+D+L (%d) should equal matches (%d)", rec.Wins+rec.Draws+rec.Losses, rec.Matches)
	}
	if rec.Matches == 0 {
		t.Error("Then scored meetings should be counted")
	}
}

// Scenario: Team statistics report wins, losses, draws and goals.
func TestScenario_TeamStats(t *testing.T) {
	// Given the match data is loaded
	s := loadOnce(t)
	// When I request statistics for Flamengo in 2019 Brasileirão
	rec := s.TeamStats("Flamengo", CompBrasileirao, 2019, VenueAll)
	// Then a full record is returned
	if rec.Matches == 0 {
		t.Fatal("Then Flamengo should have 2019 Brasileirão matches")
	}
	if rec.Wins+rec.Draws+rec.Losses != rec.Matches {
		t.Errorf("Then W+D+L should equal matches; got %d vs %d", rec.Wins+rec.Draws+rec.Losses, rec.Matches)
	}
	// And the home subset never exceeds the full set
	home := s.TeamStats("Flamengo", CompBrasileirao, 2019, VenueHome)
	if home.Matches > rec.Matches {
		t.Errorf("Then home matches (%d) cannot exceed all matches (%d)", home.Matches, rec.Matches)
	}
}

// Scenario: 2019 Brasileirão standings crown Flamengo as champion.
func TestScenario_Standings2019Champion(t *testing.T) {
	// Given the match data is loaded
	s := loadOnce(t)
	// When I compute the 2019 Brasileirão standings
	table := s.Standings(CompBrasileirao, 2019)
	// Then there is a table and it is sorted by points descending
	if len(table) < 10 {
		t.Fatalf("Then a full table is expected; got %d teams", len(table))
	}
	for i := 1; i < len(table); i++ {
		if table[i-1].Points() < table[i].Points() {
			t.Errorf("Then table must be sorted by points; row %d (%d) < row %d (%d)",
				i-1, table[i-1].Points(), i, table[i].Points())
		}
	}
	// And the champion is Flamengo (historically true for 2019)
	if !TeamMatches(table[0].Team, "Flamengo") {
		t.Errorf("Then 2019 champion should be Flamengo; got %q", table[0].Team)
	}
}

// Scenario: Overlapping datasets are de-duplicated to a real season size.
func TestScenario_DedupYieldsRealSeasonSize(t *testing.T) {
	// Given the (overlapping) match data is loaded
	s := loadOnce(t)
	// When I count 2019 Brasileirão Série A fixtures
	matches := s.FindMatches(MatchFilter{Competition: CompBrasileirao, Season: 2019}, 0)
	// Then it is close to a real 20-team double round-robin (380), not a
	// multiple of it (the datasets overlap ~3x before dedup)
	if len(matches) < 380 || len(matches) > 400 {
		t.Errorf("Then 2019 Série A should be ~380 fixtures after dedup; got %d", len(matches))
	}
	// And the champion played ~38 games, not ~76
	rec := s.TeamStats("Flamengo", CompBrasileirao, 2019, VenueAll)
	if rec.Matches < 36 || rec.Matches > 40 {
		t.Errorf("Then Flamengo should have ~38 matches in 2019; got %d", rec.Matches)
	}
	if rec.Points() != 90 {
		t.Errorf("Then Flamengo 2019 should total 90 points (historical); got %d", rec.Points())
	}
}

// Scenario: Same-named clubs in different states stay distinct.
func TestScenario_StateDisambiguation(t *testing.T) {
	// Given the team-name keys are state-aware
	// When two Atlético clubs in different states are keyed
	mg := TeamKey("Atletico-MG", "MG")
	pr := TeamKey("Athletico-PR", "PR")
	// Then they do not collide
	if mg == pr {
		t.Errorf("Then Atlético-MG and Athletico-PR must differ; both = %q", mg)
	}
	// And spelling variants of the same club do collide
	if TeamKey("Vasco", "RJ") != TeamKey("Vasco da Gama-RJ", "RJ") {
		t.Errorf("Then Vasco spellings should share a key; got %q vs %q",
			TeamKey("Vasco", "RJ"), TeamKey("Vasco da Gama-RJ", "RJ"))
	}
}

// Scenario: Competition statistics produce a plausible goal average.
func TestScenario_CompetitionStats(t *testing.T) {
	// Given the match data is loaded
	s := loadOnce(t)
	// When I aggregate Brasileirão statistics
	cs := s.CompetitionStats(CompBrasileirao, 0)
	// Then the average goals per match is in a realistic football range
	if cs.Matches == 0 {
		t.Fatal("Then there should be Brasileirão matches")
	}
	avg := cs.AvgGoals()
	if avg < 1.5 || avg > 4.0 {
		t.Errorf("Then avg goals/match should be ~2-3; got %.2f", avg)
	}
	// And home/away/draw counts sum to total matches
	if cs.HomeWins+cs.AwayWins+cs.Draws != cs.Matches {
		t.Errorf("Then result split should sum to matches; got %d vs %d",
			cs.HomeWins+cs.AwayWins+cs.Draws, cs.Matches)
	}
}

// Scenario: Biggest wins are sorted by goal margin.
func TestScenario_BiggestWins(t *testing.T) {
	// Given the match data is loaded
	s := loadOnce(t)
	// When I ask for the 5 biggest wins
	matches := s.BiggestWins("", 0, 5)
	// Then there are 5, ordered by descending margin
	if len(matches) != 5 {
		t.Fatalf("Then 5 matches expected; got %d", len(matches))
	}
	for i := 1; i < len(matches); i++ {
		if margin(matches[i-1]) < margin(matches[i]) {
			t.Errorf("Then margins should be non-increasing; %d < %d", margin(matches[i-1]), margin(matches[i]))
		}
	}
}

// Scenario: Find Brazilian players, top-rated first.
func TestScenario_SearchBrazilianPlayers(t *testing.T) {
	// Given the player data is loaded
	s := loadOnce(t)
	// When I search for Brazilian players
	players := s.SearchPlayers(PlayerFilter{Nationality: "Brazil"}, 10)
	// Then results are returned, all Brazilian, sorted by rating
	if len(players) == 0 {
		t.Fatal("Then there should be Brazilian players")
	}
	for i, p := range players {
		if !containsFold(p.Nationality, "Brazil") {
			t.Errorf("Then player %s should be Brazilian; got %q", p.Name, p.Nationality)
		}
		if i > 0 && players[i-1].Overall < p.Overall {
			t.Errorf("Then players should be sorted by rating desc")
		}
	}
	// And the top Brazilian is Neymar (rating 92 in this dataset)
	if !containsFold(players[0].Name, "Neymar") {
		t.Errorf("Then top Brazilian should be Neymar; got %q (%d)", players[0].Name, players[0].Overall)
	}
}

// Scenario: Find a specific player by name (Gabriel Barbosa lookup analog).
func TestScenario_SearchPlayerByName(t *testing.T) {
	// Given the player data is loaded
	s := loadOnce(t)
	// When I search for "Coutinho"
	players := s.SearchPlayers(PlayerFilter{Name: "Coutinho"}, 5)
	// Then at least one match is returned
	if len(players) == 0 {
		t.Fatal("Then Coutinho should be found")
	}
	if !containsFold(players[0].Name, "Coutinho") {
		t.Errorf("Then result should match the name; got %q", players[0].Name)
	}
}

// Scenario: Filter players by club.
func TestScenario_SearchPlayersByClub(t *testing.T) {
	// Given the player data is loaded
	s := loadOnce(t)
	// When I list players from FC Barcelona
	players := s.SearchPlayers(PlayerFilter{Club: "Barcelona"}, 30)
	// Then they all belong to a Barcelona club
	if len(players) == 0 {
		t.Fatal("Then Barcelona should have players")
	}
	for _, p := range players {
		if !containsFold(p.Club, "Barcelona") {
			t.Errorf("Then club should contain Barcelona; got %q", p.Club)
		}
	}
}
