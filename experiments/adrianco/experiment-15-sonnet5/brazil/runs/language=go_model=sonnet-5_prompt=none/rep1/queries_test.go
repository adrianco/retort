package main

import "testing"

// buildTestStore assembles a small, hand-crafted set of matches and players
// covering enough scenarios to exercise every query without touching disk.
func buildTestStore() *Store {
	s := newStore()

	// Brasileirão 2019: Flamengo win the title, Santos second.
	add := func(home, away string, hg, ag, season int, comp string) {
		s.addMatch(Match{
			Competition: comp,
			Season:      season,
			HomeTeam:    home,
			AwayTeam:    away,
			HomeGoals:   hg,
			AwayGoals:   ag,
			HasGoals:    true,
			DateStr:     "2019-01-01",
		})
	}
	add("Flamengo-RJ", "Santos-SP", 2, 1, 2019, "Brasileirão")
	add("Santos-SP", "Flamengo-RJ", 0, 0, 2019, "Brasileirão")
	add("Flamengo-RJ", "Palmeiras-SP", 3, 0, 2019, "Brasileirão")
	add("Palmeiras-SP", "Santos-SP", 1, 1, 2019, "Brasileirão")
	add("Flamengo-RJ", "Fluminense-RJ", 5, 0, 2019, "Brasileirão")
	// A Fla-Flu match in a different competition/season for filter tests.
	add("Fluminense-RJ", "Flamengo-RJ", 1, 2, 2020, "Copa do Brasil")

	s.addPlayer(Player{Name: "Gabriel Barbosa", Nationality: "Brazil", Overall: 82, Club: "Flamengo", Position: "ST"})
	s.addPlayer(Player{Name: "Diego Alves", Nationality: "Brazil", Overall: 80, Club: "Flamengo", Position: "GK"})
	s.addPlayer(Player{Name: "L. Messi", Nationality: "Argentina", Overall: 94, Club: "FC Barcelona", Position: "RF"})

	return s
}

func TestStandingsBrasileirao2019(t *testing.T) {
	s := buildTestStore()
	res := s.Standings(2019, "Brasileirão")
	if res.Champion != "Flamengo-RJ" {
		t.Fatalf("Champion = %q, want Flamengo-RJ", res.Champion)
	}
	var flamengo StandingsRow
	for _, row := range res.Table {
		if row.Team == "Flamengo-RJ" {
			flamengo = row
		}
	}
	// 4 matches: 3 wins, 1 draw => 10 points, GF 10 GA 1.
	if flamengo.Points != 10 || flamengo.Won != 3 || flamengo.Drawn != 1 || flamengo.Lost != 0 {
		t.Fatalf("Flamengo row = %+v, want 10 pts / 3W 1D 0L", flamengo)
	}
	if flamengo.GoalsFor != 10 || flamengo.GoalsAgainst != 1 {
		t.Fatalf("Flamengo goals = %+v", flamengo)
	}
	for i, row := range res.Table {
		if row.Position != i+1 {
			t.Fatalf("table not positioned correctly: %+v", res.Table)
		}
	}
}

func TestHeadToHead(t *testing.T) {
	s := buildTestStore()
	res, ok := s.HeadToHead("Flamengo", "Fluminense", "", 0, 10)
	if !ok {
		t.Fatal("HeadToHead(Flamengo, Fluminense) resolution failed")
	}
	if res.Summary.MatchesPlayed != 2 {
		t.Fatalf("MatchesPlayed = %d, want 2", res.Summary.MatchesPlayed)
	}
	if res.Summary.TeamAWins != 2 || res.Summary.TeamBWins != 0 {
		t.Fatalf("summary = %+v, want Flamengo 2-0", res.Summary)
	}
	if res.Summary.TeamAGoals != 7 || res.Summary.TeamBGoals != 1 {
		t.Fatalf("goals = %+v, want 7-1", res.Summary)
	}

	// Filtered by competition, only the 2020 Copa do Brasil match remains.
	filtered, ok := s.HeadToHead("Flamengo", "Fluminense", "Copa do Brasil", 0, 10)
	if !ok || filtered.Summary.MatchesPlayed != 1 {
		t.Fatalf("competition-filtered H2H = %+v, ok=%v", filtered.Summary, ok)
	}
}

func TestHeadToHeadUnknownTeam(t *testing.T) {
	s := buildTestStore()
	if _, ok := s.HeadToHead("Flamengo", "Nonexistent FC", "", 0, 10); ok {
		t.Fatal("expected HeadToHead to fail for an unresolvable team")
	}
}

func TestTeamRecordVenueFilter(t *testing.T) {
	s := buildTestStore()
	home, ok := s.TeamRecord("Flamengo", 2019, "", "home")
	if !ok {
		t.Fatal("TeamRecord resolution failed")
	}
	// Flamengo has 3 home matches in 2019 in the fixture.
	if home.Played != 3 || home.Won != 3 {
		t.Fatalf("home record = %+v, want 3 played / 3 won", home)
	}
	if home.WinRatePct != 100 {
		t.Fatalf("win rate = %v, want 100", home.WinRatePct)
	}

	away, ok := s.TeamRecord("Flamengo", 2019, "", "away")
	if !ok || away.Played != 1 || away.Drawn != 1 {
		t.Fatalf("away record = %+v, ok=%v, want 1 played / 1 draw", away, ok)
	}
}

func TestTeamRecordSquadPlayers(t *testing.T) {
	s := buildTestStore()
	rec, ok := s.TeamRecord("Flamengo", 0, "", "")
	if !ok {
		t.Fatal("TeamRecord resolution failed")
	}
	if len(rec.SquadPlayers) != 2 {
		t.Fatalf("SquadPlayers = %+v, want 2 (Gabriel Barbosa, Diego Alves)", rec.SquadPlayers)
	}
	if rec.SquadPlayers[0].Name != "Gabriel Barbosa" {
		t.Fatalf("expected highest-overall player first, got %+v", rec.SquadPlayers[0])
	}
}

func TestSearchMatchesBothTeams(t *testing.T) {
	s := buildTestStore()
	res := s.SearchMatches("Flamengo", "Santos", "", 0, "", "", 10)
	if res.TotalMatches != 2 {
		t.Fatalf("TotalMatches = %d, want 2", res.TotalMatches)
	}
	if res.HeadToHead == nil || res.HeadToHead.TeamAWins != 1 || res.HeadToHead.Draws != 1 {
		t.Fatalf("head to head = %+v", res.HeadToHead)
	}
}

func TestSearchMatchesUnknownTeamNotesIt(t *testing.T) {
	s := buildTestStore()
	res := s.SearchMatches("Nonexistent FC", "", "", 0, "", "", 10)
	if res.TotalMatches != 0 || res.Note == "" {
		t.Fatalf("expected zero matches and a note, got %+v", res)
	}
}

func TestStatsOverview(t *testing.T) {
	s := buildTestStore()
	res := s.StatsOverview("Brasileirão", 2019)
	if res.TotalMatches != 5 {
		t.Fatalf("TotalMatches = %d, want 5", res.TotalMatches)
	}
	// Goals: 3, 0, 3, 2, 5 = 13 total across 5 matches => avg 2.6
	if res.AvgGoalsPerMatch != 2.6 {
		t.Fatalf("AvgGoalsPerMatch = %v, want 2.6", res.AvgGoalsPerMatch)
	}
	if len(res.BiggestWins) == 0 || res.BiggestWins[0].GoalDifference != 5 {
		t.Fatalf("BiggestWins = %+v, want top diff 5 (Flamengo 5-0 Fluminense)", res.BiggestWins)
	}
}

func TestSearchPlayers(t *testing.T) {
	s := buildTestStore()
	res := s.SearchPlayers("", "Brazil", "Flamengo", "", 0, 10)
	if res.TotalFound != 2 {
		t.Fatalf("TotalFound = %d, want 2", res.TotalFound)
	}
	if res.Players[0].Name != "Gabriel Barbosa" {
		t.Fatalf("expected Gabriel Barbosa first (higher overall), got %+v", res.Players[0])
	}

	byName := s.SearchPlayers("Messi", "", "", "", 0, 10)
	if byName.TotalFound != 1 || byName.Players[0].Nationality != "Argentina" {
		t.Fatalf("name search = %+v", byName)
	}

	byRating := s.SearchPlayers("", "", "", "", 90, 10)
	if byRating.TotalFound != 1 || byRating.Players[0].Name != "L. Messi" {
		t.Fatalf("min_overall filter = %+v", byRating)
	}
}
