// Context:
//   - BDD-style (Given/When/Then) tests for the loader and the query layer,
//     exercised against the real bundled Kaggle CSV files. They cover the five
//     capability areas in the specification: loading, match search, head-to-head,
//     team statistics, computed standings, league aggregates and player search.
//   - The 2019 Brasileirão Série A is used as a gold-standard fixture because its
//     final table is publicly known (Flamengo champion on 90 points with a
//     28-6-4 record), which lets us assert exact, meaningful numbers.
//   - The store is loaded once and shared across tests for speed.
package soccer

import (
	"path/filepath"
	"strings"
	"sync"
	"testing"
)

const testDataDir = "../../data/kaggle"

var (
	sharedStore *Store
	loadOnce    sync.Once
	loadErr     error
)

// store loads (once) and returns the shared store, skipping the test if the
// data files are not present.
func store(t *testing.T) *Store {
	t.Helper()
	loadOnce.Do(func() {
		sharedStore, loadErr = Load(testDataDir)
	})
	if loadErr != nil {
		t.Fatalf("loading data: %v", loadErr)
	}
	if sharedStore == nil || len(sharedStore.Matches) == 0 {
		t.Skipf("no data available at %s", filepath.Clean(testDataDir))
	}
	return sharedStore
}

func TestLoad_AllSourcesAndPlayers(t *testing.T) {
	// Given the bundled datasets
	s := store(t)

	// When loaded
	// Then a substantial number of matches and the full player set are present
	if len(s.Matches) < 10000 {
		t.Errorf("expected >10000 matches, got %d", len(s.Matches))
	}
	if len(s.Players) != 18207 {
		t.Errorf("expected 18207 players, got %d", len(s.Players))
	}

	// And all five canonical competitions are represented
	want := map[string]bool{
		CompSerieA: false, CompSerieB: false, CompSerieC: false,
		CompCopaDoBrasil: false, CompLibertadores: false,
	}
	for _, c := range s.Competitions() {
		if _, ok := want[c]; ok {
			want[c] = true
		}
	}
	for c, seen := range want {
		if !seen {
			t.Errorf("competition %q missing from loaded data", c)
		}
	}
}

func TestSearchMatches_BetweenTwoTeams(t *testing.T) {
	// Given the loaded match data
	s := store(t)

	// When searching for matches between Flamengo and Fluminense
	matches := s.SearchMatches(MatchQuery{Team: "Flamengo", Opponent: "Fluminense"})

	// Then a non-empty list is returned
	if len(matches) == 0 {
		t.Fatal("expected Fla-Flu matches, got none")
	}
	// And every match actually involves both teams
	for _, m := range matches {
		flHome := TeamMatches("Flamengo", m.HomeNorm)
		flAway := TeamMatches("Flamengo", m.AwayNorm)
		fluHome := TeamMatches("Fluminense", m.HomeNorm)
		fluAway := TeamMatches("Fluminense", m.AwayNorm)
		if !((flHome && fluAway) || (flAway && fluHome)) {
			t.Errorf("match does not involve both teams: %s", m.Line())
		}
	}
}

func TestSearchMatches_FilterBySeasonAndVenue(t *testing.T) {
	// Given the loaded match data
	s := store(t)

	// When searching Palmeiras home matches in the 2019 Série A
	matches := s.SearchMatches(MatchQuery{
		Team: "Palmeiras", Season: 2019, Competition: CompSerieA, Venue: "home",
	})

	// Then there are results and each is a 2019 Série A home game for Palmeiras
	if len(matches) == 0 {
		t.Fatal("expected Palmeiras 2019 home matches")
	}
	for _, m := range matches {
		if m.Season != 2019 || m.Competition != CompSerieA {
			t.Errorf("unexpected match: %s", m.Line())
		}
		if !TeamMatches("Palmeiras", m.HomeNorm) {
			t.Errorf("expected Palmeiras at home: %s", m.Line())
		}
	}
}

func TestHeadToHead_ConsistentRecord(t *testing.T) {
	// Given the loaded match data
	s := store(t)

	// When computing the Flamengo vs Fluminense head-to-head
	h := s.HeadToHead("Flamengo", "Fluminense")

	// Then there are matches and the W/D/L tallies are internally consistent
	if len(h.Matches) == 0 {
		t.Fatal("expected head-to-head matches")
	}
	played := 0
	for _, m := range h.Matches {
		if m.HasScore {
			played++
		}
	}
	if h.Team1Wins+h.Team2Wins+h.Draws != played {
		t.Errorf("W+D+L (%d) != played matches (%d)",
			h.Team1Wins+h.Team2Wins+h.Draws, played)
	}
}

func TestTeamStats_PointsAndWinRate(t *testing.T) {
	// Given the loaded match data
	s := store(t)

	// When requesting Flamengo's 2019 Série A record
	rec := s.TeamStats("Flamengo", 2019, CompSerieA, "")

	// Then it equals the publicly known champion record: 38 games, 28-6-4, 90 pts
	if rec.Played != 38 {
		t.Errorf("expected 38 matches, got %d", rec.Played)
	}
	if rec.Wins != 28 || rec.Draws != 6 || rec.Losses != 4 {
		t.Errorf("expected 28-6-4, got %d-%d-%d", rec.Wins, rec.Draws, rec.Losses)
	}
	if rec.Points() != 90 {
		t.Errorf("expected 90 points, got %d", rec.Points())
	}
	if rec.WinRate() <= 0.7 {
		t.Errorf("expected win rate >70%%, got %.1f%%", rec.WinRate()*100)
	}
}

func TestStandings_2019SerieAChampion(t *testing.T) {
	// Given the loaded match data
	s := store(t)

	// When computing the 2019 Série A table
	table := s.Standings(CompSerieA, 2019)

	// Then there are 20 teams and Flamengo is champion on 90 points
	if len(table) != 20 {
		t.Fatalf("expected 20 teams, got %d", len(table))
	}
	champ := table[0]
	if champ.Team != "Flamengo" {
		t.Errorf("expected champion Flamengo, got %q", champ.Team)
	}
	if champ.Points() != 90 {
		t.Errorf("expected champion on 90 points, got %d", champ.Points())
	}
	// And the table is sorted by points (non-increasing)
	for i := 1; i < len(table); i++ {
		if table[i-1].Points() < table[i].Points() {
			t.Errorf("table not sorted by points at row %d", i)
		}
	}
}

func TestLeagueAggregate_SaneAverages(t *testing.T) {
	// Given the loaded match data
	s := store(t)

	// When aggregating the 2019 Série A
	stats := s.LeagueAggregate(CompSerieA, 2019, 5)

	// Then it covers a full season and reports plausible figures
	if stats.Matches != 380 {
		t.Errorf("expected 380 matches in 2019 Série A, got %d", stats.Matches)
	}
	if stats.AvgGoals() < 1.5 || stats.AvgGoals() > 4.0 {
		t.Errorf("implausible average goals per match: %.2f", stats.AvgGoals())
	}
	if stats.HomeWinRate() <= 0 || stats.HomeWinRate() >= 1 {
		t.Errorf("implausible home win rate: %.2f", stats.HomeWinRate())
	}
	// And the biggest wins are sorted by goal margin
	for i := 1; i < len(stats.BiggestWins); i++ {
		prev := abs(stats.BiggestWins[i-1].HomeGoals - stats.BiggestWins[i-1].AwayGoals)
		cur := abs(stats.BiggestWins[i].HomeGoals - stats.BiggestWins[i].AwayGoals)
		if prev < cur {
			t.Errorf("biggest wins not sorted by margin at %d", i)
		}
	}
}

func TestSearchPlayers_TopBrazilian(t *testing.T) {
	// Given the loaded player data
	s := store(t)

	// When searching Brazilian players sorted by rating
	players := s.SearchPlayers(PlayerQuery{Nationality: "Brazil", Limit: 5})

	// Then there are results led by the highest-rated Brazilian, Neymar
	if len(players) == 0 {
		t.Fatal("expected Brazilian players")
	}
	if players[0].Name != "Neymar Jr" {
		t.Errorf("expected top Brazilian to be Neymar Jr, got %q", players[0].Name)
	}
	// And the list is sorted by overall rating (non-increasing)
	for i := 1; i < len(players); i++ {
		if players[i-1].Overall < players[i].Overall {
			t.Errorf("players not sorted by rating at %d", i)
		}
	}
}

func TestSearchPlayers_ByClubAndPosition(t *testing.T) {
	// Given the loaded player data
	s := store(t)

	// When filtering players at a Brazilian club present in the FIFA data
	// (the dataset is FIFA-19 era, which licenses Grêmio but not Flamengo).
	players := s.SearchPlayers(PlayerQuery{Club: "Grêmio", Limit: 50})

	// Then results exist and all belong to that club
	if len(players) == 0 {
		t.Fatal("expected players at Grêmio")
	}
	for _, p := range players {
		if !strings.Contains(normalizeText(p.Club), "gremio") {
			t.Errorf("player %q not at Grêmio (club=%q)", p.Name, p.Club)
		}
	}
}
