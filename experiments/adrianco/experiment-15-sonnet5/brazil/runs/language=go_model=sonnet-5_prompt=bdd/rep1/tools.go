package main

import (
	"encoding/json"
	"fmt"
	"strings"
)

// BuildToolRegistry constructs the full set of MCP tools exposed by the
// server, covering the match, team, player, competition, and statistics
// query categories required by the specification.
func BuildToolRegistry() *ToolRegistry {
	tr := NewToolRegistry()

	tr.Register(Tool{
		Name:        "search_matches",
		Description: "Find matches by team, opponent, competition (Brasileirao, Copa do Brasil, Copa Libertadores), and/or season. Returns the most recent matching results first.",
		InputSchema: schema(`{
			"type": "object",
			"properties": {
				"team": {"type": "string", "description": "Team name, e.g. 'Flamengo' or 'Palmeiras-SP'"},
				"opponent": {"type": "string", "description": "If set, only matches against this team"},
				"competition": {"type": "string", "description": "Substring match, e.g. 'brasileirao', 'libertadores', 'copa do brasil'"},
				"season": {"type": "integer", "description": "Year, e.g. 2023"},
				"limit": {"type": "integer", "description": "Max results, default 25"}
			}
		}`),
	}, handleSearchMatches)

	tr.Register(Tool{
		Name:        "head_to_head",
		Description: "Compare two teams' full match history against each other, with win/draw/goal totals (e.g. Fla-Flu derby record).",
		InputSchema: schema(`{
			"type": "object",
			"properties": {
				"team_a": {"type": "string"},
				"team_b": {"type": "string"},
				"competition": {"type": "string", "description": "Optional substring filter"}
			},
			"required": ["team_a", "team_b"]
		}`),
	}, handleHeadToHead)

	tr.Register(Tool{
		Name:        "team_record",
		Description: "Compute a team's win/draw/loss record and goals for/against, optionally scoped to a season, competition, and home/away venue.",
		InputSchema: schema(`{
			"type": "object",
			"properties": {
				"team": {"type": "string"},
				"season": {"type": "integer"},
				"competition": {"type": "string"},
				"venue": {"type": "string", "enum": ["home", "away", ""], "description": "Restrict to home or away matches; omit for both"}
			},
			"required": ["team"]
		}`),
	}, handleTeamRecord)

	tr.Register(Tool{
		Name:        "standings",
		Description: "Calculate a league table (points, W/D/L, goals, position) for a season from match results. Works best for Brasileirao; marks bottom four as relegated for 20-team tables.",
		InputSchema: schema(`{
			"type": "object",
			"properties": {
				"season": {"type": "integer"},
				"competition": {"type": "string", "description": "Substring match, default 'brasileirao'"}
			},
			"required": ["season"]
		}`),
	}, handleStandings)

	tr.Register(Tool{
		Name:        "search_players",
		Description: "Search the FIFA player dataset by name, nationality, club, and/or position. Results sorted by overall rating, descending.",
		InputSchema: schema(`{
			"type": "object",
			"properties": {
				"name": {"type": "string"},
				"nationality": {"type": "string", "description": "e.g. 'Brazil'"},
				"club": {"type": "string"},
				"position": {"type": "string", "description": "e.g. 'ST', 'GK', 'CB'"},
				"min_overall": {"type": "integer"},
				"limit": {"type": "integer", "description": "Max results, default 25"}
			}
		}`),
	}, handleSearchPlayers)

	tr.Register(Tool{
		Name:        "top_players",
		Description: "Return the highest-rated players, optionally filtered by nationality, club, or position (e.g. top Brazilian players, top players at Flamengo).",
		InputSchema: schema(`{
			"type": "object",
			"properties": {
				"nationality": {"type": "string"},
				"club": {"type": "string"},
				"position": {"type": "string"},
				"limit": {"type": "integer", "description": "Max results, default 10"}
			}
		}`),
	}, handleTopPlayers)

	tr.Register(Tool{
		Name:        "team_players",
		Description: "List FIFA players belonging to a club, joined to match-data team names via name normalization, with the squad's average rating.",
		InputSchema: schema(`{
			"type": "object",
			"properties": {
				"team": {"type": "string"},
				"limit": {"type": "integer", "description": "Max results, default 25"}
			},
			"required": ["team"]
		}`),
	}, handleTeamPlayers)

	tr.Register(Tool{
		Name:        "biggest_wins",
		Description: "List the largest victories by goal difference, optionally filtered by competition and season.",
		InputSchema: schema(`{
			"type": "object",
			"properties": {
				"competition": {"type": "string"},
				"season": {"type": "integer"},
				"limit": {"type": "integer", "description": "Max results, default 10"}
			}
		}`),
	}, handleBiggestWins)

	tr.Register(Tool{
		Name:        "stats_summary",
		Description: "Compute aggregate statistics for a competition/season: average goals per match, home/away/draw win rates, and the biggest win.",
		InputSchema: schema(`{
			"type": "object",
			"properties": {
				"competition": {"type": "string"},
				"season": {"type": "integer"}
			}
		}`),
	}, handleStatsSummary)

	tr.Register(Tool{
		Name:        "best_record",
		Description: "Rank teams by win rate for a competition/season and venue (e.g. best home record, best away record).",
		InputSchema: schema(`{
			"type": "object",
			"properties": {
				"competition": {"type": "string"},
				"season": {"type": "integer"},
				"venue": {"type": "string", "enum": ["home", "away", ""]},
				"min_matches": {"type": "integer", "description": "Minimum matches played to qualify, default 5"},
				"limit": {"type": "integer", "description": "Max results, default 10"}
			}
		}`),
	}, handleBestRecord)

	return tr
}

func schema(s string) json.RawMessage {
	return json.RawMessage(s)
}

func dateStr(m Match) string {
	if !m.HasDate {
		return "unknown date"
	}
	return m.Date.Format("2006-01-02")
}

// --- search_matches ---

type searchMatchesArgs struct {
	Team        string `json:"team"`
	Opponent    string `json:"opponent"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Limit       int    `json:"limit"`
}

func handleSearchMatches(store *Store, raw json.RawMessage) (string, error) {
	var args searchMatchesArgs
	if err := unmarshalArgs(raw, &args); err != nil {
		return "", err
	}
	matches := store.FilterMatches(MatchFilter{
		Team:        args.Team,
		Opponent:    args.Opponent,
		Competition: args.Competition,
		Season:      args.Season,
		Limit:       args.Limit,
	})
	if len(matches) == 0 {
		return "No matches found for the given criteria.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d match(es):\n", len(matches))
	for _, m := range matches {
		fmt.Fprintf(&b, "- %s: %s %d-%d %s (%s", dateStr(m), m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Competition)
		if m.Round != "" {
			fmt.Fprintf(&b, " Round %s", m.Round)
		}
		if m.Stage != "" {
			fmt.Fprintf(&b, " %s", m.Stage)
		}
		b.WriteString(")\n")
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

// --- head_to_head ---

type headToHeadArgs struct {
	TeamA       string `json:"team_a"`
	TeamB       string `json:"team_b"`
	Competition string `json:"competition"`
}

func handleHeadToHead(store *Store, raw json.RawMessage) (string, error) {
	var args headToHeadArgs
	if err := unmarshalArgs(raw, &args); err != nil {
		return "", err
	}
	if args.TeamA == "" || args.TeamB == "" {
		return "", fmt.Errorf("both team_a and team_b are required")
	}
	res := store.HeadToHead(args.TeamA, args.TeamB, args.Competition)
	if res.TotalMatches == 0 {
		return fmt.Sprintf("No matches found between %s and %s in the dataset.", res.TeamA, res.TeamB), nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s:\n", res.TeamA, res.TeamB)
	shown := res.Matches
	const maxShown = 10
	if len(shown) > maxShown {
		shown = shown[:maxShown]
	}
	for _, m := range shown {
		fmt.Fprintf(&b, "- %s: %s %d-%d %s (%s)\n", dateStr(m), m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Competition)
	}
	if len(res.Matches) > maxShown {
		fmt.Fprintf(&b, "... (%d more matches in dataset)\n", len(res.Matches)-maxShown)
	}
	fmt.Fprintf(&b, "\nHead-to-head in dataset (%d matches): %s %d wins, %s %d wins, %d draws\n",
		res.TotalMatches, res.TeamA, res.WinsA, res.TeamB, res.WinsB, res.Draws)
	fmt.Fprintf(&b, "Goals: %s %d - %d %s", res.TeamA, res.GoalsA, res.GoalsB, res.TeamB)
	return b.String(), nil
}

// --- team_record ---

type teamRecordArgs struct {
	Team        string `json:"team"`
	Season      int    `json:"season"`
	Competition string `json:"competition"`
	Venue       string `json:"venue"`
}

func handleTeamRecord(store *Store, raw json.RawMessage) (string, error) {
	var args teamRecordArgs
	if err := unmarshalArgs(raw, &args); err != nil {
		return "", err
	}
	if args.Team == "" {
		return "", fmt.Errorf("team is required")
	}
	res := store.TeamRecord(args.Team, args.Season, args.Competition, args.Venue)
	if res.MatchesPlayed == 0 {
		return fmt.Sprintf("No matches found for %s with the given filters.", res.Team), nil
	}

	scope := res.Team
	if args.Venue != "" {
		scope += " " + strings.ToLower(args.Venue) + " record"
	} else {
		scope += " record"
	}
	if args.Season != 0 {
		scope += fmt.Sprintf(" (%d)", args.Season)
	}
	if args.Competition != "" {
		scope += fmt.Sprintf(" [%s]", args.Competition)
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n", scope)
	fmt.Fprintf(&b, "- Matches: %d\n", res.MatchesPlayed)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", res.Wins, res.Draws, res.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d\n", res.GoalsFor, res.GoalsAgainst)
	fmt.Fprintf(&b, "- Win rate: %.1f%%", res.WinRate()*100)
	return b.String(), nil
}

// --- standings ---

type standingsArgs struct {
	Season      int    `json:"season"`
	Competition string `json:"competition"`
}

func handleStandings(store *Store, raw json.RawMessage) (string, error) {
	var args standingsArgs
	if err := unmarshalArgs(raw, &args); err != nil {
		return "", err
	}
	if args.Season == 0 {
		return "", fmt.Errorf("season is required")
	}
	competition := args.Competition
	if competition == "" {
		competition = "brasileirao"
	}
	rows := store.Standings(args.Season, competition)
	if len(rows) == 0 {
		return fmt.Sprintf("No matches found for season %d / competition %q.", args.Season, competition), nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Standings (calculated from matches):\n", args.Season, titleCompetition(competition))
	for _, r := range rows {
		label := ""
		if r.Position == 1 {
			label = " - Champion"
		} else if r.Relegated {
			label = " - Relegated"
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL) GF:%d GA:%d GD:%+d%s\n",
			r.Position, r.Team, r.Points, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff(), label)
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

func titleCompetition(competition string) string {
	switch strings.ToLower(competition) {
	case "brasileirao":
		return "Brasileirao"
	default:
		return competition
	}
}

// --- search_players ---

type searchPlayersArgs struct {
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	MinOverall  int    `json:"min_overall"`
	Limit       int    `json:"limit"`
}

func handleSearchPlayers(store *Store, raw json.RawMessage) (string, error) {
	var args searchPlayersArgs
	if err := unmarshalArgs(raw, &args); err != nil {
		return "", err
	}
	players := store.SearchPlayers(PlayerFilter{
		Name:        args.Name,
		Nationality: args.Nationality,
		Club:        args.Club,
		Position:    args.Position,
		MinOverall:  args.MinOverall,
		Limit:       args.Limit,
	})
	return formatPlayerList(players, "Found"), nil
}

// --- top_players ---

type topPlayersArgs struct {
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	Limit       int    `json:"limit"`
}

func handleTopPlayers(store *Store, raw json.RawMessage) (string, error) {
	var args topPlayersArgs
	if err := unmarshalArgs(raw, &args); err != nil {
		return "", err
	}
	limit := args.Limit
	if limit <= 0 {
		limit = 10
	}
	players := store.SearchPlayers(PlayerFilter{
		Nationality: args.Nationality,
		Club:        args.Club,
		Position:    args.Position,
		Limit:       limit,
	})
	return formatPlayerList(players, "Top"), nil
}

func formatPlayerList(players []Player, verb string) string {
	if len(players) == 0 {
		return "No players found for the given criteria."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d player(s):\n", verb, len(players))
	for i, p := range players {
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s, Nationality: %s\n",
			i+1, p.Name, p.Overall, p.Position, p.Club, p.Nationality)
	}
	return strings.TrimRight(b.String(), "\n")
}

// --- team_players ---

type teamPlayersArgs struct {
	Team  string `json:"team"`
	Limit int    `json:"limit"`
}

func handleTeamPlayers(store *Store, raw json.RawMessage) (string, error) {
	var args teamPlayersArgs
	if err := unmarshalArgs(raw, &args); err != nil {
		return "", err
	}
	if args.Team == "" {
		return "", fmt.Errorf("team is required")
	}
	res := store.TeamPlayers(args.Team, args.Limit)
	if len(res.Players) == 0 {
		return fmt.Sprintf("No FIFA-dataset players found for club %q.", res.Team), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s players (avg rating: %.1f):\n", res.Team, res.AverageOverall)
	for i, p := range res.Players {
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Nationality: %s\n", i+1, p.Name, p.Overall, p.Position, p.Nationality)
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

// --- biggest_wins ---

type biggestWinsArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Limit       int    `json:"limit"`
}

func handleBiggestWins(store *Store, raw json.RawMessage) (string, error) {
	var args biggestWinsArgs
	if err := unmarshalArgs(raw, &args); err != nil {
		return "", err
	}
	limit := args.Limit
	if limit <= 0 {
		limit = 10
	}
	matches := store.BiggestWins(args.Competition, args.Season, limit)
	if len(matches) == 0 {
		return "No matches found for the given criteria.", nil
	}
	var b strings.Builder
	b.WriteString("Biggest victories in dataset:\n")
	for i, m := range matches {
		fmt.Fprintf(&b, "%d. %s: %s %d-%d %s (%s)\n", i+1, dateStr(m), m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Competition)
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

// --- stats_summary ---

type statsSummaryArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
}

func handleStatsSummary(store *Store, raw json.RawMessage) (string, error) {
	var args statsSummaryArgs
	if err := unmarshalArgs(raw, &args); err != nil {
		return "", err
	}
	res := store.StatsSummary(args.Competition, args.Season)
	if res.MatchesConsidered == 0 {
		return "No matches found for the given criteria.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Statistics over %d match(es):\n", res.MatchesConsidered)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", res.AvgGoalsPerMatch)
	fmt.Fprintf(&b, "- Home win rate: %.1f%%\n", res.HomeWinRate*100)
	fmt.Fprintf(&b, "- Away win rate: %.1f%%\n", res.AwayWinRate*100)
	fmt.Fprintf(&b, "- Draw rate: %.1f%%\n", res.DrawRate*100)
	if res.BiggestWin != nil {
		m := *res.BiggestWin
		fmt.Fprintf(&b, "- Biggest win: %s: %s %d-%d %s (%s)", dateStr(m), m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Competition)
	}
	return b.String(), nil
}

// --- best_record ---

type bestRecordArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Venue       string `json:"venue"`
	MinMatches  int    `json:"min_matches"`
	Limit       int    `json:"limit"`
}

func handleBestRecord(store *Store, raw json.RawMessage) (string, error) {
	var args bestRecordArgs
	if err := unmarshalArgs(raw, &args); err != nil {
		return "", err
	}
	limit := args.Limit
	if limit <= 0 {
		limit = 10
	}
	minMatches := args.MinMatches
	if minMatches <= 0 {
		minMatches = 5
	}
	rows := store.BestRecord(args.Competition, args.Season, args.Venue, minMatches, limit)
	if len(rows) == 0 {
		return "No teams found for the given criteria.", nil
	}
	var b strings.Builder
	venueLabel := "overall"
	if args.Venue != "" {
		venueLabel = strings.ToLower(args.Venue)
	}
	fmt.Fprintf(&b, "Best %s record:\n", venueLabel)
	for i, r := range rows {
		fmt.Fprintf(&b, "%d. %s - %d matches, %dW-%dD-%dL, win rate %.1f%%, GF:%d GA:%d\n",
			i+1, r.Team, r.MatchesPlayed, r.Wins, r.Draws, r.Losses, r.WinRate()*100, r.GoalsFor, r.GoalsAgainst)
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

func unmarshalArgs(raw json.RawMessage, dst interface{}) error {
	if len(raw) == 0 {
		return nil
	}
	if err := json.Unmarshal(raw, dst); err != nil {
		return fmt.Errorf("invalid arguments: %w", err)
	}
	return nil
}
