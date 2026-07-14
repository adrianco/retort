// soccer_test.go - BDD (Given/When/Then) tests for the knowledge graph.
//
// Context
// -------
// These tests follow the Behaviour-Driven Development structure requested in the
// specification's Testing Approach section. Each test is written as a Given /
// When / Then scenario mapping directly onto the Gherkin features in the spec
// (match queries, team statistics, player search, standings, head-to-head and
// aggregate statistics).
//
// The datasets are loaded once from the repository's real data directory (found
// relative to this test file) and shared across scenarios. This also exercises
// the filesystem loading path that the -data flag uses.
package soccer

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// loadTestDB loads the real datasets relative to this source file so tests work
// regardless of the working directory.
func loadTestDB(t *testing.T) *DB {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot determine test file location")
	}
	dataDir := filepath.Join(filepath.Dir(file), "..", "..", "data", "kaggle")
	db, err := Load(os.DirFS(dataDir))
	if err != nil {
		t.Fatalf("Given the datasets, loading failed: %v", err)
	}
	return db
}

func TestLoad_AllDatasets(t *testing.T) {
	// Given the six CSV datasets
	// When the knowledge graph is loaded
	db := loadTestDB(t)

	// Then a substantial number of matches and players are available
	if len(db.Matches) < 10000 {
		t.Errorf("Then expected >10000 matches, got %d", len(db.Matches))
	}
	if len(db.Players) < 18000 {
		t.Errorf("Then expected >18000 players, got %d", len(db.Players))
	}
}

func TestLoad_ScoresAndDatesParsed(t *testing.T) {
	// Given the loaded matches
	db := loadTestDB(t)

	// When we inspect them
	scored, dated := 0, 0
	for _, m := range db.Matches {
		if m.HasScore {
			scored++
		}
		if m.HasDate {
			dated++
		}
	}

	// Then the vast majority have parseable scores and dates
	if scored < len(db.Matches)*9/10 {
		t.Errorf("Then expected >=90%% scored matches, got %d/%d", scored, len(db.Matches))
	}
	if dated < len(db.Matches)*9/10 {
		t.Errorf("Then expected >=90%% dated matches, got %d/%d", dated, len(db.Matches))
	}
}

func TestNormalize_TeamNameVariations(t *testing.T) {
	// Given several spellings of the same clubs
	cases := []struct{ raw, wantCanon string }{
		{"Palmeiras-SP", "Palmeiras"},
		{"Flamengo-RJ", "Flamengo"},
		{"América - MG", "América"},
		{"Nacional (URU)", "Nacional"},
		{"Barcelona-EQU", "Barcelona"},
		{"São Paulo", "São Paulo"},
	}
	for _, c := range cases {
		// When canonicalised
		got := CanonicalName(c.raw)
		// Then the suffix is stripped while accents are preserved
		if got != c.wantCanon {
			t.Errorf("CanonicalName(%q) = %q, want %q", c.raw, got, c.wantCanon)
		}
	}

	// And variants compare equal regardless of accents/suffixes
	if !NameMatches("Sao Paulo", "São Paulo-SP") {
		t.Error("Then 'Sao Paulo' should match 'São Paulo-SP'")
	}
	if !NameMatches("flamengo", "Flamengo-RJ") {
		t.Error("Then 'flamengo' should match 'Flamengo-RJ'")
	}
	if NameMatches("Palmeiras", "Santos") {
		t.Error("Then unrelated teams must not match")
	}
}

func TestMatchQuery_BetweenTwoTeams(t *testing.T) {
	// Given the match data is loaded
	db := loadTestDB(t)

	// When I search for matches between Flamengo and Fluminense
	matches := db.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})

	// Then I should receive a non-empty list
	if len(matches) == 0 {
		t.Fatal("Then expected at least one Fla-Flu match")
	}
	// And each match should involve both teams and carry date + scores
	for _, m := range matches {
		bothPresent := (NameMatches("Flamengo", m.HomeTeam) || NameMatches("Flamengo", m.AwayTeam)) &&
			(NameMatches("Fluminense", m.HomeTeam) || NameMatches("Fluminense", m.AwayTeam))
		if !bothPresent {
			t.Errorf("Then match %s does not involve both teams", FormatMatch(m))
		}
	}
	// And results are sorted most-recent-first
	for i := 1; i < len(matches); i++ {
		if matches[i-1].HasDate && matches[i].HasDate && matches[i-1].Date.Before(matches[i].Date) {
			t.Error("Then matches should be sorted descending by date")
			break
		}
	}
}

func TestMatchQuery_BySeasonAndCompetition(t *testing.T) {
	// Given the match data is loaded
	db := loadTestDB(t)

	// When I search Palmeiras matches in the 2019 Brasileirão
	matches := db.FindMatches(MatchFilter{Team: "Palmeiras", Season: 2019, Competition: CompBrasileirao})

	// Then results are non-empty and respect the filters
	if len(matches) == 0 {
		t.Fatal("Then expected Palmeiras 2019 Brasileirão matches")
	}
	for _, m := range matches {
		if m.Season != 2019 || m.Competition != CompBrasileirao {
			t.Errorf("Then match %s violates season/competition filter", FormatMatch(m))
		}
	}
}

func TestTeamStats_PalmeirasSeason(t *testing.T) {
	// Given the match data is loaded
	db := loadTestDB(t)

	// When I request statistics for Palmeiras in season 2019
	stats := db.ComputeTeamStats("Palmeiras", 2019, CompBrasileirao, "all")

	// Then I should receive wins, losses, draws and goals that are internally consistent
	if stats.Played == 0 {
		t.Fatal("Then expected a non-zero number of matches")
	}
	if stats.Wins+stats.Draws+stats.Losses != stats.Played {
		t.Errorf("Then W+D+L (%d) must equal played (%d)", stats.Wins+stats.Draws+stats.Losses, stats.Played)
	}
	if stats.GoalsFor < 0 || stats.GoalsAgainst < 0 {
		t.Error("Then goal tallies must be non-negative")
	}
	// And a 38-game season should yield ~38 matches
	if stats.Played < 30 {
		t.Errorf("Then expected a full season (~38 games), got %d", stats.Played)
	}
}

func TestTeamStats_HomeVenueSubset(t *testing.T) {
	// Given the match data is loaded
	db := loadTestDB(t)

	// When I compute all vs home-only records for Corinthians in 2019
	all := db.ComputeTeamStats("Corinthians", 2019, CompBrasileirao, "all")
	home := db.ComputeTeamStats("Corinthians", 2019, CompBrasileirao, "home")

	// Then home matches are a subset of all matches
	if home.Played == 0 || home.Played >= all.Played {
		t.Errorf("Then home played (%d) should be >0 and < all played (%d)", home.Played, all.Played)
	}
}

func TestHeadToHead_PalmeirasSantos(t *testing.T) {
	// Given the match data is loaded
	db := loadTestDB(t)

	// When I compare Palmeiras and Santos head-to-head
	r := db.HeadToHead("Palmeiras", "Santos", "")

	// Then the totals are consistent
	if r.Total == 0 {
		t.Fatal("Then expected several Palmeiras-Santos matches")
	}
	if r.AWins+r.BWins+r.Draws != r.Total {
		t.Errorf("Then wins+draws (%d) must equal total (%d)", r.AWins+r.BWins+r.Draws, r.Total)
	}
	if len(r.Matches) != r.Total {
		t.Errorf("Then match list length (%d) must equal total (%d)", len(r.Matches), r.Total)
	}
}

func TestPlayerQuery_BrazilianPlayers(t *testing.T) {
	// Given the FIFA player data is loaded
	db := loadTestDB(t)

	// When I filter for Brazilian players
	players := db.FindPlayers(PlayerFilter{Nationality: "Brazil"})

	// Then I should receive many players, all Brazilian, sorted by overall desc
	if len(players) < 500 {
		t.Fatalf("Then expected >500 Brazilian players, got %d", len(players))
	}
	for _, p := range players {
		if !strings.EqualFold(p.Nationality, "Brazil") {
			t.Errorf("Then player %s has nationality %q", p.Name, p.Nationality)
			break
		}
	}
	for i := 1; i < len(players); i++ {
		if players[i-1].Overall < players[i].Overall {
			t.Error("Then players must be sorted by overall descending")
			break
		}
	}
}

func TestPlayerQuery_ByName(t *testing.T) {
	// Given the FIFA player data is loaded
	db := loadTestDB(t)

	// When I search by a well-known name fragment
	players := db.FindPlayers(PlayerFilter{Name: "Neymar"})

	// Then at least one matching player is returned
	if len(players) == 0 {
		t.Fatal("Then expected to find Neymar")
	}
	if !strings.Contains(strings.ToLower(players[0].Name), "neymar") {
		t.Errorf("Then top result %q should contain 'neymar'", players[0].Name)
	}
}

func TestStandings_2019Brasileirao(t *testing.T) {
	// Given the match data is loaded
	db := loadTestDB(t)

	// When I compute the 2019 Brasileirão standings
	rows := db.Standings(CompBrasileirao, 2019)

	// Then a 20-team league table is produced
	if len(rows) != 20 {
		t.Fatalf("Then expected 20 teams, got %d", len(rows))
	}
	// And it is sorted by points (then goal difference) descending
	for i := 1; i < len(rows); i++ {
		a, b := rows[i-1], rows[i]
		if a.Points() < b.Points() {
			t.Error("Then standings must be sorted by points descending")
			break
		}
	}
	// And the 2019 champion is Flamengo (historical fact derivable from data)
	if !NameMatches("Flamengo", rows[0].Team) {
		t.Errorf("Then 2019 champion should be Flamengo, got %q", rows[0].Team)
	}
}

func TestStatistics_GoalAverages(t *testing.T) {
	// Given the match data is loaded
	db := loadTestDB(t)

	// When I aggregate goal statistics for the Brasileirão
	gs := db.GoalStatistics(MatchFilter{Competition: CompBrasileirao})

	// Then averages and rates are within sane football ranges
	if gs.Matches == 0 {
		t.Fatal("Then expected scored matches")
	}
	if gs.AvgGoals < 1.5 || gs.AvgGoals > 4.0 {
		t.Errorf("Then average goals per match (%.2f) is out of expected range", gs.AvgGoals)
	}
	rateSum := gs.HomeWinRate + gs.AwayWinRate + gs.DrawRate
	if rateSum < 0.99 || rateSum > 1.01 {
		t.Errorf("Then win/draw rates should sum to 1.0, got %.3f", rateSum)
	}
	if gs.HomeWinRate <= gs.AwayWinRate {
		t.Error("Then home advantage implies home win rate > away win rate")
	}
}

func TestStatistics_BiggestWins(t *testing.T) {
	// Given the match data is loaded
	db := loadTestDB(t)

	// When I ask for the biggest victories
	wins := db.BiggestWins(MatchFilter{}, 5)

	// Then I get up to 5 matches ordered by margin descending
	if len(wins) == 0 {
		t.Fatal("Then expected some lopsided matches")
	}
	for i := 1; i < len(wins); i++ {
		m1 := abs(wins[i-1].HomeGoals - wins[i-1].AwayGoals)
		m2 := abs(wins[i].HomeGoals - wins[i].AwayGoals)
		if m1 < m2 {
			t.Error("Then biggest wins must be sorted by margin descending")
			break
		}
	}
	// And the very biggest margin should be large
	top := abs(wins[0].HomeGoals - wins[0].AwayGoals)
	if top < 5 {
		t.Errorf("Then top margin (%d) seems too small", top)
	}
}

func TestStatistics_BestHomeRecord(t *testing.T) {
	// Given the match data is loaded
	db := loadTestDB(t)

	// When I ask for the best home records in the 2019 Brasileirão
	recs := db.BestRecords(CompBrasileirao, 2019, "home", 10, 3)

	// Then I receive a ranked, non-empty list by win rate
	if len(recs) == 0 {
		t.Fatal("Then expected best home records")
	}
	for i := 1; i < len(recs); i++ {
		if recs[i-1].WinRate() < recs[i].WinRate() {
			t.Error("Then best records must be sorted by win rate descending")
			break
		}
	}
}

func TestStandings_PrefersScoredSource(t *testing.T) {
	// Given that one dataset lists the 2022 Brasileirão with blank scores while
	// another carries the real results
	db := loadTestDB(t)

	// When I compute the 2022 standings
	rows := db.Standings(CompBrasileirao, 2022)

	// Then a complete 20-team table with real points is produced (the scored
	// source was selected) and the champion is Palmeiras
	if len(rows) != 20 {
		t.Fatalf("Then expected 20 teams, got %d", len(rows))
	}
	if rows[0].Points() < 70 {
		t.Errorf("Then champion should have a realistic points tally, got %d", rows[0].Points())
	}
	if !NameMatches("Palmeiras", rows[0].Team) {
		t.Errorf("Then 2022 champion should be Palmeiras, got %q", rows[0].Team)
	}
	// And a full home record spans ~19 games
	home := db.ComputeTeamStats("Corinthians", 2022, CompBrasileirao, "home")
	if home.Played < 18 {
		t.Errorf("Then Corinthians should have ~19 home games in 2022, got %d", home.Played)
	}
}

func TestPlayerQuery_MultiTokenName(t *testing.T) {
	// Given the FIFA player data is loaded
	db := loadTestDB(t)

	// When I search a two-word name where tokens are non-adjacent variants
	players := db.FindPlayers(PlayerFilter{Name: "Gabriel Jesus"})

	// Then the player is found via token matching
	if len(players) == 0 {
		t.Fatal("Then expected to find Gabriel Jesus")
	}
	lower := strings.ToLower(players[0].Name)
	if !strings.Contains(lower, "gabriel") || !strings.Contains(lower, "jesus") {
		t.Errorf("Then top result %q should contain both tokens", players[0].Name)
	}
}

func TestCompetitions_Coverage(t *testing.T) {
	// Given the match data is loaded
	db := loadTestDB(t)

	// When I list competitions
	comps := db.Competitions()

	// Then the major Brazilian competitions are present
	wantKeys := map[string]bool{CompBrasileirao: false, CompCopaDoBrasil: false, CompLibertadores: false}
	for _, c := range comps {
		if _, ok := wantKeys[c.Key]; ok {
			wantKeys[c.Key] = true
		}
	}
	for k, found := range wantKeys {
		if !found {
			t.Errorf("Then expected competition %q to be present", k)
		}
	}
}
