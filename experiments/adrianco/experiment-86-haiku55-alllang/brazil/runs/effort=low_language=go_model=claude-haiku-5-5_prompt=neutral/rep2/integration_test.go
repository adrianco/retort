package main

import (
	"os"
	"strings"
	"testing"
	"time"
)

// realDataDir is the Kaggle data shipped with the repository.
const realDataDir = "data/kaggle"

// Integration tests run against the real CSV files. They are skipped when the
// data is not present, so the unit tests still run in a bare checkout.
func realStore(t *testing.T) *Store {
	t.Helper()
	if _, err := os.Stat(realDataDir); err != nil {
		t.Skipf("real dataset not found at %s: %v", realDataDir, err)
	}
	start := time.Now()
	st, err := LoadStore(realDataDir)
	if err != nil {
		t.Fatalf("loading real data: %v", err)
	}
	if elapsed := time.Since(start); elapsed > 5*time.Second {
		t.Errorf("loading took %s; the spec asks for responses under 5s", elapsed)
	}
	return st
}

func TestIntegration_AllSixFilesLoad(t *testing.T) {
	st := realStore(t)
	// Every competition is present, which shows each file contributed.
	for _, comp := range []string{compBrasileirao, compCup, compLibertadores, compSerieB} {
		if countWhere(st.Matches, func(m Match) bool { return m.Competition == comp }) == 0 {
			t.Errorf("no matches loaded for %s", comp)
		}
	}
	if len(st.Players) < 18000 {
		t.Errorf("expected about 18,207 players, got %d", len(st.Players))
	}
}

func TestIntegration_StandingsMatchPublishedTable(t *testing.T) {
	st := realStore(t)
	// The 2019 Brasileirão table computed from results agrees with the published
	// final table: Flamengo 90 pts (28W, 6D, 4L), then Palmeiras and Santos on 74.
	rows := st.standings(compBrasileirao, 2019)
	if len(rows) != 20 {
		t.Fatalf("2019 table has %d teams, want 20", len(rows))
	}
	champ := rows[0]
	if champ.Name != "Flamengo-RJ" || champ.Points() != 90 || champ.Wins != 28 || champ.Draws != 6 || champ.Losses != 4 {
		t.Errorf("champion = %s %d pts (%dW %dD %dL)", champ.Name, champ.Points(), champ.Wins, champ.Draws, champ.Losses)
	}
	for _, r := range rows {
		if r.Played != 38 {
			t.Errorf("%s played %d matches in 2019, want 38", r.Name, r.Played)
		}
	}
}

func TestIntegration_SampleQuestions(t *testing.T) {
	st := realStore(t)
	questions := []struct {
		name, tool, args string
		wantSubstrings   []string
	}{
		{"Flamengo vs Fluminense", "find_matches", `{"team":"Flamengo","opponent":"Fluminense","limit":3}`,
			[]string{"Flamengo vs Fluminense", "Head-to-head in dataset:"}},
		{"Corinthians 2022 home record", "team_stats", `{"team":"Corinthians","venue":"home","season":2022}`,
			[]string{"Corinthians home record (2022):", "Win rate:"}},
		{"Who won the 2019 Brasileirão", "standings", `{"season":2019,"limit":1}`,
			[]string{"1. Flamengo-RJ - 90 pts", "Champion"}},
		{"Average goals per match", "competition_stats", `{"competition":"Brasileirão"}`,
			[]string{"Goals per match:"}},
		{"Best home record", "team_ranking", `{"venue":"home","competition":"Brasileirão","season":2022}`,
			[]string{"Team ranking by win rate"}},
		{"Copa do Brasil finals", "find_matches", `{"competition":"Copa do Brasil","finals_only":true,"limit":2}`,
			[]string{"Final"}},
		{"Brazilian players at Brazilian clubs", "brazilian_clubs_summary", `{}`,
			[]string{"Brazilian players at Brazilian clubs:"}},
		{"Who is Gabriel Jesus", "search_players", `{"name":"Gabriel Jesus"}`,
			[]string{"Player search results", "Gabriel Jesus"}},
		{"Who is Gabriel Barbosa (not in the FIFA file)", "search_players", `{"name":"Gabriel Barbosa"}`,
			[]string{"No players found."}},
	}
	for _, q := range questions {
		t.Run(q.name, func(t *testing.T) {
			start := time.Now()
			out := mustCall(t, st, q.tool, q.args)
			if elapsed := time.Since(start); elapsed > 5*time.Second {
				t.Errorf("took %s; spec limit is 5s", elapsed)
			}
			for _, want := range q.wantSubstrings {
				if !strings.Contains(out, want) {
					t.Errorf("missing %q in:\n%s", want, out)
				}
			}
		})
	}
}
