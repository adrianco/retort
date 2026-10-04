package dsl

import "brsoccer/acceptance/driver"

// Statistics is the part of the language about aggregate figures.
type Statistics struct {
	ctx    *context
	driver driver.SoccerDriver
}

// Summarise asks for overall figures: competition, season, team.
func (s *Statistics) Summarise(args ...string) {
	s.ctx.t.Helper()
	s.driver.SummariseCompetition(parseParams(s.ctx.t, args...))
}

// ConfirmSummary checks figures such as "matches: 4", "average goals: 2.50",
// "home win rate: 50.0%", "average corners: 6.00".
func (s *Statistics) ConfirmSummary(args ...string) {
	s.ctx.t.Helper()
	s.driver.ConfirmSummary(parseParams(s.ctx.t, args...))
}

func (s *Statistics) ConfirmAverageGoalsBetween(low, high float64) {
	s.ctx.t.Helper()
	s.driver.ConfirmAverageGoalsBetween(low, high)
}

// BiggestWins asks for the most one-sided results: competition, season, team.
func (s *Statistics) BiggestWins(args ...string) {
	s.ctx.t.Helper()
	s.driver.BiggestWins(parseParams(s.ctx.t, args...))
}

// ConfirmBiggestWinsInOrder checks the first results listed, e.g. "Santos 8-0 Bolívar".
func (s *Statistics) ConfirmBiggestWinsInOrder(results ...string) {
	s.ctx.t.Helper()
	s.driver.ConfirmBiggestWinsInOrder(results)
}

func (s *Statistics) ConfirmBiggestWinMarginAtLeast(goals int) {
	s.ctx.t.Helper()
	s.driver.ConfirmBiggestWinMarginAtLeast(goals)
}

func (s *Statistics) CompareSeasons(seasons ...string) {
	s.ctx.t.Helper()
	s.driver.CompareSeasons(seasons)
}

// ConfirmSeason checks one season of a comparison: season, matches, average goals, champion.
func (s *Statistics) ConfirmSeason(args ...string) {
	s.ctx.t.Helper()
	s.driver.ConfirmSeasonComparison(parseParams(s.ctx.t, args...))
}
