// Package main — Brazilian Soccer MCP Server.
//
// query_test.go: Behavioral tests for the query engine — match search,
// team records, head-to-head, season standings, player search and aggregate
// statistics — asserted against known ground-truth facts in the datasets
// (e.g. Flamengo were 2019 Brasileirão champions with 90 points).
package main

import (
	"strings"
	"testing"
)

func TestFindMatchesByTeamAndOpponent(t *testing.T) {
	ds := testDataset(t)
	ms := ds.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
	if len(ms) == 0 {
		t.Fatal("expected some Flamengo vs Fluminense matches")
	}
	for _, m := range ms {
		if !(m.Involves("flamengo") && m.Involves("fluminense")) {
			t.Errorf("match does not involve both teams: %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
}

func TestFindMatchesBySeasonAndCompetition(t *testing.T) {
	ds := testDataset(t)
	ms := ds.FindMatches(MatchFilter{Team: "Palmeiras", Season: 2019, Source: "Brasileirao"})
	if len(ms) != 38 {
		t.Errorf("Palmeiras 2019 Brasileirão: got %d matches, want 38", len(ms))
	}
}

func TestTeamRecord(t *testing.T) {
	ds := testDataset(t)
	rec := ds.TeamRecord("Flamengo", MatchFilter{Season: 2019, Source: "Brasileirao"}, VenueAll)
	if rec.Matches != 38 {
		t.Errorf("matches = %d, want 38", rec.Matches)
	}
	if rec.Wins != 28 || rec.Draws != 6 || rec.Losses != 4 {
		t.Errorf("record = %dW %dD %dL, want 28W 6D 4L", rec.Wins, rec.Draws, rec.Losses)
	}
	if rec.Wins+rec.Draws+rec.Losses != rec.Matches {
		t.Error("W+D+L must equal matches")
	}
}

func TestTeamRecordHomeOnly(t *testing.T) {
	ds := testDataset(t)
	rec := ds.TeamRecord("Flamengo", MatchFilter{Season: 2019, Source: "Brasileirao"}, VenueHome)
	if rec.Matches != 19 {
		t.Errorf("home matches = %d, want 19", rec.Matches)
	}
}

func TestHeadToHead(t *testing.T) {
	ds := testDataset(t)
	h := ds.HeadToHead("Palmeiras", "Santos")
	if h.Total() == 0 {
		t.Fatal("expected Palmeiras-Santos meetings")
	}
	if h.AWins+h.BWins+h.Draws != h.Total() {
		t.Error("h2h totals inconsistent")
	}
}

func TestStandings(t *testing.T) {
	ds := testDataset(t)
	table := ds.Standings("Brasileirão", 2019)
	if len(table) < 4 {
		t.Fatalf("expected a full standings table, got %d rows", len(table))
	}
	champ := table[0]
	if !strings.Contains(strings.ToLower(champ.Team), "flamengo") {
		t.Errorf("2019 champion = %q, want Flamengo", champ.Team)
	}
	if champ.Points != 90 {
		t.Errorf("champion points = %d, want 90", champ.Points)
	}
	if champ.Wins != 28 {
		t.Errorf("champion wins = %d, want 28", champ.Wins)
	}
	// Table must be sorted by points descending.
	for i := 1; i < len(table); i++ {
		if table[i-1].Points < table[i].Points {
			t.Errorf("standings not sorted at row %d", i)
		}
	}
}

func TestSearchPlayersByName(t *testing.T) {
	ds := testDataset(t)
	ps := ds.SearchPlayers(PlayerFilter{Name: "Neymar"})
	if len(ps) == 0 {
		t.Fatal("expected to find Neymar")
	}
	if !strings.Contains(ps[0].Name, "Neymar") {
		t.Errorf("first result = %q, want a Neymar", ps[0].Name)
	}
}

func TestSearchPlayersBrazilianSorted(t *testing.T) {
	ds := testDataset(t)
	ps := ds.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: 5})
	if len(ps) != 5 {
		t.Fatalf("expected 5 top Brazilians, got %d", len(ps))
	}
	for i := 1; i < len(ps); i++ {
		if ps[i-1].Overall < ps[i].Overall {
			t.Errorf("players not sorted by Overall desc at %d", i)
		}
	}
	if ps[0].Overall < 88 {
		t.Errorf("top Brazilian overall = %d, expected >= 88", ps[0].Overall)
	}
}

func TestSearchPlayersByClub(t *testing.T) {
	ds := testDataset(t)
	// Santos is one of the Brazilian clubs present in this FIFA edition.
	ps := ds.SearchPlayers(PlayerFilter{Club: "Santos"})
	if len(ps) == 0 {
		t.Fatal("expected players at Santos")
	}
	for _, p := range ps {
		if !strings.Contains(NormalizeTeam(p.Club), "santos") {
			t.Errorf("player %q club %q does not match Santos", p.Name, p.Club)
		}
	}
}

func TestCompetitionStats(t *testing.T) {
	ds := testDataset(t)
	s := ds.Stats(MatchFilter{Source: "Brasileirao", Season: 2019})
	if s.Matches != 380 {
		t.Errorf("matches = %d, want 380", s.Matches)
	}
	if s.AvgGoals < 1.0 || s.AvgGoals > 5.0 {
		t.Errorf("avg goals = %.2f, out of sane range", s.AvgGoals)
	}
	if s.HomeWinRate <= 0 || s.HomeWinRate >= 1 {
		t.Errorf("home win rate = %.3f, out of (0,1)", s.HomeWinRate)
	}
	if s.HomeWins+s.AwayWins+s.Draws != s.Matches {
		t.Error("result breakdown must sum to matches")
	}
}

func TestBiggestWins(t *testing.T) {
	ds := testDataset(t)
	top := ds.BiggestWins(MatchFilter{Source: "Brasileirao"}, 5)
	if len(top) != 5 {
		t.Fatalf("expected 5 biggest wins, got %d", len(top))
	}
	for i := 1; i < len(top); i++ {
		mPrev := abs(top[i-1].HomeGoals - top[i-1].AwayGoals)
		mCur := abs(top[i].HomeGoals - top[i].AwayGoals)
		if mPrev < mCur {
			t.Errorf("biggest wins not sorted by margin at %d", i)
		}
	}
	if abs(top[0].HomeGoals-top[0].AwayGoals) < 4 {
		t.Errorf("top margin = %d, expected a blowout", abs(top[0].HomeGoals-top[0].AwayGoals))
	}
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}
