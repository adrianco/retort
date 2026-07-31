// samples.go is the catalogue of natural-language questions this server is
// designed to answer, each paired with the tool call that answers it. It backs
// both the `-demo` mode of the binary and the acceptance test that checks every
// question still produces an answer.
package mcpsrv

// SampleQuestion is one natural-language question and the tool call that
// answers it.
type SampleQuestion struct {
	Question    string
	Tool        string
	Args        map[string]any
	ExpectError bool // the honest answer is "that is not in the data"
}

// SampleQuestions returns the demonstration set. It covers all five capability
// categories in the specification: match, team, player, competition and
// statistical queries, plus the cross-dataset player/match join.
func SampleQuestions() []SampleQuestion {
	return []SampleQuestion{
		// --- Match queries --------------------------------------------------
		{
			Question: "Show me all Flamengo vs Fluminense matches",
			Tool:     "search_matches",
			Args:     map[string]any{"team": "Flamengo", "opponent": "Fluminense", "limit": 10},
		},
		{
			Question: "What matches did Palmeiras play in 2023?",
			Tool:     "search_matches",
			Args:     map[string]any{"team": "Palmeiras", "season": 2023, "limit": 10},
		},
		{
			Question: "Find all Copa do Brasil finals",
			Tool:     "search_matches",
			Args:     map[string]any{"competition": "copa-do-brasil", "stage": "final", "limit": 60, "sort": "date_asc"},
		},
		{
			Question: "When did Flamengo last play Corinthians, and what was the score?",
			Tool:     "search_matches",
			Args:     map[string]any{"team": "Flamengo", "opponent": "Corinthians", "limit": 1},
		},
		{
			Question: "Which matches did Grêmio play at home in the 2019 Brasileirão?",
			Tool:     "search_matches",
			Args:     map[string]any{"team": "Gremio", "competition": "serie-a", "season": 2019, "venue": "home", "limit": 20},
		},
		{
			Question: "Show me the biggest wins in the dataset",
			Tool:     "search_matches",
			Args:     map[string]any{"sort": "goal_diff", "limit": 10},
		},

		// --- Team queries ---------------------------------------------------
		{
			Question: "What is Corinthians' home record in the 2022 Brasileirão?",
			Tool:     "team_stats",
			Args:     map[string]any{"team": "Corinthians", "competition": "serie-a", "season": 2022, "venue": "home"},
		},
		{
			Question: "What competitions has Palmeiras played in?",
			Tool:     "team_stats",
			Args:     map[string]any{"team": "Palmeiras"},
		},
		{
			Question: "Compare Palmeiras and Santos head-to-head",
			Tool:     "head_to_head",
			Args:     map[string]any{"team_a": "Palmeiras", "team_b": "Santos", "limit": 10},
		},
		{
			Question: "How do Grêmio and Internacional compare in the Gre-Nal?",
			Tool:     "head_to_head",
			Args:     map[string]any{"team_a": "Gremio", "team_b": "Internacional", "limit": 10},
		},
		{
			Question: "Which clubs are called Atlético?",
			Tool:     "search_teams",
			Args:     map[string]any{"query": "Atletico", "limit": 10},
		},

		// --- Competition queries --------------------------------------------
		{
			Question: "Who won the 2019 Brasileirão?",
			Tool:     "standings",
			Args:     map[string]any{"competition": "serie-a", "season": 2019},
		},
		{
			Question: "Which teams were relegated in 2020?",
			Tool:     "standings",
			Args:     map[string]any{"competition": "serie-a", "season": 2020},
		},
		{
			Question: "Show the 2018 Copa Libertadores bracket",
			Tool:     "competition_bracket",
			Args:     map[string]any{"competition": "libertadores", "season": 2018},
		},
		{
			Question: "What competitions and seasons are available?",
			Tool:     "list_competitions",
			Args:     map[string]any{},
		},

		// --- Statistical analysis -------------------------------------------
		{
			Question: "What is the average number of goals per match in the Brasileirão?",
			Tool:     "league_stats",
			Args:     map[string]any{"competition": "serie-a"},
		},
		{
			Question: "Which team scored the most goals in Série A in 2023?",
			Tool:     "league_stats",
			Args:     map[string]any{"competition": "serie-a", "season": 2023, "top_n": 5},
		},
		{
			Question: "Which team has the best away record in the Brasileirão?",
			Tool:     "league_stats",
			Args:     map[string]any{"competition": "serie-a", "min_matches": 100, "top_n": 5},
		},
		{
			Question: "Compare the 2018 and 2019 Brasileirão seasons",
			Tool:     "compare_seasons",
			Args:     map[string]any{"competition": "serie-a", "seasons": []int{2018, 2019}},
		},
		{
			Question: "Show me all derbies in 2023",
			Tool:     "derbies",
			Args:     map[string]any{"season": 2023, "limit": 30},
		},

		// --- Player queries -------------------------------------------------
		{
			Question: "Who are the top Brazilian players in the dataset?",
			Tool:     "search_players",
			Args:     map[string]any{"nationality": "Brazil", "sort_by": "overall", "limit": 10},
		},
		{
			Question: "How many Brazilian players are at Brazilian clubs, and how good are they?",
			Tool:     "search_players",
			Args:     map[string]any{"nationality": "Brazil", "brazilian_clubs_only": true, "group_by": "club", "limit": 10},
		},
		{
			Question: "Who are the highest-rated players at Grêmio?",
			Tool:     "club_squad",
			Args:     map[string]any{"club": "Gremio", "limit": 10},
		},
		{
			Question: "Show me all forwards at Atlético Mineiro",
			Tool:     "search_players",
			Args:     map[string]any{"club": "Atletico Mineiro", "position": "forward", "limit": 10},
		},
		{
			Question: "Who is Neymar Jr?",
			Tool:     "player_profile",
			Args:     map[string]any{"name": "Neymar"},
		},
		{
			Question: "Which players play for Flamengo?",
			Tool:     "club_squad",
			Args:     map[string]any{"club": "Flamengo"},
		},
		{
			Question:    "Who is Gabriel Barbosa?",
			Tool:        "player_profile",
			Args:        map[string]any{"name": "Gabriel Barbosa"},
			ExpectError: true, // not present in the FIFA 19 snapshot
		},

		// --- Provenance -----------------------------------------------------
		{
			Question: "What data is this server working from?",
			Tool:     "dataset_info",
			Args:     map[string]any{},
		},
	}
}
