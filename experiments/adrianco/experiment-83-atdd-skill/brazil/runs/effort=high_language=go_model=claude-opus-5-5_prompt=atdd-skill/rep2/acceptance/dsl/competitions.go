package dsl

import (
	"testing"

	"brsoccer/acceptance/drivers"
)

// Competitions is the language for tables, champions and brackets.
type Competitions struct {
	t      *testing.T
	driver drivers.SystemDriver
}

// Standings asks for a league table; the competition defaults to the
// Brasileirão.
func (c *Competitions) Standings(args ...string) {
	c.t.Helper()
	c.driver.Standings(NewParams(c.t, args...).Criteria())
}

func (c *Competitions) Bracket(args ...string) {
	c.t.Helper()
	c.driver.Bracket(NewParams(c.t, args...).Criteria())
}

func (c *Competitions) ConfirmChampion(team string, facts ...string) {
	c.t.Helper()
	c.driver.ConfirmChampion(team, NewParams(c.t, facts...).Expectations())
}

func (c *Competitions) ConfirmFinishingOrder(teams ...string) {
	c.t.Helper()
	c.driver.ConfirmFinishingOrder(teams...)
}

func (c *Competitions) ConfirmRelegated(teams ...string) {
	c.t.Helper()
	c.driver.ConfirmRelegated(teams...)
}

func (c *Competitions) ConfirmTeamsInTable(n int) {
	c.t.Helper()
	c.driver.ConfirmTeamsInTable(n)
}

// ConfirmTie checks a knockout tie, e.g. ConfirmTie("stage: final",
// "winner: River Plate", "aggregate: River Plate 5-3 Boca Juniors").
func (c *Competitions) ConfirmTie(facts ...string) {
	c.t.Helper()
	p := NewParams(c.t, facts...)
	c.driver.ConfirmTie(p.Required("stage"), p.Expectations())
}

func (c *Competitions) ConfirmNoStage(stage string) {
	c.t.Helper()
	c.driver.ConfirmNoStage(stage)
}
