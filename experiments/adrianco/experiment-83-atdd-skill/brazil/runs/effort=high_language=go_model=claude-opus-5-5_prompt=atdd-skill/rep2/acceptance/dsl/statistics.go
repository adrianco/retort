package dsl

import (
	"testing"

	"brsoccer/acceptance/drivers"
)

// Statistics is the language for aggregated analysis across many matches.
type Statistics struct {
	t      *testing.T
	driver drivers.SystemDriver
}

func (s *Statistics) ForCompetition(args ...string) {
	s.t.Helper()
	s.driver.CompetitionStatistics(NewParams(s.t, args...).Criteria())
}

func (s *Statistics) BiggestWins(args ...string) {
	s.t.Helper()
	s.driver.BiggestWins(NewParams(s.t, args...).Criteria())
}

func (s *Statistics) CompareSeasons(seasons ...string) {
	s.t.Helper()
	s.driver.CompareSeasons(map[string]string{}, seasons...)
}

func (s *Statistics) Derbies(args ...string) {
	s.t.Helper()
	s.driver.Derbies(NewParams(s.t, args...).Criteria())
}

func (s *Statistics) Confirm(facts ...string) {
	s.t.Helper()
	s.driver.ConfirmStatistics(NewParams(s.t, facts...).Expectations())
}

func (s *Statistics) ConfirmWinsInOrder(lines ...string) {
	s.t.Helper()
	s.driver.ConfirmWinsInOrder(lines...)
}

func (s *Statistics) ConfirmSeason(season string, facts ...string) {
	s.t.Helper()
	s.driver.ConfirmSeason(season, NewParams(s.t, facts...).Expectations())
}

func (s *Statistics) ConfirmDerbies(names ...string) {
	s.t.Helper()
	s.driver.ConfirmDerbies(names...)
}

func (s *Statistics) ConfirmDerbyCount(n int) {
	s.t.Helper()
	s.driver.ConfirmDerbyCount(n)
}
