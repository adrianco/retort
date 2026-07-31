// tools_competition.go: competition centred tools - the catalogue, computed
// league tables, season summaries (including cup brackets) and season
// comparisons.
package soccerserver

import (
	"fmt"
	"sort"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

func (a *api) listCompetitionsTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "list_competitions",
		Title:       "List competitions",
		Description: "List the competitions in the data with their seasons, match counts and coverage. Call this first when you are unsure which seasons can be answered.",
		InputSchema: mcp.Object(map[string]*mcp.Prop{}),
		Handler:     a.listCompetitions,
	}
}

func (a *api) listCompetitions(args mcp.Args) (*mcp.ToolResult, error) {
	var b strings.Builder
	b.WriteString("Competitions in the knowledge graph:\n")
	items := make([]map[string]any, 0, 5)
	for _, c := range a.store.CompetitionsWithData() {
		seasons := a.store.Seasons(c.ID)
		matches := len(a.store.CompetitionMatches(c.ID))
		fmt.Fprintf(&b, "- %s (%s) [%s]: %d matches, %d seasons (%d-%d), %s played as a %s\n",
			c.Name, c.Short, c.ID, matches, len(seasons), seasons[0], seasons[len(seasons)-1], c.Kind,
			strings.ReplaceAll(c.Format, "_", " "))
		items = append(items, map[string]any{
			"id": c.ID, "name": c.Name, "short_name": c.Short, "kind": c.Kind, "format": c.Format,
			"matches": matches, "seasons": seasons,
		})
	}
	return mcp.TextWithData(b.String(), map[string]any{"competitions": items}), nil
}

func (a *api) standingsTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "standings",
		Title:       "League table",
		Description: "Compute a league table from match results: points, wins, draws, losses, goals, goal difference, champion and relegation zone. Answers \"Who won the 2019 Brasileirão?\" and \"Which teams were relegated in 2020?\".",
		InputSchema: mcp.Object(map[string]*mcp.Prop{
			"competition":   mcp.Str("League competition: brasileirao, serie-b or serie-c (default brasileirao)."),
			"season":        mcp.Int("Season year."),
			"through_round": mcp.Int("Only count matches up to this round, for a mid-season table."),
			"venue":         mcp.Enum("Build a home-only or away-only table (default any).", "home", "away", "any"),
			"limit":         mcp.IntRange("How many rows to show (default all).", 1, maxLimit),
		}, "season"),
		Handler: a.standings,
	}
}

func (a *api) standings(args mcp.Args) (*mcp.ToolResult, error) {
	compArg := args.String("competition")
	if compArg == "" {
		compArg = soccer.CompBrasileirao
	}
	comp, res := a.resolveCompetition(compArg)
	if res != nil {
		return res, nil
	}
	season, err := args.Int("season", 0)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	if len(a.store.SeasonMatches(comp, season)) == 0 {
		return mcp.ErrorResult("no %s matches for season %d; available seasons: %s",
			soccer.CompetitionLabel(comp), season, seasonList(a.store.Seasons(comp))), nil
	}
	var opts soccer.StandingsOptions
	if opts.ThroughRound, err = args.Int("through_round", 0); err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	venue, err := soccer.ParseVenue(args.String("venue"))
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	opts.Venue = venue
	limit, err := args.Int("limit", 0)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}

	table := a.store.Standings(comp, season, opts)
	text := soccer.FormatStandings(table, limit) + verdict(table)
	return mcp.TextWithData(text, table), nil
}

func seasonList(seasons []int) string {
	parts := make([]string, 0, len(seasons))
	for _, s := range seasons {
		parts = append(parts, fmt.Sprint(s))
	}
	return strings.Join(parts, ", ")
}

func (a *api) seasonSummaryTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "season_summary",
		Title:       "Season summary",
		Description: "Summarise one competition season: champion, relegation, top scoring clubs and headline statistics for leagues; the stage-by-stage bracket and the winner for cups and the Libertadores. Answers \"Show the 2018 Copa Libertadores bracket\".",
		InputSchema: mcp.Object(map[string]*mcp.Prop{
			"competition": mcp.Str("Competition id or name (default brasileirao)."),
			"season":      mcp.Int("Season year."),
		}, "season"),
		Handler: a.seasonSummary,
	}
}

func (a *api) seasonSummary(args mcp.Args) (*mcp.ToolResult, error) {
	compArg := args.String("competition")
	if compArg == "" {
		compArg = soccer.CompBrasileirao
	}
	comp, res := a.resolveCompetition(compArg)
	if res != nil {
		return res, nil
	}
	season, err := args.Int("season", 0)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	matches := a.store.SeasonMatches(comp, season)
	if len(matches) == 0 {
		return mcp.ErrorResult("no %s matches for season %d; available seasons: %s",
			soccer.CompetitionLabel(comp), season, seasonList(a.store.Seasons(comp))), nil
	}
	c, _ := soccer.CompetitionByID(comp)
	agg := a.store.Aggregate(soccer.MatchFilter{CompetitionID: comp, Season: season})

	var b strings.Builder
	fmt.Fprintf(&b, "%s %d\n\n", c.Name, season)
	data := map[string]any{"competition": comp, "season": season, "statistics": agg}

	if c.Kind == "league" {
		table := a.store.Standings(comp, season, soccer.StandingsOptions{})
		b.WriteString(soccer.FormatStandings(table, 0))
		b.WriteString(verdict(table))
		data["standings"] = table
	} else {
		bracket, order := bracketOf(matches)
		b.WriteString("Bracket:\n")
		stages := make([]map[string]any, 0, len(order))
		for _, stage := range order {
			ties := bracket[stage]
			fmt.Fprintf(&b, "\n%s (%d matches):\n", strings.ToUpper(stage[:1])+stage[1:], len(ties))
			// Knockout rounds are small enough to print in full; a group stage
			// is not, and the full list is in the structured payload anyway.
			shown := ties
			if len(shown) > maxBracketMatches {
				shown = shown[:maxBracketMatches]
			}
			for _, m := range shown {
				b.WriteString(soccer.MatchLine(m) + "\n")
			}
			if len(ties) > len(shown) {
				fmt.Fprintf(&b, "... (%d more %s fixtures; use search_matches with stage=%q for the rest)\n",
					len(ties)-len(shown), stage, stage)
			}
			stages = append(stages, map[string]any{"stage": stage, "matches": matchesJSON(ties)})
		}
		data["bracket"] = stages
		if winner, note, final := cupWinner(bracket); len(final) > 0 {
			switch {
			case winner != "":
				fmt.Fprintf(&b, "\nWinner (from the final in the data): %s\n", winner)
				data["winner"] = winner
			case note != "":
				fmt.Fprintf(&b, "\nNo winner can be read from the data: %s.\n", note)
			}
			data["final"] = matchesJSON(final)
		}
	}
	b.WriteString("\n" + soccer.FormatAggregate("Season statistics:", agg))
	if best := a.store.TeamRecords(soccer.MatchFilter{CompetitionID: comp, Season: season}, "goals_for", 0, 3); len(best) > 0 {
		b.WriteString("\nMost goals scored:\n")
		for i, r := range best {
			fmt.Fprintf(&b, "%d. %s - %d goals in %d matches\n", i+1, r.TeamName, r.GoalsFor, r.Matches)
		}
		data["top_scoring_teams"] = best
	}
	if big := a.store.BiggestWins(soccer.MatchFilter{CompetitionID: comp, Season: season}, 3); len(big) > 0 {
		b.WriteString("\nBiggest wins:\n")
		for _, m := range big {
			b.WriteString(soccer.MatchLine(m) + "\n")
		}
		data["biggest_wins"] = matchesJSON(big)
	}
	return mcp.TextWithData(b.String(), data), nil
}

// maxBracketMatches caps how many fixtures of one stage the bracket prints.
const maxBracketMatches = 16

// verdict renders what the table can and cannot decide about the title.
func verdict(t *soccer.Standings) string {
	switch {
	case t.Champion != "":
		out := fmt.Sprintf("\nChampion: %s.", t.Champion)
		if len(t.Relegated) > 0 {
			out += fmt.Sprintf(" Relegated: %s.", strings.Join(t.Relegated, ", "))
		}
		return out + "\n"
	case t.Leader != "":
		return fmt.Sprintf("\n%s leads the table, but fixtures are missing from the data, so the champion cannot be decided from it.\n", t.Leader)
	}
	return ""
}

// stageOrder ranks knockout stages from earliest to latest.
var stageOrder = map[string]int{
	"group stage": 0, "round of 16": 1, "quarterfinals": 2, "semifinals": 3,
	"final": 4, "final (inferred)": 4,
}

func bracketOf(matches []*soccer.Match) (map[string][]*soccer.Match, []string) {
	bracket := map[string][]*soccer.Match{}
	for _, m := range matches {
		stage := m.Stage
		if stage == "" {
			if m.Round > 0 {
				stage = fmt.Sprintf("round %d", m.Round)
			} else {
				stage = "unclassified fixtures"
			}
		}
		bracket[stage] = append(bracket[stage], m)
	}
	order := make([]string, 0, len(bracket))
	for stage := range bracket {
		order = append(order, stage)
		sort.SliceStable(bracket[stage], func(i, j int) bool { return bracket[stage][i].Date.Before(bracket[stage][j].Date) })
	}
	sort.Slice(order, func(i, j int) bool {
		oi, iok := stageOrder[order[i]]
		oj, jok := stageOrder[order[j]]
		if iok != jok {
			return jok // known stages first
		}
		if iok && jok && oi != oj {
			return oi < oj
		}
		return order[i] < order[j]
	})
	return bracket, order
}

// cupWinner reads the winner off the final by aggregate score over both legs.
// A tie was settled by a penalty shoot-out, which the data does not record, so
// it is reported as undecided rather than guessed.
func cupWinner(bracket map[string][]*soccer.Match) (winner, note string, final []*soccer.Match) {
	for _, key := range []string{"final", "final (inferred)"} {
		if ms, ok := bracket[key]; ok {
			final = ms
			break
		}
	}
	if len(final) == 0 {
		return "", "", nil
	}
	agg := map[string]int{}
	names := map[string]string{}
	var ids []string
	for _, m := range final {
		for id, goals := range map[string]int{m.HomeTeamID: m.HomeGoals, m.AwayTeamID: m.AwayGoals} {
			if _, seen := agg[id]; !seen {
				ids = append(ids, id)
			}
			agg[id] += goals
		}
		names[m.HomeTeamID], names[m.AwayTeamID] = m.HomeName, m.AwayName
	}
	sort.Strings(ids) // deterministic when the aggregate is level
	best, bestScore, tied := "", -1, false
	for _, id := range ids {
		switch score := agg[id]; {
		case score > bestScore:
			best, bestScore, tied = id, score, false
		case score == bestScore:
			tied = true
		}
	}
	if best == "" {
		return "", "", final
	}
	if tied {
		return "", "the final finished level on aggregate and the shoot-out is not in the data", final
	}
	return names[best], "", final
}

func (a *api) compareSeasonsTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "compare_seasons",
		Title:       "Compare seasons",
		Description: "Put several seasons of one competition side by side: matches, goals per match, home advantage, champion and top scoring club. Answers \"Compare the 2018 and 2019 seasons\".",
		InputSchema: mcp.Object(map[string]*mcp.Prop{
			"competition": mcp.Str("Competition id or name (default brasileirao)."),
			"seasons":     mcp.IntArray("Seasons to compare, e.g. [2018, 2019]."),
			"season_from": mcp.Int("Alternative to seasons: first season of a range."),
			"season_to":   mcp.Int("Alternative to seasons: last season of a range."),
		}),
		Handler: a.compareSeasons,
	}
}

func (a *api) compareSeasons(args mcp.Args) (*mcp.ToolResult, error) {
	compArg := args.String("competition")
	if compArg == "" {
		compArg = soccer.CompBrasileirao
	}
	comp, res := a.resolveCompetition(compArg)
	if res != nil {
		return res, nil
	}
	seasons, err := args.Ints("seasons")
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	from, err := args.Int("season_from", 0)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	to, err := args.Int("season_to", 0)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	if from != 0 || to != 0 {
		for _, s := range a.store.Seasons(comp) {
			if (from == 0 || s >= from) && (to == 0 || s <= to) {
				seasons = append(seasons, s)
			}
		}
	}
	if len(seasons) == 0 {
		seasons = a.store.Seasons(comp)
	}
	if len(seasons) < 2 {
		return mcp.ErrorResult("give at least two seasons to compare (available: %s)", seasonList(a.store.Seasons(comp))), nil
	}
	cmp := a.store.CompareSeasons(comp, seasons)
	if len(cmp.Seasons) == 0 {
		return mcp.ErrorResult("none of those seasons exist for %s; available: %s",
			soccer.CompetitionLabel(comp), seasonList(a.store.Seasons(comp))), nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s season comparison:\n\n", soccer.CompetitionLabel(comp))
	fmt.Fprintf(&b, "%-8s %-8s %-7s %-9s %-9s %-9s %-22s %s\n", "season", "matches", "goals", "goals/match", "home win%", "draw%", "champion", "top scorers")
	rows := make([]map[string]any, 0, len(cmp.Seasons))
	for _, season := range cmp.Seasons {
		agg := cmp.Aggregates[season]
		champion := cmp.Champions[season]
		if champion == "" {
			champion = "-"
		}
		top := cmp.TopScorers[season]
		fmt.Fprintf(&b, "%-8d %-8d %-7d %-11.2f %-9.1f %-9.1f %-22s %s (%d)\n",
			season, agg.Matches, agg.Goals, agg.AvgGoals, agg.HomeWinRate, agg.DrawRate, champion, top.TeamName, top.GoalsFor)
		rows = append(rows, map[string]any{
			"season": season, "statistics": agg, "champion": champion,
			"top_scoring_team": top.TeamName, "top_scoring_goals": top.GoalsFor,
		})
	}
	return mcp.TextWithData(b.String(), map[string]any{"competition": comp, "seasons": rows}), nil
}
