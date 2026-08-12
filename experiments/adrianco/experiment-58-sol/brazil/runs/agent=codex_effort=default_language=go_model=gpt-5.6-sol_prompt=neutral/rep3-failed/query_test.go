package main

import (
	"testing"
	"time"
)

func testDate(s string) time.Time { t, _ := time.Parse("2006-01-02", s); return t }

func syntheticDB() *Database {
	db := &Database{Matches: []Match{
		{Date: testDate("2022-01-01"), Competition: "Brasileirão Série A", Season: 2022, HomeTeam: "Alpha-SP", AwayTeam: "Beta-RJ", HomeGoals: 2, AwayGoals: 0, Source: "Brasileirao_Matches.csv"},
		{Date: testDate("2022-02-01"), Competition: "Brasileirão Série A", Season: 2022, HomeTeam: "Beta-RJ", AwayTeam: "Alpha-SP", HomeGoals: 1, AwayGoals: 1, Source: "Brasileirao_Matches.csv"},
		{Date: testDate("2022-03-01"), Competition: "Brasileirão Série A", Season: 2022, HomeTeam: "Alpha-SP", AwayTeam: "Gamma-MG", HomeGoals: 0, AwayGoals: 1, Source: "Brasileirao_Matches.csv"},
		// An overlapping lower-priority source must not inflate calculations.
		{Date: testDate("2022-01-02"), Competition: "Brasileirão Série A", Season: 2022, HomeTeam: "Alpha", AwayTeam: "Beta", HomeGoals: 2, AwayGoals: 0, Source: "novo_campeonato_brasileiro.csv"},
	}, Players: []Player{
		{ID: 1, Name: "Jogador Um", Nationality: "Brazil", Overall: 80, Club: "Alpha", Position: "ST"},
		{ID: 2, Name: "Jogador Dois", Nationality: "Brazil", Overall: 85, Club: "Beta", Position: "GK"},
	}}
	db.sort()
	return db
}

func TestSearchMatchesNormalizesNamesAndFilters(t *testing.T) {
	db := syntheticDB()
	got := db.SearchMatches(MatchFilter{Team: "Álpha", Opponent: "Beta", Season: 2022, Limit: 10})
	if len(got) != 3 {
		t.Fatalf("expected union view to retain 3 source records, got %d", len(got))
	}
	if got[0].HomeTeam != "Beta-RJ" {
		t.Fatalf("results not newest-first: %+v", got[0])
	}
}

func TestStatisticsUseAuthoritativeSource(t *testing.T) {
	db := syntheticDB()
	stats := db.TeamStatistics("Alpha", MatchFilter{Competition: "Serie A", Season: 2022})
	if stats.Matches != 3 || stats.Wins != 1 || stats.Draws != 1 || stats.Losses != 1 || stats.GoalsFor != 3 || stats.GoalsAgainst != 2 || stats.Points != 4 {
		t.Fatalf("unexpected stats: %+v", stats)
	}
	h := db.HeadToHead("Alpha", "Beta", MatchFilter{Season: 2022, Limit: 10})
	if h.Matches != 2 || h.Team1Wins != 1 || h.Draws != 1 {
		t.Fatalf("unexpected head-to-head: %+v", h)
	}
}

func TestStandingsAndTieBreaks(t *testing.T) {
	table := syntheticDB().Standings("Brasileirao", 2022)
	if len(table) != 3 {
		t.Fatalf("got %d teams", len(table))
	}
	if table[0].Team != "Alpha" || table[0].Points != 4 || table[0].Played != 3 {
		t.Fatalf("unexpected leader: %+v", table[0])
	}
	if table[1].Team != "Gamma" || table[1].Points != 3 {
		t.Fatalf("unexpected second place: %+v", table[1])
	}
}

func TestPlayerFiltersOrderByRating(t *testing.T) {
	players := syntheticDB().SearchPlayers(PlayerFilter{Nationality: "brasil", Limit: 10})
	if len(players) != 2 || players[0].Overall != 85 {
		t.Fatalf("unexpected players: %+v", players)
	}
	forwards := syntheticDB().SearchPlayers(PlayerFilter{Position: "forwards", Limit: 10})
	if len(forwards) != 1 || forwards[0].Name != "Jogador Um" {
		t.Fatalf("unexpected forwards: %+v", forwards)
	}
}
