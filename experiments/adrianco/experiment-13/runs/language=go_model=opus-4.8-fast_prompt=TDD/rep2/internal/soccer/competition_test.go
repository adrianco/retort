package soccer

import (
	"math"
	"testing"
)

func TestStandings(t *testing.T) {
	kb := testKB()
	table := kb.Standings("Brasileirão", 2019)
	if len(table) != 3 {
		t.Fatalf("teams = %d, want 3", len(table))
	}
	// Expected order: Flamengo (7 pts), Fluminense (1), Gremio (0).
	if !TeamsMatch(table[0].Team, "Flamengo") || table[0].Points() != 7 {
		t.Errorf("1st = %q %d pts, want Flamengo 7", table[0].Team, table[0].Points())
	}
	if !TeamsMatch(table[1].Team, "Fluminense") || table[1].Points() != 1 {
		t.Errorf("2nd = %q %d pts, want Fluminense 1", table[1].Team, table[1].Points())
	}
	if !TeamsMatch(table[2].Team, "Gremio") {
		t.Errorf("3rd = %q, want Gremio", table[2].Team)
	}
}

func TestStandingsPicksMostCompleteSource(t *testing.T) {
	// Two sources cover the same competition+season; the one with more
	// matches must be used and they must not be double-counted.
	kb := &KB{Matches: []Match{
		// Sparse source: only one match.
		{Competition: CompBrasileirao, Season: 2020, Source: "sparse.csv",
			HomeTeam: "A", AwayTeam: "B", HomeGoals: 1, AwayGoals: 0, HasScore: true},
		// Complete source: two matches.
		{Competition: CompBrasileirao, Season: 2020, Source: "full.csv",
			HomeTeam: "A", AwayTeam: "B", HomeGoals: 3, AwayGoals: 0, HasScore: true},
		{Competition: CompBrasileirao, Season: 2020, Source: "full.csv",
			HomeTeam: "B", AwayTeam: "A", HomeGoals: 1, AwayGoals: 1, HasScore: true},
	}}
	table := kb.Standings("Brasileirão", 2020)
	if len(table) != 2 {
		t.Fatalf("teams = %d, want 2", len(table))
	}
	// From the full source only: A has 1W 1D (3-0, 1-1) = 4 pts over 2 games.
	var a TeamRecord
	for _, r := range table {
		if r.Team == "A" {
			a = r
		}
	}
	if a.Matches != 2 || a.Points() != 4 {
		t.Errorf("A from full source = %+v, want 2 matches / 4 pts", a)
	}
}

func TestCompetitionStats(t *testing.T) {
	kb := testKB()
	cs := kb.CompetitionStats(MatchFilter{Competition: "Brasileirão", Season: 2019})
	if cs.Matches != 3 {
		t.Fatalf("matches = %d, want 3", cs.Matches)
	}
	// Goals: (2+1)+(0+0)+(5+0) = 8 over 3 matches.
	if cs.TotalGoals != 8 {
		t.Errorf("total goals = %d, want 8", cs.TotalGoals)
	}
	if math.Abs(cs.AvgGoals()-8.0/3.0) > 1e-9 {
		t.Errorf("avg goals = %v", cs.AvgGoals())
	}
	// Home results: Fla 2-1 W, Flu 0-0 D, Fla 5-0 W => 2 home wins, 1 draw.
	if cs.HomeWins != 2 || cs.Draws != 1 || cs.AwayWins != 0 {
		t.Errorf("H/D/A = %d/%d/%d, want 2/1/0", cs.HomeWins, cs.Draws, cs.AwayWins)
	}
}

func TestBiggestWins(t *testing.T) {
	kb := testKB()
	top := kb.BiggestWins(MatchFilter{}, 2)
	if len(top) != 2 {
		t.Fatalf("got %d", len(top))
	}
	// Largest margin is Flamengo 5-0 Gremio (margin 5).
	if top[0].HomeGoals-top[0].AwayGoals != 5 {
		t.Errorf("top margin = %d, want 5", top[0].HomeGoals-top[0].AwayGoals)
	}
}
