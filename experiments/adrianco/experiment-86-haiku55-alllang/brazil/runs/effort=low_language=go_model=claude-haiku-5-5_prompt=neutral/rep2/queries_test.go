package main

import (
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

// callTool runs a named tool against st with a JSON argument string.
func callTool(t *testing.T, st *Store, name, args string) (string, error) {
	t.Helper()
	for _, tool := range newTools(st) {
		if tool.Name == name {
			return tool.run(json.RawMessage(args))
		}
	}
	t.Fatalf("no tool named %q", name)
	return "", nil
}

// mustCall runs a tool and fails the test on error.
func mustCall(t *testing.T, st *Store, name, args string) string {
	t.Helper()
	out, err := callTool(t, st, name, args)
	if err != nil {
		t.Fatalf("%s(%s) returned error: %v", name, args, err)
	}
	return out
}

func assertContains(t *testing.T, text string, wants ...string) {
	t.Helper()
	for _, want := range wants {
		if !strings.Contains(text, want) {
			t.Errorf("output missing %q\n--- output ---\n%s", want, text)
		}
	}
}

func TestFeature_MatchQueries(t *testing.T) {
	st := fixtureStore(t)

	t.Run("Scenario: find matches between two teams with a head-to-head summary", func(t *testing.T) {
		// Given the match data is loaded
		// When I search for matches between "Flamengo" and "Fluminense"
		out := mustCall(t, st, "find_matches", `{"team":"Flamengo","opponent":"Fluminense"}`)
		// Then I receive each match with date, score and competition
		assertContains(t, out,
			"Flamengo vs Fluminense (2 matches):",
			"- 2019-09-01: Fluminense 0-0 Flamengo (Brasileirão Serie A, Round 22)",
			"- 2019-05-01: Flamengo 2-1 Fluminense (Brasileirão Serie A, Round 5)",
		)
		// And the head-to-head record is summarized
		assertContains(t, out, "Head-to-head in dataset: Flamengo 1 wins, Fluminense 0 wins, 1 draws")
	})

	t.Run("Scenario: finals of the Copa do Brasil", func(t *testing.T) {
		// Given the Copa do Brasil data includes a two-legged final
		// When I ask for finals only
		out := mustCall(t, st, "find_matches", `{"competition":"Copa do Brasil","finals_only":true}`)
		// Then both legs of the last round are listed
		assertContains(t, out, "Matches (2):", "Copa do Brasil, Round 8, Final")
	})

	t.Run("Scenario: Libertadores final", func(t *testing.T) {
		out := mustCall(t, st, "find_matches", `{"competition":"Libertadores","finals_only":true}`)
		assertContains(t, out, "Flamengo 2-1 River Plate (Copa Libertadores, final)")
	})

	t.Run("Scenario: filter by date range", func(t *testing.T) {
		// Given matches throughout 2019
		// When I ask for July 2019 only
		out := mustCall(t, st, "find_matches", `{"competition":"Brasileirão","date_from":"2019-07-01","date_to":"2019-07-31"}`)
		// Then only the 10 July fixture is returned
		assertContains(t, out, "Matches (1):", "2019-07-10: Corinthians 1-1 Palmeiras")
	})

	t.Run("Scenario: unknown team gives a clear error", func(t *testing.T) {
		_, err := callTool(t, st, "find_matches", `{"team":"Nonexistent FC"}`)
		if err == nil || !strings.Contains(err.Error(), "no team matching") {
			t.Fatalf("expected a no-team error, got %v", err)
		}
	})

	t.Run("Scenario: the same club under two spellings is one club", func(t *testing.T) {
		// Given Atletico Mineiro (BR-Football spelling) and Atlético-MG (Brasileirão)
		// When I list matches for the first spelling
		out := mustCall(t, st, "find_matches", `{"team":"Atletico Mineiro","competition":"Brasileirão"}`)
		// Then the 2019 Brasileirão results for Atlético-MG appear
		assertContains(t, out, "2019-08-12: Atlético-MG 4-0 Santos")
	})
}

func TestFeature_TeamQueries(t *testing.T) {
	st := fixtureStore(t)

	t.Run("Scenario: a team's home record in a season", func(t *testing.T) {
		// Given Palmeiras won its only 2019 home game 3-0
		// When I request the home record for 2019
		out := mustCall(t, st, "team_stats", `{"team":"Palmeiras","venue":"home","season":2019}`)
		// Then the wins, goals and win rate are reported
		assertContains(t, out,
			"Palmeiras home record (2019):",
			"- Matches: 1",
			"- Wins: 1, Draws: 0, Losses: 0",
			"- Goals For: 3, Goals Against: 0",
			"- Win rate: 100.0%",
		)
	})

	t.Run("Scenario: team ranking by win rate", func(t *testing.T) {
		// Given Atlético-MG won both of its 2019 Brasileirão games
		// When I rank teams by win rate
		out := mustCall(t, st, "team_ranking", `{"competition":"Brasileirão","season":2019,"min_matches":1,"limit":1}`)
		// Then it is first
		assertContains(t, out, "1. Atlético-MG - 100.0% win rate (2W in 2 matches)")
	})

	t.Run("Scenario: an unknown venue is rejected", func(t *testing.T) {
		if _, err := callTool(t, st, "team_stats", `{"team":"Palmeiras","venue":"neutral"}`); err == nil {
			t.Fatal("expected an error for venue neutral")
		}
	})
}

func TestFeature_Standings(t *testing.T) {
	st := fixtureStore(t)

	t.Run("Scenario: calculate the 2019 table from match results", func(t *testing.T) {
		// Given the 2019 Brasileirão fixtures
		// When I request the standings
		out := mustCall(t, st, "standings", `{"season":2019}`)
		// Then points, record and goal difference are calculated
		// Atlético-MG: two wins (6 pts). Palmeiras: a win and a draw (4 pts, GD +3).
		// Flamengo: a win, a draw and a loss (4 pts, GD 0).
		assertContains(t, out,
			"2019 Brasileirão Serie A standings (calculated from matches):",
			"1. Atlético-MG - 6 pts (2W, 0D, 0L, GD +5) - Champion",
			"2. Palmeiras - 4 pts (1W, 1D, 0L, GD +3)",
			"3. Flamengo - 4 pts (1W, 1D, 1L, GD +0)",
		)
	})

	t.Run("Scenario: the latest season is the default", func(t *testing.T) {
		// Given the fixtures include a 2023 Serie A match from BR-Football
		// When no season is given
		out := mustCall(t, st, "standings", `{}`)
		// Then the table for the latest season (2023) is returned
		assertContains(t, out, "2023 Brasileirão Serie A standings")
	})
}

func TestFeature_CompetitionAndStatistics(t *testing.T) {
	st := fixtureStore(t)

	t.Run("Scenario: aggregate statistics for a season", func(t *testing.T) {
		// Given seven 2019 Brasileirão matches with 17 goals in total
		// When I request competition statistics
		out := mustCall(t, st, "competition_stats", `{"competition":"Brasileirão","season":2019}`)
		// Then goals per match, home/draw/away rates and the biggest win are reported
		assertContains(t, out,
			"- Matches: 7",
			"- Goals per match: 2.43",
			"- Home win rate: 57.1%, Draw rate: 42.9%, Away win rate: 0.0%",
			"1. 2019-08-12: Atlético-MG 4-0 Santos",
		)
	})

	t.Run("Scenario: resolve competition wording", func(t *testing.T) {
		cases := map[string]string{
			"Brasileirão":    compBrasileirao,
			"serie a":        compBrasileirao,
			"copa do brasil": compCup,
			"Libertadores":   compLibertadores,
			"Serie B":        compSerieB,
			"":               "",
		}
		for in, want := range cases {
			got, err := resolveCompetition(in)
			if err != nil || got != want {
				t.Errorf("resolveCompetition(%q) = %q, %v; want %q", in, got, err, want)
			}
		}
		if _, err := resolveCompetition("Premier League"); err == nil {
			t.Error("expected an error for an unknown competition")
		}
	})
}

func TestFeature_PlayerQueries(t *testing.T) {
	st := fixtureStore(t)

	t.Run("Scenario: find players by name", func(t *testing.T) {
		out := mustCall(t, st, "search_players", `{"name":"Neymar"}`)
		assertContains(t, out, "1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain")
	})

	t.Run("Scenario: top Brazilian players at a club, sorted by rating", func(t *testing.T) {
		// Given Flamengo has two Brazilian players in the FIFA data
		// When I search Brazilian players at Flamengo
		out := mustCall(t, st, "search_players", `{"nationality":"Brazil","club":"Flamengo","min_overall":80}`)
		// Then they are listed best first
		assertContains(t, out, "1. Gabriel Barbosa", "2. Diego Ribas")
	})

	t.Run("Scenario: filter by position group", func(t *testing.T) {
		out := mustCall(t, st, "search_players", `{"position":"forwards"}`)
		assertContains(t, out, "Gabriel Barbosa", "Vitoria Player")
		if strings.Contains(out, "Alisson") {
			t.Error("goalkeeper should not match the forward group")
		}
	})

	t.Run("Scenario: Brazilian players at Brazilian clubs", func(t *testing.T) {
		// Given Vitória Guimarães and Santos Laguna are not Brazilian clubs
		// When I summarize Brazilian players at Brazilian clubs
		out := mustCall(t, st, "brazilian_clubs_summary", `{}`)
		// Then CR Flamengo is counted and the two Portuguese-style names are not
		assertContains(t, out, "- CR Flamengo: 2 players (avg rating: 82)")
		if strings.Contains(out, "Vitória Guimarães:") || strings.Contains(out, "Santos Laguna:") {
			t.Errorf("non-Brazilian clubs were counted:\n%s", out)
		}
	})
}

func TestFeature_ToolArguments(t *testing.T) {
	st := fixtureStore(t)

	t.Run("Scenario: malformed arguments are reported as an error", func(t *testing.T) {
		if _, err := callTool(t, st, "find_matches", `{"season":"twenty"}`); err == nil {
			t.Fatal("expected an error for a string season")
		}
	})

	t.Run("Scenario: no arguments uses the defaults", func(t *testing.T) {
		out := mustCall(t, st, "find_matches", "")
		if !strings.HasPrefix(out, "Matches (") {
			t.Fatalf("unexpected output: %s", out)
		}
	})

	t.Run("Scenario: every tool has a schema with an object type", func(t *testing.T) {
		for _, tool := range newTools(st) {
			if tool.InputSchema["type"] != "object" {
				t.Errorf("%s schema is not an object", tool.Name)
			}
			if _, err := json.Marshal(tool.InputSchema); err != nil {
				t.Errorf("%s schema does not marshal: %v", tool.Name, err)
			}
		}
	})
}

func TestBDD_StepsCoverRequiredQuestionTypes(t *testing.T) {
	// The spec asks for at least 20 example questions to be answerable.
	// Each entry is one tool call that answers a spec example. The test
	// checks that each call succeeds and returns something non-empty.
	st := fixtureStore(t)
	questions := []struct{ tool, args string }{
		{"find_matches", `{"team":"Flamengo","opponent":"Fluminense"}`},
		{"find_matches", `{"team":"Palmeiras","season":2019}`},
		{"find_matches", `{"competition":"Copa do Brasil","finals_only":true}`},
		{"team_stats", `{"team":"Corinthians","venue":"home","season":2019}`},
		{"team_stats", `{"team":"Palmeiras","competition":"Brasileirão","season":2019}`},
		{"standings", `{"season":2019}`},
		{"team_ranking", `{"venue":"home","competition":"Brasileirão","min_matches":1}`},
		{"competition_stats", `{"competition":"Brasileirão"}`},
		{"search_players", `{"nationality":"Brazil"}`},
		{"search_players", `{"name":"Gabriel Barbosa"}`},
		{"search_players", `{"club":"Flamengo"}`},
		{"brazilian_clubs_summary", `{}`},
	}
	for i, q := range questions {
		t.Run(fmt.Sprintf("Scenario %d: %s %s", i+1, q.tool, q.args), func(t *testing.T) {
			out := mustCall(t, st, q.tool, q.args)
			if strings.TrimSpace(out) == "" {
				t.Fatal("empty answer")
			}
		})
	}
}
