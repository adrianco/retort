// tools_match.go: the match centred tools - searching fixtures, one match in
// detail, head-to-head records and derbies.
package soccerserver

import (
	"fmt"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

func (a *api) searchMatchesTool() *mcp.Tool {
	props := commonFilterProps()
	props["team"] = mcp.Str("Club to search for, e.g. \"Flamengo\", \"Atletico Mineiro\", \"Palmeiras-SP\".")
	props["opponent"] = mcp.Str("Restrict to matches against this club.")
	props["venue"] = mcp.Enum("Whether the team played at home, away, or either (default any).", "home", "away", "any")
	props["round"] = mcp.Int("League round number.")
	props["stage"] = mcp.Str("Cup or Libertadores stage, e.g. \"final\", \"semifinals\", \"group stage\".")
	props["result"] = mcp.Enum("Restrict to matches the team won, drew or lost.", "win", "draw", "loss")
	props["min_total_goals"] = mcp.Int("Only matches with at least this many goals in total.")
	props["sort"] = mcp.Enum("Ordering (default date_desc).", "date_desc", "date_asc", "goals_desc", "margin_desc")
	props["limit"] = mcp.IntRange("Maximum number of matches to return (default 20, max 200).", 1, maxLimit)
	props["offset"] = mcp.Int("Number of matches to skip, for paging.")

	return &mcp.Tool{
		Name:        "search_matches",
		Title:       "Search matches",
		Description: "Find matches by club, opponent, venue, competition, season, date range, round or stage. Answers questions such as \"Show me all Flamengo vs Fluminense matches\", \"What matches did Palmeiras play in 2023?\" and \"Find all Copa do Brasil finals\".",
		InputSchema: mcp.Object(props),
		Handler:     a.searchMatches,
	}
}

func (a *api) searchMatches(args mcp.Args) (*mcp.ToolResult, error) {
	var f soccer.MatchFilter
	if res := a.applyCommonFilters(args, &f); res != nil {
		return res, nil
	}
	var team, opponent *soccer.Team
	if args.Has("team") {
		t, res := a.resolveTeam(args.String("team"), "team")
		if res != nil {
			return res, nil
		}
		team = t
		f.TeamID = t.ID
	}
	if args.Has("opponent") {
		t, res := a.resolveTeam(args.String("opponent"), "opponent")
		if res != nil {
			return res, nil
		}
		opponent = t
		f.OpponentID = t.ID
	}
	if f.TeamID == "" && f.OpponentID != "" {
		f.TeamID, f.OpponentID = f.OpponentID, ""
		team, opponent = opponent, nil
	}
	venue, err := soccer.ParseVenue(args.String("venue"))
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	f.Venue = venue
	if f.Round, err = args.Int("round", 0); err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	if f.MinTotalGoals, err = args.Int("min_total_goals", 0); err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	if f.Offset, err = args.Int("offset", 0); err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	f.Stage = args.String("stage")
	f.Result = args.String("result")
	f.Sort = args.String("sort")
	// "won" and "at home" only mean something relative to a club.
	if f.TeamID == "" {
		if f.Result != "" {
			return mcp.ErrorResult("`result` needs a `team`: a match is only a win or a loss from one club's point of view."), nil
		}
		if venue != soccer.VenueAny {
			return mcp.ErrorResult("`venue` needs a `team`: pass the club whose home or away fixtures you want."), nil
		}
	}
	limit, res := limitArg(args, defaultLimit)
	if res != nil {
		return res, nil
	}
	f.Limit = limit

	page := a.store.FindMatches(f)
	title := matchSearchTitle(team, opponent, f)
	text := soccer.FormatMatches(title, page.Matches, page.Total, f.Offset)
	if page.Total == 0 {
		text += a.emptyMatchHint(f, team)
	}
	if team != nil && page.Total > 0 {
		rec := recordOf(page.Matches, team.ID)
		text += fmt.Sprintf("\nRecord in the matches shown: %dW %dD %dL, %d-%d on goals.\n",
			rec.Wins, rec.Draws, rec.Losses, rec.GoalsFor, rec.GoalsAgainst)
	}
	return mcp.TextWithData(text, map[string]any{
		"total":   page.Total,
		"shown":   len(page.Matches),
		"scope":   scopeLabel(f),
		"matches": matchesJSON(page.Matches),
	}), nil
}

func recordOf(ms []*soccer.Match, teamID string) soccer.Record {
	var r soccer.Record
	for _, m := range ms {
		r.Add(m, teamID)
	}
	return r
}

func matchSearchTitle(team, opponent *soccer.Team, f soccer.MatchFilter) string {
	switch {
	case team != nil && opponent != nil:
		return fmt.Sprintf("%s vs %s (%s):", team.Name, opponent.Name, scopeLabel(f))
	case team != nil:
		venue := ""
		switch f.Venue {
		case soccer.VenueHome:
			venue = " at home"
		case soccer.VenueAway:
			venue = " away"
		}
		return fmt.Sprintf("%s matches%s (%s):", team.Name, venue, scopeLabel(f))
	default:
		return fmt.Sprintf("Matches (%s):", scopeLabel(f))
	}
}

// emptyMatchHint explains an empty result instead of leaving the model to
// guess, which is where wrong answers usually come from.
func (a *api) emptyMatchHint(f soccer.MatchFilter, team *soccer.Team) string {
	var b strings.Builder
	if team != nil {
		if len(team.Seasons) > 0 {
			b.WriteString(fmt.Sprintf("%s appears in the data between %d and %d, in: %s.\n",
				team.Name, team.Seasons[0], team.Seasons[len(team.Seasons)-1], strings.Join(compLabels(team.CompIDs), ", ")))
		} else {
			b.WriteString(fmt.Sprintf("%s has no matches at all in the provided data.\n", team.Name))
		}
	}
	if f.CompetitionID != "" {
		seasons := a.store.Seasons(f.CompetitionID)
		if len(seasons) > 0 {
			b.WriteString(fmt.Sprintf("%s covers seasons %d-%d in this dataset.\n",
				soccer.CompetitionLabel(f.CompetitionID), seasons[0], seasons[len(seasons)-1]))
		}
	}
	return b.String()
}

func compLabels(ids []string) []string {
	out := make([]string, 0, len(ids))
	for _, id := range ids {
		out = append(out, soccer.CompetitionLabel(id))
	}
	return out
}

func (a *api) headToHeadTool() *mcp.Tool {
	props := commonFilterProps()
	props["team_a"] = mcp.Str("First club.")
	props["team_b"] = mcp.Str("Second club.")
	props["limit"] = mcp.IntRange("How many individual matches to list (default 10, max 200).", 1, maxLimit)
	return &mcp.Tool{
		Name:        "head_to_head",
		Title:       "Head-to-head record",
		Description: "Compare two clubs directly: every meeting in the data, the win/draw/loss split, goals, the derby name if it is a traditional rivalry, and the biggest win for each side. Answers \"Compare Palmeiras and Santos head-to-head\" or \"When did Flamengo last play Corinthians?\".",
		InputSchema: mcp.Object(props, "team_a", "team_b"),
		Handler:     a.headToHead,
	}
}

func (a *api) headToHead(args mcp.Args) (*mcp.ToolResult, error) {
	teamA, res := a.resolveTeam(args.String("team_a"), "team_a")
	if res != nil {
		return res, nil
	}
	teamB, res := a.resolveTeam(args.String("team_b"), "team_b")
	if res != nil {
		return res, nil
	}
	if teamA.ID == teamB.ID {
		return mcp.ErrorResult("team_a and team_b both resolve to %s; pass two different clubs.", teamA.Name), nil
	}
	var f soccer.MatchFilter
	if res := a.applyCommonFilters(args, &f); res != nil {
		return res, nil
	}
	limit, res := limitArg(args, 10)
	if res != nil {
		return res, nil
	}
	f.Limit = limit
	h := a.store.HeadToHead(teamA.ID, teamB.ID, f)
	text := soccer.FormatHeadToHead(h, limit)
	return mcp.TextWithData(text, map[string]any{
		"team_a":       teamA.ID,
		"team_b":       teamB.ID,
		"total":        h.Total,
		"team_a_wins":  h.AWins,
		"team_b_wins":  h.BWins,
		"draws":        h.Draws,
		"team_a_goals": h.AGoals,
		"team_b_goals": h.BGoals,
		"rivalry":      h.Rivalry,
		"matches":      matchesJSON(h.Matches),
	}), nil
}

func (a *api) matchDetailsTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "match_details",
		Title:       "Match details",
		Description: "Show one match in full, including the extended statistics (shots, corners, attacks, half-time trend) that BR-Football-Dataset.csv adds. Give either match_id, or two clubs plus an optional date.",
		InputSchema: mcp.Object(map[string]*mcp.Prop{
			"match_id": mcp.Str("Match id as returned by search_matches."),
			"team":     mcp.Str("One of the clubs."),
			"opponent": mcp.Str("The other club."),
			"date":     mcp.Str("Match date (YYYY-MM-DD). Without it the most recent meeting is used."),
			"season":   mcp.Int("Season to disambiguate."),
		}),
		Handler: a.matchDetails,
	}
}

func (a *api) matchDetails(args mcp.Args) (*mcp.ToolResult, error) {
	if id := args.String("match_id"); id != "" {
		m := a.store.Match(id)
		if m == nil {
			return mcp.ErrorResult("no match with id %q; ids come from search_matches.", id), nil
		}
		return mcp.TextWithData(soccer.FormatMatchDetail(m), matchesJSON([]*soccer.Match{m})[0]), nil
	}
	if !args.Has("team") || !args.Has("opponent") {
		return mcp.ErrorResult("give match_id, or both team and opponent."), nil
	}
	teamA, res := a.resolveTeam(args.String("team"), "team")
	if res != nil {
		return res, nil
	}
	teamB, res := a.resolveTeam(args.String("opponent"), "opponent")
	if res != nil {
		return res, nil
	}
	f := soccer.MatchFilter{TeamID: teamA.ID, OpponentID: teamB.ID, Sort: "date_desc"}
	season, err := args.Int("season", 0)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	f.Season = season
	if d := args.String("date"); d != "" {
		day, res := parseDateArg(d, "date")
		if res != nil {
			return res, nil
		}
		f.From, f.To = day, endOfDay(day)
	}
	page := a.store.FindMatches(f)
	if len(page.Matches) == 0 {
		return mcp.ErrorResult("no %s vs %s match found for those filters.", teamA.Name, teamB.Name), nil
	}
	m := page.Matches[0]
	text := soccer.FormatMatchDetail(m)
	if page.Total > 1 {
		text += fmt.Sprintf("\n(%d meetings match these filters; this is the most recent. Use head_to_head for the full list.)\n", page.Total)
	}
	return mcp.TextWithData(text, matchesJSON([]*soccer.Match{m})[0]), nil
}

func (a *api) findDerbiesTool() *mcp.Tool {
	props := commonFilterProps()
	props["rivalry"] = mcp.Str("Restrict to one derby by name, e.g. \"Fla-Flu\", \"Grenal\", \"Derby Paulista\".")
	props["team"] = mcp.Str("Restrict to derbies involving this club.")
	props["limit"] = mcp.IntRange("Maximum matches to list (default 20, max 200).", 1, maxLimit)
	return &mcp.Tool{
		Name:        "find_derbies",
		Title:       "Find derbies",
		Description: "List matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, Clássico Mineiro, Atletiba, Ba-Vi, Clássico Rei and more). Answers \"Show me all derbies in 2023\".",
		InputSchema: mcp.Object(props),
		Handler:     a.findDerbies,
	}
}

func (a *api) findDerbies(args mcp.Args) (*mcp.ToolResult, error) {
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
	limit, res := limitArg(args, defaultLimit)
	if res != nil {
		return res, nil
	}
	rivalry := args.String("rivalry")
	derbies := a.store.Derbies(f, rivalry, limit)

	var b strings.Builder
	fmt.Fprintf(&b, "Derbies (%s):\n", scopeLabel(f))
	if len(derbies) == 0 {
		b.WriteString("No derby fixtures match those filters. Known derbies: ")
		names := make([]string, 0, len(soccer.Rivalries()))
		for _, r := range soccer.Rivalries() {
			names = append(names, r.Name)
		}
		b.WriteString(strings.Join(names, ", ") + ".\n")
		return mcp.TextWithData(b.String(), map[string]any{"matches": []any{}}), nil
	}
	items := make([]map[string]any, 0, len(derbies))
	for _, d := range derbies {
		fmt.Fprintf(&b, "%s [%s]\n", soccer.MatchLine(d.Match), d.Rivalry.Name)
		item := matchesJSON([]*soccer.Match{d.Match})[0]
		item["rivalry"] = d.Rivalry.Name
		items = append(items, item)
	}
	return mcp.TextWithData(b.String(), map[string]any{"matches": items, "count": len(items)}), nil
}
