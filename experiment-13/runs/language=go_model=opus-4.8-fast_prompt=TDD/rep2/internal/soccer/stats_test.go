package soccer

import (
	"math"
	"testing"
)

func TestTeamRecord(t *testing.T) {
	kb := testKB()
	// Flamengo across all matches in testKB:
	//  W 2-1 vs Fluminense (home), D 0-0 vs Fluminense (away),
	//  W 5-0 vs Gremio (home), W 3-1 at Palmeiras (away), D 2-2 vs Palmeiras (Copa).
	rec := kb.TeamRecord(MatchFilter{Team: "Flamengo"})
	if rec.Matches != 5 {
		t.Fatalf("matches = %d, want 5", rec.Matches)
	}
	if rec.Wins != 3 || rec.Draws != 2 || rec.Losses != 0 {
		t.Errorf("W/D/L = %d/%d/%d, want 3/2/0", rec.Wins, rec.Draws, rec.Losses)
	}
	// GF = 2+0+5+3+2 = 12 ; GA = 1+0+0+1+2 = 4
	if rec.GoalsFor != 12 || rec.GoalsAgainst != 4 {
		t.Errorf("GF/GA = %d/%d, want 12/4", rec.GoalsFor, rec.GoalsAgainst)
	}
	if rec.Points() != 3*3+2 {
		t.Errorf("points = %d, want 11", rec.Points())
	}
	if math.Abs(rec.WinRate()-60.0) > 0.01 {
		t.Errorf("win rate = %.2f, want 60.00", rec.WinRate())
	}
}

func TestTeamRecordHomeOnly2019(t *testing.T) {
	kb := testKB()
	// Flamengo home in 2019 Brasileirão: 2-1 vs Fluminense, 5-0 vs Gremio.
	rec := kb.TeamRecord(MatchFilter{HomeTeam: "Flamengo", Season: 2019, Competition: "Brasileirão"})
	if rec.Matches != 2 || rec.Wins != 2 {
		t.Errorf("home 2019 record = %+v, want 2 matches / 2 wins", rec)
	}
	if rec.GoalsFor != 7 || rec.GoalsAgainst != 1 {
		t.Errorf("GF/GA = %d/%d, want 7/1", rec.GoalsFor, rec.GoalsAgainst)
	}
}

func TestHeadToHead(t *testing.T) {
	kb := testKB()
	h := kb.HeadToHead("Flamengo", "Fluminense")
	if len(h.Matches) != 2 {
		t.Fatalf("matches = %d, want 2", len(h.Matches))
	}
	// Flamengo: 1 win (2-1), 1 draw (0-0), Fluminense 0 wins.
	if h.Team1Wins != 1 || h.Team2Wins != 0 || h.Draws != 1 {
		t.Errorf("h2h = %d-%d-%d, want 1-0-1", h.Team1Wins, h.Draws, h.Team2Wins)
	}
}
