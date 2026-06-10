// query_test.go - BDD (Given/When/Then) tests for the query engine of the
// Brazilian Soccer MCP server.
//
// Context: Covers the spec's required capabilities - match queries,
// head-to-head, team statistics, computed league standings (2019 champion
// Flamengo with 90 points), competition aggregates and FIFA player search.
package main

import (
	"strings"
	"testing"
)

func TestFindMatchesBetweenTwoTeams(t *testing.T) {
	// Scenario: Find matches between two teams (Fla-Flu derby).
	// Given the match data is loaded
	s := sharedStore(t)
	// When I search for matches between "Flamengo" and "Fluminense"
	matches := s.FilterMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
	// Then I should receive a list of matches
	if len(matches) < 20 {
		t.Fatalf("expected at least 20 Fla-Flu matches, got %d", len(matches))
	}
	// And each match should have date, scores, and competition
	for _, m := range matches {
		if m.Date.IsZero() {
			t.Errorf("match missing date: %+v", m)
		}
		if m.Competition == "" {
			t.Errorf("match missing competition: %+v", m)
		}
		if m.HomeGoals < 0 || m.AwayGoals < 0 {
			t.Errorf("match has invalid score: %+v", m)
		}
	}
}

func TestFindMatchesBySeasonAndTeam(t *testing.T) {
	// Scenario: "What matches did Palmeiras play in 2023?"
	// Given the match data is loaded
	s := sharedStore(t)
	// When I search for Palmeiras matches in season 2023
	matches := s.FilterMatches(MatchFilter{Team: "Palmeiras", Season: 2023})
	// Then matches from the 2023 season are returned
	if len(matches) < 30 {
		t.Fatalf("expected at least 30 Palmeiras 2023 matches, got %d", len(matches))
	}
	for _, m := range matches {
		if m.Season != 2023 {
			t.Errorf("got match from season %d, want 2023", m.Season)
		}
	}
}

func TestFindMatchesByDateRange(t *testing.T) {
	// Scenario: Find matches in a specific date window.
	// Given the match data is loaded
	s := sharedStore(t)
	from, _ := parseDate("2019-11-01")
	to, _ := parseDate("2019-11-30")
	// When I search for Flamengo matches in November 2019
	matches := s.FilterMatches(MatchFilter{Team: "Flamengo", From: from, To: to})
	// Then every match falls inside the window
	if len(matches) == 0 {
		t.Fatal("expected Flamengo matches in November 2019")
	}
	for _, m := range matches {
		if m.Date.Before(from) || m.Date.After(to.AddDate(0, 0, 1)) {
			t.Errorf("match outside date range: %s", m.Date)
		}
	}
}

func TestHeadToHeadRecord(t *testing.T) {
	// Scenario: Compare Palmeiras and Santos head-to-head.
	// Given the match data is loaded
	s := sharedStore(t)
	// When I request the head-to-head record
	h := s.HeadToHead("Palmeiras", "Santos", "")
	// Then wins, draws and matches are consistent
	if len(h.Matches) == 0 {
		t.Fatal("expected Palmeiras vs Santos matches")
	}
	if h.Wins1+h.Wins2+h.Draws != len(h.Matches) {
		t.Errorf("W1 %d + W2 %d + D %d != total %d", h.Wins1, h.Wins2, h.Draws, len(h.Matches))
	}
}

func TestTeamStatisticsForSeason(t *testing.T) {
	// Scenario: Get team statistics (spec example: Corinthians home record,
	// 2022 Brasileirão: 19 matches).
	// Given the match data is loaded
	s := sharedStore(t)
	// When I request home statistics for Corinthians in season 2022
	total, _, n := s.TeamStats("Corinthians", 2022, "Brasileirão", "home")
	// Then I should receive wins, losses, draws, and goals over 19 home matches
	if n != 19 || total.Played != 19 {
		t.Errorf("Corinthians 2022 home matches = %d, want 19", total.Played)
	}
	if total.Wins+total.Draws+total.Losses != total.Played {
		t.Errorf("record does not add up: %+v", total)
	}
	if total.GoalsFor == 0 {
		t.Error("expected nonzero goals for")
	}
}

func TestStandingsChampion2019(t *testing.T) {
	// Scenario: "Who won the 2019 Brasileirão?" - computed from match results.
	// Given the match data is loaded
	s := sharedStore(t)
	// When I compute the 2019 Série A standings
	rows, n := s.Standings(CompSerieA, 2019)
	// Then the table has 20 teams over 380 matches
	if len(rows) != 20 {
		t.Fatalf("expected 20 teams, got %d", len(rows))
	}
	if n != 380 {
		t.Errorf("expected 380 matches, got %d", n)
	}
	// And Flamengo is champion with 90 points (28W, 6D, 4L)
	top := rows[0]
	if !strings.Contains(normalizeText(top.Team), "flamengo") {
		t.Errorf("2019 champion = %s, want Flamengo", top.Team)
	}
	if top.Points() != 90 || top.Wins != 28 || top.Draws != 6 || top.Losses != 4 {
		t.Errorf("Flamengo 2019 = %d pts (%dW %dD %dL), want 90 pts (28W 6D 4L)",
			top.Points(), top.Wins, top.Draws, top.Losses)
	}
	// And every team played 38 matches
	for _, r := range rows {
		if r.Played != 38 {
			t.Errorf("%s played %d matches, want 38", r.Team, r.Played)
		}
	}
}

func TestStandingsHistoricalSeason(t *testing.T) {
	// Scenario: Standings for a season only covered by the historical dataset.
	// Given the match data is loaded
	s := sharedStore(t)
	// When I compute the 2006 Série A standings
	rows, _ := s.Standings(CompSerieA, 2006)
	// Then São Paulo is champion (real 2006 result)
	if len(rows) == 0 {
		t.Fatal("expected 2006 standings")
	}
	if !strings.Contains(normalizeText(rows[0].Team), "sao paulo") {
		t.Errorf("2006 champion = %s, want São Paulo", rows[0].Team)
	}
}

func TestCompetitionStatistics(t *testing.T) {
	// Scenario: "What's the average goals per match in the Brasileirão?"
	// Given the match data is loaded
	s := sharedStore(t)
	// When I request Brasileirão aggregate statistics
	st := s.CompetitionStats("Brasileirão Série A", 0, 5)
	// Then sensible aggregates are returned
	if st.Matches < 8000 {
		t.Errorf("expected >8000 Série A matches, got %d", st.Matches)
	}
	if avg := st.AvgGoals(); avg < 2.0 || avg > 3.5 {
		t.Errorf("average goals per match = %.2f, expected between 2.0 and 3.5", avg)
	}
	if hwr := st.HomeWinRate(); hwr < 35 || hwr > 60 {
		t.Errorf("home win rate = %.1f%%, expected between 35%% and 60%%", hwr)
	}
	// And the biggest wins are sorted by margin
	if len(st.BiggestWins) != 5 {
		t.Fatalf("expected 5 biggest wins, got %d", len(st.BiggestWins))
	}
	if abs(st.BiggestWins[0].HomeGoals-st.BiggestWins[0].AwayGoals) < 5 {
		t.Errorf("biggest Série A win margin %d, expected >= 5", abs(st.BiggestWins[0].HomeGoals-st.BiggestWins[0].AwayGoals))
	}
}

func TestPlayerSearchByName(t *testing.T) {
	// Scenario: "Who is Neymar?" - search FIFA player data by name.
	// Given the player data is loaded
	s := sharedStore(t)
	// When I search by name
	players := s.SearchPlayers(PlayerFilter{Name: "Neymar"})
	// Then the player is found with ratings and club
	if len(players) == 0 {
		t.Fatal("expected to find Neymar")
	}
	p := players[0]
	if p.Overall != 92 || p.Nationality != "Brazil" {
		t.Errorf("Neymar = overall %d nationality %s, want 92 Brazil", p.Overall, p.Nationality)
	}
}

func TestPlayerSearchBrazilians(t *testing.T) {
	// Scenario: "Find all Brazilian players in the dataset."
	// Given the player data is loaded
	s := sharedStore(t)
	// When I filter by nationality Brazil
	players := s.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
	// Then all 827 Brazilian players are returned, sorted by overall rating
	if len(players) != 827 {
		t.Errorf("expected 827 Brazilian players, got %d", len(players))
	}
	for i := 1; i < len(players); i++ {
		if players[i].Overall > players[i-1].Overall {
			t.Fatal("players not sorted by overall rating")
		}
	}
}

func TestPlayerSearchByClubAndPosition(t *testing.T) {
	// Scenario: Cross-filter players by club and position group.
	// Given the player data is loaded
	s := sharedStore(t)
	// When I search for goalkeepers at Santos
	players := s.SearchPlayers(PlayerFilter{Club: "Santos", Position: "goalkeeper"})
	// Then only Santos goalkeepers are returned
	if len(players) == 0 {
		t.Fatal("expected Santos goalkeepers in FIFA data")
	}
	for _, p := range players {
		if p.Position != "GK" {
			t.Errorf("%s has position %s, want GK", p.Name, p.Position)
		}
		if !strings.Contains(normalizeText(p.Club), "santos") {
			t.Errorf("%s plays for %s, want Santos", p.Name, p.Club)
		}
	}
}

func TestPlayerSearchByMinimumRating(t *testing.T) {
	// Scenario: "Who are the top Brazilian players?" with a rating floor.
	// Given the player data is loaded
	s := sharedStore(t)
	// When I search Brazilians rated 85+
	players := s.SearchPlayers(PlayerFilter{Nationality: "Brazil", MinOverall: 85})
	// Then only highly rated players are returned
	if len(players) == 0 {
		t.Fatal("expected Brazilian players rated 85+")
	}
	for _, p := range players {
		if p.Overall < 85 {
			t.Errorf("%s overall %d below the 85 floor", p.Name, p.Overall)
		}
	}
}

func TestCrossFileQuery(t *testing.T) {
	// Scenario: Cross-file query - a club appears in both match data and
	// FIFA player data.
	// Given both match and player data are loaded
	s := sharedStore(t)
	// When I query Santos matches and Santos players
	matches := s.FilterMatches(MatchFilter{Team: "Santos", Competition: "Brasileirão"})
	players := s.SearchPlayers(PlayerFilter{Club: "Santos"})
	players = func() []Player { // keep only exact-club Santos (not Santos Laguna)
		var out []Player
		for _, p := range players {
			if p.Club == "Santos" {
				out = append(out, p)
			}
		}
		return out
	}()
	// Then both sides return data for the same club
	if len(matches) == 0 {
		t.Error("expected Santos matches")
	}
	if len(players) == 0 {
		t.Error("expected Santos players in FIFA data")
	}
}
