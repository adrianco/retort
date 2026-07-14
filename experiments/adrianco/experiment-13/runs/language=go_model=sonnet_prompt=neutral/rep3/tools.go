package main

import (
	"fmt"
	"strings"
)

func allTools() []toolDef {
	return []toolDef{
		{
			Name:        "search_matches",
			Description: "Search matches by team, competition, season, or date range across all datasets (Brasileirao, Copa do Brasil, Libertadores, historical data)",
			InputSchema: inputSchema{
				Type: "object",
				Properties: map[string]property{
					"team":        {Type: "string", Description: "Team name to search for (home or away, partial match supported)"},
					"home_team":   {Type: "string", Description: "Search by home team only"},
					"away_team":   {Type: "string", Description: "Search by away team only"},
					"competition": {Type: "string", Description: "Competition filter: 'Brasileirao', 'Copa do Brasil', 'Libertadores'"},
					"season":      {Type: "integer", Description: "Year of the season (e.g. 2023)"},
					"start_date":  {Type: "string", Description: "Start date filter (YYYY-MM-DD)"},
					"end_date":    {Type: "string", Description: "End date filter (YYYY-MM-DD)"},
					"limit":       {Type: "integer", Description: "Maximum number of results (default 20, max 100)"},
				},
			},
		},
		{
			Name:        "get_team_stats",
			Description: "Get a team's win/loss/draw record, goals scored and conceded for a given competition and season",
			InputSchema: inputSchema{
				Type: "object",
				Properties: map[string]property{
					"team":        {Type: "string", Description: "Team name (partial match supported)"},
					"competition": {Type: "string", Description: "Competition filter (optional)"},
					"season":      {Type: "integer", Description: "Season year (optional)"},
				},
				Required: []string{"team"},
			},
		},
		{
			Name:        "head_to_head",
			Description: "Get head-to-head record and recent matches between two teams",
			InputSchema: inputSchema{
				Type: "object",
				Properties: map[string]property{
					"team1":       {Type: "string", Description: "First team name"},
					"team2":       {Type: "string", Description: "Second team name"},
					"competition": {Type: "string", Description: "Filter by competition (optional)"},
					"season":      {Type: "integer", Description: "Filter by season year (optional)"},
				},
				Required: []string{"team1", "team2"},
			},
		},
		{
			Name:        "search_players",
			Description: "Search FIFA 19 player database by name, nationality, club, or position",
			InputSchema: inputSchema{
				Type: "object",
				Properties: map[string]property{
					"name":        {Type: "string", Description: "Player name (partial match)"},
					"nationality": {Type: "string", Description: "Nationality filter (e.g. 'Brazilian', 'Argentina')"},
					"club":        {Type: "string", Description: "Club name filter (e.g. 'Flamengo', 'Palmeiras')"},
					"position":    {Type: "string", Description: "Position filter (e.g. 'ST', 'GK', 'CB')"},
					"min_overall": {Type: "integer", Description: "Minimum FIFA overall rating"},
					"max_age":     {Type: "integer", Description: "Maximum player age"},
					"limit":       {Type: "integer", Description: "Maximum number of results (default 20)"},
				},
			},
		},
		{
			Name:        "get_standings",
			Description: "Calculate league standings for a given season and competition from match results",
			InputSchema: inputSchema{
				Type: "object",
				Properties: map[string]property{
					"season":      {Type: "integer", Description: "Season year (required)"},
					"competition": {Type: "string", Description: "Competition name (default: 'Brasileirao')"},
					"limit":       {Type: "integer", Description: "Show top N teams (default 20)"},
				},
				Required: []string{"season"},
			},
		},
		{
			Name:        "get_biggest_wins",
			Description: "Get the biggest victories (by goal difference) across all or specific competitions",
			InputSchema: inputSchema{
				Type: "object",
				Properties: map[string]property{
					"competition": {Type: "string", Description: "Competition filter (optional)"},
					"season":      {Type: "integer", Description: "Season year filter (optional)"},
					"limit":       {Type: "integer", Description: "Number of results (default 10)"},
				},
			},
		},
		{
			Name:        "get_competition_stats",
			Description: "Get aggregate statistics for a competition: total matches, goals, home win rate, average goals per match",
			InputSchema: inputSchema{
				Type: "object",
				Properties: map[string]property{
					"competition": {Type: "string", Description: "Competition name filter (optional)"},
					"season":      {Type: "integer", Description: "Season year filter (optional)"},
				},
			},
		},
	}
}

func dispatchTool(db *Database, name string, args map[string]interface{}) (string, error) {
	switch name {
	case "search_matches":
		return toolSearchMatches(db, args)
	case "get_team_stats":
		return toolGetTeamStats(db, args)
	case "head_to_head":
		return toolHeadToHead(db, args)
	case "search_players":
		return toolSearchPlayers(db, args)
	case "get_standings":
		return toolGetStandings(db, args)
	case "get_biggest_wins":
		return toolGetBiggestWins(db, args)
	case "get_competition_stats":
		return toolGetCompetitionStats(db, args)
	default:
		return "", fmt.Errorf("unknown tool: %s", name)
	}
}

func argString(args map[string]interface{}, key string) string {
	v, ok := args[key]
	if !ok {
		return ""
	}
	s, _ := v.(string)
	return s
}

func argInt(args map[string]interface{}, key string) int {
	v, ok := args[key]
	if !ok {
		return 0
	}
	switch n := v.(type) {
	case float64:
		return int(n)
	case int:
		return n
	}
	return 0
}

func toolSearchMatches(db *Database, args map[string]interface{}) (string, error) {
	f := MatchFilter{
		Team:        argString(args, "team"),
		HomeTeam:    argString(args, "home_team"),
		AwayTeam:    argString(args, "away_team"),
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
		StartDate:   argString(args, "start_date"),
		EndDate:     argString(args, "end_date"),
	}
	limit := argInt(args, "limit")
	if limit <= 0 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}

	matches := db.FilterMatches(f)
	if len(matches) == 0 {
		return "No matches found matching the given criteria.", nil
	}

	total := len(matches)
	if len(matches) > limit {
		matches = matches[:limit]
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Found %d matches (showing %d):\n\n", total, len(matches)))
	for _, m := range matches {
		sb.WriteString(FormatMatch(m))
		sb.WriteString("\n")
	}
	return sb.String(), nil
}

func toolGetTeamStats(db *Database, args map[string]interface{}) (string, error) {
	team := argString(args, "team")
	if team == "" {
		return "", fmt.Errorf("team parameter is required")
	}
	competition := argString(args, "competition")
	season := argInt(args, "season")

	stats := db.TeamStatsByFilter(team, competition, season)
	if stats.Matches == 0 {
		return fmt.Sprintf("No matches found for team '%s'.", team), nil
	}

	var sb strings.Builder
	desc := team
	if competition != "" {
		desc += " in " + competition
	}
	if season != 0 {
		desc += fmt.Sprintf(" (%d)", season)
	}
	sb.WriteString(fmt.Sprintf("Stats for %s:\n\n", desc))
	sb.WriteString(FormatStats(stats))
	sb.WriteString("\n")

	// Also show home vs away split
	homeStats := db.TeamStatsByFilter(team+"_home_only", competition, season)
	_ = homeStats // computed separately below
	var homeW, homeD, homeL, homeGF, homeGA int
	var awayW, awayD, awayL, awayGF, awayGA int
	for _, m := range db.Matches {
		if !m.IsPrimary {
			continue
		}
		if m.Date == "" || m.Date == "NA" {
			continue
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if teamMatches(m.HomeNorm, team) {
			homeGF += m.HomeGoal
			homeGA += m.AwayGoal
			switch {
			case m.HomeGoal > m.AwayGoal:
				homeW++
			case m.HomeGoal == m.AwayGoal:
				homeD++
			default:
				homeL++
			}
		}
		if teamMatches(m.AwayNorm, team) {
			awayGF += m.AwayGoal
			awayGA += m.HomeGoal
			switch {
			case m.AwayGoal > m.HomeGoal:
				awayW++
			case m.AwayGoal == m.HomeGoal:
				awayD++
			default:
				awayL++
			}
		}
	}
	hTotal := homeW + homeD + homeL
	aTotal := awayW + awayD + awayL
	if hTotal > 0 {
		sb.WriteString(fmt.Sprintf("\nHome: %dW/%dD/%dL, Goals %d-%d\n", homeW, homeD, homeL, homeGF, homeGA))
	}
	if aTotal > 0 {
		sb.WriteString(fmt.Sprintf("Away: %dW/%dD/%dL, Goals %d-%d\n", awayW, awayD, awayL, awayGF, awayGA))
	}

	return sb.String(), nil
}

func toolHeadToHead(db *Database, args map[string]interface{}) (string, error) {
	team1 := argString(args, "team1")
	team2 := argString(args, "team2")
	if team1 == "" || team2 == "" {
		return "", fmt.Errorf("team1 and team2 are required")
	}
	competition := argString(args, "competition")
	season := argInt(args, "season")

	matches, s1, s2 := db.HeadToHead(team1, team2, competition, season)
	if len(matches) == 0 {
		return fmt.Sprintf("No head-to-head matches found between '%s' and '%s'.", team1, team2), nil
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Head-to-Head: %s vs %s (%d matches)\n\n", team1, team2, len(matches)))
	sb.WriteString(fmt.Sprintf("Summary:\n"))
	sb.WriteString(fmt.Sprintf("  %s: %d wins, %d draws, %d losses, GF: %d, GA: %d\n",
		team1, s1.Wins, s1.Draws, s1.Losses, s1.GoalsFor, s1.GoalsAgainst))
	sb.WriteString(fmt.Sprintf("  %s: %d wins, %d draws, %d losses, GF: %d, GA: %d\n\n",
		team2, s2.Wins, s2.Draws, s2.Losses, s2.GoalsFor, s2.GoalsAgainst))

	limit := 20
	shown := matches
	if len(shown) > limit {
		shown = shown[:limit]
	}
	sb.WriteString(fmt.Sprintf("Recent matches (showing %d of %d):\n", len(shown), len(matches)))
	for _, m := range shown {
		sb.WriteString(FormatMatch(m))
		sb.WriteString("\n")
	}
	return sb.String(), nil
}

func toolSearchPlayers(db *Database, args map[string]interface{}) (string, error) {
	f := PlayerFilter{
		Name:        argString(args, "name"),
		Nationality: argString(args, "nationality"),
		Club:        argString(args, "club"),
		Position:    argString(args, "position"),
		MinOverall:  argInt(args, "min_overall"),
		MaxAge:      argInt(args, "max_age"),
	}
	limit := argInt(args, "limit")
	if limit <= 0 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}

	players := db.SearchPlayers(f)
	if len(players) == 0 {
		return "No players found matching the given criteria.", nil
	}

	total := len(players)
	if len(players) > limit {
		players = players[:limit]
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Found %d players (showing %d, sorted by overall rating):\n\n", total, len(players)))
	for i, p := range players {
		sb.WriteString(fmt.Sprintf("%d. %s\n", i+1, FormatPlayer(p)))
	}
	return sb.String(), nil
}

func toolGetStandings(db *Database, args map[string]interface{}) (string, error) {
	season := argInt(args, "season")
	if season == 0 {
		return "", fmt.Errorf("season parameter is required")
	}
	competition := argString(args, "competition")
	if competition == "" {
		competition = "Brasileirao"
	}
	limit := argInt(args, "limit")
	if limit <= 0 {
		limit = 20
	}

	standings := db.Standings(season, competition)
	if len(standings) == 0 {
		return fmt.Sprintf("No data found for %s %d.", competition, season), nil
	}

	if len(standings) > limit {
		standings = standings[:limit]
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%s %d Standings:\n\n", competition, season))
	sb.WriteString(fmt.Sprintf("%-4s %-30s %5s %4s %4s %4s %5s %5s %5s %5s\n",
		"Pos", "Team", "Pts", "P", "W", "D", "L", "GF", "GA", "GD"))
	sb.WriteString(strings.Repeat("-", 75) + "\n")
	for i, s := range standings {
		sb.WriteString(fmt.Sprintf("%-4d %-30s %5d %4d %4d %4d %4d %5d %5d %+5d\n",
			i+1, truncate(s.Team, 30), s.Points, s.Matches, s.Wins, s.Draws, s.Losses,
			s.GoalsFor, s.GoalsAgainst, s.GoalDiff()))
	}
	return sb.String(), nil
}

func toolGetBiggestWins(db *Database, args map[string]interface{}) (string, error) {
	competition := argString(args, "competition")
	season := argInt(args, "season")
	limit := argInt(args, "limit")
	if limit <= 0 {
		limit = 10
	}

	matches := db.BiggestWins(competition, season, limit)
	if len(matches) == 0 {
		return "No matches found.", nil
	}

	var sb strings.Builder
	desc := "all competitions"
	if competition != "" {
		desc = competition
	}
	if season != 0 {
		desc += fmt.Sprintf(" %d", season)
	}
	sb.WriteString(fmt.Sprintf("Biggest wins in %s:\n\n", desc))
	for i, m := range matches {
		diff := m.HomeGoal - m.AwayGoal
		if diff < 0 {
			diff = -diff
		}
		sb.WriteString(fmt.Sprintf("%d. (Diff: %d) %s\n", i+1, diff, FormatMatch(m)))
	}
	return sb.String(), nil
}

func toolGetCompetitionStats(db *Database, args map[string]interface{}) (string, error) {
	competition := argString(args, "competition")
	season := argInt(args, "season")

	stats := db.CompetitionStats(competition, season)

	var sb strings.Builder
	desc := "All competitions"
	if competition != "" {
		desc = competition
	}
	if season != 0 {
		desc += fmt.Sprintf(" %d", season)
	}
	sb.WriteString(fmt.Sprintf("Statistics for %s:\n\n", desc))
	sb.WriteString(fmt.Sprintf("Total matches:     %d\n", stats.TotalMatches))
	sb.WriteString(fmt.Sprintf("Total goals:       %d\n", stats.TotalGoals))
	sb.WriteString(fmt.Sprintf("Average goals/match: %.2f\n", stats.AvgGoals))
	sb.WriteString(fmt.Sprintf("Home wins:         %d (%.1f%%)\n", stats.HomeWins, stats.HomeWinRate))
	sb.WriteString(fmt.Sprintf("Draws:             %d (%.1f%%)\n", stats.Draws,
		float64(stats.Draws)/float64(max1(stats.TotalMatches))*100))
	sb.WriteString(fmt.Sprintf("Away wins:         %d (%.1f%%)\n", stats.AwayWins,
		float64(stats.AwayWins)/float64(max1(stats.TotalMatches))*100))
	return sb.String(), nil
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n-3] + "..."
}

func max1(n int) int {
	if n < 1 {
		return 1
	}
	return n
}
