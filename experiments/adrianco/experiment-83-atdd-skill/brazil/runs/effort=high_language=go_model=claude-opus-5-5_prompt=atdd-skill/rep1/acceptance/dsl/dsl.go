// Package dsl is the domain-specific language in which the acceptance
// specs are written. It speaks only about matches, teams, players and
// competitions; how the soccer knowledge server is reached is the
// business of the protocol driver underneath.
package dsl

import (
	"testing"
	"time"

	"brsoccer/acceptance/driver"
)

type DSL struct {
	ctx    *context
	driver driver.SoccerDriver

	Matches      *Matches
	Teams        *Teams
	Players      *Players
	Competitions *Competitions
	Statistics   *Statistics
	Datasets     *Datasets
	Assistant    *Assistant
}

// context carries the current test and the sequences the DSL uses to
// generate default values.
type context struct {
	t          testing.TB
	nextDate   time.Time
	nextRound  int
	nextPlayer int
}

// New starts a spec against a server that knows only the facts the spec
// itself establishes.
func New(t *testing.T) *DSL {
	t.Helper()
	return build(t, driver.NewSyntheticDriver(t))
}

// NewWithProvidedData starts a spec against a server holding the
// provided Kaggle datasets.
func NewWithProvidedData(t *testing.T) *DSL {
	t.Helper()
	return build(t, driver.NewProvidedDataDriver(t))
}

func build(t testing.TB, d driver.SoccerDriver) *DSL {
	ctx := &context{t: t, nextDate: time.Date(2023, 1, 1, 0, 0, 0, 0, time.UTC), nextRound: 1, nextPlayer: 1}
	return &DSL{
		ctx:          ctx,
		driver:       d,
		Matches:      &Matches{ctx: ctx, driver: d},
		Teams:        &Teams{ctx: ctx, driver: d},
		Players:      &Players{ctx: ctx, driver: d},
		Competitions: &Competitions{ctx: ctx, driver: d, matches: &Matches{ctx: ctx, driver: d}},
		Statistics:   &Statistics{ctx: ctx, driver: d},
		Datasets:     &Datasets{ctx: ctx, driver: d},
		Assistant:    &Assistant{ctx: ctx, driver: d},
	}
}

// Within points the DSL at a sub-test, so that failures are reported
// against the question being asked.
func (d *DSL) Within(t *testing.T) {
	d.ctx.t = t
	d.driver.UseTest(t)
}

// ConfirmAnsweredWithin checks how long the last question took to answer.
func (d *DSL) ConfirmAnsweredWithin(limit string) {
	d.ctx.t.Helper()
	dur, err := time.ParseDuration(limit)
	if err != nil {
		d.ctx.t.Fatalf("time limit %q is not a duration", limit)
	}
	d.driver.ConfirmAnsweredWithin(dur)
}

// ConfirmToldUnknown checks that the user was told the named team,
// player or competition is not in the data.
func (d *DSL) ConfirmToldUnknown(name string) {
	d.ctx.t.Helper()
	d.driver.ConfirmToldUnknown(name)
}
