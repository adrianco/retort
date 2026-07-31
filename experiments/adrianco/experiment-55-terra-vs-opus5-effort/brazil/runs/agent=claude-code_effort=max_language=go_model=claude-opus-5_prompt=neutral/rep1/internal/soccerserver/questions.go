// questions.go is the catalogue of natural language questions this server can
// answer, each paired with the tool call that answers it.
//
// It is not documentation that can drift: the demo mode runs it, the
// soccer://sample-questions resource renders it, and TestSampleQuestions
// executes every entry and fails if any call errors or returns nothing.
package soccerserver

// SampleQuestion pairs a question with the tool call that answers it.
type SampleQuestion struct {
	Question string         `json:"question"`
	Category string         `json:"category"`
	Tool     string         `json:"tool"`
	Args     map[string]any `json:"args"`
	// Expect is a substring the answer must contain, used by the tests to
	// prove the call really answered the question.
	Expect string `json:"-"`
}

// SampleQuestions covers all five capability groups from the specification:
// match queries, team queries, player queries, competition queries and
// statistical analysis.
var SampleQuestions = []SampleQuestion{
	// ---- Match queries -----------------------------------------------------
	{
		Question: "Show me all Flamengo vs Fluminense matches",
		Category: "match", Tool: "head_to_head",
		Args:   map[string]any{"team_a": "Flamengo", "team_b": "Fluminense", "limit": 10},
		Expect: "Fla-Flu",
	},
	{
		Question: "What matches did Palmeiras play in 2023?",
		Category: "match", Tool: "search_matches",
		Args:   map[string]any{"team": "Palmeiras", "season": 2023, "limit": 10},
		Expect: "Palmeiras",
	},
	{
		Question: "Find all Copa do Brasil finals",
		Category: "match", Tool: "search_matches",
		Args:   map[string]any{"competition": "copa-do-brasil", "stage": "final", "limit": 40, "sort": "date_asc"},
		Expect: "final",
	},
	{
		Question: "When did Flamengo last play Corinthians, and what was the score?",
		Category: "match", Tool: "match_details",
		Args:   map[string]any{"team": "Flamengo", "opponent": "Corinthians"},
		Expect: "Corinthians",
	},
	{
		Question: "Which matches did Grêmio win away from home in the 2019 Brasileirão?",
		Category: "match", Tool: "search_matches",
		Args:   map[string]any{"team": "Gremio", "competition": "brasileirao", "season": 2019, "venue": "away", "result": "win"},
		Expect: "Grêmio",
	},
	{
		Question: "Show me all derbies in 2023",
		Category: "match", Tool: "find_derbies",
		Args:   map[string]any{"season": 2023, "limit": 20},
		Expect: "Derbies",
	},

	// ---- Team queries ------------------------------------------------------
	{
		Question: "What is Corinthians' home record in 2022?",
		Category: "team", Tool: "team_stats",
		Args:   map[string]any{"team": "Corinthians", "competition": "brasileirao", "season": 2022, "venue": "home"},
		Expect: "Win rate",
	},
	{
		Question: "Which team scored the most goals in Serie A 2023?",
		Category: "team", Tool: "best_records",
		Args:   map[string]any{"competition": "Serie A", "season": 2023, "metric": "goals_for", "limit": 5},
		Expect: "goals for",
	},
	{
		Question: "Compare Palmeiras and Santos head-to-head",
		Category: "team", Tool: "head_to_head",
		Args:   map[string]any{"team_a": "Palmeiras", "team_b": "Santos", "limit": 5},
		Expect: "Head-to-head",
	},
	{
		Question: "What competitions has Palmeiras played in?",
		Category: "team", Tool: "team_profile",
		Args:   map[string]any{"team": "Palmeiras"},
		Expect: "By competition",
	},
	{
		Question: "Which clubs from Rio de Janeiro are in the data?",
		Category: "team", Tool: "list_teams",
		Args:   map[string]any{"state": "RJ", "limit": 15},
		Expect: "Flamengo",
	},

	// ---- Player queries ----------------------------------------------------
	{
		Question: "Find all Brazilian players in the dataset",
		Category: "player", Tool: "search_players",
		Args:   map[string]any{"nationality": "Brazil", "limit": 10},
		Expect: "Brazil",
	},
	{
		Question: "Who are the top Brazilian players?",
		Category: "player", Tool: "search_players",
		Args:   map[string]any{"nationality": "Brazil", "sort": "overall_desc", "limit": 5},
		Expect: "Neymar",
	},
	{
		Question: "Who is Neymar?",
		Category: "player", Tool: "player_profile",
		Args:   map[string]any{"name": "Neymar"},
		Expect: "Overall",
	},
	{
		Question: "Who are the highest-rated players at Grêmio?",
		Category: "player", Tool: "search_players",
		Args:   map[string]any{"club": "Gremio", "limit": 5},
		Expect: "Overall",
	},
	{
		Question: "Show me all forwards at Cruzeiro",
		Category: "player", Tool: "search_players",
		Args:   map[string]any{"club": "Cruzeiro", "position": "forward", "limit": 10},
		Expect: "Players",
	},
	{
		Question: "Which Brazilian clubs have squads in the player data, and how strong are they?",
		Category: "player", Tool: "club_squads",
		Args:   map[string]any{"brazilian_only": true, "limit": 20},
		Expect: "avg rating",
	},
	{
		Question: "Who is Gabriel Barbosa?",
		Category: "player", Tool: "player_profile",
		Args:   map[string]any{"name": "Gabriel Barbosa"},
		Expect: "", // may legitimately be "not in this snapshot"; the tool must still answer
	},

	// ---- Competition queries ----------------------------------------------
	{
		Question: "Who won the 2019 Brasileirão?",
		Category: "competition", Tool: "standings",
		Args:   map[string]any{"competition": "brasileirao", "season": 2019},
		Expect: "Champion",
	},
	{
		Question: "Which teams were relegated in 2020?",
		Category: "competition", Tool: "standings",
		Args:   map[string]any{"competition": "brasileirao", "season": 2020},
		Expect: "Relegated",
	},
	{
		Question: "Show the 2018 Copa Libertadores bracket",
		Category: "competition", Tool: "season_summary",
		Args:   map[string]any{"competition": "libertadores", "season": 2018},
		Expect: "final",
	},
	{
		Question: "Which competitions and seasons are covered?",
		Category: "competition", Tool: "list_competitions",
		Args:   map[string]any{},
		Expect: "Brasileirão",
	},
	{
		Question: "Compare the 2018 and 2019 seasons",
		Category: "competition", Tool: "compare_seasons",
		Args:   map[string]any{"competition": "brasileirao", "seasons": []any{2018, 2019}},
		Expect: "champion",
	},

	// ---- Statistical analysis ---------------------------------------------
	{
		Question: "What's the average goals per match in the Brasileirão?",
		Category: "stats", Tool: "league_statistics",
		Args:   map[string]any{"competition": "brasileirao"},
		Expect: "average goals per match",
	},
	{
		Question: "Which team has the best home record?",
		Category: "stats", Tool: "best_records",
		Args:   map[string]any{"venue": "home", "metric": "win_rate", "min_matches": 100, "limit": 5},
		Expect: "win rate",
	},
	{
		Question: "Which team has the best away record?",
		Category: "stats", Tool: "best_records",
		Args:   map[string]any{"venue": "away", "metric": "win_rate", "min_matches": 100, "limit": 5},
		Expect: "win rate",
	},
	{
		Question: "Show me the biggest wins in the dataset",
		Category: "stats", Tool: "biggest_wins",
		Args:   map[string]any{"limit": 5},
		Expect: "Biggest victories",
	},
	{
		Question: "How did the 2019 Brasileirão compare with 2020 on goals and home advantage?",
		Category: "stats", Tool: "compare_seasons",
		Args:   map[string]any{"competition": "brasileirao", "seasons": []any{2019, 2020}},
		Expect: "goals/match",
	},

	// ---- Knowledge graph ---------------------------------------------------
	{
		Question: "How is Flamengo connected in the knowledge graph?",
		Category: "graph", Tool: "graph_neighbors",
		Args:   map[string]any{"entity": "team:flamengo-rj", "node_types": []any{"state", "competition", "team"}, "limit": 15},
		Expect: "relationships",
	},
	{
		Question: "How is a Grêmio player connected to the Copa Libertadores?",
		Category: "graph", Tool: "graph_path",
		Args:   map[string]any{"from": "team:gremio-rs", "to": "competition:libertadores", "max_depth": 4},
		Expect: "Path",
	},
	{
		Question: "What data is available and what are its limits?",
		Category: "meta", Tool: "list_datasets",
		Args:   map[string]any{},
		Expect: "matches",
	},
}
