// Package tools implements all MCP tool handlers for Brazilian soccer queries.
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

// RegisterMatchTools registers all match-related MCP tools on s.
func RegisterMatchTools(s *server.MCPServer, store *data.Store) {
	s.AddTool(mcp.NewTool("search_matches",
		mcp.WithDescription("Search for matches by team, season, competition, or date range. Returns match results with scores."),
		mcp.WithString("team", mcp.Description("Team name to search for (home or away). Leave empty to search all."), mcp.Required()),
		mcp.WithString("competition",
			mcp.Description("Filter by competition: 'brasileirao', 'cup', 'libertadores', 'all' (default 'all')"),
			mcp.DefaultString("all"),
		),
		mcp.WithNumber("season", mcp.Description("Filter by season year (e.g. 2023). 0 means all seasons.")),
		mcp.WithString("date_from", mcp.Description("Start date filter YYYY-MM-DD (optional)")),
		mcp.WithString("date_to", mcp.Description("End date filter YYYY-MM-DD (optional)")),
		mcp.WithNumber("limit", mcp.Description("Maximum results to return (default 20)")),
	), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return searchMatches(store, req)
	})

	s.AddTool(mcp.NewTool("head_to_head",
		mcp.WithDescription("Get head-to-head record between two teams across all competitions."),
		mcp.WithString("team1", mcp.Description("First team name"), mcp.Required()),
		mcp.WithString("team2", mcp.Description("Second team name"), mcp.Required()),
		mcp.WithString("competition",
			mcp.Description("Filter competition: 'brasileirao', 'cup', 'libertadores', 'all' (default 'all')"),
			mcp.DefaultString("all"),
		),
	), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return headToHead(store, req)
	})

	s.AddTool(mcp.NewTool("biggest_wins",
		mcp.WithDescription("Find the biggest victories (largest goal difference) across all competitions."),
		mcp.WithString("competition",
			mcp.Description("Filter competition: 'brasileirao', 'cup', 'libertadores', 'historical', 'all' (default 'all')"),
			mcp.DefaultString("all"),
		),
		mcp.WithNumber("limit", mcp.Description("Maximum results to return (default 10)")),
	), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return biggestWins(store, req)
	})
}

func searchMatches(store *data.Store, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	args := req.GetArguments()
	team, _ := args["team"].(string)
	competition, _ := args["competition"].(string)
	if competition == "" {
		competition = "all"
	}
	seasonF, _ := args["season"].(float64)
	season := int(seasonF)
	dateFrom, _ := args["date_from"].(string)
	dateTo, _ := args["date_to"].(string)
	limitF, _ := args["limit"].(float64)
	limit := int(limitF)
	if limit <= 0 {
		limit = 20
	}

	type result struct {
		date, comp, home, away string
		hg, ag                 int
		season                 int
		extra                  string
	}

	var results []result

	addMatch := func(m data.Match) {
		if team != "" && !data.TeamMatches(m.HomeTeam, team) && !data.TeamMatches(m.AwayTeam, team) {
			return
		}
		if season != 0 && m.Season != season {
			return
		}
		if dateFrom != "" || dateTo != "" {
			t, err := data.ParseDate(m.Datetime)
			if err == nil {
				if dateFrom != "" {
					tf, _ := data.ParseDate(dateFrom)
					if t.Before(tf) {
						return
					}
				}
				if dateTo != "" {
					tt, _ := data.ParseDate(dateTo)
					if t.After(tt) {
						return
					}
				}
			}
		}
		extra := ""
		if m.Round != "" {
			extra = "Round " + m.Round
		}
		if m.Stage != "" {
			extra = m.Stage
		}
		results = append(results, result{
			date:   m.Datetime,
			comp:   m.Source,
			home:   data.NormalizeTeam(m.HomeTeam),
			away:   data.NormalizeTeam(m.AwayTeam),
			hg:     m.HomeGoal,
			ag:     m.AwayGoal,
			season: m.Season,
			extra:  extra,
		})
	}

	if competition == "all" || competition == "brasileirao" {
		for _, m := range store.BrasileiraoMatches {
			addMatch(m)
		}
		for _, m := range store.HistoricalMatches {
			hm := data.Match{
				Datetime: m.Date,
				HomeTeam: m.HomeTeam,
				AwayTeam: m.AwayTeam,
				HomeGoal: m.HomeGoals,
				AwayGoal: m.AwayGoals,
				Season:   m.Year,
				Round:    fmt.Sprintf("%d", m.Round),
				Source:   "brasileirao",
			}
			addMatch(hm)
		}
	}
	if competition == "all" || competition == "cup" {
		for _, m := range store.CupMatches {
			addMatch(m)
		}
	}
	if competition == "all" || competition == "libertadores" {
		for _, m := range store.LibertadoresMatches {
			addMatch(m)
		}
	}

	// Sort by date descending
	sort.Slice(results, func(i, j int) bool {
		ti, _ := data.ParseDate(results[i].date)
		tj, _ := data.ParseDate(results[j].date)
		return ti.After(tj)
	})

	total := len(results)
	if len(results) > limit {
		results = results[:limit]
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Found %d match(es)", total))
	if total > limit {
		sb.WriteString(fmt.Sprintf(" (showing %d most recent)", limit))
	}
	sb.WriteString(":\n\n")

	for _, r := range results {
		comp := compLabel(r.comp)
		sb.WriteString(fmt.Sprintf("%-12s  %s %d-%d %s  [%s %d]",
			r.date[:10],
			r.home, r.hg, r.ag, r.away,
			comp, r.season,
		))
		if r.extra != "" {
			sb.WriteString("  " + r.extra)
		}
		sb.WriteString("\n")
	}

	return mcp.NewToolResultText(sb.String()), nil
}

func headToHead(store *data.Store, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	args := req.GetArguments()
	team1, _ := args["team1"].(string)
	team2, _ := args["team2"].(string)
	competition, _ := args["competition"].(string)
	if competition == "" {
		competition = "all"
	}

	if team1 == "" || team2 == "" {
		return mcp.NewToolResultText("Both team1 and team2 are required."), nil
	}

	type matchResult struct {
		date, home, away, comp string
		hg, ag, season         int
	}

	var matches []matchResult
	t1wins, t2wins, draws := 0, 0, 0

	check := func(m data.Match) {
		t1Home := data.TeamMatches(m.HomeTeam, team1) && data.TeamMatches(m.AwayTeam, team2)
		t2Home := data.TeamMatches(m.HomeTeam, team2) && data.TeamMatches(m.AwayTeam, team1)
		if !t1Home && !t2Home {
			return
		}

		var t1g, t2g int
		var home, away string
		if t1Home {
			t1g, t2g = m.HomeGoal, m.AwayGoal
			home = data.NormalizeTeam(m.HomeTeam)
			away = data.NormalizeTeam(m.AwayTeam)
		} else {
			t1g, t2g = m.AwayGoal, m.HomeGoal
			home = data.NormalizeTeam(m.HomeTeam)
			away = data.NormalizeTeam(m.AwayTeam)
		}

		switch {
		case t1g > t2g:
			t1wins++
		case t2g > t1g:
			t2wins++
		default:
			draws++
		}

		matches = append(matches, matchResult{
			date:   m.Datetime,
			home:   home,
			away:   away,
			comp:   m.Source,
			hg:     m.HomeGoal,
			ag:     m.AwayGoal,
			season: m.Season,
		})
	}

	if competition == "all" || competition == "brasileirao" {
		for _, m := range store.BrasileiraoMatches {
			check(m)
		}
		for _, m := range store.HistoricalMatches {
			check(data.Match{
				Datetime: m.Date, HomeTeam: m.HomeTeam, AwayTeam: m.AwayTeam,
				HomeGoal: m.HomeGoals, AwayGoal: m.AwayGoals, Season: m.Year, Source: "brasileirao",
			})
		}
	}
	if competition == "all" || competition == "cup" {
		for _, m := range store.CupMatches {
			check(m)
		}
	}
	if competition == "all" || competition == "libertadores" {
		for _, m := range store.LibertadoresMatches {
			check(m)
		}
	}

	sort.Slice(matches, func(i, j int) bool {
		ti, _ := data.ParseDate(matches[i].date)
		tj, _ := data.ParseDate(matches[j].date)
		return ti.After(tj)
	})

	total := len(matches)
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Head-to-head: %s vs %s\n", team1, team2))
	sb.WriteString(fmt.Sprintf("Total matches: %d\n", total))
	sb.WriteString(fmt.Sprintf("%s wins: %d  |  %s wins: %d  |  Draws: %d\n\n", team1, t1wins, team2, t2wins, draws))

	show := matches
	if len(show) > 20 {
		show = show[:20]
		sb.WriteString(fmt.Sprintf("Most recent 20 of %d matches:\n", total))
	} else {
		sb.WriteString("All matches:\n")
	}

	for _, r := range show {
		sb.WriteString(fmt.Sprintf("  %-12s  %s %d-%d %s  [%s %d]\n",
			r.date[:min(10, len(r.date))],
			r.home, r.hg, r.ag, r.away,
			compLabel(r.comp), r.season,
		))
	}

	return mcp.NewToolResultText(sb.String()), nil
}

func biggestWins(store *data.Store, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	args := req.GetArguments()
	competition, _ := args["competition"].(string)
	if competition == "" {
		competition = "all"
	}
	limitF, _ := args["limit"].(float64)
	limit := int(limitF)
	if limit <= 0 {
		limit = 10
	}

	type entry struct {
		date, home, away, comp string
		hg, ag, diff, season   int
	}
	var entries []entry

	add := func(date, home, away, comp string, hg, ag, season int) {
		diff := hg - ag
		if diff < 0 {
			diff = -diff
		}
		entries = append(entries, entry{date, home, away, comp, hg, ag, diff, season})
	}

	if competition == "all" || competition == "brasileirao" {
		for _, m := range store.BrasileiraoMatches {
			add(m.Datetime, data.NormalizeTeam(m.HomeTeam), data.NormalizeTeam(m.AwayTeam), "brasileirao", m.HomeGoal, m.AwayGoal, m.Season)
		}
		for _, m := range store.HistoricalMatches {
			add(m.Date, m.HomeTeam, m.AwayTeam, "brasileirao", m.HomeGoals, m.AwayGoals, m.Year)
		}
	}
	if competition == "all" || competition == "cup" {
		for _, m := range store.CupMatches {
			add(m.Datetime, data.NormalizeTeam(m.HomeTeam), data.NormalizeTeam(m.AwayTeam), "cup", m.HomeGoal, m.AwayGoal, m.Season)
		}
	}
	if competition == "all" || competition == "libertadores" {
		for _, m := range store.LibertadoresMatches {
			add(m.Datetime, data.NormalizeTeam(m.HomeTeam), data.NormalizeTeam(m.AwayTeam), "libertadores", m.HomeGoal, m.AwayGoal, m.Season)
		}
	}

	sort.Slice(entries, func(i, j int) bool {
		return entries[i].diff > entries[j].diff
	})

	if len(entries) > limit {
		entries = entries[:limit]
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Biggest victories (top %d):\n\n", limit))
	for i, e := range entries {
		d := e.date
		if len(d) > 10 {
			d = d[:10]
		}
		sb.WriteString(fmt.Sprintf("%2d. %s  %s %d-%d %s  (diff=%d) [%s %d]\n",
			i+1, d, e.home, e.hg, e.ag, e.away, e.diff, compLabel(e.comp), e.season))
	}
	return mcp.NewToolResultText(sb.String()), nil
}

func compLabel(source string) string {
	switch source {
	case "brasileirao":
		return "Brasileirão"
	case "cup":
		return "Copa do Brasil"
	case "libertadores":
		return "Libertadores"
	}
	return source
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
