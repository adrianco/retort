package dsl

import (
	"time"

	"brsoccer/acceptance/driver"
)

// Matches is the part of the language about match results.
type Matches struct {
	ctx    *context
	driver driver.SoccerDriver
}

// Played records that a match took place.
//
//	home, away   team names, exactly as the data source writes them
//	score        "2-1" (default "1-0")
//	date         "2023-09-03" (default: a week after the previous match)
//	season       default: the year of the date
//	competition  Brasileirão (default), Copa do Brasil, Libertadores, Série B, Série C
//	stage        e.g. "final", "semifinals", "group stage"
//	round        league round (default: sequential)
//	source       which record holds it: "Série A results", "historical archive",
//	             "extended statistics" (default: the usual record for the competition)
//	corners, shots   "7-3" — extended statistics
func (m *Matches) Played(args ...string) {
	t := m.ctx.t
	t.Helper()
	p := parseParams(t, args...)

	date := m.ctx.nextDate
	if p.Has("date") {
		d, err := time.Parse("2006-01-02", p.Get("date", ""))
		if err != nil {
			t.Fatalf("match date %q should be written as YYYY-MM-DD", p.Get("date", ""))
		}
		date = d
	}
	m.ctx.nextDate = m.ctx.nextDate.AddDate(0, 0, 7)

	homeGoals, awayGoals, _ := p.Pair(t, "score", 1, 0)
	fixture := driver.MatchFixture{
		Home:        p.Get("home", "Home Team"),
		Away:        p.Get("away", "Away Team"),
		HomeGoals:   homeGoals,
		AwayGoals:   awayGoals,
		Date:        date,
		Season:      p.Int(t, "season", date.Year()),
		Competition: p.Get("competition", "Brasileirão"),
		Stage:       p.Get("stage", ""),
		Round:       p.Int(t, "round", m.ctx.nextRound),
		Source:      p.Get("source", ""),
	}
	m.ctx.nextRound++
	if hc, ac, ok := p.Pair(t, "corners", 0, 0); ok {
		fixture.Corners = &[2]int{hc, ac}
	}
	if hs, as, ok := p.Pair(t, "shots", 0, 0); ok {
		fixture.Shots = &[2]int{hs, as}
	}
	m.driver.RecordMatch(fixture)
}

// Search asks for matches meeting the given criteria:
// team, opponent, venue (home/away), competition, season, from, to, stage.
func (m *Matches) Search(args ...string) {
	m.ctx.t.Helper()
	m.driver.SearchMatches(parseParams(m.ctx.t, args...))
}

// FindLastMeeting asks when two teams last played each other.
func (m *Matches) FindLastMeeting(team, opponent string) {
	m.ctx.t.Helper()
	m.driver.FindLastMeeting(team, opponent)
}

// SearchDerbies asks for matches between traditional rivals.
func (m *Matches) SearchDerbies(args ...string) {
	m.ctx.t.Helper()
	m.driver.SearchDerbies(parseParams(m.ctx.t, args...))
}

// ConfirmFound checks that each described match was found. Matches are
// described as "Home 2-1 Away", optionally followed by " on 2023-09-03".
func (m *Matches) ConfirmFound(matches ...string) {
	m.ctx.t.Helper()
	m.driver.ConfirmMatchesFound(matches)
}

func (m *Matches) ConfirmFoundExactly(count int) {
	m.ctx.t.Helper()
	m.driver.ConfirmMatchCount(count, true)
}

func (m *Matches) ConfirmFoundAtLeast(count int) {
	m.ctx.t.Helper()
	m.driver.ConfirmMatchCount(count, false)
}

// ConfirmHeadToHead checks the head-to-head summary given with the matches,
// e.g. "Flamengo wins: 1", "draws: 1".
func (m *Matches) ConfirmHeadToHead(args ...string) {
	m.ctx.t.Helper()
	m.driver.ConfirmHeadToHead(parseParams(m.ctx.t, args...))
}

// ConfirmMatchStatistics checks the extended statistics of the match found,
// e.g. "corners: 7-3", "shots: 14-6".
func (m *Matches) ConfirmMatchStatistics(args ...string) {
	m.ctx.t.Helper()
	m.driver.ConfirmMatchStatistics(parseParams(m.ctx.t, args...))
}
