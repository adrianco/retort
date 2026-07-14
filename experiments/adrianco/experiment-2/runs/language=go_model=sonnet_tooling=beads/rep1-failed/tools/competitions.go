package tools

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"brazilian-soccer-mcp/data"
)

// RegisterCompetitionTools registers competition/standings MCP tools.
func RegisterCompetitionTools(s *server.MCPServer, store *data.Store) {
	s.AddTool(mcp.NewTool("standings",
		mcp.WithDescription("Calculate league standings for a season from match results."),
		mcp.WithNumber("season", mcp.Description("Season year (required)"), mcp.Required()),
		mcp.WithString("competition",
			mcp.Description("Competition: 'brasileirao' (default), 'cup', 'libertadores'"),
			mcp.DefaultString("brasileirao"),
		),
	), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return standings(store, req)
	})

	s.AddTool(mcp.NewTool("list_seasons",
		mcp.WithDescription("List available seasons for a competition in the dataset."),
		mcp.WithString("competition",
			mcp.Description("Competition: 'brasileirao', 'cup', 'libertadores', 'all'"),
			mcp.DefaultString("all"),
		),
	), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return listSeasons(store, req)
	})

	s.AddTool(mcp.NewTool("match_stats_summary",
		mcp.WithDescription("Summary statistics for a competition and season: avg goals, home win rate, etc."),
		mcp.WithString("competition",
			mcp.Description("Competition: 'brasileirao', 'cup', 'libertadores', 'all'"),
			mcp.DefaultString("brasileirao"),
		),
		mcp.WithNumber("season", mcp.Description("Season year (0 = all seasons)")),
	), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return matchStatsSummary(store, req)
	})
}

func standings(store *data.Store, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	args := req.GetArguments()
	seasonF, _ := args["season"].(float64)
	season := int(seasonF)
	competition, _ := args["competition"].(string)
	if competition == "" {
		competition = "brasileirao"
	}

	if season == 0 {
		return mcp.NewToolResultText("season parameter is required for standings."), nil
	}

	records := buildRecord(store, "", competition, season)

	type entry struct {
		r *teamRecord
	}
	var list []entry
	for _, r := range records {
		list = append(list, entry{r})
	}

	sort.Slice(list, func(i, j int) bool {
		pi, pj := list[i].r.points(), list[j].r.points()
		if pi != pj {
			return pi > pj
		}
		if list[i].r.wins != list[j].r.wins {
			return list[i].r.wins > list[j].r.wins
		}
		return list[i].r.goalsDiff > list[j].r.goalsDiff
	})

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("%s %d Standings (calculated from match results):\n\n", compLabel(competition), season))
	sb.WriteString(fmt.Sprintf("%-3s  %-28s  %4s  %4s  %4s  %4s  %4s  %4s  %4s  %4s\n",
		"#", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"))
	sb.WriteString(strings.Repeat("-", 82) + "\n")

	for i, e := range list {
		r := e.r
		if r.played == 0 {
			continue
		}
		marker := ""
		if i == 0 {
			marker = " ★ Champion"
		}
		sb.WriteString(fmt.Sprintf("%-3d  %-28s  %4d  %4d  %4d  %4d  %4d  %4d  %+4d  %4d%s\n",
			i+1, truncate(r.team, 28),
			r.played, r.wins, r.draws, r.losses,
			r.goalsFor, r.goalsAgainst, r.goalsDiff, r.points(), marker))
	}

	return mcp.NewToolResultText(sb.String()), nil
}

func listSeasons(store *data.Store, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	args := req.GetArguments()
	competition, _ := args["competition"].(string)
	if competition == "" {
		competition = "all"
	}

	seasonSet := make(map[string]map[int]bool)

	if competition == "all" || competition == "brasileirao" {
		if seasonSet["brasileirao"] == nil {
			seasonSet["brasileirao"] = make(map[int]bool)
		}
		for _, m := range store.BrasileiraoMatches {
			seasonSet["brasileirao"][m.Season] = true
		}
		for _, m := range store.HistoricalMatches {
			seasonSet["brasileirao"][m.Year] = true
		}
	}
	if competition == "all" || competition == "cup" {
		if seasonSet["cup"] == nil {
			seasonSet["cup"] = make(map[int]bool)
		}
		for _, m := range store.CupMatches {
			seasonSet["cup"][m.Season] = true
		}
	}
	if competition == "all" || competition == "libertadores" {
		if seasonSet["libertadores"] == nil {
			seasonSet["libertadores"] = make(map[int]bool)
		}
		for _, m := range store.LibertadoresMatches {
			seasonSet["libertadores"][m.Season] = true
		}
	}

	var sb strings.Builder
	for _, comp := range []string{"brasileirao", "cup", "libertadores"} {
		ss := seasonSet[comp]
		if len(ss) == 0 {
			continue
		}
		var seasons []int
		for s := range ss {
			seasons = append(seasons, s)
		}
		sort.Ints(seasons)
		sb.WriteString(fmt.Sprintf("%s: %v\n", compLabel(comp), seasons))
	}
	return mcp.NewToolResultText(sb.String()), nil
}

func matchStatsSummary(store *data.Store, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	args := req.GetArguments()
	competition, _ := args["competition"].(string)
	if competition == "" {
		competition = "brasileirao"
	}
	seasonF, _ := args["season"].(float64)
	season := int(seasonF)

	type stats struct {
		total, homeWins, awayWins, draws int
		totalGoals                        int
	}
	s := stats{}

	process := func(hg, ag, seas int, comp string) {
		if competition != "all" && comp != competition {
			return
		}
		if season != 0 && seas != season {
			return
		}
		s.total++
		s.totalGoals += hg + ag
		switch {
		case hg > ag:
			s.homeWins++
		case ag > hg:
			s.awayWins++
		default:
			s.draws++
		}
	}

	if competition == "all" || competition == "brasileirao" {
		for _, m := range store.BrasileiraoMatches {
			process(m.HomeGoal, m.AwayGoal, m.Season, "brasileirao")
		}
		for _, m := range store.HistoricalMatches {
			process(m.HomeGoals, m.AwayGoals, m.Year, "brasileirao")
		}
	}
	if competition == "all" || competition == "cup" {
		for _, m := range store.CupMatches {
			process(m.HomeGoal, m.AwayGoal, m.Season, "cup")
		}
	}
	if competition == "all" || competition == "libertadores" {
		for _, m := range store.LibertadoresMatches {
			process(m.HomeGoal, m.AwayGoal, m.Season, "libertadores")
		}
	}

	if s.total == 0 {
		return mcp.NewToolResultText("No matches found with given filters."), nil
	}

	var sb strings.Builder
	compDesc := competition
	if competition != "all" {
		compDesc = compLabel(competition)
	}
	seasonDesc := "all seasons"
	if season != 0 {
		seasonDesc = fmt.Sprintf("%d", season)
	}
	sb.WriteString(fmt.Sprintf("Match statistics — %s, %s:\n\n", compDesc, seasonDesc))
	sb.WriteString(fmt.Sprintf("Total matches:         %d\n", s.total))
	sb.WriteString(fmt.Sprintf("Total goals:           %d\n", s.totalGoals))
	sb.WriteString(fmt.Sprintf("Avg goals per match:   %.2f\n", float64(s.totalGoals)/float64(s.total)))
	sb.WriteString(fmt.Sprintf("Home wins:             %d (%.1f%%)\n", s.homeWins, pct(s.homeWins, s.total)))
	sb.WriteString(fmt.Sprintf("Away wins:             %d (%.1f%%)\n", s.awayWins, pct(s.awayWins, s.total)))
	sb.WriteString(fmt.Sprintf("Draws:                 %d (%.1f%%)\n", s.draws, pct(s.draws, s.total)))

	return mcp.NewToolResultText(sb.String()), nil
}

func pct(n, total int) float64 {
	if total == 0 {
		return 0
	}
	return float64(n) / float64(total) * 100
}
