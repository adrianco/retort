// tools_test.go — the sample questions from the specification, answered
// through the MCP tools, with checks on content and response time.
package main

import (
	"strings"
	"testing"
	"time"
)

type question struct {
	ask       string // natural-language question the LLM would receive
	tool      string
	args      Args
	want      []string // substrings that must appear
	notWant   []string
	aggregate bool // aggregate queries get 5s, simple lookups 2s
}

var sampleQuestions = []question{
	// 1. Match queries
	{ask: "Show me all Flamengo vs Fluminense matches", tool: "search_matches",
		args: Args{"team": "Flamengo", "opponent": "Fluminense"},
		want: []string{"Flamengo vs Fluminense (Fla-Flu)", "2023-11-11: Flamengo 1-1 Fluminense",
			"Head-to-head in dataset: Flamengo 18 wins, Fluminense 14 wins, 12 draws"}},
	{ask: "What matches did Palmeiras play in 2023?", tool: "search_matches",
		args: Args{"team": "Palmeiras", "season": 2023, "limit": 100},
		want: []string{"Palmeiras matches season 2023", "Brasileirão 2023", "Copa do Brasil"}},
	{ask: "Find all Copa do Brasil finals", tool: "knockout_bracket",
		args: Args{"competition": "Copa do Brasil", "stage": "final"},
		want: []string{"Palmeiras win the title", "Cruzeiro win the title", "Athletico-PR win the title",
			"Grêmio win the title", "2018-10-17 Corinthians 1-2 Cruzeiro"},
		notWant: []string{"quarterfinals", "Desportiva"}},
	{ask: "Find Libertadores matches between two dates", tool: "search_matches",
		args: Args{"competition": "Libertadores", "date_from": "2019-11-01", "date_to": "2019-11-30"},
		want: []string{"Flamengo 2-1 River Plate (Libertadores final)"}},

	// 2. Team queries
	{ask: "What is Corinthians' home record in 2022?", tool: "team_record",
		args: Args{"team": "Corinthians", "season": 2022, "venue": "home", "competition": "Brasileirão"},
		want: []string{"Corinthians home record (2022 Brasileirão)", "Matches: 19", "Wins: 12, Draws: 4, Losses: 3",
			"Goals For: 24, Goals Against: 11", "Win rate: 63.2%"}},
	{ask: "Which team scored the most goals in Serie A 2022?", tool: "rank_teams",
		args: Args{"metric": "goals_for", "season": 2022, "competition": "Serie A"},
		want: []string{"1. Palmeiras - 64 goals scored", "380 matches"}, aggregate: true},
	{ask: "Compare Palmeiras and Santos head-to-head", tool: "head_to_head",
		args: Args{"team_a": "Palmeiras", "team_b": "Santos"},
		want: []string{"Palmeiras vs Santos (Clássico da Saudade)", "Palmeiras wins: 17, Santos wins: 16, Draws: 8"}},
	{ask: "What competitions has Palmeiras played in?", tool: "team_overview",
		args: Args{"team": "Palmeiras"},
		want: []string{"Brasileirão Série A:", "Copa do Brasil:", "Copa Libertadores:", "Copa Libertadores 2020", "Brasileirão 2022"}},

	// 3. Player queries
	{ask: "Find all Brazilian players in the dataset", tool: "search_players",
		args: Args{"nationality": "Brazil", "limit": 5},
		want: []string{"827 found", "1. Neymar Jr - Overall: 92", "Position: LW", "Club: Paris Saint-Germain"}},
	{ask: "Who are the highest-rated players at Flamengo?", tool: "search_players",
		args: Args{"club": "Flamengo"},
		want: []string{"Flamengo has no players in FIFA 19"}},
	{ask: "Who are the highest-rated players at Grêmio?", tool: "search_players",
		args: Args{"club": "Gremio", "limit": 3},
		want: []string{"club Grêmio", "20 found", "Overall: 83"}},
	{ask: "Show me all forwards from Santos", tool: "search_players",
		args: Args{"club": "Santos", "position": "forwards"},
		want: []string{"Club: Santos", "Position: ST"}, notWant: []string{"Santos Laguna"}},
	{ask: "Show me all forwards from São Paulo FC", tool: "search_players",
		args: Args{"club": "São Paulo FC", "position": "forward"},
		want: []string{"São Paulo has no players in FIFA 19"}},
	{ask: "Who is Gabriel Barbosa?", tool: "player_profile",
		args: Args{"name": "Gabriel Barbosa"},
		want: []string{"No player named", "Gabriel Jesus"}},
	{ask: "Who is Neymar?", tool: "player_profile",
		args: Args{"name": "neymar"},
		want: []string{"Neymar Jr", "Overall: 92, Potential: 93", "Paris Saint-Germain"}},
	{ask: "Brazilian players at Brazilian clubs", tool: "club_squads",
		args: Args{"nationality": "Brazil"},
		want: []string{"Brazil players at Brazilian clubs", "Grêmio: 20 players", "Atlético-MG: 20 players"}},

	// 4. Competition queries
	{ask: "Who won the 2019 Brasileirão?", tool: "standings",
		args: Args{"season": 2019},
		want: []string{"1. Flamengo - 90 pts (28W, 6D, 4L", "2. Santos - 74 pts (22W, 8D, 8L", "3. Palmeiras - 74 pts (21W, 11D, 6L",
			"Champion: Flamengo with 90 points"}, aggregate: true},
	{ask: "Show the 2018 Copa Libertadores bracket", tool: "knockout_bracket",
		args: Args{"competition": "Libertadores", "season": 2018},
		want: []string{"Round of 16", "Quarterfinals", "Semifinals", "Final", "River Plate win the title"}},
	{ask: "Which teams were relegated in 2020?", tool: "standings",
		args: Args{"season": 2020},
		want: []string{"Relegated (bottom 4): Vasco da Gama, Goiás, Coritiba, Botafogo"}, aggregate: true},
	{ask: "Who won the 2003 Brasileirão (24 teams)?", tool: "standings",
		args: Args{"season": "2003", "limit": 3},
		want: []string{"1. Cruzeiro - 100 pts", "Champion: Cruzeiro"}, aggregate: true},

	// 5. Statistical analysis
	{ask: "What's the average goals per match in the Brasileirão?", tool: "competition_stats",
		args: Args{"competition": "Brasileirão"},
		want: []string{"Average goals per match: 2.5", "Home win rate:", "Goals per match by season:", "- 2019: 2.31"}, aggregate: true},
	{ask: "Which team has the best away record?", tool: "rank_teams",
		args: Args{"metric": "win_rate", "venue": "away", "min_matches": 100},
		want: []string{"away games only", "1. "}, aggregate: true},
	{ask: "Which team has the best home record?", tool: "rank_teams",
		args: Args{"metric": "win_rate", "venue": "home", "min_matches": 100},
		want: []string{"home games only", "1. Grêmio"}, aggregate: true},
	{ask: "Show me the biggest wins in the dataset", tool: "biggest_wins",
		args: Args{"competition": "Brasileirão", "limit": 5},
		want: []string{"1. 2003-04-27: Goiás 7-0 Juventude"}, aggregate: true},
	{ask: "Compare the 2018 and 2019 seasons", tool: "competition_stats",
		args: Args{"seasons": "2018,2019"},
		want: []string{"| 2018 | 380 | 2.18", "| 2019 | 380 | 2.31", "Champion (calculated): Palmeiras", "Champion (calculated): Flamengo"}, aggregate: true},

	// Simple lookups / relationship queries
	{ask: "When did Flamengo last play Corinthians? What was the score?", tool: "search_matches",
		args: Args{"team": "Flamengo", "opponent": "Corinthians", "limit": 1},
		want: []string{"2023-10-08: Corinthians 1-1 Flamengo"}},
	{ask: "Show me all derbies in 2023", tool: "search_matches",
		args: Args{"derbies_only": true, "season": 2023, "limit": 100},
		want: []string{"[Fla-Flu]", "[Grenal]", "[Derby Paulista]"}},
	{ask: "Which players play for Cruzeiro, and how did Cruzeiro do in 2018? (cross-file)", tool: "team_overview",
		args: Args{"team": "Cruzeiro"},
		want: []string{"FIFA 19 squad: 20 players", "Copa do Brasil 2018", "2019 Brasileirão: 17/20"}},
	{ask: "Grenal head-to-head in the Brasileirão since 2015", tool: "head_to_head",
		args: Args{"team_a": "Internacional", "team_b": "Grêmio", "competition": "Serie A", "season_from": 2015},
		want: []string{"(Grenal)", "Meetings:"}},
	{ask: "Which spellings refer to Atlético Mineiro?", tool: "find_team",
		args: Args{"query": "Atletico Mineiro"},
		want: []string{"1. Atlético-MG", "Atletico-MG", "Atlético - MG"}},
	{ask: "Which data is available?", tool: "dataset_info",
		args: Args{},
		want: []string{"fifa_data.csv: 18207 rows", "novo_campeonato_brasileiro.csv: 6886 rows", "BR-Football-Dataset.csv: 10296 rows",
			"Brazilian_Cup_Matches.csv: 1337 rows", "Libertadores_Matches.csv: 1255 rows", "Brasileirao_Matches.csv: 4180 rows"}},
	{ask: "Série B 2023 table", tool: "standings",
		args: Args{"season": 2023, "competition": "Série B", "limit": 2},
		want: []string{"2023 Brasileirão Série B", "1. Vitória"}, aggregate: true},
	{ask: "Atlético-MG record in the 2021 Brasileirão", tool: "team_record",
		args: Args{"team": "Atlético Mineiro", "season": 2021, "competition": "brasileirao"},
		want: []string{"Wins: 26, Draws: 6, Losses: 6", "League finish: 1 of 20"}},
}

func TestSampleQuestions(t *testing.T) {
	s := testStore(t)
	if len(sampleQuestions) < 20 {
		t.Fatalf("only %d sample questions", len(sampleQuestions))
	}
	for _, q := range sampleQuestions {
		t.Run(q.ask, func(t *testing.T) {
			start := time.Now()
			out, err := CallTool(s, q.tool, q.args)
			elapsed := time.Since(start)
			if err != nil {
				t.Fatalf("%s(%v): %v", q.tool, q.args, err)
			}
			for _, w := range q.want {
				if !strings.Contains(out, w) {
					t.Errorf("missing %q in output:\n%s", w, out)
				}
			}
			for _, w := range q.notWant {
				if strings.Contains(out, w) {
					t.Errorf("unexpected %q in output:\n%s", w, out)
				}
			}
			limit := 2 * time.Second
			if q.aggregate {
				limit = 5 * time.Second
			}
			if elapsed > limit {
				t.Errorf("took %s (limit %s)", elapsed, limit)
			}
		})
	}
}

func TestToolErrors(t *testing.T) {
	s := testStore(t)
	cases := []struct {
		tool string
		args Args
		want string
	}{
		{"team_record", Args{"team": "Xyzzy United"}, "no team matching"},
		{"team_record", Args{}, "team is required"},
		{"standings", Args{}, "season is required"},
		{"standings", Args{"season": 2019, "competition": "Libertadores"}, "knockout"},
		{"search_matches", Args{"competition": "Premier League"}, "unknown competition"},
		{"search_matches", Args{"season": "twenty"}, "must be a number"},
		{"rank_teams", Args{"metric": "style"}, "unknown metric"},
		{"head_to_head", Args{"team_a": "Flamengo", "team_b": "Flamengo-RJ"}, "same team"},
		{"knockout_bracket", Args{"competition": "Brasileirão"}, "Libertadores or Copa do Brasil"},
		{"no_such_tool", Args{}, "unknown tool"},
	}
	for _, c := range cases {
		_, err := CallTool(s, c.tool, c.args)
		if err == nil || !strings.Contains(err.Error(), c.want) {
			t.Errorf("%s(%v) error = %v, want %q", c.tool, c.args, err, c.want)
		}
	}
}

func TestNoMatchesIsNotAnError(t *testing.T) {
	s := testStore(t)
	out, err := CallTool(s, "search_matches", Args{"team": "Flamengo", "season": 1990})
	if err != nil || !strings.Contains(out, "No matches found") {
		t.Errorf("got %q, %v", out, err)
	}
}

func TestHeadToHeadIsSymmetric(t *testing.T) {
	s := testStore(t)
	a, b := mustTeam(t, s, "Corinthians"), mustTeam(t, s, "Palmeiras")
	h1 := s.HeadToHead(a, b, MatchFilter{})
	h2 := s.HeadToHead(b, a, MatchFilter{})
	if h1.AWins != h2.BWins || h1.BWins != h2.AWins || h1.Draws != h2.Draws || len(h1.Matches) != len(h2.Matches) {
		t.Errorf("asymmetric: %+v vs %+v", h1, h2)
	}
	if h1.AWins+h1.BWins+h1.Draws != len(h1.Matches) {
		t.Error("results do not add up")
	}
}

func TestRecordsConsistentWithStandings(t *testing.T) {
	s := testStore(t)
	rs, ms := s.Standings(CompSerieA, 2019)
	totalGF, totalGA, wins, losses := 0, 0, 0, 0
	for _, r := range rs {
		totalGF += r.GF
		totalGA += r.GA
		wins += r.W
		losses += r.L
	}
	ag := Summarise(ms)
	if totalGF != ag.Goals || totalGA != ag.Goals || wins != losses || wins != ag.HomeWins+ag.AwayWins {
		t.Errorf("table and aggregate disagree: GF %d GA %d goals %d W %d L %d", totalGF, totalGA, ag.Goals, wins, losses)
	}
}

func TestPositionCodes(t *testing.T) {
	codes := PositionCodes("forwards")
	for _, c := range []string{"ST", "CF", "LW", "RW"} {
		if !codes[c] {
			t.Errorf("forwards should include %s", c)
		}
	}
	if !PositionCodes("GK")["GK"] || !PositionCodes("goalkeeper")["GK"] {
		t.Error("goalkeeper mapping")
	}
	if c := PositionCodes("ST,CF"); !c["ST"] || !c["CF"] {
		t.Error("comma list")
	}
}

func TestNormalizeStage(t *testing.T) {
	cases := map[string]string{
		"final": "final", "Finals": "final", "semi-final": "semifinals", "quarterfinals": "quarterfinals",
		"last 16": "round of 16", "Round of 16": "round of 16", "group": "group stage",
	}
	for in, want := range cases {
		if got := NormalizeStage(in); got != want {
			t.Errorf("NormalizeStage(%q) = %q, want %q", in, got, want)
		}
	}
}
