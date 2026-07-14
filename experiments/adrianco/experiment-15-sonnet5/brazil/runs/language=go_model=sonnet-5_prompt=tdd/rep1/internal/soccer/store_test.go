package soccer

import (
	"testing"
	"time"
)

func mkMatch(date string, competition string, season int, home, away string, homeGoals, awayGoals int) Match {
	d, err := ParseDate(date)
	if err != nil {
		panic(err)
	}
	return Match{
		Date:        d,
		Season:      season,
		Competition: competition,
		HomeTeam:    home,
		AwayTeam:    away,
		HomeKey:     NormalizeTeamKey(home),
		AwayKey:     NormalizeTeamKey(away),
		HomeGoals:   homeGoals,
		AwayGoals:   awayGoals,
	}
}

func testFixtureMatches() []Match {
	return []Match{
		mkMatch("2023-05-28", "Brasileirao", 2023, "Fluminense", "Flamengo", 1, 0),
		mkMatch("2023-09-03", "Brasileirao", 2023, "Flamengo", "Fluminense", 2, 1),
		mkMatch("2022-11-06", "Brasileirao", 2022, "Flamengo", "Palmeiras", 3, 0),
		mkMatch("2021-08-15", "Copa do Brasil", 2021, "Flamengo", "Fluminense", 0, 0),
		mkMatch("2020-01-01", "Brasileirao", 2020, "Palmeiras", "Santos", 1, 1),
	}
}

func TestFindMatchesByTeam(t *testing.T) {
	s := NewStore(testFixtureMatches(), nil)
	got := s.FindMatches(MatchFilter{Team: "Flamengo"})
	if len(got) != 4 {
		t.Fatalf("got %d matches, want 4", len(got))
	}
	// Most recent first.
	if !got[0].Date.Equal(mustParseDate(t, "2023-09-03")) {
		t.Errorf("expected most recent match first, got date %v", got[0].Date)
	}
}

func TestFindMatchesByTeamAndOpponent(t *testing.T) {
	s := NewStore(testFixtureMatches(), nil)
	got := s.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
	if len(got) != 3 {
		t.Fatalf("got %d matches, want 3", len(got))
	}
}

func TestFindMatchesByCompetitionAndSeason(t *testing.T) {
	s := NewStore(testFixtureMatches(), nil)
	got := s.FindMatches(MatchFilter{Competition: "Brasileirao", Season: 2023})
	if len(got) != 2 {
		t.Fatalf("got %d matches, want 2", len(got))
	}
}

func TestFindMatchesByDateRange(t *testing.T) {
	s := NewStore(testFixtureMatches(), nil)
	from := mustParseDate(t, "2022-01-01")
	to := mustParseDate(t, "2023-01-01")
	got := s.FindMatches(MatchFilter{From: from, To: to})
	if len(got) != 1 {
		t.Fatalf("got %d matches, want 1", len(got))
	}
}

func TestFindMatchesLimit(t *testing.T) {
	s := NewStore(testFixtureMatches(), nil)
	got := s.FindMatches(MatchFilter{Team: "Flamengo", Limit: 1})
	if len(got) != 1 {
		t.Fatalf("got %d matches, want 1", len(got))
	}
}

func TestFindMatchesTeamNormalization(t *testing.T) {
	s := NewStore(testFixtureMatches(), nil)
	got := s.FindMatches(MatchFilter{Team: "flamengo-rj"})
	if len(got) != 4 {
		t.Fatalf("got %d matches, want 4 (team name should normalize regardless of state suffix/case)", len(got))
	}
}

func TestHeadToHead(t *testing.T) {
	s := NewStore(testFixtureMatches(), nil)
	got := s.HeadToHead("Flamengo", "Fluminense")
	if len(got.Matches) != 3 {
		t.Fatalf("got %d matches, want 3", len(got.Matches))
	}
	if got.TeamAWins != 1 {
		t.Errorf("expected TeamA (Flamengo) wins = 1, got %d", got.TeamAWins)
	}
	if got.TeamBWins != 1 {
		t.Errorf("expected TeamB (Fluminense) wins = 1, got %d", got.TeamBWins)
	}
	if got.Draws != 1 {
		t.Errorf("expected draws = 1, got %d", got.Draws)
	}
}

func TestHeadToHeadNoMatches(t *testing.T) {
	s := NewStore(testFixtureMatches(), nil)
	got := s.HeadToHead("Flamengo", "Santos")
	if len(got.Matches) != 0 {
		t.Fatalf("got %d matches, want 0", len(got.Matches))
	}
	if got.TeamAWins != 0 || got.TeamBWins != 0 || got.Draws != 0 {
		t.Errorf("expected all-zero record, got %+v", got)
	}
}

func TestTeamRecordHomeOnly(t *testing.T) {
	s := NewStore(testFixtureMatches(), nil)
	rec := s.TeamRecord(TeamRecordFilter{Team: "Flamengo", Venue: "home"})
	// Home matches for Flamengo: 2023-09-03 (2-1 win), 2022-11-06 (3-0 win),
	// 2021-08-15 (0-0 draw).
	if rec.Matches != 3 {
		t.Fatalf("got %d matches, want 3", rec.Matches)
	}
	if rec.Wins != 2 || rec.Draws != 1 || rec.Losses != 0 {
		t.Errorf("unexpected record: W=%d D=%d L=%d", rec.Wins, rec.Draws, rec.Losses)
	}
	if rec.GoalsFor != 5 || rec.GoalsAgainst != 1 {
		t.Errorf("unexpected goals: for=%d against=%d", rec.GoalsFor, rec.GoalsAgainst)
	}
	wantWinRate := 2.0 / 3.0 * 100
	if diff := rec.WinRate - wantWinRate; diff > 0.01 || diff < -0.01 {
		t.Errorf("unexpected win rate: %v, want %v", rec.WinRate, wantWinRate)
	}
}

func TestTeamRecordAllVenuesWithSeasonFilter(t *testing.T) {
	s := NewStore(testFixtureMatches(), nil)
	rec := s.TeamRecord(TeamRecordFilter{Team: "Flamengo", Season: 2023})
	// 2023: away loss vs Fluminense (0-1) and home win vs Fluminense (2-1).
	if rec.Matches != 2 {
		t.Fatalf("got %d matches, want 2", rec.Matches)
	}
	if rec.Wins != 1 || rec.Draws != 0 || rec.Losses != 1 {
		t.Errorf("unexpected record: W=%d D=%d L=%d", rec.Wins, rec.Draws, rec.Losses)
	}
}

func testFixtureLeague() []Match {
	return []Match{
		mkMatch("2020-01-01", "TestLeague", 2020, "A", "B", 2, 1),
		mkMatch("2020-01-08", "TestLeague", 2020, "B", "C", 1, 1),
		mkMatch("2020-01-15", "TestLeague", 2020, "C", "A", 0, 3),
		mkMatch("2020-01-22", "TestLeague", 2020, "B", "A", 0, 0),
		mkMatch("2020-01-29", "TestLeague", 2020, "C", "B", 2, 0),
		mkMatch("2020-02-05", "TestLeague", 2020, "A", "C", 1, 1),
	}
}

func TestStandings(t *testing.T) {
	s := NewStore(testFixtureLeague(), nil)
	table := s.Standings("TestLeague", 2020)
	if len(table) != 3 {
		t.Fatalf("got %d teams, want 3", len(table))
	}

	want := []struct {
		team               string
		played, w, d, l    int
		gf, ga, gd, points int
	}{
		{"A", 4, 2, 2, 0, 6, 2, 4, 8},
		{"C", 4, 1, 2, 1, 4, 5, -1, 5},
		{"B", 4, 0, 2, 2, 2, 5, -3, 2},
	}
	for i, w := range want {
		got := table[i]
		if got.Team != w.team {
			t.Errorf("position %d: got team %q, want %q", i, got.Team, w.team)
			continue
		}
		if got.Played != w.played || got.Wins != w.w || got.Draws != w.d || got.Losses != w.l {
			t.Errorf("%s: got P=%d W=%d D=%d L=%d, want P=%d W=%d D=%d L=%d",
				w.team, got.Played, got.Wins, got.Draws, got.Losses, w.played, w.w, w.d, w.l)
		}
		if got.GoalsFor != w.gf || got.GoalsAgainst != w.ga || got.GoalDiff != w.gd {
			t.Errorf("%s: got GF=%d GA=%d GD=%d, want GF=%d GA=%d GD=%d",
				w.team, got.GoalsFor, got.GoalsAgainst, got.GoalDiff, w.gf, w.ga, w.gd)
		}
		if got.Points != w.points {
			t.Errorf("%s: got points=%d, want %d", w.team, got.Points, w.points)
		}
	}
}

func TestBiggestWins(t *testing.T) {
	matches := []Match{
		mkMatch("2019-10-27", "Brasileirao", 2019, "Flamengo", "Gremio", 5, 0),
		mkMatch("2012-05-27", "Libertadores", 2012, "Santos", "Bolivar", 8, 0),
		mkMatch("2015-09-13", "Brasileirao", 2015, "Palmeiras", "Sao Paulo", 6, 0),
		mkMatch("2023-09-03", "Brasileirao", 2023, "Flamengo", "Fluminense", 1, 1),
	}
	s := NewStore(matches, nil)
	got := s.BiggestWins(BiggestWinsFilter{Limit: 2})
	if len(got) != 2 {
		t.Fatalf("got %d matches, want 2", len(got))
	}
	if got[0].HomeTeam != "Santos" || got[0].AwayTeam != "Bolivar" {
		t.Errorf("expected biggest win first (Santos 8-0 Bolivar), got %+v", got[0])
	}
	if got[1].HomeTeam != "Palmeiras" {
		t.Errorf("expected second biggest win (Palmeiras 6-0), got %+v", got[1])
	}
}

func TestBiggestWinsFilteredByCompetition(t *testing.T) {
	matches := []Match{
		mkMatch("2019-10-27", "Brasileirao", 2019, "Flamengo", "Gremio", 5, 0),
		mkMatch("2012-05-27", "Libertadores", 2012, "Santos", "Bolivar", 8, 0),
	}
	s := NewStore(matches, nil)
	got := s.BiggestWins(BiggestWinsFilter{Competition: "Brasileirao"})
	if len(got) != 1 {
		t.Fatalf("got %d matches, want 1", len(got))
	}
	if got[0].HomeTeam != "Flamengo" {
		t.Errorf("expected Flamengo match, got %+v", got[0])
	}
}

func TestStatsSummary(t *testing.T) {
	matches := []Match{
		mkMatch("2020-01-01", "TestLeague", 2020, "A", "B", 2, 1), // home win
		mkMatch("2020-01-08", "TestLeague", 2020, "B", "C", 1, 1), // draw
		mkMatch("2020-01-15", "TestLeague", 2020, "C", "A", 0, 3), // away win
		mkMatch("2020-01-22", "TestLeague", 2020, "B", "A", 0, 0), // draw
	}
	s := NewStore(matches, nil)
	summary := s.StatsSummary(MatchFilter{Competition: "TestLeague", Season: 2020})
	if summary.TotalMatches != 4 {
		t.Fatalf("got %d matches, want 4", summary.TotalMatches)
	}
	// Total goals: 3+2+3+0 = 8, over 4 matches = 2.0 avg.
	if summary.AvgGoalsPerMatch != 2.0 {
		t.Errorf("unexpected avg goals per match: %v", summary.AvgGoalsPerMatch)
	}
	if summary.HomeWinRate != 25.0 {
		t.Errorf("unexpected home win rate: %v", summary.HomeWinRate)
	}
	if summary.AwayWinRate != 25.0 {
		t.Errorf("unexpected away win rate: %v", summary.AwayWinRate)
	}
	if summary.DrawRate != 50.0 {
		t.Errorf("unexpected draw rate: %v", summary.DrawRate)
	}
}

func testFixturePlayers() []Player {
	return []Player{
		{ID: 1, Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Club: "Paris Saint-Germain", Position: "LW"},
		{ID: 2, Name: "Alisson", Nationality: "Brazil", Overall: 89, Club: "Liverpool", Position: "GK"},
		{ID: 3, Name: "Casemiro", Nationality: "Brazil", Overall: 89, Club: "Real Madrid", Position: "CDM"},
		{ID: 4, Name: "L. Messi", Nationality: "Argentina", Overall: 94, Club: "FC Barcelona", Position: "RF"},
		{ID: 5, Name: "Gabriel Barbosa", Nationality: "Brazil", Overall: 77, Club: "Flamengo", Position: "ST"},
	}
}

func TestSearchPlayersByName(t *testing.T) {
	s := NewStore(nil, testFixturePlayers())
	got := s.SearchPlayers(PlayerFilter{Name: "gabriel barbosa"})
	if len(got) != 1 || got[0].Name != "Gabriel Barbosa" {
		t.Fatalf("got %+v, want Gabriel Barbosa", got)
	}
}

func TestSearchPlayersByNationality(t *testing.T) {
	s := NewStore(nil, testFixturePlayers())
	got := s.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
	if len(got) != 4 {
		t.Fatalf("got %d players, want 4", len(got))
	}
	// Sorted by Overall descending.
	if got[0].Name != "Neymar Jr" {
		t.Errorf("expected Neymar Jr first (highest overall), got %s", got[0].Name)
	}
}

func TestSearchPlayersByClubSubstring(t *testing.T) {
	s := NewStore(nil, testFixturePlayers())
	got := s.SearchPlayers(PlayerFilter{Club: "Flamengo"})
	if len(got) != 1 || got[0].Name != "Gabriel Barbosa" {
		t.Fatalf("got %+v, want Gabriel Barbosa", got)
	}
}

func TestSearchPlayersMinOverallAndLimit(t *testing.T) {
	s := NewStore(nil, testFixturePlayers())
	got := s.SearchPlayers(PlayerFilter{MinOverall: 89, Limit: 2})
	if len(got) != 2 {
		t.Fatalf("got %d players, want 2", len(got))
	}
	if got[0].Overall < got[1].Overall {
		t.Errorf("expected descending overall order, got %d then %d", got[0].Overall, got[1].Overall)
	}
}

func mustParseDate(t *testing.T, s string) time.Time {
	t.Helper()
	d, err := ParseDate(s)
	if err != nil {
		t.Fatalf("ParseDate(%q): %v", s, err)
	}
	return d
}
