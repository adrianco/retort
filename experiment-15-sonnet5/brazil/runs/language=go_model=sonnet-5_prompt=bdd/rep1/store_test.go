package main

import (
	"testing"
	"time"
)

func mustDate(t *testing.T, s string) time.Time {
	t.Helper()
	tm, err := ParseFlexibleDate(s)
	if err != nil {
		t.Fatalf("mustDate(%q): %v", s, err)
	}
	return tm
}

func newTestMatch(t *testing.T, competition, date string, season int, home string, homeGoals int, away string, awayGoals int) Match {
	t.Helper()
	homeKey, homeDisp := NormalizeTeamName(home)
	awayKey, awayDisp := NormalizeTeamName(away)
	return Match{
		Competition: competition,
		Date:        mustDate(t, date),
		HasDate:     true,
		Season:      season,
		HomeTeam:    homeDisp,
		AwayTeam:    awayDisp,
		HomeTeamKey: homeKey,
		AwayTeamKey: awayKey,
		HomeGoals:   homeGoals,
		AwayGoals:   awayGoals,
	}
}

func newTestPlayer(name string, overall int, club, nationality, position string) Player {
	clubKey, clubDisp := NormalizeTeamName(club)
	return Player{
		Name:        name,
		Overall:     overall,
		Club:        clubDisp,
		ClubKey:     clubKey,
		Nationality: nationality,
		Position:    position,
	}
}

// buildFixtureStore returns a small, hand-built Store covering three teams
// across two competitions/seasons, used to test query behaviour without
// depending on the full CSV datasets.
func buildFixtureStore(t *testing.T) *Store {
	t.Helper()
	s := &Store{
		Matches: []Match{
			newTestMatch(t, "Brasileirao", "2023-09-03", 2023, "Flamengo", 2, "Fluminense", 1),
			newTestMatch(t, "Brasileirao", "2023-05-28", 2023, "Fluminense", 1, "Flamengo", 0),
			newTestMatch(t, "Brasileirao", "2023-06-10", 2023, "Flamengo", 3, "Palmeiras", 0),
			newTestMatch(t, "Brasileirao", "2023-08-01", 2023, "Palmeiras", 1, "Flamengo", 1),
			newTestMatch(t, "Brasileirao", "2023-04-01", 2023, "Palmeiras", 4, "Fluminense", 0),
			newTestMatch(t, "Brasileirao", "2023-10-01", 2023, "Fluminense", 2, "Palmeiras", 2),
			newTestMatch(t, "Copa do Brasil", "2022-01-01", 2022, "Flamengo", 5, "Fluminense", 0),
		},
		Players: []Player{
			newTestPlayer("Neymar Jr", 92, "Paris Saint-Germain", "Brazil", "LW"),
			newTestPlayer("Gabriel Barbosa", 84, "Flamengo", "Brazil", "ST"),
			newTestPlayer("Everton Ribeiro", 80, "Flamengo", "Brazil", "RM"),
			newTestPlayer("Lionel Messi", 94, "Paris Saint-Germain", "Argentina", "RW"),
			newTestPlayer("Marquinhos", 87, "Paris Saint-Germain", "Brazil", "CB"),
		},
	}
	s.BuildIndexes()
	return s
}

func Test_GivenMatchesForATeam_WhenFilteringByTeam_ThenOnlyThatTeamsMatchesAreReturned(t *testing.T) {
	// Given a store with matches for Flamengo, Fluminense, and Palmeiras
	store := buildFixtureStore(t)

	// When filtering matches by team "Fluminense"
	got := store.FilterMatches(MatchFilter{Team: "Fluminense"})

	// Then every returned match involves Fluminense
	if len(got) == 0 {
		t.Fatal("expected at least one match, got none")
	}
	for _, m := range got {
		if m.HomeTeam != "Fluminense" && m.AwayTeam != "Fluminense" {
			t.Errorf("match %+v does not involve Fluminense", m)
		}
	}
}

func Test_GivenMatchesAcrossSeasons_WhenFilteringBySeason_ThenOnlyThatSeasonsMatchesAreReturned(t *testing.T) {
	// Given a store with matches in both 2022 and 2023
	store := buildFixtureStore(t)

	// When filtering by season 2022
	got := store.FilterMatches(MatchFilter{Season: 2022})

	// Then only the single 2022 match is returned
	if len(got) != 1 {
		t.Fatalf("got %d matches, want 1", len(got))
	}
	if got[0].Season != 2022 {
		t.Errorf("got season %d, want 2022", got[0].Season)
	}
}

func Test_GivenNoMatchingCriteria_WhenFilteringMatches_ThenAnEmptySliceIsReturned(t *testing.T) {
	// Given a store with no matches for "Corinthians"
	store := buildFixtureStore(t)

	// When filtering matches by team "Corinthians"
	got := store.FilterMatches(MatchFilter{Team: "Corinthians"})

	// Then no matches are returned
	if len(got) != 0 {
		t.Errorf("got %d matches, want 0", len(got))
	}
}

func Test_GivenTwoRivalTeams_WhenComputingHeadToHead_ThenWinDrawAndGoalTotalsAreCorrect(t *testing.T) {
	// Given a store where Flamengo and Fluminense have played three times
	// (two wins for Flamengo, one for Fluminense, no draws)
	store := buildFixtureStore(t)

	// When computing their head-to-head record across all competitions
	got := store.HeadToHead("Flamengo", "Fluminense", "")

	// Then the win/draw and goal totals match the fixture data
	if got.TotalMatches != 3 {
		t.Fatalf("got %d total matches, want 3", got.TotalMatches)
	}
	if got.WinsA != 2 || got.WinsB != 1 || got.Draws != 0 {
		t.Errorf("got WinsA=%d WinsB=%d Draws=%d, want 2/1/0", got.WinsA, got.WinsB, got.Draws)
	}
	if got.GoalsA != 7 || got.GoalsB != 2 {
		t.Errorf("got GoalsA=%d GoalsB=%d, want 7/2", got.GoalsA, got.GoalsB)
	}
}

func Test_GivenATeamsSeasonMatches_WhenComputingTeamRecord_ThenWinDrawLossAndGoalsAreCorrect(t *testing.T) {
	// Given Flamengo's four 2023 Brasileirao matches (2 wins, 1 draw, 1 loss)
	store := buildFixtureStore(t)

	// When computing Flamengo's 2023 Brasileirao record
	got := store.TeamRecord("Flamengo", 2023, "Brasileirao", "")

	// Then the record matches the fixture data
	if got.MatchesPlayed != 4 || got.Wins != 2 || got.Draws != 1 || got.Losses != 1 {
		t.Errorf("got %+v, want played=4 wins=2 draws=1 losses=1", got)
	}
	if got.GoalsFor != 6 || got.GoalsAgainst != 3 {
		t.Errorf("got GoalsFor=%d GoalsAgainst=%d, want 6/3", got.GoalsFor, got.GoalsAgainst)
	}
}

func Test_GivenAVenueFilter_WhenComputingTeamRecord_ThenOnlyThatVenuesMatchesCount(t *testing.T) {
	// Given Flamengo has exactly two home matches in the 2023 Brasileirao fixtures, both wins
	store := buildFixtureStore(t)

	// When computing Flamengo's 2023 Brasileirao home-only record
	got := store.TeamRecord("Flamengo", 2023, "Brasileirao", "home")

	// Then only the two home matches are counted
	if got.MatchesPlayed != 2 || got.Wins != 2 {
		t.Errorf("got %+v, want played=2 wins=2", got)
	}
}

func Test_GivenASeasonsResults_WhenComputingStandings_ThenTeamsAreRankedByPoints(t *testing.T) {
	// Given the fixture's 2023 Brasileirao results, where Flamengo finishes top
	store := buildFixtureStore(t)

	// When computing the 2023 Brasileirao standings
	rows := store.Standings(2023, "Brasileirao")

	// Then Flamengo is ranked first with the correct points total
	if len(rows) != 3 {
		t.Fatalf("got %d rows, want 3", len(rows))
	}
	if rows[0].Team != "Flamengo" || rows[0].Position != 1 {
		t.Errorf("got leader %+v, want Flamengo in position 1", rows[0])
	}
	if rows[0].Points != 7 {
		t.Errorf("got %d points, want 7", rows[0].Points)
	}
}

func Test_GivenASeasonsResults_WhenComputingStandings_ThenPointsAreDescendingOrder(t *testing.T) {
	// Given the fixture's 2023 Brasileirao standings
	store := buildFixtureStore(t)

	// When computing the standings
	rows := store.Standings(2023, "Brasileirao")

	// Then each row has points less than or equal to the previous row
	for i := 1; i < len(rows); i++ {
		if rows[i].Points > rows[i-1].Points {
			t.Errorf("standings not sorted: row %d (%d pts) > row %d (%d pts)", i, rows[i].Points, i-1, rows[i-1].Points)
		}
	}
}

func Test_GivenMatchesWithVaryingGoalDifferences_WhenFindingBiggestWins_ThenLargestMarginComesFirst(t *testing.T) {
	// Given a fixture where Flamengo's 5-0 win is the largest margin in the dataset
	store := buildFixtureStore(t)

	// When listing the biggest wins
	got := store.BiggestWins("", 0, 1)

	// Then the 5-0 win is returned first
	if len(got) != 1 {
		t.Fatalf("got %d matches, want 1", len(got))
	}
	if got[0].GoalDiff() != 5 {
		t.Errorf("got goal diff %d, want 5", got[0].GoalDiff())
	}
}

func Test_GivenASetOfMatches_WhenComputingStatsSummary_ThenRatesSumToOne(t *testing.T) {
	// Given the fixture's 2023 Brasileirao matches
	store := buildFixtureStore(t)

	// When computing the stats summary
	got := store.StatsSummary("Brasileirao", 2023)

	// Then home/away/draw rates sum to (approximately) 1
	total := got.HomeWinRate + got.AwayWinRate + got.DrawRate
	if total < 0.999 || total > 1.001 {
		t.Errorf("got rates summing to %f, want ~1.0", total)
	}
	if got.MatchesConsidered != 6 {
		t.Errorf("got %d matches considered, want 6", got.MatchesConsidered)
	}
}

func Test_GivenHomeRecordsAcrossTeams_WhenRankingBestRecord_ThenThePerfectHomeRecordComesFirst(t *testing.T) {
	// Given Flamengo won both of its 2023 Brasileirao home matches
	store := buildFixtureStore(t)

	// When ranking best home record
	rows := store.BestRecord("Brasileirao", 2023, "home", 1, 10)

	// Then Flamengo is ranked first with a 100% win rate
	if len(rows) == 0 {
		t.Fatal("expected at least one row")
	}
	if rows[0].Team != "Flamengo" || rows[0].WinRate() != 1.0 {
		t.Errorf("got leader %+v, want Flamengo at 100%% win rate", rows[0])
	}
}

func Test_GivenPlayersOfDifferentNationalities_WhenSearchingByNationality_ThenOnlyThatNationalityIsReturned(t *testing.T) {
	// Given a mix of Brazilian and non-Brazilian players
	store := buildFixtureStore(t)

	// When searching for Brazilian players
	got := store.SearchPlayers(PlayerFilter{Nationality: "Brazil"})

	// Then every returned player is Brazilian, sorted by descending overall
	if len(got) != 4 {
		t.Fatalf("got %d players, want 4", len(got))
	}
	for i, p := range got {
		if p.Nationality != "Brazil" {
			t.Errorf("player %s has nationality %s, want Brazil", p.Name, p.Nationality)
		}
		if i > 0 && got[i-1].Overall < p.Overall {
			t.Errorf("players not sorted by descending overall at index %d", i)
		}
	}
}

func Test_GivenPlayersAtDifferentClubs_WhenSearchingByClub_ThenOnlyThatClubsPlayersAreReturned(t *testing.T) {
	// Given two players at Flamengo and three elsewhere
	store := buildFixtureStore(t)

	// When searching for Flamengo's players
	got := store.SearchPlayers(PlayerFilter{Club: "Flamengo-RJ"})

	// Then exactly the two Flamengo players are returned, regardless of the "-RJ" suffix used in the query
	if len(got) != 2 {
		t.Fatalf("got %d players, want 2", len(got))
	}
	for _, p := range got {
		if p.Club != "Flamengo" {
			t.Errorf("got player at club %q, want Flamengo", p.Club)
		}
	}
}

func Test_GivenATeamsFifaRoster_WhenFetchingTeamPlayers_ThenAverageOverallIsCorrect(t *testing.T) {
	// Given Flamengo's two players rated 84 and 80
	store := buildFixtureStore(t)

	// When fetching Flamengo's roster
	got := store.TeamPlayers("Flamengo", 10)

	// Then the average overall rating is (84+80)/2 = 82
	if len(got.Players) != 2 {
		t.Fatalf("got %d players, want 2", len(got.Players))
	}
	if got.AverageOverall != 82 {
		t.Errorf("got average overall %f, want 82", got.AverageOverall)
	}
}
