// Brazilian Soccer MCP Server
//
// File: store_test.go
// Responsibility: Behavior-Driven (Given/When/Then) tests for the query engine.
// Each test builds a small, deterministic in-memory Store fixture so the
// expected results are known exactly, then exercises one capability area:
// finding matches, team records, head-to-head, computed standings, competition
// statistics and player search. This complements loader_test.go, which checks
// the engine against the real bundled datasets.
package main

import "testing"

// fixtureStore builds a Store with a hand-crafted mini Brasileirão season so
// assertions can be exact. Two clubs share the base name "Atletico" to exercise
// suffix handling.
func fixtureStore() *Store {
	s := NewStore()
	add := func(date, home, hState, away, aState string, hg, ag, season int, comp, source string) {
		d, _ := parseDate(date)
		s.Matches = append(s.Matches, Match{
			Date:        d,
			HasDate:     true,
			HomeTeam:    teamDisplay(home, hState),
			AwayTeam:    teamDisplay(away, aState),
			HomeKey:     teamFullKey(home, hState),
			AwayKey:     teamFullKey(away, aState),
			HomeBase:    teamBaseKey(home),
			AwayBase:    teamBaseKey(away),
			HomeGoal:    hg,
			AwayGoal:    ag,
			HasScore:    true,
			Season:      season,
			Competition: comp,
			Source:      source,
		})
	}
	const comp = "Brasileirão Série A"
	const src = "Brasileirao_Matches.csv"
	// A tiny 3-team double round robin for 2023.
	add("2023-05-01", "Flamengo-RJ", "RJ", "Palmeiras-SP", "SP", 2, 1, 2023, comp, src)
	add("2023-05-08", "Palmeiras-SP", "SP", "Flamengo-RJ", "RJ", 0, 0, 2023, comp, src)
	add("2023-05-15", "Flamengo-RJ", "RJ", "Atletico-MG", "MG", 3, 0, 2023, comp, src)
	add("2023-05-22", "Atletico-MG", "MG", "Flamengo-RJ", "RJ", 1, 1, 2023, comp, src)
	add("2023-05-29", "Palmeiras-SP", "SP", "Atletico-MG", "MG", 2, 2, 2023, comp, src)
	add("2023-06-05", "Atletico-MG", "MG", "Palmeiras-SP", "SP", 0, 1, 2023, comp, src)
	// A different-state namesake that must stay distinct from Atletico-MG.
	add("2023-06-12", "Flamengo-RJ", "RJ", "Atletico-PR", "PR", 4, 0, 2023, comp, src)
	// The SAME Flamengo-Palmeiras game duplicated from another dataset (no
	// suffix, different source) to exercise de-duplication.
	add("2023-05-01", "Flamengo", "", "Palmeiras", "", 2, 1, 2023, comp, "BR-Football-Dataset.csv")
	s.Index()
	return s
}

// Scenario: Find matches between two teams.
func TestFindMatchesBetweenTeams(t *testing.T) {
	// Given the match data is loaded
	s := fixtureStore()
	// When I search for matches between "Flamengo" and "Palmeiras"
	got := s.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Palmeiras", Dedup: true})
	// Then I should receive exactly the two meetings (the duplicate collapses)
	if len(got) != 2 {
		t.Fatalf("expected 2 deduped meetings, got %d", len(got))
	}
	// And each match should have a date and a score
	for _, m := range got {
		if !m.HasDate || !m.HasScore {
			t.Errorf("match missing date/score: %+v", m)
		}
	}
}

// Scenario: A bare team query is state-insensitive but distinct clubs stay apart.
func TestFindMatchesSuffixHandling(t *testing.T) {
	// Given the match data is loaded
	s := fixtureStore()
	// When I search for "Atletico-MG" specifically
	mg := s.FindMatches(MatchFilter{Team: "Atletico-MG"})
	// Then the Atletico-PR game is excluded
	for _, m := range mg {
		if m.HomeBase == "atletico" && (m.HomeKey == "atletico-pr" || m.AwayKey == "atletico-pr") {
			t.Errorf("Atletico-MG query leaked an Atletico-PR match: %s", formatMatch(m))
		}
	}
	// And a bare "Atletico" query reaches both namesakes
	all := s.FindMatches(MatchFilter{Team: "Atletico"})
	if len(all) <= len(mg) {
		t.Errorf("bare 'Atletico' (%d) should match more games than 'Atletico-MG' (%d)", len(all), len(mg))
	}
}

// Scenario: Get team statistics for a season.
func TestTeamStats(t *testing.T) {
	// Given the match data is loaded
	s := fixtureStore()
	// When I request statistics for "Flamengo" in season 2023
	rec := s.TeamStats("Flamengo", MatchFilter{Season: 2023})
	// Then I should receive wins, draws, losses and goals
	// Flamengo games: W vs Pal(2-1), D vs Pal(0-0), W vs AtlMG(3-0), D vs AtlMG(1-1), W vs AtlPR(4-0)
	if rec.Matches != 5 {
		t.Fatalf("expected 5 matches, got %d", rec.Matches)
	}
	if rec.Wins != 3 || rec.Draws != 2 || rec.Losses != 0 {
		t.Errorf("record = %dW %dD %dL, want 3W 2D 0L", rec.Wins, rec.Draws, rec.Losses)
	}
	if rec.GoalsFor != 10 || rec.GoalsAgainst != 2 {
		t.Errorf("goals = %d-%d, want 10-2", rec.GoalsFor, rec.GoalsAgainst)
	}
	if rec.Points() != 11 {
		t.Errorf("points = %d, want 11", rec.Points())
	}
}

// Scenario: Home/away filtering.
func TestTeamStatsHomeOnly(t *testing.T) {
	// Given the match data is loaded
	s := fixtureStore()
	// When I request Flamengo's home record
	rec := s.TeamStats("Flamengo", MatchFilter{Season: 2023, HomeAway: "home"})
	// Then only home games count (vs Pal 2-1, vs AtlMG 3-0, vs AtlPR 4-0)
	if rec.Matches != 3 || rec.Wins != 3 {
		t.Errorf("home record = %d matches %dW, want 3 matches 3W", rec.Matches, rec.Wins)
	}
}

// Scenario: Head-to-head record.
func TestHeadToHead(t *testing.T) {
	// Given the match data is loaded
	s := fixtureStore()
	// When I compare Flamengo and Atletico-MG head-to-head
	h := s.HeadToHead("Flamengo", "Atletico-MG")
	// Then I should receive their aggregate record (W 3-0, D 1-1)
	if h.Team1Wins != 1 || h.Draws != 1 || h.Team2Wins != 0 {
		t.Errorf("H2H = %dW-%dD-%dL, want 1-1-0", h.Team1Wins, h.Draws, h.Team2Wins)
	}
	if h.Team1Goals != 4 || h.Team2Goals != 1 {
		t.Errorf("H2H goals = %d-%d, want 4-1", h.Team1Goals, h.Team2Goals)
	}
}

// Scenario: Compute standings from match results.
func TestStandings(t *testing.T) {
	// Given the match data is loaded
	s := fixtureStore()
	// When I request the 2023 Brasileirão standings
	table := s.Standings("Brasileirão Série A", 2023)
	// Then Flamengo tops the table on points (it is computed, not stored)
	if len(table) < 3 {
		t.Fatalf("expected at least 3 teams, got %d", len(table))
	}
	if table[0].Team != "Flamengo-RJ" {
		t.Errorf("leader = %q, want Flamengo-RJ", table[0].Team)
	}
	// And the duplicate of Flamengo-Palmeiras from the secondary dataset is
	// ignored (standings use a single source), so Flamengo shows 5 games:
	// vs Pal W+D, vs AtlMG W+D, vs AtlPR W => 3W 2D = 11 pts.
	if table[0].Matches != 5 {
		t.Errorf("leader matches = %d, want 5 (duplicate dataset ignored)", table[0].Matches)
	}
	if table[0].Points() != 11 {
		t.Errorf("leader points = %d, want 11", table[0].Points())
	}
}

// Scenario: Competition-wide statistics.
func TestCompetitionStats(t *testing.T) {
	// Given the match data is loaded
	s := fixtureStore()
	// When I compute statistics for the 2023 season
	c := s.Stats(MatchFilter{Season: 2023})
	// Then the average goals per match is positive and rates sum to ~100%
	if c.AvgGoals() <= 0 {
		t.Errorf("avg goals = %.2f, want > 0", c.AvgGoals())
	}
	sum := c.HomeWins + c.AwayWins + c.Draws
	if sum != c.WithScore {
		t.Errorf("home+away+draw (%d) != scored matches (%d)", sum, c.WithScore)
	}
	// And the biggest win is Flamengo 4-0 Atletico-PR (margin 4)
	if len(c.BiggestWins) == 0 || absDiff(c.BiggestWins[0]) != 4 {
		t.Errorf("biggest win margin = %d, want 4", absDiff(c.BiggestWins[0]))
	}
}

// Scenario: Search players by nationality and rating.
func TestSearchPlayers(t *testing.T) {
	// Given a store with a few players
	s := NewStore()
	s.Players = []Player{
		{Name: "Neymar Jr", NameKey: normKey("Neymar Jr"), Nationality: "Brazil", Overall: 92, Position: "LW", Club: "Paris", ClubKey: teamKey("Paris")},
		{Name: "Gabriel Barbosa", NameKey: normKey("Gabriel Barbosa"), Nationality: "Brazil", Overall: 83, Position: "ST", Club: "Flamengo", ClubKey: teamKey("Flamengo")},
		{Name: "L. Messi", NameKey: normKey("L. Messi"), Nationality: "Argentina", Overall: 94, Position: "RF", Club: "Barcelona", ClubKey: teamKey("Barcelona")},
	}
	// When I search Brazilian players rated 85+
	got := s.SearchPlayers(PlayerFilter{Nationality: "Brazil", MinOverall: 85})
	// Then only Neymar qualifies
	if len(got) != 1 || got[0].Name != "Neymar Jr" {
		t.Errorf("got %d players (%v), want just Neymar Jr", len(got), names(got))
	}
	// And searching by club returns the club's player
	byClub := s.SearchPlayers(PlayerFilter{Club: "Flamengo"})
	if len(byClub) != 1 || byClub[0].Name != "Gabriel Barbosa" {
		t.Errorf("club search got %v, want Gabriel Barbosa", names(byClub))
	}
}

func names(ps []Player) []string {
	out := make([]string, len(ps))
	for i, p := range ps {
		out[i] = p.Name
	}
	return out
}

// Sanity: undated matches sort after dated ones.
func TestSortMatchesDesc(t *testing.T) {
	older, _ := parseDate("2020-01-01")
	newer, _ := parseDate("2022-01-01")
	ms := []Match{
		{HasDate: false, Season: 2021},
		{HasDate: true, Date: older},
		{HasDate: true, Date: newer},
	}
	sortMatchesDesc(ms)
	if !ms[0].HasDate || !ms[0].Date.Equal(newer) {
		t.Errorf("expected newest first, got %+v", ms[0])
	}
	if ms[2].HasDate {
		t.Errorf("expected undated match last, got %+v", ms[2])
	}
}
