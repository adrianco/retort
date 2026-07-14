package tools

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"brazilian-soccer-mcp/store"
)

// TextContent mirrors mcp.TextContent for test ergonomics.
type TextContent struct {
	Text string
}

// Handlers holds the data store and provides MCP tool handler functions.
type Handlers struct {
	store *store.Store
}

// NewHandlers creates a new Handlers instance.
func NewHandlers(s *store.Store) *Handlers {
	return &Handlers{store: s}
}

// SearchMatches finds matches by team, season, and/or competition.
func (h *Handlers) SearchMatches(ctx context.Context, args map[string]interface{}) ([]TextContent, error) {
	team, _ := args["team"].(string)
	seasonFloat, hasSeason := args["season"].(float64)
	competition, _ := args["competition"].(string)

	var matches []store.MatchSummary
	if team != "" {
		matches = h.store.FindMatchesByTeam(team)
	} else if hasSeason {
		matches = h.store.FindMatchesBySeason(int(seasonFloat))
	} else {
		return []TextContent{{Text: "Please provide at least 'team' or 'season'."}}, nil
	}

	// Filter by competition if provided
	if competition != "" {
		q := strings.ToLower(competition)
		filtered := matches[:0]
		for _, m := range matches {
			if strings.Contains(strings.ToLower(m.Competition), q) {
				filtered = append(filtered, m)
			}
		}
		matches = filtered
	}

	// Filter by season if both team and season provided
	if team != "" && hasSeason {
		season := int(seasonFloat)
		filtered := matches[:0]
		for _, m := range matches {
			if m.Season == season {
				filtered = append(filtered, m)
			}
		}
		matches = filtered
	}

	if len(matches) == 0 {
		return []TextContent{{Text: "No matches found for the given criteria."}}, nil
	}

	// Sort by date descending
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Date > matches[j].Date
	})

	limit := 20
	if len(matches) > limit {
		matches = matches[:limit]
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Found %d matches (showing up to %d):\n\n", len(matches), limit))
	for _, m := range matches {
		sb.WriteString(fmt.Sprintf("- %s: %s %d-%d %s (%s, Season %d)\n",
			m.Date, m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam, m.Competition, m.Season))
	}
	return []TextContent{{Text: sb.String()}}, nil
}

// HeadToHead returns head-to-head record between two teams.
func (h *Handlers) HeadToHead(ctx context.Context, args map[string]interface{}) ([]TextContent, error) {
	team1, _ := args["team1"].(string)
	team2, _ := args["team2"].(string)
	if team1 == "" || team2 == "" {
		return []TextContent{{Text: "Please provide both 'team1' and 'team2'."}}, nil
	}

	h2h := h.store.HeadToHead(team1, team2)
	if h2h.Total == 0 {
		return []TextContent{{Text: fmt.Sprintf("No matches found between %s and %s.", team1, team2)}}, nil
	}

	text := fmt.Sprintf("Head-to-Head: %s vs %s\n\nTotal matches: %d\n%s wins: %d\n%s wins: %d\nDraws: %d",
		team1, team2,
		h2h.Total,
		team1, h2h.Team1Wins,
		team2, h2h.Team2Wins,
		h2h.Draws)
	return []TextContent{{Text: text}}, nil
}

// TeamStats returns team statistics for a given season.
func (h *Handlers) TeamStats(ctx context.Context, args map[string]interface{}) ([]TextContent, error) {
	team, _ := args["team"].(string)
	seasonFloat, _ := args["season"].(float64)
	if team == "" {
		return []TextContent{{Text: "Please provide 'team'."}}, nil
	}
	season := int(seasonFloat)

	stats := h.store.TeamStats(team, season)
	if stats.Played == 0 {
		return []TextContent{{Text: fmt.Sprintf("No data found for %s in season %d.", team, season)}}, nil
	}

	homeRate := float64(0)
	if stats.Played > 0 {
		homeRate = float64(stats.Wins) / float64(stats.Played) * 100
	}
	text := fmt.Sprintf("%s - Season %d Statistics\n\nPlayed: %d\nWins: %d | Draws: %d | Losses: %d\nGoals For: %d | Goals Against: %d\nPoints: %d\nWin Rate: %.1f%%",
		team, season,
		stats.Played,
		stats.Wins, stats.Draws, stats.Losses,
		stats.GF, stats.GA,
		stats.Points,
		homeRate)
	return []TextContent{{Text: text}}, nil
}

// SearchPlayers finds players by name, nationality, or club.
func (h *Handlers) SearchPlayers(ctx context.Context, args map[string]interface{}) ([]TextContent, error) {
	name, _ := args["name"].(string)
	nationality, _ := args["nationality"].(string)
	club, _ := args["club"].(string)

	type result struct {
		Name        string
		Nationality string
		Club        string
		Position    string
		Overall     int
		Age         int
	}
	var results []result

	if name != "" {
		for _, p := range h.store.FindPlayersByName(name) {
			results = append(results, result{p.Name, p.Nationality, p.Club, p.Position, p.Overall, p.Age})
		}
	} else if nationality != "" {
		for _, p := range h.store.FindPlayersByNationality(nationality) {
			results = append(results, result{p.Name, p.Nationality, p.Club, p.Position, p.Overall, p.Age})
		}
	} else if club != "" {
		for _, p := range h.store.FindPlayersByClub(club) {
			results = append(results, result{p.Name, p.Nationality, p.Club, p.Position, p.Overall, p.Age})
		}
	} else {
		return []TextContent{{Text: "Please provide 'name', 'nationality', or 'club'."}}, nil
	}

	if len(results) == 0 {
		return []TextContent{{Text: "No players found."}}, nil
	}

	// Sort by overall rating descending
	sort.Slice(results, func(i, j int) bool {
		return results[i].Overall > results[j].Overall
	})

	limit := 20
	if len(results) > limit {
		results = results[:limit]
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Found %d player(s) (showing up to %d):\n\n", len(results), limit))
	for i, p := range results {
		sb.WriteString(fmt.Sprintf("%d. %s (Age %d) | %s | Club: %s | Position: %s | Overall: %d\n",
			i+1, p.Name, p.Age, p.Nationality, p.Club, p.Position, p.Overall))
	}
	return []TextContent{{Text: sb.String()}}, nil
}

// LeagueStandings returns the Brasileirão standings for a season.
func (h *Handlers) LeagueStandings(ctx context.Context, args map[string]interface{}) ([]TextContent, error) {
	seasonFloat, _ := args["season"].(float64)
	season := int(seasonFloat)
	if season == 0 {
		return []TextContent{{Text: "Please provide 'season' (year)."}}, nil
	}

	standings := h.store.LeagueStandings(season)
	if len(standings) == 0 {
		return []TextContent{{Text: fmt.Sprintf("No standings data for season %d.", season)}}, nil
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Brasileirão Serie A - %d Standings\n\n", season))
	sb.WriteString(fmt.Sprintf("%-4s %-25s %4s %4s %4s %4s %4s %4s %4s %4s\n",
		"Pos", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"))
	sb.WriteString(strings.Repeat("-", 70) + "\n")
	for _, e := range standings {
		sb.WriteString(fmt.Sprintf("%-4d %-25s %4d %4d %4d %4d %4d %4d %4d %4d\n",
			e.Position, e.Team, e.Played, e.Wins, e.Draws, e.Losses, e.GF, e.GA, e.GD, e.Points))
	}
	return []TextContent{{Text: sb.String()}}, nil
}

// BiggestWins returns the biggest victories across all competitions.
func (h *Handlers) BiggestWins(ctx context.Context, args map[string]interface{}) ([]TextContent, error) {
	limitFloat, _ := args["limit"].(float64)
	limit := int(limitFloat)
	if limit <= 0 {
		limit = 10
	}

	wins := h.store.BiggestWins(limit)
	if len(wins) == 0 {
		return []TextContent{{Text: "No match data found."}}, nil
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Top %d Biggest Victories:\n\n", limit))
	for i, m := range wins {
		sb.WriteString(fmt.Sprintf("%d. %s: %s vs %s %d-%d (Goal diff: %d, %s Season %d)\n",
			i+1, m.Date, m.HomeTeam, m.AwayTeam, m.HomeGoal, m.AwayGoal, m.GoalDiff, m.Competition, m.Season))
	}
	return []TextContent{{Text: sb.String()}}, nil
}

// Statistics returns overall statistics about the dataset.
func (h *Handlers) Statistics(ctx context.Context, args map[string]interface{}) ([]TextContent, error) {
	avg := h.store.AverageGoalsPerMatch()
	text := fmt.Sprintf("Brazilian Soccer Dataset Statistics\n\nAverage goals per match: %.2f\n", avg)
	return []TextContent{{Text: text}}, nil
}
