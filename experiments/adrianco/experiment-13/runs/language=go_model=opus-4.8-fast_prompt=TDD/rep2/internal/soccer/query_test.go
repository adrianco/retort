package soccer

import (
	"testing"
	"time"
)

// testKB builds a small, deterministic knowledge base for query tests.
func testKB() *KB {
	d := func(s string) time.Time { t, _ := ParseDate(s); return t }
	mk := func(comp string, season int, date, home, away string, hg, ag int) Match {
		return Match{
			Competition: comp, Season: season,
			Date: d(date), HasDate: true,
			HomeTeam: home, AwayTeam: away,
			HomeGoals: hg, AwayGoals: ag, HasScore: true,
			Source: comp + ".csv", // one synthetic source per competition
		}
	}
	return &KB{
		Matches: []Match{
			mk(CompBrasileirao, 2019, "2019-05-01", "Flamengo-RJ", "Fluminense-RJ", 2, 1),
			mk(CompBrasileirao, 2019, "2019-09-03", "Fluminense-RJ", "Flamengo-RJ", 0, 0),
			mk(CompBrasileirao, 2019, "2019-10-27", "Flamengo-RJ", "Gremio-RS", 5, 0),
			mk(CompBrasileirao, 2018, "2018-06-10", "Palmeiras-SP", "Flamengo-RJ", 1, 3),
			mk(CompCopaDoBrasil, 2019, "2019-07-15", "Flamengo", "Palmeiras", 2, 2),
		},
		Players: []Player{
			{ID: 1, Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Club: "Paris Saint-Germain", Position: "LW"},
			{ID: 2, Name: "Gabriel Barbosa", Nationality: "Brazil", Overall: 83, Club: "Flamengo", Position: "ST"},
			{ID: 3, Name: "Bruno Henrique", Nationality: "Brazil", Overall: 80, Club: "Flamengo", Position: "LW"},
			{ID: 4, Name: "L. Messi", Nationality: "Argentina", Overall: 94, Club: "FC Barcelona", Position: "RF"},
		},
	}
}

func TestSearchMatchesByTeam(t *testing.T) {
	kb := testKB()
	got := kb.SearchMatches(MatchFilter{Team: "Flamengo"})
	// All 5 matches involve Flamengo.
	if len(got) != 5 {
		t.Fatalf("got %d matches, want 5", len(got))
	}
	// Results must be sorted most-recent first.
	for i := 1; i < len(got); i++ {
		if got[i-1].Date.Before(got[i].Date) {
			t.Errorf("matches not sorted descending by date")
		}
	}
}

func TestSearchMatchesByTeamAndOpponent(t *testing.T) {
	kb := testKB()
	got := kb.SearchMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
	if len(got) != 2 {
		t.Fatalf("Fla-Flu matches = %d, want 2", len(got))
	}
}

func TestSearchMatchesByCompetitionAndSeason(t *testing.T) {
	kb := testKB()
	got := kb.SearchMatches(MatchFilter{Competition: "Brasileirão", Season: 2019})
	if len(got) != 3 {
		t.Fatalf("got %d, want 3", len(got))
	}
}

func TestSearchMatchesHomeAwayAndLimit(t *testing.T) {
	kb := testKB()
	got := kb.SearchMatches(MatchFilter{HomeTeam: "Flamengo"})
	// Flamengo at home: 2019-05-01, 2019-10-27 (Brasileirão) and 2019-07-15 (Copa).
	if len(got) != 3 {
		t.Fatalf("home matches = %d, want 3", len(got))
	}
	got = kb.SearchMatches(MatchFilter{Team: "Flamengo", Limit: 1})
	if len(got) != 1 {
		t.Fatalf("limit not applied: %d", len(got))
	}
	if got[0].Date.Format("2006-01-02") != "2019-10-27" {
		t.Errorf("limit returned wrong (not most recent) match: %v", got[0].Date)
	}
}

func TestSearchMatchesByDateRange(t *testing.T) {
	kb := testKB()
	from, _ := ParseDate("2019-06-01")
	to, _ := ParseDate("2019-12-31")
	got := kb.SearchMatches(MatchFilter{DateFrom: from, DateTo: to})
	// 2019-07-15, 2019-09-03, 2019-10-27.
	if len(got) != 3 {
		t.Fatalf("date-range matches = %d, want 3", len(got))
	}
}
