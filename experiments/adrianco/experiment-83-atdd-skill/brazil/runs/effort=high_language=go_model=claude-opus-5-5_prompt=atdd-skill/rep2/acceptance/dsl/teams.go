package dsl

import (
	"testing"

	"brsoccer/acceptance/drivers"
)

// Teams is the language for asking how clubs have performed.
type Teams struct {
	t      *testing.T
	driver drivers.SystemDriver
}

func (tm *Teams) Record(team string, args ...string) {
	tm.t.Helper()
	tm.driver.TeamRecord(team, NewParams(tm.t, args...).Criteria())
}

func (tm *Teams) Overview(team string) {
	tm.t.Helper()
	tm.driver.TeamOverview(team)
}

func (tm *Teams) HeadToHead(team, opponent string, args ...string) {
	tm.t.Helper()
	tm.driver.HeadToHead(team, opponent, NewParams(tm.t, args...).Criteria())
}

// Rank orders teams, e.g. Rank("by: goals scored", "season: 2023").
func (tm *Teams) Rank(args ...string) {
	tm.t.Helper()
	tm.driver.RankTeams(NewParams(tm.t, args...).Criteria())
}

func (tm *Teams) CompetitionsPlayed(team string) {
	tm.t.Helper()
	tm.driver.CompetitionsPlayed(team)
}

// ConfirmRecord takes facts such as "wins: 2" or "win rate: 50.0".
func (tm *Teams) ConfirmRecord(facts ...string) {
	tm.t.Helper()
	tm.driver.ConfirmRecord(NewParams(tm.t, facts...).Expectations())
}

func (tm *Teams) ConfirmHeadToHead(facts ...string) {
	tm.t.Helper()
	tm.driver.ConfirmHeadToHead(NewParams(tm.t, facts...).Expectations())
}

func (tm *Teams) ConfirmRankedFirst(team string, facts ...string) {
	tm.t.Helper()
	tm.driver.ConfirmRankedFirst(team, NewParams(tm.t, facts...).Expectations())
}

func (tm *Teams) ConfirmCompetitions(names ...string) {
	tm.t.Helper()
	tm.driver.ConfirmCompetitionsPlayed(names...)
}

func (tm *Teams) ConfirmSquad(facts ...string) {
	tm.t.Helper()
	tm.driver.ConfirmSquad(NewParams(tm.t, facts...).Expectations())
}
