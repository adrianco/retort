// BDD scenarios for match, team, head-to-head, standings and aggregate queries.

package main

import (
	"testing"
	"time"
)

func TestFindMatches(t *testing.T) {
	ds := loadTestDataset(t)

	t.Run("Given the match data is loaded", func(t *testing.T) {
		t.Run("When I search for matches between Flamengo and Fluminense, Then I receive fixtures with date, score and competition", func(t *testing.T) {
			got := ds.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
			if len(got) == 0 {
				t.Fatal("no Fla-Flu matches found")
			}
			for _, m := range got {
				if m.Date.IsZero() || m.Competition == "" {
					t.Fatalf("incomplete match %+v", m)
				}
				if !(ParseTeam("Flamengo", "").Matches(m.Home) || ParseTeam("Flamengo", "").Matches(m.Away)) {
					t.Fatalf("Flamengo not in %+v", m)
				}
			}
		})

		t.Run("When results are returned, Then they are most recent first", func(t *testing.T) {
			got := ds.FindMatches(MatchFilter{Team: "Palmeiras", Season: 2023})
			for i := 1; i < len(got); i++ {
				if got[i].Date.After(got[i-1].Date) {
					t.Fatal("results not sorted newest first")
				}
			}
		})

		t.Run("When I request a Copa do Brasil final, Then the competition filter applies", func(t *testing.T) {
			got := ds.FindMatches(MatchFilter{Competition: "Copa do Brasil", Season: 2023})
			if len(got) == 0 {
				t.Fatal("no Copa do Brasil 2023 matches")
			}
			for _, m := range got {
				if m.Competition != CompCopaBrasil {
					t.Fatalf("wrong competition %q", m.Competition)
				}
			}
		})

		t.Run("When a date range is given, Then only matches inside it are returned", func(t *testing.T) {
			from := time.Date(2019, 1, 1, 0, 0, 0, 0, time.UTC)
			to := time.Date(2019, 12, 31, 23, 59, 59, 0, time.UTC)
			for _, m := range ds.FindMatches(MatchFilter{Competition: CompBrasileirao, From: from, To: to}) {
				if m.Date.Year() != 2019 {
					t.Fatalf("match outside range: %v", m.Date)
				}
			}
		})

		t.Run("When a venue is given, Then only home or away matches are returned", func(t *testing.T) {
			for _, m := range ds.FindMatches(MatchFilter{Team: "Corinthians", Venue: "home", Season: 2022}) {
				if !ParseTeam("Corinthians", "").Matches(m.Home) {
					t.Fatalf("not a home match: %+v", m)
				}
			}
		})
	})
}

func TestTeamRecord(t *testing.T) {
	ds := loadTestDataset(t)

	t.Run("Given Corinthians' 2022 home matches", func(t *testing.T) {
		rec, matches := ds.TeamRecord(MatchFilter{Team: "Corinthians", Venue: "home", Season: 2022, Competition: CompBrasileirao})

		t.Run("When I request the record, Then wins, draws, losses and goals add up", func(t *testing.T) {
			if rec.Played != len(matches) {
				t.Fatalf("played %d != matches %d", rec.Played, len(matches))
			}
			if rec.Wins+rec.Draws+rec.Losses != rec.Played {
				t.Fatalf("W+D+L %d != played %d", rec.Wins+rec.Draws+rec.Losses, rec.Played)
			}
			// The 2022 file lists 19 home fixtures, but four have NA scores (not yet
			// played) and are correctly skipped, leaving 15 completed matches.
			if rec.Played != 15 || rec.Wins != 10 || rec.Draws != 4 || rec.Losses != 1 {
				t.Fatalf("record = %+v, want 15 played, 10W 4D 1L", rec)
			}
		})
		t.Run("When I request the win rate, Then it is a percentage of matches played", func(t *testing.T) {
			want := float64(rec.Wins) / float64(rec.Played) * 100
			if rec.WinRate() != want {
				t.Fatalf("win rate %v, want %v", rec.WinRate(), want)
			}
		})
	})

	t.Run("Given a team with no matches", func(t *testing.T) {
		t.Run("When I request its record, Then it reports zero played", func(t *testing.T) {
			rec, _ := ds.TeamRecord(MatchFilter{Team: "Nonexistent FC"})
			if rec.Played != 0 || rec.WinRate() != 0 {
				t.Fatalf("got %+v", rec)
			}
		})
	})
}

func TestHeadToHead(t *testing.T) {
	ds := loadTestDataset(t)

	t.Run("Given Palmeiras and Santos", func(t *testing.T) {
		t.Run("When I compare them head-to-head, Then the record is from the first team's view and sums to the fixtures", func(t *testing.T) {
			rec, played := ds.HeadToHead("Palmeiras", "Santos")
			if rec.Played == 0 {
				t.Fatal("expected Palmeiras v Santos history")
			}
			if rec.Played != len(played) {
				t.Fatalf("played %d != fixtures %d", rec.Played, len(played))
			}
			if rec.Wins+rec.Draws+rec.Losses != rec.Played {
				t.Fatal("W+D+L does not equal played")
			}
			// The reverse view must mirror the wins and losses.
			rev, _ := ds.HeadToHead("Santos", "Palmeiras")
			if rev.Wins != rec.Losses || rev.Losses != rec.Wins || rev.Draws != rec.Draws {
				t.Fatalf("views disagree: %+v vs %+v", rec, rev)
			}
		})
	})
}

func TestStandings(t *testing.T) {
	ds := loadTestDataset(t)

	t.Run("Given the 2019 Brasileirão results", func(t *testing.T) {
		table := ds.Standings(CompBrasileirao, 2019)

		t.Run("When I build the table, Then it has 20 clubs each playing 38 games", func(t *testing.T) {
			if len(table) != 20 {
				t.Fatalf("clubs = %d, want 20", len(table))
			}
			for _, r := range table {
				if r.Played != 38 {
					t.Fatalf("%s played %d, want 38", r.Team, r.Played)
				}
			}
		})

		t.Run("When I read the leader, Then Flamengo is champion with 90 points (28W 6D 4L)", func(t *testing.T) {
			top := table[0]
			if top.Team != "Flamengo" || top.Points != 90 || top.Wins != 28 || top.Draws != 6 || top.Losses != 4 {
				t.Fatalf("leader = %+v", top)
			}
		})

		t.Run("When I read the table, Then it is sorted by points", func(t *testing.T) {
			for i := 1; i < len(table); i++ {
				if table[i].Points > table[i-1].Points {
					t.Fatal("table not sorted by points")
				}
			}
		})

		t.Run("When points are computed, Then they follow 3 for a win and 1 for a draw", func(t *testing.T) {
			for _, r := range table {
				if r.Points != 3*r.Wins+r.Draws {
					t.Fatalf("%s points %d != 3*%d+%d", r.Team, r.Points, r.Wins, r.Draws)
				}
			}
		})
	})

	t.Run("Given a season with no data", func(t *testing.T) {
		t.Run("When I build the table, Then it is empty", func(t *testing.T) {
			if got := ds.Standings(CompBrasileirao, 1800); len(got) != 0 {
				t.Fatalf("expected empty table, got %d rows", len(got))
			}
		})
	})
}

func TestAggregate(t *testing.T) {
	ds := loadTestDataset(t)

	t.Run("Given the 2023 Brasileirão Série A", func(t *testing.T) {
		s := ds.Aggregate(MatchFilter{Competition: CompBrasileirao, Season: 2023})

		t.Run("When I compute aggregates, Then goals per match is a plausible average", func(t *testing.T) {
			if s.Matches == 0 || s.GoalsPerMatch < 1.5 || s.GoalsPerMatch > 4 {
				t.Fatalf("stats = %+v", s)
			}
		})
		t.Run("When I compute percentages, Then home, draw and away shares sum to 100", func(t *testing.T) {
			sum := s.HomeWinPct + s.DrawPct + s.AwayWinPct
			if sum < 99.9 || sum > 100.1 {
				t.Fatalf("percentages sum to %v", sum)
			}
		})
	})

	t.Run("Given an empty filter", func(t *testing.T) {
		t.Run("When I compute aggregates, Then no division by zero occurs", func(t *testing.T) {
			s := ds.Aggregate(MatchFilter{Season: 1800})
			if s.Matches != 0 || s.GoalsPerMatch != 0 {
				t.Fatalf("stats = %+v", s)
			}
		})
	})
}

func TestBiggestWins(t *testing.T) {
	ds := loadTestDataset(t)

	t.Run("Given all matches", func(t *testing.T) {
		t.Run("When I ask for the biggest wins, Then they are ordered by margin and limited", func(t *testing.T) {
			got := ds.BiggestWins(MatchFilter{}, 5)
			if len(got) != 5 {
				t.Fatalf("got %d, want 5", len(got))
			}
			margin := func(m Match) int {
				d := m.HomeGoals - m.AwayGoals
				if d < 0 {
					return -d
				}
				return d
			}
			for i := 1; i < len(got); i++ {
				if margin(got[i]) > margin(got[i-1]) {
					t.Fatal("not ordered by margin")
				}
			}
		})
	})
}
