package dsl

import "brsoccer/acceptance/driver"

// Teams is the part of the language about clubs and their records.
type Teams struct {
	ctx    *context
	driver driver.SoccerDriver
}

// RecordFor asks for a team's record: team, season, competition, venue.
func (tm *Teams) RecordFor(args ...string) {
	tm.ctx.t.Helper()
	tm.driver.TeamRecord(parseParams(tm.ctx.t, args...))
}

// ConfirmRecord checks a team's record: matches, wins, draws, losses,
// goals for, goals against, win rate.
func (tm *Teams) ConfirmRecord(args ...string) {
	tm.ctx.t.Helper()
	tm.driver.ConfirmTeamRecord(parseParams(tm.ctx.t, args...))
}

// ConfirmCompetitionRecord checks the part of a record earned in one competition.
func (tm *Teams) ConfirmCompetitionRecord(args ...string) {
	tm.ctx.t.Helper()
	tm.driver.ConfirmCompetitionRecord(parseParams(tm.ctx.t, args...))
}

func (tm *Teams) CompareHeadToHead(team, opponent string) {
	tm.ctx.t.Helper()
	tm.driver.CompareHeadToHead(team, opponent)
}

// ConfirmHeadToHead checks e.g. "meetings: 3", "Palmeiras wins: 1", "draws: 1", "Santos goals: 2".
func (tm *Teams) ConfirmHeadToHead(args ...string) {
	tm.ctx.t.Helper()
	tm.driver.ConfirmHeadToHead(parseParams(tm.ctx.t, args...))
}

func (tm *Teams) ConfirmHeadToHeadMeetingsAtLeast(count int) {
	tm.ctx.t.Helper()
	tm.driver.ConfirmHeadToHeadMeetingsAtLeast(count)
}

func (tm *Teams) CompetitionsPlayedBy(team string) {
	tm.ctx.t.Helper()
	tm.driver.CompetitionsPlayedBy(team)
}

func (tm *Teams) ConfirmPlayedIn(competitions ...string) {
	tm.ctx.t.Helper()
	tm.driver.ConfirmPlayedIn(competitions)
}

// Rank asks for teams ranked "by" goals scored, win rate, points...,
// optionally limited by venue, season and competition.
func (tm *Teams) Rank(args ...string) {
	tm.ctx.t.Helper()
	tm.driver.RankTeams(parseParams(tm.ctx.t, args...))
}

// ConfirmRankedFirst checks the leader of the ranking: team, value.
func (tm *Teams) ConfirmRankedFirst(args ...string) {
	tm.ctx.t.Helper()
	tm.driver.ConfirmRankedFirst(parseParams(tm.ctx.t, args...))
}

func (tm *Teams) ConfirmSomeTeamRankedFirst() {
	tm.ctx.t.Helper()
	tm.driver.ConfirmRankedFirst(Params{})
}

// FindTeam asks which team a name refers to.
func (tm *Teams) FindTeam(name string) {
	tm.ctx.t.Helper()
	tm.driver.FindTeam(name)
}

// ConfirmKnownAs checks the names under which the team appears in the data.
func (tm *Teams) ConfirmKnownAs(names ...string) {
	tm.ctx.t.Helper()
	tm.driver.ConfirmKnownAs(names)
}

// ProfileClub asks about a club as a whole: its squad and its results.
func (tm *Teams) ProfileClub(team string) {
	tm.ctx.t.Helper()
	tm.driver.ProfileClub(team)
}

func (tm *Teams) ConfirmSquadIncludes(players ...string) {
	tm.ctx.t.Helper()
	tm.driver.ConfirmSquadIncludes(players)
}

func (tm *Teams) ConfirmSquadSizeAtLeast(count int) {
	tm.ctx.t.Helper()
	tm.driver.ConfirmSquadSizeAtLeast(count)
}
