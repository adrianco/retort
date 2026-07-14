// Unit tests for the soccer domain internals -- the fine-grained TDD layer
// beneath the acceptance suite: name normalization, multi-format date parsing,
// and the individual Store query calculations.
package soccer

import (
	"testing"
	"time"
)

func TestCleanTeamNameStripsSuffixes(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP":   "Palmeiras",
		"Flamengo-RJ":    "Flamengo",
		"Nacional (URU)": "Nacional",
		"Barcelona-EQU":  "Barcelona",
		"São Paulo":      "São Paulo",
		"América - MG":   "América",
		"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ": "Boavista Sport Club (antigo Esporte Clube Barreira)",
	}
	for in, want := range cases {
		if got := CleanTeamName(in); got != want {
			t.Errorf("CleanTeamName(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestNormalizeKeyIsAccentAndCaseInsensitive(t *testing.T) {
	if NormalizeKey("São Paulo") != NormalizeKey("Sao Paulo-SP") {
		t.Errorf("expected São Paulo and Sao Paulo-SP to normalize equal")
	}
	if NormalizeKey("Grêmio") != "gremio" {
		t.Errorf("NormalizeKey(Grêmio) = %q, want gremio", NormalizeKey("Grêmio"))
	}
}

func TestParseDateFormats(t *testing.T) {
	cases := map[string]string{
		"2012-05-19 18:30:00": "2012-05-19",
		"2023-09-24":          "2023-09-24",
		"29/03/2003":          "2003-03-29",
	}
	for in, want := range cases {
		got, ok := parseDate(in)
		if !ok {
			t.Errorf("parseDate(%q) failed", in)
			continue
		}
		if got.Format("2006-01-02") != want {
			t.Errorf("parseDate(%q) = %s, want %s", in, got.Format("2006-01-02"), want)
		}
	}
	if _, ok := parseDate("not a date"); ok {
		t.Errorf("expected parseDate to fail on garbage")
	}
}

// buildStore returns a small deterministic store for query unit tests.
func buildStore() *Store {
	s := NewStore()
	d := func(s string) (time.Time, bool) { return parseDate(s) }
	t1, _ := d("2023-09-03")
	t2, _ := d("2023-05-28")
	s.AddMatch(Match{Competition: "Brasileirão", Season: 2023, Date: t1, HasDate: true, HomeTeam: "Flamengo", AwayTeam: "Fluminense", HomeGoals: 2, AwayGoals: 1})
	s.AddMatch(Match{Competition: "Brasileirão", Season: 2023, Date: t2, HasDate: true, HomeTeam: "Fluminense", AwayTeam: "Flamengo", HomeGoals: 1, AwayGoals: 0})
	s.AddMatch(Match{Competition: "Brasileirão", Season: 2023, HomeTeam: "Palmeiras", AwayTeam: "Santos", HomeGoals: 3, AwayGoals: 0})
	return s
}

func TestFindMatchesBetweenTeams(t *testing.T) {
	s := buildStore()
	got := s.FindMatches(MatchQuery{Team: "Flamengo", Opponent: "Fluminense"})
	if len(got) != 2 {
		t.Fatalf("expected 2 Fla-Flu matches, got %d", len(got))
	}
	// Most recent first.
	if !got[0].Date.After(got[1].Date) {
		t.Errorf("expected newest match first")
	}
}

func TestHeadToHeadRecord(t *testing.T) {
	s := buildStore()
	h := s.HeadToHead("Flamengo", "Fluminense")
	if h.Team1Wins != 1 || h.Team2Wins != 1 || h.Draws != 0 {
		t.Errorf("expected 1-1-0, got %d-%d-%d", h.Team1Wins, h.Team2Wins, h.Draws)
	}
}

func TestTeamStatsAndVenueFilter(t *testing.T) {
	s := buildStore()
	all := s.TeamStats("Flamengo", "", 2023, VenueAll)
	if all.Played != 2 || all.Wins != 1 || all.Losses != 1 || all.GoalsFor != 2 || all.GoalsAgainst != 2 {
		t.Errorf("unexpected all-venue record: %+v", all)
	}
	home := s.TeamStats("Flamengo", "", 2023, VenueHome)
	if home.Played != 1 || home.Wins != 1 {
		t.Errorf("unexpected home record: %+v", home)
	}
}

func TestStandingsOrdering(t *testing.T) {
	s := buildStore()
	rows := s.Standings("Brasileirão", 2023)
	if len(rows) == 0 {
		t.Fatal("expected standings rows")
	}
	// Palmeiras won 3-0 => 3 pts, best goal difference, should top the table.
	if rows[0].Team != "Palmeiras" {
		t.Errorf("expected Palmeiras top of table, got %s", rows[0].Team)
	}
}

func TestLeagueStatsAggregates(t *testing.T) {
	s := buildStore()
	stats := s.LeagueStats("Brasileirão", 2023, 5)
	if stats.Matches != 3 {
		t.Fatalf("expected 3 matches, got %d", stats.Matches)
	}
	wantAvg := float64(2+1+1+0+3+0) / 3
	if stats.AvgGoals != wantAvg {
		t.Errorf("avg goals = %.3f, want %.3f", stats.AvgGoals, wantAvg)
	}
	if len(stats.BiggestWins) == 0 || abs(stats.BiggestWins[0].HomeGoals-stats.BiggestWins[0].AwayGoals) != 3 {
		t.Errorf("expected biggest win with margin 3, got %+v", stats.BiggestWins)
	}
}

func TestSearchPlayersSortedByOverall(t *testing.T) {
	s := NewStore()
	s.AddPlayer(Player{Name: "Dudu", Nationality: "Brazil", Overall: 78, Club: "Palmeiras"})
	s.AddPlayer(Player{Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Club: "Paris Saint-Germain"})
	s.AddPlayer(Player{Name: "L. Messi", Nationality: "Argentina", Overall: 94, Club: "FC Barcelona"})

	got := s.SearchPlayers(PlayerQuery{Nationality: "Brazil"})
	if len(got) != 2 {
		t.Fatalf("expected 2 Brazilians, got %d", len(got))
	}
	if got[0].Name != "Neymar Jr" {
		t.Errorf("expected Neymar first (highest overall), got %s", got[0].Name)
	}
}
