// query_test.go holds the BDD (Given-When-Then) scenarios for the query layer,
// following the testing approach in the specification.
package main

import (
	"strings"
	"testing"
)

// Feature: Match Queries

func TestScenario_FindMatchesBetweenTwoTeams(t *testing.T) {
	// Given the match data is loaded
	store := loadedStore(t)

	// When I search for matches between "Flamengo" and "Fluminense"
	matches := FindMatches(store, MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})

	// Then I should receive a list of matches
	if len(matches) == 0 {
		t.Fatal("expected Fla-Flu matches, got none")
	}
	// And each match should have both teams and a competition
	for _, m := range matches {
		hasFla := strings.Contains(m.HomeKey, "flamengo") || strings.Contains(m.AwayKey, "flamengo")
		hasFlu := strings.Contains(m.HomeKey, "fluminense") || strings.Contains(m.AwayKey, "fluminense")
		if !hasFla || !hasFlu {
			t.Errorf("match does not involve both teams: %s vs %s", m.HomeTeam, m.AwayTeam)
		}
		if m.Competition == "" {
			t.Error("match is missing a competition")
		}
	}
}

func TestScenario_FindMatchesByCompetitionAndSeason(t *testing.T) {
	// Given the match data is loaded
	store := loadedStore(t)

	// When I search for the 2019 Brasileirão Série A season
	matches := FindMatches(store, MatchFilter{Competition: "Brasileirão", Season: 2019})

	// Then a full 20-team double round-robin (380 matches) is returned
	if len(matches) != 380 {
		t.Errorf("2019 Brasileirão returned %d matches, want 380", len(matches))
	}
	// And the competition filter excludes Série B and Série C
	for _, m := range matches {
		if m.Competition != "Brasileirão Série A" {
			t.Errorf("unexpected competition in results: %q", m.Competition)
		}
	}
}

func TestScenario_MatchesAreSortedNewestFirst(t *testing.T) {
	store := loadedStore(t)
	// When I search a team's matches
	matches := FindMatches(store, MatchFilter{Team: "Santos"})
	// Then dated results are ordered newest-first
	var prev int64 = 1 << 62
	for _, m := range matches {
		if !m.HasDate {
			continue
		}
		if u := m.Date.Unix(); u > prev {
			t.Fatal("matches are not sorted newest-first")
		} else {
			prev = u
		}
	}
}

// Feature: Team Queries

func TestScenario_GetTeamStatistics(t *testing.T) {
	// Given the match data is loaded
	store := loadedStore(t)

	// When I request statistics for "Palmeiras" in season "2019"
	rec := ComputeTeamRecord(store, MatchFilter{
		Team: "Palmeiras", Season: 2019, Competition: "Brasileirão",
	})

	// Then I should receive wins, losses, draws and goals
	if rec.Played != 38 {
		t.Errorf("Palmeiras 2019 played %d, want 38", rec.Played)
	}
	if rec.Wins+rec.Draws+rec.Losses != rec.Played {
		t.Errorf("W+D+L (%d) does not equal played (%d)",
			rec.Wins+rec.Draws+rec.Losses, rec.Played)
	}
	if rec.Points() != rec.Wins*3+rec.Draws {
		t.Error("points calculation is inconsistent")
	}
	if rec.GoalsFor == 0 || rec.GoalsAgainst == 0 {
		t.Error("expected non-zero goals for and against")
	}
}

func TestScenario_TeamHomeRecord(t *testing.T) {
	store := loadedStore(t)
	// When I request a team's home-only record for a season
	home := ComputeTeamRecord(store, MatchFilter{
		Team: "Corinthians", Season: 2019, Competition: "Brasileirão", Venue: "home",
	})
	// Then it covers exactly the 19 home fixtures of a 38-game season
	if home.Played != 19 {
		t.Errorf("Corinthians 2019 home matches = %d, want 19", home.Played)
	}
}

// Feature: Statistical Analysis

func TestScenario_HeadToHeadRecord(t *testing.T) {
	store := loadedStore(t)
	// When I compute the head-to-head between two long-standing rivals
	h2h := HeadToHead(store, "Flamengo", "Fluminense", "")
	// Then the wins, draws and losses account for every decided match
	if len(h2h.Matches) == 0 {
		t.Fatal("expected head-to-head matches")
	}
	decided := h2h.Team1Wins + h2h.Team2Wins + h2h.Draws
	if decided == 0 {
		t.Fatal("expected decided results in head-to-head")
	}
	if decided > len(h2h.Matches) {
		t.Errorf("decided results (%d) exceed match count (%d)", decided, len(h2h.Matches))
	}
}

func TestScenario_CompetitionStatistics(t *testing.T) {
	store := loadedStore(t)
	// When I aggregate the 2019 Brasileirão
	stats := ComputeCompetitionStats(store, MatchFilter{Competition: "Brasileirão", Season: 2019})
	// Then it reports a plausible average goals per match and home-win rate
	if stats.Matches != 380 {
		t.Errorf("expected 380 matches, got %d", stats.Matches)
	}
	if stats.AvgGoals() < 1.5 || stats.AvgGoals() > 4.0 {
		t.Errorf("average goals %.2f is implausible", stats.AvgGoals())
	}
	if stats.HomeWinRate() < 20 || stats.HomeWinRate() > 80 {
		t.Errorf("home win rate %.1f%% is implausible", stats.HomeWinRate())
	}
	if len(stats.BiggestWins) == 0 {
		t.Error("expected biggest-wins list to be populated")
	}
}

// Feature: Competition Queries

func TestScenario_LeagueStandings(t *testing.T) {
	// Given the match data is loaded
	store := loadedStore(t)

	// When I calculate the 2019 Brasileirão standings
	rows := Standings(store, "Brasileirão", 2019)

	// Then there are 20 ranked teams
	if len(rows) != 20 {
		t.Fatalf("expected 20 teams in 2019 standings, got %d", len(rows))
	}
	// And Flamengo are champions on 90 points (the known 2019 result)
	champ := rows[0]
	if !strings.Contains(normalizeTeamKey(champ.Team), "flamengo") {
		t.Errorf("expected Flamengo as champion, got %q", champ.Team)
	}
	if champ.Points() != 90 {
		t.Errorf("expected champion on 90 points, got %d", champ.Points())
	}
	if champ.Played != 38 {
		t.Errorf("expected champion to have played 38, got %d", champ.Played)
	}
	// And the table is sorted by points descending
	for i := 1; i < len(rows); i++ {
		if rows[i-1].Points() < rows[i].Points() {
			t.Errorf("standings not sorted at rank %d", i+1)
		}
	}
}

// Feature: Player Queries

func TestScenario_FindBrazilianPlayers(t *testing.T) {
	// Given the player data is loaded
	store := loadedStore(t)

	// When I search for players with nationality "Brazil"
	players := SearchPlayers(store, PlayerFilter{Nationality: "Brazil"})

	// Then I receive a substantial list, all Brazilian, sorted by rating
	if len(players) < 500 {
		t.Errorf("expected many Brazilian players, got %d", len(players))
	}
	for _, p := range players {
		if !strings.Contains(normalizeText(p.Nationality), "brazil") {
			t.Errorf("non-Brazilian player in results: %s (%s)", p.Name, p.Nationality)
		}
	}
	for i := 1; i < len(players); i++ {
		if players[i-1].Overall < players[i].Overall {
			t.Error("players not sorted by overall rating")
			break
		}
	}
}

func TestScenario_SearchPlayerByName(t *testing.T) {
	store := loadedStore(t)
	// When I search for a player by name
	players := SearchPlayers(store, PlayerFilter{Name: "Neymar"})
	// Then a matching Brazilian player is found
	if len(players) == 0 {
		t.Fatal("expected to find Neymar")
	}
	if !strings.Contains(normalizeText(players[0].Nationality), "brazil") {
		t.Errorf("expected Neymar to be Brazilian, got %q", players[0].Nationality)
	}
}

func TestScenario_FilterPlayersByClub(t *testing.T) {
	store := loadedStore(t)
	// When I filter players by a Brazilian club present in the FIFA data
	players := SearchPlayers(store, PlayerFilter{Club: "Santos"})
	// Then every result belongs to that club
	if len(players) == 0 {
		t.Fatal("expected Santos players in FIFA data")
	}
	for _, p := range players {
		if !strings.Contains(p.ClubKey, "santos") {
			t.Errorf("player %s is at %q, expected Santos", p.Name, p.Club)
		}
	}
}

func TestScenario_FilterPlayersByMinimumRating(t *testing.T) {
	store := loadedStore(t)
	// When I require a minimum overall rating
	players := SearchPlayers(store, PlayerFilter{Nationality: "Brazil", MinOverall: 85})
	// Then every returned player meets the threshold
	for _, p := range players {
		if p.Overall < 85 {
			t.Errorf("player %s has overall %d, below threshold", p.Name, p.Overall)
		}
	}
}
