package mcpserver

import (
	"strings"
	"testing"

	"brazilian-soccer-mcp/internal/soccer"
)

func mustDate(t *testing.T, s string) soccer.Match {
	t.Helper()
	d, err := soccer.ParseDate(s)
	if err != nil {
		t.Fatal(err)
	}
	return soccer.Match{Date: d}
}

func TestFormatMatch(t *testing.T) {
	m := soccer.Match{
		Competition: "Brasileirao",
		Round:       "22",
		HomeTeam:    "Flamengo",
		AwayTeam:    "Fluminense",
		HomeGoals:   2,
		AwayGoals:   1,
	}
	m.Date = mustDate(t, "2023-09-03").Date

	got := FormatMatch(m)
	want := "2023-09-03: Flamengo 2-1 Fluminense (Brasileirao Round 22)"
	if got != want {
		t.Errorf("FormatMatch() = %q, want %q", got, want)
	}
}

func TestFormatMatchNoRound(t *testing.T) {
	m := soccer.Match{
		Competition: "Libertadores",
		HomeTeam:    "River Plate",
		AwayTeam:    "Boca Juniors",
		HomeGoals:   3,
		AwayGoals:   1,
	}
	m.Date = mustDate(t, "2018-12-08").Date

	got := FormatMatch(m)
	want := "2018-12-08: River Plate 3-1 Boca Juniors (Libertadores)"
	if got != want {
		t.Errorf("FormatMatch() = %q, want %q", got, want)
	}
}

func TestFormatMatchesEmpty(t *testing.T) {
	got := FormatMatches(nil)
	if !strings.Contains(got, "No matches found") {
		t.Errorf("FormatMatches(nil) = %q, want a no-matches message", got)
	}
}

func TestFormatHeadToHead(t *testing.T) {
	r := soccer.HeadToHeadResult{
		TeamA:     "Flamengo",
		TeamB:     "Fluminense",
		TeamAWins: 1,
		TeamBWins: 1,
		Draws:     1,
	}
	got := FormatHeadToHead(r)
	if !strings.Contains(got, "Flamengo 1 wins") || !strings.Contains(got, "Fluminense 1 wins") || !strings.Contains(got, "1 draws") {
		t.Errorf("FormatHeadToHead() = %q, missing expected record summary", got)
	}
}

func TestFormatTeamRecord(t *testing.T) {
	r := soccer.TeamRecord{
		Team: "Corinthians", Matches: 19, Wins: 11, Draws: 5, Losses: 3,
		GoalsFor: 28, GoalsAgainst: 15, WinRate: 57.9,
	}
	got := FormatTeamRecord(r)
	if !strings.Contains(got, "Corinthians") || !strings.Contains(got, "Wins: 11") || !strings.Contains(got, "57.9%") {
		t.Errorf("FormatTeamRecord() = %q, missing expected fields", got)
	}
}

func TestFormatStandings(t *testing.T) {
	table := []soccer.StandingEntry{
		{Team: "Flamengo", Played: 38, Wins: 28, Draws: 6, Losses: 4, GoalsFor: 88, GoalsAgainst: 40, GoalDiff: 48, Points: 90},
	}
	got := FormatStandings(table, "Brasileirao", 2019)
	if !strings.Contains(got, "1. Flamengo - 90 pts") {
		t.Errorf("FormatStandings() = %q, missing expected standing line", got)
	}
}

func TestFormatStatsSummary(t *testing.T) {
	sum := soccer.Summary{TotalMatches: 100, AvgGoalsPerMatch: 2.47, HomeWinRate: 47.3, AwayWinRate: 30.0, DrawRate: 22.7}
	got := FormatStatsSummary(sum)
	if !strings.Contains(got, "2.47") || !strings.Contains(got, "47.3%") {
		t.Errorf("FormatStatsSummary() = %q, missing expected fields", got)
	}
}

func TestFormatPlayers(t *testing.T) {
	players := []soccer.Player{
		{Name: "Neymar Jr", Overall: 92, Position: "LW", Club: "Paris Saint-Germain"},
	}
	got := FormatPlayers(players)
	if !strings.Contains(got, "1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain") {
		t.Errorf("FormatPlayers() = %q, missing expected player line", got)
	}
}

func TestFormatPlayersEmpty(t *testing.T) {
	got := FormatPlayers(nil)
	if !strings.Contains(got, "No players found") {
		t.Errorf("FormatPlayers(nil) = %q, want a no-players message", got)
	}
}
