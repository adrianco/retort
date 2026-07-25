// Package bdd is a tiny Given/When/Then harness for the test suite.
//
// Context
//
//	The specification asks for BDD scenarios written in Gherkin style:
//
//	    Scenario: Find matches between two teams
//	      Given the match data is loaded
//	      When I search for matches between "Flamengo" and "Fluminense"
//	      Then I should receive a list of matches
//
//	Rather than pull in a Cucumber runner and maintain feature files separately
//	from the assertions, this package keeps the same structure inside ordinary
//	Go tests: each scenario is a subtest, each step is logged in order, and a
//	failure prints the steps that led to it. `go test -v` reads like a feature
//	file, and `go test` stays a single command with no extra tooling.
package bdd

import (
	"strings"
	"testing"
)

// S is a scenario under execution.
type S struct {
	*testing.T
	steps []string
}

// Feature logs the feature a group of scenarios belongs to.
func Feature(t *testing.T, name string) {
	t.Helper()
	t.Logf("Feature: %s", name)
}

// Scenario runs one named scenario as a subtest.
func Scenario(t *testing.T, name string, fn func(s *S)) {
	t.Helper()
	t.Run(scenarioName(name), func(t *testing.T) {
		t.Helper()
		s := &S{T: t}
		t.Logf("Scenario: %s", name)
		defer func() {
			if t.Failed() {
				t.Logf("steps executed:\n  %s", strings.Join(s.steps, "\n  "))
			}
		}()
		fn(s)
	})
}

// scenarioName turns a sentence into a subtest name Go will not mangle.
func scenarioName(name string) string {
	return strings.ReplaceAll(name, " ", "_")
}

func (s *S) step(keyword, desc string, fn func()) {
	s.Helper()
	s.steps = append(s.steps, keyword+" "+desc)
	s.Logf("  %s %s", keyword, desc)
	if fn != nil {
		fn()
	}
}

// Given establishes preconditions.
func (s *S) Given(desc string, fn func()) { s.Helper(); s.step("Given", desc, fn) }

// When performs the action under test.
func (s *S) When(desc string, fn func()) { s.Helper(); s.step("When", desc, fn) }

// Then asserts the outcome.
func (s *S) Then(desc string, fn func()) { s.Helper(); s.step("Then", desc, fn) }

// And continues the previous keyword.
func (s *S) And(desc string, fn func()) { s.Helper(); s.step("And", desc, fn) }
