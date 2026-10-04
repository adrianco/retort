// Package dsl is the domain-specific language our executable specifications
// are written in. It speaks Brazilian football, supplies defaults so specs
// only state what matters, and hands every interaction to a protocol driver.
package dsl

import (
	"testing"

	"brsoccer/acceptance/drivers"
)

// Scenario is the entry point for a spec. Its fields are the domain areas a
// spec can talk about.
type Scenario struct {
	Records      *Records
	Matches      *Matches
	Teams        *Teams
	Players      *Players
	Competitions *Competitions
	Statistics   *Statistics
	Datasets     *Datasets
	Fan          *Fan
}

// NewScenario gives the spec its own, empty set of records and its own
// instance of the system, so specs are functionally isolated and can run in
// parallel.
func NewScenario(t *testing.T) *Scenario {
	t.Helper()
	t.Parallel()
	records := drivers.NewRecordsStub(t)
	system := drivers.NewMCPDriver(t, records.StartSystem)
	return newScenario(t, records, system)
}

// ProvidedDataScenario asks questions of the system loaded with the provided
// Kaggle datasets. Records cannot be added to it.
func ProvidedDataScenario(t *testing.T) *Scenario {
	t.Helper()
	t.Parallel()
	system := drivers.NewMCPDriver(t, drivers.ProvidedDataSystem)
	return newScenario(t, nil, system)
}

func newScenario(t *testing.T, records drivers.RecordsDriver, system drivers.SystemDriver) *Scenario {
	return &Scenario{
		Records:      &Records{t: t, driver: records},
		Matches:      &Matches{t: t, driver: system},
		Teams:        &Teams{t: t, driver: system},
		Players:      &Players{t: t, driver: system},
		Competitions: &Competitions{t: t, driver: system},
		Statistics:   &Statistics{t: t, driver: system},
		Datasets:     &Datasets{t: t, driver: system},
		Fan:          &Fan{t: t, driver: system},
	}
}
