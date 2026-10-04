package main

import (
	"strings"
	"testing"
	"time"
)

// sampleQuestions maps natural-language questions (from the specification
// and beyond) to the tool call an LLM would make, and checks that the answer
// contains the facts needed to respond. Expected values were verified
// against the raw CSV files and real-world results.
var sampleQuestions = []struct {
	question string
	tool     string
	args     map[string]any
	want     []string
}{
	// --- Match queries ---
	{"Show me all Flamengo vs Fluminense matches", "search_matches",
		map[string]any{"team": "Flamengo", "opponent": "Fluminense", "limit": 50},
		[]string{"44 matches found", "(Fla-Flu)", "Head-to-head in selection: Flamengo 18 wins, Fluminense 14 wins, 12 draws"}},
	{"What matches did Palmeiras play in 2023?", "search_matches",
		map[string]any{"team": "Palmeiras", "season": 2023},
		[]string{"43 matches found for Palmeiras, season 2023", "2023-12-07: Cruzeiro 1-1 Palmeiras"}},
	{"Find all Copa do Brasil finals", "knockout_matches",
		map[string]any{"competition": "Copa do Brasil", "stage": "final"},
		[]string{"Palmeiras 3-1 Coritiba on aggregate: Palmeiras won the title", "Athletico Paranaense 3-1 Internacional on aggregate: Athletico Paranaense won the title",
			"Atlético Mineiro 6-1 Athletico Paranaense", "Flamengo 1-2 São Paulo on aggregate: São Paulo won the title"}},
	{"When did Flamengo last play Corinthians?", "search_matches",
		map[string]any{"team": "Flamengo", "opponent": "Corinthians", "limit": 1},
		[]string{"2023-10-08: Corinthians 1-1 Flamengo"}},
	{"What was the score? (follow-up: same lookup)", "search_matches",
		map[string]any{"team": "Flamengo", "opponent": "Corinthians", "limit": 1, "order": "recent"},
		[]string{"Corinthians 1-1 Flamengo"}},
	{"Which Libertadores matches were played in November 2019?", "search_matches",
		map[string]any{"competition": "Libertadores", "date_from": "01/11/2019", "date_to": "2019-11-30"},
		[]string{"2019-11-23: Flamengo 2-1 River Plate (Copa Libertadores 2019, final)"}},

	// --- Team queries ---
	{"What is Corinthians' home record in 2022?", "team_record",
		map[string]any{"team": "Corinthians", "season": 2022, "venue": "home", "competition": "Brasileirão"},
		[]string{"Corinthians home record (2022 Brasileirão Série A)", "Matches: 19", "Wins: 12, Draws: 4, Losses: 3", "Goals For: 24, Goals Against: 11", "Win rate: 63.2%"}},
	{"Which team scored the most goals in Serie A 2023?", "team_rankings",
		map[string]any{"metric": "goals_for", "competition": "Serie A", "season": 2023},
		[]string{"1. Grêmio - 63 goals scored", "2. Palmeiras - 61 goals scored"}},
	{"Compare Palmeiras and Santos head-to-head", "head_to_head",
		map[string]any{"team_a": "Palmeiras", "team_b": "Santos"},
		[]string{"Palmeiras vs Santos (Clássico da Saudade)", "Head-to-head in dataset: Palmeiras", "By competition:"}},
	{"What competitions has Palmeiras played in?", "team_overview",
		map[string]any{"team": "Palmeiras"},
		[]string{"Brasileirão Série A: 733 matches", "Copa do Brasil:", "Copa Libertadores:", "2016: 1st/20 (champion)", "Rivals: Corinthians (Derby Paulista)"}},

	// --- Player queries ---
	{"Find all Brazilian players in the dataset", "search_players",
		map[string]any{"nationality": "Brazil", "limit": 10},
		[]string{"827 players found", "1. Neymar Jr - Overall: 92", "Position: LW, Club: Paris Saint-Germain", "Brazilian players at Brazilian clubs:", "- Santos: 20 players"}},
	{"Who are the highest-rated players at Flamengo?", "search_players",
		map[string]any{"club": "Flamengo"},
		[]string{"0 players found", "Flamengo appears in the match data but has no squad in the FIFA 19 dataset"}},
	{"Show me all forwards from São Paulo FC", "search_players",
		map[string]any{"club": "São Paulo FC", "position": "forwards"},
		[]string{"0 players found", "São Paulo appears in the match data"}},
	{"Which players play for Santos?", "search_players",
		map[string]any{"club": "Santos"},
		[]string{"20 players found", "Club: Santos"}},
	{"Who is Gabriel Barbosa?", "get_player",
		map[string]any{"name": "Gabriel Barbosa"},
		[]string{"No player named \"Gabriel Barbosa\"", "Gabriel Jesus - Overall: 83"}},
	{"Who is Neymar?", "get_player",
		map[string]any{"name": "neymar"},
		[]string{"Neymar Jr (FIFA 19 ID 190871)", "Club: Paris Saint-Germain, Position: LW", "Overall: 92, Potential: 93"}},
	{"Who are the top Brazilian goalkeepers?", "search_players",
		map[string]any{"nationality": "Brazilian", "position": "goalkeepers", "limit": 3},
		[]string{"1. Ederson - Overall: 86", "2. Alisson - Overall: 85"}},
	{"How has the club of Grêmio's best FIFA player performed? (cross-file)", "get_player",
		map[string]any{"name": "Ronaldo Cabrais"},
		[]string{"Club: Grêmio", "Club in match data: Grêmio - 923 matches"}},

	// --- Competition queries ---
	{"Who won the 2019 Brasileirão?", "standings",
		map[string]any{"season": 2019, "top": 3},
		[]string{"1. Flamengo - 90 pts (28W, 6D, 4L)", "- Champion", "2. Santos - 74 pts (22W, 8D, 8L)", "3. Palmeiras - 74 pts (21W, 11D, 6L)"}},
	{"Show the 2018 Copa Libertadores bracket", "knockout_matches",
		map[string]any{"competition": "Copa Libertadores", "season": 2018},
		[]string{"Round of 16:", "Quarterfinals:", "Semifinals:", "Boca Juniors 3-5 River Plate on aggregate: River Plate won the title"}},
	{"Which teams were relegated in 2020?", "standings",
		map[string]any{"season": 2020, "top": 1},
		[]string{"Relegated: Vasco da Gama, Goiás, Coritiba, Botafogo"}},
	{"Who won the 2009 Brasileirão?", "standings",
		map[string]any{"season": 2009, "top": 1},
		[]string{"1. Flamengo - 67 pts", "Champion"}},
	{"What did the 2023 table look like? (incomplete data must be flagged)", "standings",
		map[string]any{"season": 2023, "top": 3},
		[]string{"WARNING: the dataset is missing 3 of the 380 matches", "Leader in dataset"}},
	{"Show the 2022 Serie B table", "standings",
		map[string]any{"season": 2022, "competition": "Serie B", "top": 4},
		[]string{"1. Cruzeiro - 78 pts"}},

	// --- Statistical analysis ---
	{"What's the average goals per match in the Brasileirão?", "league_stats",
		map[string]any{"competition": "Brasileirão"},
		[]string{"8403 matches, seasons 2003-2023", "Average goals per match: 2.57", "Home win rate: 49.7%"}},
	{"Which team has the best away record?", "team_rankings",
		map[string]any{"metric": "win_rate", "venue": "away", "competition": "Serie A"},
		[]string{"away matches only", "1. Cruzeiro - 33.0% wins"}},
	{"Which team has the best home record?", "team_rankings",
		map[string]any{"metric": "win_rate", "venue": "home", "competition": "Serie A"},
		[]string{"home matches only", "1. Grêmio - 59.1% wins"}},
	{"Show me the biggest wins in the dataset", "biggest_wins",
		map[string]any{},
		[]string{"1. 2021-06-08: São Paulo 9-1 4 de Julho (Copa do Brasil 2021, round 3)", "Average goals per match:", "Home win rate:"}},
	{"What was the highest-scoring Brasileirão match?", "biggest_wins",
		map[string]any{"competition": "Brasileirão", "sort_by": "total_goals", "limit": 1},
		[]string{"1. 2003-10-22: Bahia 4-7 Santos"}},
	{"Compare the 2018 and 2019 seasons", "compare_seasons",
		map[string]any{"seasons": "2018,2019"},
		[]string{"2018 (380 matches)", "Champion (calculated): Palmeiras, 80 pts", "2019 (380 matches)", "Champion (calculated): Flamengo, 90 pts"}},
	{"Show me all derbies in 2023", "find_derbies",
		map[string]any{"season": 2023},
		[]string{"Fla-Flu", "Grenal", "Derby Paulista", "Choque-Rei"}},
	{"What is the Grenal head-to-head record?", "head_to_head",
		map[string]any{"team_a": "Gremio", "team_b": "Internacional", "competition": "Serie A"},
		[]string{"Grêmio vs Internacional (Grenal), Brasileirão Série A"}},
	{"How do team names get normalised for Athletico?", "list_teams",
		map[string]any{"query": "athletico"},
		[]string{"Athletico Paranaense [id atletico-pr]", "Atletico-PR", "Athletico Paranaense - PR"}},
}

func TestSampleQuestions(t *testing.T) {
	srv := newTestServer(t)
	if len(sampleQuestions) < 20 {
		t.Fatalf("only %d sample questions; the spec requires at least 20", len(sampleQuestions))
	}
	for _, q := range sampleQuestions {
		t.Run(q.question, func(t *testing.T) {
			start := time.Now()
			text, err := srv.CallTool(q.tool, q.args)
			elapsed := time.Since(start)
			if err != nil {
				t.Fatalf("%s(%v): %v", q.tool, q.args, err)
			}
			for _, w := range q.want {
				if !strings.Contains(text, w) {
					t.Errorf("answer missing %q\n--- answer ---\n%s", w, text)
				}
			}
			// Spec: simple lookups < 2 s, aggregates < 5 s.
			if elapsed > 2*time.Second {
				t.Errorf("took %s", elapsed)
			}
		})
	}
}

func BenchmarkAggregateQueries(b *testing.B) {
	srv := NewServer(loadTestStore(b), nil)
	for i := 0; i < b.N; i++ {
		for _, call := range []struct {
			tool string
			args map[string]any
		}{
			{"team_overview", map[string]any{"team": "Flamengo"}},
			{"league_stats", map[string]any{}},
			{"team_rankings", map[string]any{"metric": "points_rate"}},
			{"search_players", map[string]any{"nationality": "Brazil"}},
		} {
			if _, err := srv.CallTool(call.tool, call.args); err != nil {
				b.Fatal(err)
			}
		}
	}
}
