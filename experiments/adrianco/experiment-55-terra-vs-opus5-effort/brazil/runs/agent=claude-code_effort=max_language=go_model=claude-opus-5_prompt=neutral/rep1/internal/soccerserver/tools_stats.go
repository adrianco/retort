// tools_stats.go: aggregate statistics over any slice of matches, plus the
// "biggest wins" and "highest scoring" lists.
package soccerserver

import (
	"fmt"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

func (a *api) leagueStatisticsTool() *mcp.Tool {
	props := commonFilterProps()
	props["team"] = mcp.Str("Restrict the statistics to matches involving this club.")
	return &mcp.Tool{
		Name:        "league_statistics",
		Title:       "Aggregate statistics",
		Description: "Aggregate statistics for any slice of the data: average goals per match, home/draw/away split, both-teams-scored and over-2.5 rates, biggest margin and highest scoring match. Answers \"What's the average goals per match in the Brasileirão?\".",
		InputSchema: mcp.Object(props),
		Handler:     a.leagueStatistics,
	}
}

func (a *api) leagueStatistics(args mcp.Args) (*mcp.ToolResult, error) {
	var f soccer.MatchFilter
	if res := a.applyCommonFilters(args, &f); res != nil {
		return res, nil
	}
	if args.Has("team") {
		t, res := a.resolveTeam(args.String("team"), "team")
		if res != nil {
			return res, nil
		}
		f.TeamID = t.ID
	}
	agg := a.store.Aggregate(f)
	title := fmt.Sprintf("Statistics for %s:", scopeLabel(f))
	if f.TeamID != "" {
		title = fmt.Sprintf("Statistics for %s matches (%s):", a.store.Teams.Team(f.TeamID).Name, scopeLabel(f))
	}
	text := soccer.FormatAggregate(title, agg)

	if agg.Matches > 0 {
		if big := a.store.BiggestWins(f, 3); len(big) > 0 {
			text += "\nBiggest victories:\n"
			for _, m := range big {
				text += soccer.MatchLine(m) + "\n"
			}
		}
		if high := a.store.HighestScoring(f, 3); len(high) > 0 {
			text += "\nHighest scoring matches:\n"
			for _, m := range high {
				text += soccer.MatchLine(m) + "\n"
			}
		}
	}
	return mcp.TextWithData(text, map[string]any{"scope": scopeLabel(f), "statistics": agg}), nil
}

func (a *api) biggestWinsTool() *mcp.Tool {
	props := commonFilterProps()
	props["team"] = mcp.Str("Restrict to matches involving this club.")
	props["order_by"] = mcp.Enum("Rank by winning margin (default) or by total goals.", "margin", "total_goals")
	props["limit"] = mcp.IntRange("How many matches to list (default 10, max 200).", 1, maxLimit)
	return &mcp.Tool{
		Name:        "biggest_wins",
		Title:       "Biggest wins",
		Description: "List the heaviest victories, or the highest scoring matches, in any slice of the data. Answers \"Show me the biggest wins in the dataset\".",
		InputSchema: mcp.Object(props),
		Handler:     a.biggestWins,
	}
}

func (a *api) biggestWins(args mcp.Args) (*mcp.ToolResult, error) {
	var f soccer.MatchFilter
	if res := a.applyCommonFilters(args, &f); res != nil {
		return res, nil
	}
	if args.Has("team") {
		t, res := a.resolveTeam(args.String("team"), "team")
		if res != nil {
			return res, nil
		}
		f.TeamID = t.ID
	}
	limit, res := limitArg(args, 10)
	if res != nil {
		return res, nil
	}
	var ms []*soccer.Match
	title := "Biggest victories"
	if strings.EqualFold(args.String("order_by"), "total_goals") {
		ms = a.store.HighestScoring(f, limit)
		title = "Highest scoring matches"
	} else {
		ms = a.store.BiggestWins(f, limit)
	}
	text := soccer.FormatMatches(fmt.Sprintf("%s (%s):", title, scopeLabel(f)), ms, len(ms), 0)
	return mcp.TextWithData(text, map[string]any{"matches": matchesJSON(ms)}), nil
}

func (a *api) listDatasetsTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "list_datasets",
		Title:       "Dataset coverage",
		Description: "Describe the loaded CSVs: rows, licences, competitions, season coverage, how many fixtures were merged across sources, and the size of the knowledge graph. Call this to check what can and cannot be answered.",
		InputSchema: mcp.Object(map[string]*mcp.Prop{}),
		Handler:     a.listDatasets,
	}
}

func (a *api) listDatasets(args mcp.Args) (*mcp.ToolResult, error) {
	s := a.store
	sum := s.Summary()
	first, last := s.DateRange()

	var b strings.Builder
	b.WriteString("Brazilian soccer knowledge graph\n")
	fmt.Fprintf(&b, "- %d matches (%s to %s), %d clubs, %d players\n",
		sum.Matches, first.Format("2006-01-02"), last.Format("2006-01-02"), sum.Teams, sum.Players)
	fmt.Fprintf(&b, "- Graph: %d nodes, %d edges, loaded in %d ms from %s\n\n", sum.GraphNodes, sum.GraphEdges, sum.LoadMillis, s.DataDir)
	b.WriteString("Source files:\n")
	for _, d := range s.Datasets {
		fmt.Fprintf(&b, "- %s (%s): %d rows, %d used", d.File, d.License, d.Rows, d.Used)
		if len(d.Competitions) > 0 {
			fmt.Fprintf(&b, ", %s %d-%d", strings.Join(compLabels(d.Competitions), "/"), d.SeasonMin, d.SeasonMax)
		}
		fmt.Fprintf(&b, "\n  %s\n", d.Description)
	}
	matchRows := 0
	for _, d := range s.Datasets {
		if len(d.Competitions) > 0 {
			matchRows += d.Used
		}
	}
	fmt.Fprintf(&b, "\nThe five match files overlap; %d source rows describe %d distinct fixtures once merged.\n",
		matchRows, sum.Matches)
	b.WriteString("\nMatches per competition:\n")
	for _, c := range s.CompetitionsWithData() {
		seasons := s.Seasons(c.ID)
		fmt.Fprintf(&b, "- %-28s %5d matches, seasons %d-%d\n", c.Name, sum.PerComp[c.ID], seasons[0], seasons[len(seasons)-1])
	}
	if len(s.Anomalies) > 0 {
		fmt.Fprintf(&b, "\nRows rejected as inconsistent (%d):\n", len(s.Anomalies))
		for i, note := range s.Anomalies {
			if i == 5 {
				fmt.Fprintf(&b, "- ... and %d more\n", len(s.Anomalies)-5)
				break
			}
			fmt.Fprintf(&b, "- %s\n", note)
		}
	}
	b.WriteString("\nKnown gaps: the FIFA player file is a single 2019 snapshot, and its unlicensed\n" +
		"Brazilian clubs carry placeholder player names. There are no goalscorer, lineup or\n" +
		"attendance columns anywhere in the data, so those questions cannot be answered.\n")

	return mcp.TextWithData(b.String(), map[string]any{
		"summary":   sum,
		"datasets":  s.Datasets,
		"data_dir":  s.DataDir,
		"anomalies": s.Anomalies,
		"graph":     map[string]any{"nodes_by_type": s.Graph.CountsByType(), "edges_by_type": s.Graph.EdgeCountsByType()},
	}), nil
}
