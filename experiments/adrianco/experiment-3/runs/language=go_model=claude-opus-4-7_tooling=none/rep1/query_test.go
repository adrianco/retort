// BDD scenarios for the query layer: match, team, player, competition and
// statistical queries.
package main

import (
	"strings"
	"testing"
)

// Feature: Match Queries
//
// Scenario: Find matches between two teams.
func TestScenario_FindMatchesBetweenTwoTeams(t *testing.T) {
	// Given the match data is loaded
	db := testDB(t)
	// When I search for matches between "Flamengo" and "Fluminense"
	matches := db.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
	// Then I should receive a list of matches
	if len(matches) < 20 {
		t.Fatalf("expected many Fla-Flu matches, got %d", len(matches))
	}
	// And each match should have date, scores and competition
	for _, m := range matches {
		if !m.HasDate {
			t.Errorf("match missing date: %s vs %s", m.HomeTeam, m.AwayTeam)
		}
		if m.Competition == "" {
			t.Errorf("match missing competition")
		}
		// And each match must actually involve both teams
		fla := identityMatches(m.HomeID, "Flamengo") || identityMatches(m.AwayID, "Flamengo")
		flu := identityMatches(m.HomeID, "Fluminense") || identityMatches(m.AwayID, "Fluminense")
		if !fla || !flu {
			t.Errorf("unrelated match returned: %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
}

// Scenario: Filter matches by season and competition.
func TestScenario_FindMatchesBySeasonAndCompetition(t *testing.T) {
	// Given the match data is loaded
	db := testDB(t)
	// When I request Palmeiras' 2019 Brasileirão matches
	matches := db.FindMatches(MatchFilter{
		Team: "Palmeiras", Competition: "Brasileirão Série A",
		Season: 2019, HasSeason: true,
	})
	// Then every result is from the 2019 season
	if len(matches) == 0 {
		t.Fatal("expected Palmeiras matches in 2019")
	}
	for _, m := range matches {
		if m.Season != 2019 {
			t.Errorf("match outside requested season: %d", m.Season)
		}
	}
	// And a full league season is 38 matches
	if len(matches) != 38 {
		t.Errorf("expected 38 league matches for Palmeiras in 2019, got %d", len(matches))
	}
}

// Feature: Team Queries
//
// Scenario: Get team statistics for a season.
func TestScenario_TeamStatisticsForSeason(t *testing.T) {
	// Given the match data is loaded
	db := testDB(t)
	// When I request statistics for Flamengo in the 2019 Brasileirão
	s := db.ComputeTeamStats("Flamengo", "Brasileirão Série A", 2019, true, "")
	// Then I should receive wins, losses, draws and goals
	if s.Played != 38 {
		t.Fatalf("expected 38 matches, got %d", s.Played)
	}
	if s.Wins+s.Draws+s.Losses != s.Played {
		t.Errorf("W/D/L do not sum to matches played")
	}
	// And Flamengo, the 2019 champions, had a strong record
	if s.Points() != 90 {
		t.Errorf("expected 90 points for 2019 champions Flamengo, got %d", s.Points())
	}
	if s.GoalsFor <= s.GoalsAgst {
		t.Errorf("champions expected positive goal difference")
	}
}

// Scenario: A team's home record is a subset of its full record.
func TestScenario_TeamHomeRecord(t *testing.T) {
	// Given the match data is loaded
	db := testDB(t)
	// When I request Corinthians' overall and home records for 2022
	all := db.ComputeTeamStats("Corinthians", "Brasileirão Série A", 2022, true, "")
	home := db.ComputeTeamStats("Corinthians", "Brasileirão Série A", 2022, true, "home")
	// Then the home record covers fewer matches than the full record
	if home.Played == 0 || home.Played >= all.Played {
		t.Errorf("home matches (%d) should be a non-empty subset of all (%d)",
			home.Played, all.Played)
	}
}

// Scenario: Compare two teams head-to-head.
func TestScenario_HeadToHead(t *testing.T) {
	// Given the match data is loaded
	db := testDB(t)
	// When I compare Palmeiras and Santos head-to-head
	h := db.HeadToHead("Palmeiras", "Santos", "", 0, false)
	// Then the win/draw counts are consistent with the matches found
	scored := 0
	for _, m := range h.Matches {
		if m.HasScore {
			scored++
		}
	}
	if h.AWins+h.BWins+h.Draws != scored {
		t.Errorf("wins+draws (%d) != scored matches (%d)",
			h.AWins+h.BWins+h.Draws, scored)
	}
	if len(h.Matches) < 10 {
		t.Errorf("expected many Palmeiras-Santos meetings, got %d", len(h.Matches))
	}
}

// Feature: Competition Queries
//
// Scenario: Calculate final standings for a season.
func TestScenario_CompetitionStandings(t *testing.T) {
	// Given the match data is loaded
	db := testDB(t)
	// When I calculate the 2019 Brasileirão Série A standings
	table := db.Standings("Brasileirão Série A", 2019)
	// Then the table has the 20 Série A teams
	if len(table) != 20 {
		t.Fatalf("expected 20 teams in 2019 Série A, got %d", len(table))
	}
	// And the champion is Flamengo with 90 points
	if !strings.Contains(table[0].Team, "Flamengo") {
		t.Errorf("expected Flamengo as 2019 champion, got %q", table[0].Team)
	}
	if table[0].Points() != 90 {
		t.Errorf("expected champion on 90 points, got %d", table[0].Points())
	}
	// And the table is sorted by points (descending)
	for i := 1; i < len(table); i++ {
		if table[i-1].Points() < table[i].Points() {
			t.Errorf("standings not sorted by points at row %d", i)
		}
	}
}

// Feature: Player Queries
//
// Scenario: Find Brazilian players.
func TestScenario_FindBrazilianPlayers(t *testing.T) {
	// Given the player data is loaded
	db := testDB(t)
	// When I search for players with nationality "Brazil"
	players := db.SearchPlayers(PlayerFilter{Nationality: "Brazil", SortBy: "overall"})
	// Then I should receive many players
	if len(players) < 300 {
		t.Fatalf("expected many Brazilian players, got %d", len(players))
	}
	// And they are all Brazilian
	for _, p := range players {
		if p.Nationality != "Brazil" {
			t.Errorf("non-Brazilian player returned: %s (%s)", p.Name, p.Nationality)
		}
	}
	// And they are sorted by overall rating (descending)
	for i := 1; i < len(players); i++ {
		if players[i-1].Overall < players[i].Overall {
			t.Errorf("players not sorted by overall at index %d", i)
		}
	}
}

// Scenario: Filter players by minimum rating.
func TestScenario_FilterPlayersByRating(t *testing.T) {
	// Given the player data is loaded
	db := testDB(t)
	// When I search for players rated 85 or higher
	players := db.SearchPlayers(PlayerFilter{MinOverall: 85})
	// Then every result meets the rating threshold
	if len(players) == 0 {
		t.Fatal("expected some highly-rated players")
	}
	for _, p := range players {
		if p.Overall < 85 {
			t.Errorf("player below threshold returned: %s (%d)", p.Name, p.Overall)
		}
	}
}

// Feature: Statistical Analysis
//
// Scenario: Aggregate statistics for a season.
func TestScenario_AggregateStatistics(t *testing.T) {
	// Given the match data is loaded
	db := testDB(t)
	// When I compute statistics for the 2019 Brasileirão Série A
	agg := db.ComputeAggStats("Brasileirão Série A", 2019, true, 5)
	// Then a full season is 380 matches
	if agg.Scored != 380 {
		t.Errorf("expected 380 scored matches, got %d", agg.Scored)
	}
	// And the average goals per match is realistic
	if agg.AvgGoals() < 1.5 || agg.AvgGoals() > 4.0 {
		t.Errorf("implausible average goals per match: %.2f", agg.AvgGoals())
	}
	// And home/away/draw rates sum to ~100%
	total := agg.HomeWinRate() + agg.AwayWinRate() + agg.DrawRate()
	if total < 99.5 || total > 100.5 {
		t.Errorf("win/draw rates sum to %.1f%%, expected ~100%%", total)
	}
	// And the biggest wins are ordered by goal margin
	for i := 1; i < len(agg.BiggestWins); i++ {
		if agg.BiggestWins[i-1].GoalMargin() < agg.BiggestWins[i].GoalMargin() {
			t.Errorf("biggest wins not ordered by margin at index %d", i)
		}
	}
}

// Scenario: List the competitions in the dataset.
func TestScenario_ListCompetitions(t *testing.T) {
	// Given the match data is loaded
	db := testDB(t)
	// When I list the competitions
	comps := db.Competitions()
	// Then the major Brazilian competitions are present
	found := map[string]bool{}
	for _, c := range comps {
		found[c.Name] = true
		if c.Matches == 0 {
			t.Errorf("competition %q has no matches", c.Name)
		}
	}
	for _, want := range []string{"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"} {
		if !found[want] {
			t.Errorf("expected competition %q to be listed", want)
		}
	}
}
