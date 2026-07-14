package soccer

import (
	"testing"
	"time"
)

// mustDate parses YYYY-MM-DD for fixtures.
func mustDate(s string) time.Time {
	t, err := time.Parse("2006-01-02", s)
	if err != nil {
		panic(err)
	}
	return t
}

// mkMatch builds a normalised match fixture.
func mkMatch(comp, home, away string, hg, ag, season int, date string) Match {
	m := makeMatch(comp, home, away, hg, ag, season, "", "", "test", mustDate(date))
	return m
}

// fixtureStore builds a small indexed store used across the query tests. It
// models a mini two-team league plus a couple of players.
func fixtureStore() *Store {
	s := NewStore()
	s.AddMatches([]Match{
		// Flamengo vs Palmeiras head-to-head.
		mkMatch(CompBrasileirao, "Flamengo", "Palmeiras", 3, 0, 2019, "2019-09-01"),
		mkMatch(CompBrasileirao, "Palmeiras", "Flamengo", 1, 1, 2019, "2019-05-15"),
		// Other Flamengo games in 2019.
		mkMatch(CompBrasileirao, "Flamengo", "Santos", 2, 0, 2019, "2019-08-10"),
		mkMatch(CompBrasileirao, "Santos", "Flamengo", 0, 4, 2019, "2019-06-01"),
		// A 2018 game and a cup game to test filtering.
		mkMatch(CompBrasileirao, "Flamengo", "Palmeiras", 0, 2, 2018, "2018-07-01"),
		mkMatch(CompCopaBrasil, "Flamengo", "Santos", 5, 0, 2019, "2019-07-20"),
	})
	s.AddPlayers([]Player{
		{Name: "Gabriel Barbosa", NameKey: NormalizeName("Gabriel Barbosa"), Nationality: "Brazil", Overall: 84, Club: "Flamengo", ClubKey: NormalizeTeam("Flamengo"), Position: "ST", Age: 26},
		{Name: "Bruno Henrique", NameKey: NormalizeName("Bruno Henrique"), Nationality: "Brazil", Overall: 82, Club: "Flamengo", ClubKey: NormalizeTeam("Flamengo"), Position: "LW", Age: 28},
		{Name: "L. Messi", NameKey: NormalizeName("L. Messi"), Nationality: "Argentina", Overall: 94, Club: "FC Barcelona", ClubKey: NormalizeTeam("FC Barcelona"), Position: "RF", Age: 31},
	})
	s.Index()
	return s
}

// Behaviour: match search filters by team, opponent, season and competition.

func Test_given_team_and_opponent_when_searching_then_only_head_to_head_returned(t *testing.T) {
	// Given a store with several fixtures
	s := fixtureStore()
	// When searching for Flamengo vs Palmeiras
	got := s.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Palmeiras"})
	// Then only the three Flamengo-Palmeiras games are returned
	if len(got) != 3 {
		t.Fatalf("expected 3 head-to-head matches, got %d", len(got))
	}
}

func Test_given_season_filter_when_searching_then_other_seasons_excluded(t *testing.T) {
	// Given the store
	s := fixtureStore()
	// When searching Flamengo vs Palmeiras in 2019
	got := s.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Palmeiras", Season: 2019})
	// Then the 2018 game is excluded
	if len(got) != 2 {
		t.Fatalf("expected 2 matches in 2019, got %d", len(got))
	}
}

func Test_given_results_when_searching_then_ordered_most_recent_first(t *testing.T) {
	// Given the store
	s := fixtureStore()
	// When searching all Flamengo matches
	got := s.FindMatches(MatchFilter{Team: "Flamengo"})
	// Then the newest match comes first
	if len(got) < 2 {
		t.Fatalf("expected several matches, got %d", len(got))
	}
	if got[0].Date.Before(got[1].Date) {
		t.Fatalf("expected descending dates, got %v before %v", got[0].Date, got[1].Date)
	}
}

// Behaviour: head-to-head aggregates wins, draws and goals correctly.

func Test_given_two_teams_when_head_to_head_then_record_is_aggregated(t *testing.T) {
	// Given the store (Fla 3-0 Pal, Pal 1-1 Fla in 2019; Fla 0-2 Pal in 2018)
	s := fixtureStore()
	// When computing the head-to-head
	h := s.HeadToHead("Flamengo", "Palmeiras")
	// Then totals reflect one Flamengo win, one Palmeiras win, one draw
	if h.Matches != 3 {
		t.Fatalf("expected 3 matches, got %d", h.Matches)
	}
	if h.WinsA != 1 || h.WinsB != 1 || h.Draws != 1 {
		t.Errorf("expected 1/1/1, got %d/%d/%d", h.WinsA, h.WinsB, h.Draws)
	}
	if h.GoalsA != 4 || h.GoalsB != 3 {
		t.Errorf("expected goals 4-3, got %d-%d", h.GoalsA, h.GoalsB)
	}
}

func Test_given_last_meeting_when_head_to_head_then_most_recent_reported(t *testing.T) {
	// Given the store
	s := fixtureStore()
	// When computing head-to-head
	h := s.HeadToHead("Flamengo", "Palmeiras")
	// Then the last meeting is the 2019-09-01 fixture
	if h.LastMeeting == nil || h.LastMeeting.Date.Format("2006-01-02") != "2019-09-01" {
		t.Fatalf("expected last meeting 2019-09-01, got %v", h.LastMeeting)
	}
}

// Behaviour: team record aggregates and honours competition/venue filters.

func Test_given_competition_filter_when_team_record_then_cup_excluded(t *testing.T) {
	// Given the store (5 league games + 1 cup game for Flamengo in scope)
	s := fixtureStore()
	// When computing Flamengo's Brasileirão record
	rec := s.TeamRecord("Flamengo", TeamRecordOptions{Competition: "Brasileir"})
	// Then only the 5 league matches count (the cup game is excluded)
	if rec.Played != 5 {
		t.Fatalf("expected 5 league matches, got %d", rec.Played)
	}
}

func Test_given_home_venue_when_team_record_then_only_home_games_count(t *testing.T) {
	// Given the store
	s := fixtureStore()
	// When computing Flamengo's home Brasileirão record
	rec := s.TeamRecord("Flamengo", TeamRecordOptions{Competition: "Brasileir", Venue: "home"})
	// Then only home games are counted (Fla-Pal 2019, Fla-Santos 2019, Fla-Pal 2018)
	if rec.Played != 3 {
		t.Fatalf("expected 3 home matches, got %d", rec.Played)
	}
}

// Behaviour: standings are computed from results with the usual tie-breakers.

func Test_given_season_when_standings_then_leader_has_most_points(t *testing.T) {
	// Given the store
	s := fixtureStore()
	// When computing the 2019 Brasileirão standings
	table := s.Standings("Brasileir", 2019)
	// Then Flamengo tops the table (3 wins, 1 draw from its league games)
	if len(table) == 0 {
		t.Fatal("expected a non-empty table")
	}
	if table[0].Team != "Flamengo" {
		t.Fatalf("expected Flamengo top, got %q", table[0].Team)
	}
	if table[0].Position != 1 {
		t.Errorf("expected position 1, got %d", table[0].Position)
	}
}

// Behaviour: player search filters and sorts by rating.

func Test_given_nationality_when_searching_players_then_sorted_by_rating(t *testing.T) {
	// Given the store
	s := fixtureStore()
	// When searching Brazilian players
	got := s.FindPlayers(PlayerFilter{Nationality: "Brazil"})
	// Then only Brazilians are returned, highest rating first
	if len(got) != 2 {
		t.Fatalf("expected 2 Brazilians, got %d", len(got))
	}
	if got[0].Name != "Gabriel Barbosa" {
		t.Errorf("expected Gabriel Barbosa first, got %q", got[0].Name)
	}
}

func Test_given_partial_name_when_searching_players_then_substring_matches(t *testing.T) {
	// Given the store
	s := fixtureStore()
	// When searching by a partial, differently-cased name
	got := s.FindPlayers(PlayerFilter{Name: "gabriel"})
	// Then the matching player is found
	if len(got) != 1 || got[0].Name != "Gabriel Barbosa" {
		t.Fatalf("expected to find Gabriel Barbosa, got %+v", got)
	}
}

// Behaviour: statistics summarise a filtered set of matches.

func Test_given_season_when_stats_then_average_goals_computed(t *testing.T) {
	// Given the store; the 2019 Brasileirão fixtures are:
	// 3-0, 1-1, 2-0, 0-4 => 4 games, 11 goals
	s := fixtureStore()
	// When computing statistics for 2019 Brasileirão
	st := s.Stats(MatchFilter{Competition: "Brasileir", Season: 2019}, 5)
	// Then the average goals per match is 11/4 = 2.75
	if st.Matches != 4 {
		t.Fatalf("expected 4 matches, got %d", st.Matches)
	}
	if st.TotalGoals != 11 {
		t.Fatalf("expected 11 goals, got %d", st.TotalGoals)
	}
	if got := st.AvgGoalsPerGame; got < 2.74 || got > 2.76 {
		t.Errorf("expected ~2.75 avg, got %f", got)
	}
}

func Test_given_matches_when_stats_then_biggest_win_first(t *testing.T) {
	// Given the store
	s := fixtureStore()
	// When computing statistics for all Flamengo matches
	st := s.Stats(MatchFilter{Team: "Flamengo"}, 3)
	// Then the biggest margin (the 5-0 cup win) is listed first
	if len(st.BiggestWins) == 0 {
		t.Fatal("expected biggest wins")
	}
	top := st.BiggestWins[0]
	if abs(top.HomeGoals-top.AwayGoals) != 5 {
		t.Fatalf("expected a 5-goal margin first, got %d-%d", top.HomeGoals, top.AwayGoals)
	}
}
