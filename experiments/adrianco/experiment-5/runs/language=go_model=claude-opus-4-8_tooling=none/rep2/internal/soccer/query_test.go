package soccer

import (
	"testing"
	"testing/fstest"
)

// testStore builds a small, deterministic dataset in memory so the behaviour
// scenarios do not depend on the bundled CSV files.
func testStore(t *testing.T) *Store {
	t.Helper()
	fsys := fstest.MapFS{
		"Brasileirao_Matches.csv": &fstest.MapFile{Data: []byte(
			`"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2023-09-03 16:00:00,"Flamengo-RJ","RJ","Fluminense-RJ","RJ",2,1,2023,22
2023-05-28 16:00:00,"Fluminense-RJ","RJ","Flamengo-RJ","RJ",0,0,2023,8
2023-07-01 16:00:00,"Flamengo-RJ","RJ","Palmeiras-SP","SP",3,0,2023,15
2023-07-10 16:00:00,"Palmeiras-SP","SP","Flamengo-RJ","RJ",1,1,2023,16
2023-08-01 16:00:00,"Palmeiras-SP","SP","Fluminense-RJ","RJ",2,2,2023,18
2023-08-12 16:00:00,"Fluminense-RJ","RJ","Palmeiras-SP","SP",0,1,2023,19
`)},
		"Libertadores_Matches.csv": &fstest.MapFile{Data: []byte(
			`"datetime","home_team","away_team","home_goal","away_goal","season","stage"
2023-06-01 20:00:00,"Flamengo","Fluminense",4,0,2023,"group stage"
`)},
		"fifa_data.csv": &fstest.MapFile{Data: []byte(
			",ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number\n" +
				"0,1,Neymar Jr,27,Brazil,92,93,Paris Saint-Germain,LW,10\n" +
				"1,2,Gabriel Barbosa,22,Brazil,80,85,Flamengo,ST,9\n" +
				"2,3,Bruno Henrique,28,Brazil,78,78,Flamengo,LW,27\n" +
				"3,4,L. Messi,31,Argentina,94,94,FC Barcelona,RF,10\n")},
	}
	store, err := Load(fsys, ".")
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	return store
}

// Feature: Match Queries
func TestScenarioFindMatchesBetweenTwoTeams(t *testing.T) {
	// Given the match data is loaded
	store := testStore(t)

	// When I search for matches between "Flamengo" and "Fluminense"
	matches := store.SearchMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})

	// Then I should receive a list of matches
	if len(matches) != 3 { // 2 Brasileirão + 1 Libertadores
		t.Fatalf("expected 3 Fla-Flu matches, got %d", len(matches))
	}
	// And each match should have date, scores and competition
	for _, m := range matches {
		if !m.HasDate || !m.HasScore || m.Competition == "" {
			t.Errorf("incomplete match: %+v", m)
		}
		if !oppositeSides(m, "Flamengo", "Fluminense") {
			t.Errorf("match does not involve both teams: %+v", m)
		}
	}
	// And results are sorted most-recent first
	if matches[0].Date.Before(matches[len(matches)-1].Date) {
		t.Error("matches not sorted most-recent first")
	}
}

func TestScenarioSearchByCompetitionAndSeason(t *testing.T) {
	store := testStore(t)
	got := store.SearchMatches(MatchFilter{Competition: CompLibertadores, Season: 2023})
	if len(got) != 1 || got[0].Competition != CompLibertadores {
		t.Fatalf("expected 1 Libertadores 2023 match, got %d", len(got))
	}
}

func TestScenarioVenueFilter(t *testing.T) {
	store := testStore(t)
	home := store.SearchMatches(MatchFilter{Team: "Flamengo", Venue: "home"})
	for _, m := range home {
		if !TeamMatches(m.HomeRaw, "Flamengo") {
			t.Errorf("venue=home returned away match: %+v", m)
		}
	}
}

// Feature: Head-to-head
func TestScenarioHeadToHead(t *testing.T) {
	store := testStore(t)
	h := store.HeadToHead("Flamengo", "Fluminense")
	// Flamengo: 2-1 win, 0-0 draw, 4-0 win => 2 wins, 1 draw, 0 losses
	if h.AWins != 2 || h.Draws != 1 || h.BWins != 0 {
		t.Errorf("h2h = %dW %dD %dL, want 2W 1D 0L", h.AWins, h.Draws, h.BWins)
	}
	if h.AGoals != 6 || h.BGoals != 1 {
		t.Errorf("h2h goals = %d-%d, want 6-1", h.AGoals, h.BGoals)
	}
}

// Feature: Team statistics
func TestScenarioTeamStats(t *testing.T) {
	// Given the match data is loaded
	store := testStore(t)
	// When I request statistics for "Flamengo" in season "2023"
	rec := store.TeamStats("Flamengo", "", 2023, "")
	// Then I should receive wins, losses, draws and goals
	// Flamengo matches: W2-1, D0-0, W3-0, D1-1, plus Libertadores W4-0 => 3W 2D 0L
	if rec.Played != 5 {
		t.Fatalf("played = %d, want 5", rec.Played)
	}
	if rec.Wins != 3 || rec.Draws != 2 || rec.Losses != 0 {
		t.Errorf("record = %dW %dD %dL, want 3W 2D 0L", rec.Wins, rec.Draws, rec.Losses)
	}
	if rec.GoalsFor != 10 || rec.GoalsAgainst != 2 {
		t.Errorf("goals = %d-%d, want 10-2", rec.GoalsFor, rec.GoalsAgainst)
	}
}

// Feature: Standings
func TestScenarioStandings(t *testing.T) {
	store := testStore(t)
	table := store.Standings(CompSerieA, 2023)
	if len(table) != 3 {
		t.Fatalf("expected 3 teams, got %d", len(table))
	}
	// Flamengo: W,D,W,D among Brasileirão games (2-1, 0-0, 3-0, 1-1) => 2W 2D = 8 pts
	if table[0].Team != "Flamengo-RJ" || table[0].Points() != 8 {
		t.Errorf("leader = %s %dpts, want Flamengo-RJ 8pts", table[0].Team, table[0].Points())
	}
}

// Feature: Player Queries
func TestScenarioSearchBrazilianPlayers(t *testing.T) {
	store := testStore(t)
	players := store.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
	if len(players) != 3 {
		t.Fatalf("expected 3 Brazilians, got %d", len(players))
	}
	// sorted by overall desc -> Neymar first
	if players[0].Name != "Neymar Jr" {
		t.Errorf("top player = %s, want Neymar Jr", players[0].Name)
	}
}

func TestScenarioPlayersByClub(t *testing.T) {
	store := testStore(t)
	players := store.SearchPlayers(PlayerFilter{Club: "Flamengo"})
	if len(players) != 2 {
		t.Fatalf("expected 2 Flamengo players, got %d", len(players))
	}
	summaries := store.PlayersByClub("Brazil")
	if len(summaries) == 0 || summaries[0].Club != "Flamengo" || summaries[0].Count != 2 {
		t.Errorf("expected Flamengo with 2 players at top, got %+v", summaries)
	}
}

func TestScenarioPlayerByName(t *testing.T) {
	store := testStore(t)
	players := store.SearchPlayers(PlayerFilter{Name: "Gabriel"})
	if len(players) != 1 || players[0].Name != "Gabriel Barbosa" {
		t.Fatalf("name search failed: %+v", players)
	}
}

// Feature: Statistical analysis
func TestScenarioCompetitionStats(t *testing.T) {
	store := testStore(t)
	stats := store.Stats(CompSerieA, 2023, 3)
	if stats.Matches != 6 {
		t.Fatalf("expected 6 scored matches, got %d", stats.Matches)
	}
	// total goals: (3)+(0)+(3)+(2)+(4)+(1) = 13 over 6 -> ~2.17
	if stats.TotalGoals != 13 {
		t.Errorf("total goals = %d, want 13", stats.TotalGoals)
	}
	if got := stats.AvgGoals(); got < 2.16 || got > 2.18 {
		t.Errorf("avg goals = %.3f, want ~2.17", got)
	}
	// biggest win is Flamengo 3-0 Palmeiras (margin 3)
	if len(stats.BiggestWins) == 0 || abs(stats.BiggestWins[0].HomeGoals-stats.BiggestWins[0].AwayGoals) != 3 {
		t.Errorf("biggest win margin wrong: %+v", stats.BiggestWins)
	}
}
