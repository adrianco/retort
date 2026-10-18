package main

import (
	"testing"
)

func TestFeature_LoadingAllSources(t *testing.T) {
	t.Run("Scenario: every source file is loaded", func(t *testing.T) {
		// Given the six fixture files
		// When the store is loaded
		st := fixtureStore(t)
		// Then matches come from every match file
		if countWhere(st.Matches, func(m Match) bool { return m.Competition == compLibertadores }) != 2 {
			t.Error("expected 2 Libertadores matches")
		}
		if countWhere(st.Matches, func(m Match) bool { return m.Competition == compCup }) == 0 {
			t.Error("expected Copa do Brasil matches")
		}
		// And the FIFA players are loaded despite the byte-order mark on the header
		if len(st.Players) != 7 {
			t.Errorf("expected 7 players, got %d", len(st.Players))
		}
		if st.Players[0].ID != 158023 {
			t.Errorf("first player ID = %d; BOM may not have been stripped", st.Players[0].ID)
		}
	})

	t.Run("Scenario: a season present in two files is counted once", func(t *testing.T) {
		// Given the 2019 Brasileirão appears in both the Brasileirão and historical files
		// When the store is loaded
		st := fixtureStore(t)
		// Then the 2019 Flamengo-Fluminense match is present exactly once
		n := countWhere(st.Matches, func(m Match) bool {
			return m.Competition == compBrasileirao && m.Season == 2019 &&
				st.teamLabel(m.Home) == "Flamengo" && st.teamLabel(m.Away) == "Fluminense"
		})
		if n != 1 {
			t.Errorf("Flamengo vs Fluminense 2019 appears %d times, want 1", n)
		}
	})

	t.Run("Scenario: a season missing from the preferred file is loaded from the fallback", func(t *testing.T) {
		// Given 2003 exists only in the historical file and 2023 only in BR-Football
		// When the store is loaded
		st := fixtureStore(t)
		// Then both seasons have matches
		if countWhere(st.Matches, func(m Match) bool { return m.Season == 2003 }) != 1 {
			t.Error("expected the 2003 historical match")
		}
		if countWhere(st.Matches, func(m Match) bool { return m.Season == 2023 && m.Competition == compBrasileirao }) != 1 {
			t.Error("expected the 2023 BR-Football Serie A match")
		}
	})

	t.Run("Scenario: fixtures without a score are skipped", func(t *testing.T) {
		// Given the 2022 fixture has NA scores
		// When the store is loaded
		st := fixtureStore(t)
		// Then it is not in the matches
		if countWhere(st.Matches, func(m Match) bool { return m.Season == 2022 }) != 0 {
			t.Error("unplayed 2022 fixture should be skipped")
		}
	})
}

func TestFeature_TeamIdentity(t *testing.T) {
	t.Run("Scenario: clubs that share a base name stay distinct", func(t *testing.T) {
		// Given Atlético-MG and Atlético-PR both appear
		// When the store is loaded
		st := fixtureStore(t)
		// Then the two clubs have different IDs and display names
		mg := st.resolveTeams("Atletico-MG")
		pr := st.resolveTeams("Atletico-PR")
		if len(mg) != 1 || len(pr) != 1 || mg[0] == pr[0] {
			t.Fatalf("expected distinct IDs, got MG=%v PR=%v", mg, pr)
		}
		if st.teamLabel(mg[0]) != "Atlético-MG" {
			t.Errorf("MG label = %q", st.teamLabel(mg[0]))
		}
	})

	t.Run("Scenario: a stateless name resolves to the dominant club", func(t *testing.T) {
		// Given "Atletico Mineiro" from BR-Football carries no state
		// When it is resolved
		// Then it joins Atlético-MG rather than becoming a separate club
		st := fixtureStore(t)
		ids := st.resolveTeams("Atletico Mineiro")
		if len(ids) == 0 || ids[0] != st.resolveTeams("Atletico-MG")[0] {
			t.Fatalf("Atletico Mineiro resolved to %v", ids)
		}
	})

	t.Run("Scenario: a bare name matches every state", func(t *testing.T) {
		// Given "Atletico" with no state
		// When it is resolved
		// Then it matches each Atlético in the data
		st := fixtureStore(t)
		if n := len(st.resolveTeams("Atletico")); n != 2 {
			t.Errorf("Atletico matched %d clubs, want 2", n)
		}
	})
}

func TestFeature_Finals(t *testing.T) {
	t.Run("Scenario: the last Copa do Brasil round is flagged as the final", func(t *testing.T) {
		st := fixtureStore(t)
		finals := countWhere(st.Matches, func(m Match) bool {
			return m.Competition == compCup && m.IsFinal
		})
		if finals != 2 {
			t.Errorf("expected both legs of round 8 to be finals, got %d", finals)
		}
	})

	t.Run("Scenario: the Libertadores final stage is flagged", func(t *testing.T) {
		st := fixtureStore(t)
		if countWhere(st.Matches, func(m Match) bool { return m.Competition == compLibertadores && m.IsFinal }) != 1 {
			t.Error("expected the Libertadores final to be flagged")
		}
	})
}

func countWhere(matches []Match, pred func(Match) bool) int {
	n := 0
	for _, m := range matches {
		if pred(m) {
			n++
		}
	}
	return n
}
