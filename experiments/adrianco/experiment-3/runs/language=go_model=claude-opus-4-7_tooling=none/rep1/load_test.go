// BDD scenarios for loading the six Kaggle datasets.
package main

import "testing"

// Feature: Data loading
//
// Scenario: Every provided CSV file is loaded and queryable.
func TestScenario_AllDatasetsLoad(t *testing.T) {
	// Given the data directory with all six CSV files
	// When the database is built
	db := testDB(t)

	// Then a substantial number of matches are loaded
	if len(db.AllMatches) < 23000 {
		t.Errorf("expected 23000+ raw match rows, got %d", len(db.AllMatches))
	}
	// And the FIFA player dataset is loaded
	if len(db.Players) < 18000 {
		t.Errorf("expected 18000+ players, got %d", len(db.Players))
	}
	// And every source file contributed at least one match
	sources := map[string]bool{}
	for _, m := range db.AllMatches {
		sources[m.Source] = true
	}
	for _, want := range []string{
		dataFiles.brasileirao, dataFiles.cup, dataFiles.libertadores,
		dataFiles.brFootball, dataFiles.novo,
	} {
		if !sources[want] {
			t.Errorf("no matches loaded from %s", want)
		}
	}
}

// Scenario: Overlapping datasets are deduplicated into a canonical set.
func TestScenario_OverlappingSourcesAreDeduplicated(t *testing.T) {
	// Given the loaded database
	db := testDB(t)
	// Then the canonical set is smaller than the raw set (overlap removed)
	if len(db.Matches) >= len(db.AllMatches) {
		t.Errorf("canonical set (%d) should be smaller than raw set (%d)",
			len(db.Matches), len(db.AllMatches))
	}
	// And it still holds the bulk of the data
	if len(db.Matches) < 15000 {
		t.Errorf("expected 15000+ canonical matches, got %d", len(db.Matches))
	}
	// And no single (competition, season) is served by two sources
	type key struct {
		comp   string
		season int
	}
	sourceFor := map[key]string{}
	for _, m := range db.Matches {
		if m.Season == 0 {
			continue
		}
		k := key{m.Competition, m.Season}
		if prev, ok := sourceFor[k]; ok && prev != m.Source {
			t.Fatalf("competition/season %v served by both %s and %s", k, prev, m.Source)
		}
		sourceFor[k] = m.Source
	}
}

// Scenario: Loaded matches carry usable structured fields.
func TestScenario_MatchesHaveStructuredFields(t *testing.T) {
	// Given the loaded database
	db := testDB(t)
	// Then matches expose competition, teams and (mostly) scores
	scored := 0
	for _, m := range db.Matches {
		if m.Competition == "" || m.HomeTeam == "" || m.AwayTeam == "" {
			t.Fatalf("match with empty core field: %+v", m)
		}
		if m.HasScore {
			scored++
		}
	}
	if scored == 0 {
		t.Error("expected matches with recorded scores")
	}
}
