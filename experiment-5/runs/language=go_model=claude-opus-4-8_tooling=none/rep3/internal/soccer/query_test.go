// Context: Behaviour-Driven (Given/When/Then) tests for the query engine,
// mirroring the Gherkin scenarios and "Required Capabilities" in TASK.md. They
// load the real bundled datasets so they also serve as integration coverage.
package soccer

import (
	"strings"
	"sync"
	"testing"
)

var (
	testStoreOnce sync.Once
	testStore     *Store
)

// loadTestStore loads the bundled datasets once for all tests.
func loadTestStore(t *testing.T) *Store {
	t.Helper()
	testStoreOnce.Do(func() {
		s, err := LoadStore("../../data/kaggle")
		if err != nil {
			t.Fatalf("Given the datasets, loading failed: %v", err)
		}
		testStore = s
	})
	if testStore == nil || len(testStore.Matches) == 0 {
		t.Fatal("Given the datasets, the store is empty")
	}
	return testStore
}

// Feature: data loading.
func TestScenario_AllDatasetsLoad(t *testing.T) {
	// Given the six CSV files
	s := loadTestStore(t)
	// When the store is loaded
	// Then matches and players are available
	if len(s.Matches) < 10000 {
		t.Errorf("expected >10000 matches, got %d", len(s.Matches))
	}
	if len(s.Players) < 18000 {
		t.Errorf("expected ~18207 players, got %d", len(s.Players))
	}
	// And every canonical competition is represented
	for _, comp := range []string{CompBrasileirao, CompCopaBrasil, CompLibertadores} {
		found := false
		for _, m := range s.Matches {
			if m.Competition == comp {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("competition %q has no matches", comp)
		}
	}
}

// Feature: Match Queries — Scenario: Find matches between two teams.
func TestScenario_MatchesBetweenTwoTeams(t *testing.T) {
	// Given the match data is loaded
	s := loadTestStore(t)
	// When I search for matches between "Flamengo" and "Fluminense"
	matches := s.SearchMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
	// Then I should receive a list of matches
	if len(matches) == 0 {
		t.Fatal("expected Fla-Flu matches, got none")
	}
	// And each match should have date, scores and competition
	for _, m := range matches {
		if m.DateStr == "" {
			t.Errorf("match missing date: %+v", m)
		}
		if m.Competition == "" {
			t.Errorf("match missing competition: %+v", m)
		}
		// And only Flamengo/Fluminense fixtures are returned
		flaHome := matchesQuery(m.HomeKey, "Flamengo")
		flaAway := matchesQuery(m.AwayKey, "Flamengo")
		fluHome := matchesQuery(m.HomeKey, "Fluminense")
		fluAway := matchesQuery(m.AwayKey, "Fluminense")
		if !((flaHome && fluAway) || (fluHome && flaAway)) {
			t.Errorf("unexpected fixture in Fla-Flu search: %s", FormatMatch(m))
		}
	}
}

// Feature: Match Queries — Scenario: matches by team and season.
func TestScenario_MatchesByTeamAndSeason(t *testing.T) {
	s := loadTestStore(t)
	// When I ask what matches Palmeiras played in 2019
	matches := s.SearchMatches(MatchFilter{Team: "Palmeiras", Season: 2019})
	// Then every result is from 2019 and involves Palmeiras
	if len(matches) == 0 {
		t.Fatal("expected Palmeiras 2019 matches")
	}
	for _, m := range matches {
		if m.Season != 2019 {
			t.Errorf("season filter leaked: %s", FormatMatch(m))
		}
		if !matchesQuery(m.HomeKey, "Palmeiras") && !matchesQuery(m.AwayKey, "Palmeiras") {
			t.Errorf("team filter leaked: %s", FormatMatch(m))
		}
	}
}

// Feature: Match Queries — Scenario: venue restriction.
func TestScenario_VenueRestriction(t *testing.T) {
	s := loadTestStore(t)
	// When I ask for Corinthians home matches in 2022
	matches := s.SearchMatches(MatchFilter{Team: "Corinthians", Season: 2022, Venue: "home"})
	if len(matches) == 0 {
		t.Fatal("expected Corinthians 2022 home matches")
	}
	// Then Corinthians is always the home side
	for _, m := range matches {
		if !matchesQuery(m.HomeKey, "Corinthians") {
			t.Errorf("venue=home leaked an away match: %s", FormatMatch(m))
		}
	}
}

// Feature: Team Queries — Scenario: get team statistics.
func TestScenario_TeamStatistics(t *testing.T) {
	// Given the match data is loaded
	s := loadTestStore(t)
	// When I request statistics for Corinthians home record in 2022 Brasileirão
	rec := s.TeamStats("Corinthians", MatchFilter{Season: 2022, Competition: CompBrasileirao, Venue: "home"})
	// Then I receive wins, losses, draws and goals that are internally consistent
	if rec.Matches == 0 {
		t.Fatal("expected a non-empty team record")
	}
	if rec.Wins+rec.Draws+rec.Losses != rec.Matches {
		t.Errorf("W+D+L (%d) != matches (%d)", rec.Wins+rec.Draws+rec.Losses, rec.Matches)
	}
	if rec.Points() != rec.Wins*3+rec.Draws {
		t.Errorf("points mismatch")
	}
	if rec.WinRate() < 0 || rec.WinRate() > 100 {
		t.Errorf("win rate out of range: %f", rec.WinRate())
	}
}

// Feature: Statistical Analysis — Scenario: head-to-head record.
func TestScenario_HeadToHead(t *testing.T) {
	s := loadTestStore(t)
	// When I compare Flamengo and Fluminense head-to-head
	h := s.HeadToHead("Flamengo", "Fluminense", MatchFilter{})
	// Then the wins/draws sum to the number of meetings
	if len(h.Matches) == 0 {
		t.Fatal("expected head-to-head meetings")
	}
	if h.AWins+h.BWins+h.Draws != len(h.Matches) {
		t.Errorf("A+B+draws (%d) != matches (%d)", h.AWins+h.BWins+h.Draws, len(h.Matches))
	}
	// And the relationship is symmetric when the teams are swapped
	swapped := s.HeadToHead("Fluminense", "Flamengo", MatchFilter{})
	if swapped.AWins != h.BWins || swapped.BWins != h.AWins || swapped.Draws != h.Draws {
		t.Errorf("head-to-head not symmetric: %+v vs %+v", h, swapped)
	}
}

// Feature: Competition Queries — Scenario: standings reproduce the known 2019
// Brasileirão result (the example in TASK.md: Flamengo 90 pts, 28W 6D 4L).
func TestScenario_Standings2019Brasileirao(t *testing.T) {
	// Given the match data is loaded
	s := loadTestStore(t)
	// When I compute the 2019 Brasileirão standings
	table := s.Standings(MatchFilter{Competition: CompBrasileirao, Season: 2019})
	// Then there are 20 teams
	if len(table) != 20 {
		t.Fatalf("expected 20 teams in 2019 Brasileirão, got %d", len(table))
	}
	// And Flamengo are champions with 90 points (28W, 6D, 4L)
	champ := table[0]
	if normKey(champ.Team) != normKey("Flamengo") {
		t.Errorf("expected Flamengo champion, got %q", champ.Team)
	}
	if champ.Points() != 90 || champ.Wins != 28 || champ.Draws != 6 || champ.Losses != 4 {
		t.Errorf("expected 90 pts (28W 6D 4L), got %d pts (%dW %dD %dL)",
			champ.Points(), champ.Wins, champ.Draws, champ.Losses)
	}
	// And each team played 38 matches
	for _, r := range table {
		if r.Matches != 38 {
			t.Errorf("%s played %d matches, expected 38", r.Team, r.Matches)
		}
	}
}

// Feature: Statistical Analysis — Scenario: aggregate competition statistics.
func TestScenario_CompetitionStats2019(t *testing.T) {
	s := loadTestStore(t)
	// When I compute 2019 Brasileirão aggregate stats
	c := s.CompetitionStats(MatchFilter{Competition: CompBrasileirao, Season: 2019})
	// Then there are 380 matches (38 rounds × 10)
	if c.Matches != 380 {
		t.Errorf("expected 380 matches, got %d", c.Matches)
	}
	// And the average goals per match is realistic
	if c.AvgGoals() < 2.0 || c.AvgGoals() > 3.0 {
		t.Errorf("avg goals out of expected range: %.2f", c.AvgGoals())
	}
	// And the outcome rates sum to ~100%
	sum := c.HomeWinRate() + c.AwayWinRate() + c.DrawRate()
	if sum < 99.9 || sum > 100.1 {
		t.Errorf("win/draw rates sum to %.2f, expected 100", sum)
	}
}

// Feature: Statistical Analysis — Scenario: biggest wins are sorted by margin.
func TestScenario_BiggestWins(t *testing.T) {
	s := loadTestStore(t)
	wins := s.BiggestWins(MatchFilter{Competition: CompBrasileirao}, 10)
	if len(wins) == 0 {
		t.Fatal("expected biggest-win results")
	}
	prev := 999
	for _, m := range wins {
		margin := abs(m.HomeGoal - m.AwayGoal)
		if margin > prev {
			t.Errorf("biggest wins not sorted by margin: %d after %d", margin, prev)
		}
		prev = margin
	}
	if abs(wins[0].HomeGoal-wins[0].AwayGoal) < 4 {
		t.Errorf("top result margin unexpectedly small: %s", FormatMatch(wins[0]))
	}
}

// Feature: Player Queries — Scenario: search Brazilian players, sorted by rating.
func TestScenario_BrazilianPlayers(t *testing.T) {
	// Given the player data is loaded
	s := loadTestStore(t)
	// When I search for Brazilian players
	players := s.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: 5})
	// Then I receive a ranked list led by Neymar Jr (Overall 92)
	if len(players) == 0 {
		t.Fatal("expected Brazilian players")
	}
	if players[0].Overall != 92 {
		t.Errorf("expected top Brazilian Overall 92, got %d (%s)", players[0].Overall, players[0].Name)
	}
	// And the list is sorted by Overall descending
	for i := 1; i < len(players); i++ {
		if players[i].Overall > players[i-1].Overall {
			t.Errorf("players not sorted by overall")
		}
		if players[i].Nationality != "Brazil" {
			t.Errorf("nationality filter leaked: %s", players[i].Nationality)
		}
	}
}

// Feature: Player Queries — Scenario: search by name.
func TestScenario_PlayerByName(t *testing.T) {
	s := loadTestStore(t)
	// When I search for "Gabriel"
	players := s.SearchPlayers(PlayerFilter{Name: "Gabriel"})
	// Then I get players whose name contains Gabriel
	if len(players) == 0 {
		t.Fatal("expected players named Gabriel")
	}
	for _, p := range players {
		if !containsFold(p.Name, "Gabriel") {
			t.Errorf("name filter leaked: %s", p.Name)
		}
	}
}

// Feature: Player Queries — Scenario: players at a Brazilian club (cross-file
// capability with min-rating filter).
func TestScenario_PlayersByClub(t *testing.T) {
	s := loadTestStore(t)
	// When I look for Flamengo players rated 70+
	players := s.SearchPlayers(PlayerFilter{Club: "Flamengo", MinOverall: 70})
	if len(players) == 0 {
		t.Skip("no Flamengo players >=70 in this FIFA snapshot")
	}
	for _, p := range players {
		if p.Overall < 70 {
			t.Errorf("min_overall leaked: %d", p.Overall)
		}
		if !matchesQuery(p.ClubKey, "Flamengo") {
			t.Errorf("club filter leaked: %s", p.Club)
		}
	}
}

// containsFold is an accent/case-insensitive substring check used by tests.
func containsFold(s, sub string) bool {
	return strings.Contains(strings.ToLower(foldAccents(s)), strings.ToLower(foldAccents(sub)))
}
