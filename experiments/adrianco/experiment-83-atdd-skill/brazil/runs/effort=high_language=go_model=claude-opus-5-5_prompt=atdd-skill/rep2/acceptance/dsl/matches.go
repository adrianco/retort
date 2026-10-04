package dsl

import (
	"testing"

	"brsoccer/acceptance/drivers"
)

// Matches is the language for asking about individual matches.
type Matches struct {
	t      *testing.T
	driver drivers.SystemDriver
}

func (m *Matches) Between(team, opponent string, args ...string) {
	m.t.Helper()
	c := NewParams(m.t, args...).Criteria()
	c["team"], c["opponent"] = team, opponent
	m.driver.FindMatches(c)
}

func (m *Matches) PlayedBy(team string, args ...string) {
	m.t.Helper()
	c := NewParams(m.t, args...).Criteria()
	c["team"] = team
	m.driver.FindMatches(c)
}

func (m *Matches) Finals(args ...string) {
	m.t.Helper()
	c := NewParams(m.t, args...).Criteria()
	c["stage"] = "final"
	m.driver.FindMatches(c)
}

func (m *Matches) LastMeeting(team, opponent string) {
	m.t.Helper()
	m.driver.FindMatches(map[string]string{"team": team, "opponent": opponent, "limit": "1"})
}

func (m *Matches) ConfirmShown(lines ...string) {
	m.t.Helper()
	m.driver.ConfirmMatchesShown(lines...)
}

func (m *Matches) ConfirmCount(n int) {
	m.t.Helper()
	m.driver.ConfirmMatchCount(n)
}

func (m *Matches) ConfirmCompetitionsCovered(names ...string) {
	m.t.Helper()
	m.driver.ConfirmCompetitionsInMatches(names...)
}

// ConfirmHeadToHead takes facts such as "Flamengo wins: 1" or "draws: 2".
func (m *Matches) ConfirmHeadToHead(facts ...string) {
	m.t.Helper()
	m.driver.ConfirmHeadToHeadSummary("", "", NewParams(m.t, facts...).Expectations())
}

func (m *Matches) ConfirmStatistics(facts ...string) {
	m.t.Helper()
	m.driver.ConfirmMatchStatistics(NewParams(m.t, facts...).Expectations())
}

func (m *Matches) ConfirmNoMatchesFound() {
	m.t.Helper()
	m.driver.ConfirmNoMatchesFound()
}

func (m *Matches) ConfirmNoDuplicates() {
	m.t.Helper()
	m.driver.ConfirmNoDuplicateMatches()
}
