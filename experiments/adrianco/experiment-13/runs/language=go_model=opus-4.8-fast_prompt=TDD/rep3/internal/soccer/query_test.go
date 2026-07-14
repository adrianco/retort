// Context: Brazilian Soccer MCP Server.
// File: query_test.go
// Purpose: Tests for the query engine — match search, head-to-head, team
// records, standings, player search and aggregate statistics — exercised
// against a small hand-built fixture DB.
package soccer

import (
	"testing"
	"time"
)

func d(s string) time.Time {
	t, _ := time.Parse("2006-01-02", s)
	return t
}

// fixture returns a small DB with a known set of matches and players.
func fixtureDB() *DB {
	return &DB{
		Matches: []Match{
			{Competition: CompBrasileirao, Season: 2023, Round: "1", Date: d("2023-04-01"), HasDate: true,
				HomeTeam: "Flamengo", AwayTeam: "Fluminense", HomeGoals: 2, AwayGoals: 1, HasScore: true},
			{Competition: CompBrasileirao, Season: 2023, Round: "8", Date: d("2023-05-28"), HasDate: true,
				HomeTeam: "Fluminense", AwayTeam: "Flamengo", HomeGoals: 1, AwayGoals: 0, HasScore: true},
			{Competition: CompBrasileirao, Season: 2023, Round: "5", Date: d("2023-05-01"), HasDate: true,
				HomeTeam: "Flamengo", AwayTeam: "Santos", HomeGoals: 5, AwayGoals: 0, HasScore: true},
			{Competition: CompBrasileirao, Season: 2023, Round: "6", Date: d("2023-05-10"), HasDate: true,
				HomeTeam: "Santos", AwayTeam: "Fluminense", HomeGoals: 0, AwayGoals: 0, HasScore: true},
			{Competition: CompCopaDoBrasil, Season: 2022, Date: d("2022-06-01"), HasDate: true,
				HomeTeam: "Flamengo", AwayTeam: "Corinthians", HomeGoals: 1, AwayGoals: 1, HasScore: true},
		},
		Players: []Player{
			{ID: 1, Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Potential: 92, Club: "Paris Saint-Germain", Position: "LW"},
			{ID: 2, Name: "Alisson", Nationality: "Brazil", Overall: 89, Potential: 90, Club: "Liverpool", Position: "GK"},
			{ID: 3, Name: "L. Messi", Nationality: "Argentina", Overall: 94, Potential: 94, Club: "FC Barcelona", Position: "RF"},
			{ID: 4, Name: "Gabriel Barbosa", Nationality: "Brazil", Overall: 81, Potential: 84, Club: "Flamengo", Position: "ST"},
			{ID: 5, Name: "Pedro", Nationality: "Brazil", Overall: 79, Potential: 85, Club: "Flamengo", Position: "ST"},
		},
	}
}

func TestFindMatchesByTeam(t *testing.T) {
	db := fixtureDB()
	got := db.FindMatches(MatchFilter{Team: "Flamengo"})
	if len(got) != 4 {
		t.Fatalf("Flamengo matches = %d, want 4", len(got))
	}
	// Results should be sorted by date ascending.
	for i := 1; i < len(got); i++ {
		if got[i].Date.Before(got[i-1].Date) {
			t.Errorf("results not sorted by date")
		}
	}
}

func TestFindMatchesHomeAwayAndCompetition(t *testing.T) {
	db := fixtureDB()
	home := db.FindMatches(MatchFilter{HomeTeam: "Flamengo", Competition: "Brasileirão"})
	if len(home) != 2 {
		t.Fatalf("Flamengo home Brasileirão = %d, want 2", len(home))
	}
	cup := db.FindMatches(MatchFilter{Team: "Flamengo", Competition: "Copa do Brasil"})
	if len(cup) != 1 {
		t.Fatalf("Flamengo cup = %d, want 1", len(cup))
	}
}

func TestFindMatchesByMatchup(t *testing.T) {
	db := fixtureDB()
	got := db.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
	if len(got) != 2 {
		t.Fatalf("Fla-Flu = %d, want 2", len(got))
	}
}

func TestFindMatchesBySeasonAndDateRange(t *testing.T) {
	db := fixtureDB()
	if got := db.FindMatches(MatchFilter{Season: 2022}); len(got) != 1 {
		t.Fatalf("2022 matches = %d, want 1", len(got))
	}
	got := db.FindMatches(MatchFilter{From: d("2023-05-01"), To: d("2023-05-31")})
	if len(got) != 3 {
		t.Fatalf("May 2023 matches = %d, want 3", len(got))
	}
}

func TestHeadToHead(t *testing.T) {
	db := fixtureDB()
	h := db.HeadToHead("Flamengo", "Fluminense")
	if h.AWins != 1 || h.BWins != 1 || h.Draws != 0 {
		t.Errorf("h2h = %dW %dW %dD, want 1/1/0", h.AWins, h.BWins, h.Draws)
	}
	if h.AGoals != 2 || h.BGoals != 2 {
		t.Errorf("h2h goals = %d/%d, want 2/2", h.AGoals, h.BGoals)
	}
	if len(h.Matches) != 2 {
		t.Errorf("h2h matches = %d, want 2", len(h.Matches))
	}
}

func TestTeamRecord(t *testing.T) {
	db := fixtureDB()
	// Flamengo across all Brasileirão 2023 matches: home 2-1 W vs Flu, home 5-0 W vs Santos, away 0-1 L vs Flu.
	r := db.TeamRecord(TeamFilter{Team: "Flamengo", Season: 2023, Competition: "Brasileirão"})
	if r.Matches != 3 || r.Wins != 2 || r.Draws != 0 || r.Losses != 1 {
		t.Errorf("record = %d M %d W %d D %d L, want 3/2/0/1", r.Matches, r.Wins, r.Draws, r.Losses)
	}
	if r.GoalsFor != 7 || r.GoalsAgainst != 2 {
		t.Errorf("goals = %d:%d, want 7:2", r.GoalsFor, r.GoalsAgainst)
	}
	if r.Points() != 6 {
		t.Errorf("points = %d, want 6", r.Points())
	}
}

func TestTeamRecordHomeOnly(t *testing.T) {
	db := fixtureDB()
	r := db.TeamRecord(TeamFilter{Team: "Flamengo", Season: 2023, Competition: "Brasileirão", Venue: VenueHome})
	if r.Matches != 2 || r.Wins != 2 {
		t.Errorf("home record = %d M %d W, want 2/2", r.Matches, r.Wins)
	}
}

func TestStandings(t *testing.T) {
	db := fixtureDB()
	table := db.Standings(2023, "Brasileirão")
	if len(table) != 3 {
		t.Fatalf("teams = %d, want 3 (Flamengo, Fluminense, Santos)", len(table))
	}
	// Flamengo: 2 wins 1 loss = 6 pts; Fluminense: 1W 1D 1L = 4 pts; Santos: 0W 1D 1L = 1 pt.
	if table[0].Team != "Flamengo" || table[0].Points() != 6 {
		t.Errorf("1st = %s %d pts, want Flamengo 6", table[0].Team, table[0].Points())
	}
	if table[1].Team != "Fluminense" || table[1].Points() != 4 {
		t.Errorf("2nd = %s %d pts, want Fluminense 4", table[1].Team, table[1].Points())
	}
	if table[2].Team != "Santos" {
		t.Errorf("3rd = %s, want Santos", table[2].Team)
	}
}

func TestFindPlayers(t *testing.T) {
	db := fixtureDB()
	br := db.FindPlayers(PlayerFilter{Nationality: "Brazil"})
	if len(br) != 4 {
		t.Fatalf("Brazilian players = %d, want 4", len(br))
	}
	// Sorted by overall descending.
	if br[0].Name != "Neymar Jr" {
		t.Errorf("top Brazilian = %s, want Neymar Jr", br[0].Name)
	}
	fla := db.FindPlayers(PlayerFilter{Club: "Flamengo"})
	if len(fla) != 2 {
		t.Errorf("Flamengo players = %d, want 2", len(fla))
	}
	byName := db.FindPlayers(PlayerFilter{Name: "gabriel"})
	if len(byName) != 1 || byName[0].Name != "Gabriel Barbosa" {
		t.Errorf("name search failed: %+v", byName)
	}
	limited := db.FindPlayers(PlayerFilter{Nationality: "Brazil", Limit: 2})
	if len(limited) != 2 {
		t.Errorf("limited = %d, want 2", len(limited))
	}
}

func TestAverageGoals(t *testing.T) {
	db := fixtureDB()
	// Brasileirão 2023: (3 + 1 + 5 + 0) / 4 matches = 9/4 = 2.25
	avg := db.AverageGoals(MatchFilter{Competition: "Brasileirão", Season: 2023})
	if avg < 2.24 || avg > 2.26 {
		t.Errorf("avg goals = %f, want ~2.25", avg)
	}
}

func TestBiggestWins(t *testing.T) {
	db := fixtureDB()
	wins := db.BiggestWins(MatchFilter{}, 2)
	if len(wins) != 2 {
		t.Fatalf("biggest wins = %d, want 2", len(wins))
	}
	// Largest margin is Flamengo 5-0 Santos.
	if wins[0].HomeGoals-wins[0].AwayGoals != 5 {
		t.Errorf("biggest = %d-%d, want margin 5", wins[0].HomeGoals, wins[0].AwayGoals)
	}
}
