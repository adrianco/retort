// BDD scenarios for loading the six provided datasets.

package main

import (
	"testing"
	"time"
)

func TestLoadDataset(t *testing.T) {
	t.Run("Given the provided Kaggle files", func(t *testing.T) {
		ds := loadTestDataset(t)

		t.Run("When loaded, Then all six files contribute data", func(t *testing.T) {
			if len(ds.Matches) == 0 || len(ds.Players) == 0 {
				t.Fatalf("matches=%d players=%d", len(ds.Matches), len(ds.Players))
			}
			comps := map[string]bool{}
			for _, m := range ds.Matches {
				comps[m.Competition] = true
			}
			for _, want := range []string{CompBrasileirao, CompCopaBrasil, CompLibertadore, CompSerieB} {
				if !comps[want] {
					t.Errorf("no matches loaded for %q", want)
				}
			}
		})

		t.Run("When loaded, Then the FIFA file has the expected player count", func(t *testing.T) {
			// fifa_data.csv has 18,207 player rows.
			if len(ds.Players) != 18207 {
				t.Fatalf("players = %d, want 18207", len(ds.Players))
			}
		})

		t.Run("When loaded, Then no fixture appears twice", func(t *testing.T) {
			seen := map[string]bool{}
			for _, m := range ds.Matches {
				k := fixtureKey(m)
				if seen[k] {
					t.Fatalf("duplicate fixture %s", k)
				}
				seen[k] = true
			}
		})

		t.Run("When loaded, Then every match has a valid date and goal counts", func(t *testing.T) {
			for _, m := range ds.Matches {
				if m.Date.IsZero() || m.Date.Year() < 2003 || m.Date.After(time.Now().AddDate(1, 0, 0)) {
					t.Fatalf("bad date %v in %+v", m.Date, m)
				}
				if m.HomeGoals < 0 || m.AwayGoals < 0 {
					t.Fatalf("negative goals in %+v", m)
				}
			}
		})

		t.Run("When loaded, Then the 2019 Flamengo Brasileirão season has 38 rounds", func(t *testing.T) {
			fla := ParseTeam("Flamengo", "")
			n := 0
			for _, m := range ds.Matches {
				if m.Competition != CompBrasileirao || m.Season != 2019 {
					continue
				}
				if fla.Matches(m.Home) || fla.Matches(m.Away) {
					n++
				}
			}
			if n != 38 {
				t.Fatalf("Flamengo 2019 Brasileirão matches = %d, want 38", n)
			}
		})
	})
}

func TestParseDate(t *testing.T) {
	cases := map[string]string{
		"2023-09-24":          "2023-09-24",
		"2012-05-19 18:30:00": "2012-05-19",
		"29/03/2003":          "2003-03-29",
	}
	for in, want := range cases {
		t.Run("Given the date "+in, func(t *testing.T) {
			got, ok := parseDate(in)
			if !ok || got.Format("2006-01-02") != want {
				t.Fatalf("parseDate(%q) = %v, %v; want %s", in, got, ok, want)
			}
		})
	}
	t.Run("Given a malformed date, Then it is rejected", func(t *testing.T) {
		if _, ok := parseDate("not a date"); ok {
			t.Fatal("expected rejection")
		}
	})
}

func TestParseGoals(t *testing.T) {
	t.Run("Given goal values in the different file formats", func(t *testing.T) {
		for in, want := range map[string]int{"2": 2, "2.0": 2, " 0 ": 0} {
			if got, ok := parseGoals(in); !ok || got != want {
				t.Errorf("parseGoals(%q) = %d, %v", in, got, ok)
			}
		}
		t.Run("When a goal value is blank, Then the row is rejected", func(t *testing.T) {
			if _, ok := parseGoals(""); ok {
				t.Fatal("blank goals should be rejected")
			}
		})
	})
}
