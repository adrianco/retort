// tools_team.go: club centred tools - the club catalogue, one club's dossier,
// its record under any filter, and league-wide record rankings.
package soccerserver

import (
	"fmt"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

func (a *api) listTeamsTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "list_teams",
		Title:       "List clubs",
		Description: "List the clubs in the knowledge graph, optionally filtered by name, state, country or competition. Useful to discover the exact club name to pass to the other tools.",
		InputSchema: mcp.Object(map[string]*mcp.Prop{
			"query":       mcp.Str("Substring of the club name."),
			"state":       mcp.Str("Brazilian state code, e.g. SP, RJ, MG."),
			"country":     mcp.Str("Country code for non-Brazilian clubs, e.g. ARG, URU."),
			"competition": mcp.Str("Only clubs that appear in this competition."),
			"season":      mcp.Int("Only clubs that appear in this season."),
			"min_matches": mcp.Int("Only clubs with at least this many matches (default 1)."),
			"limit":       mcp.IntRange("Maximum clubs to return (default 50, max 200).", 1, maxLimit),
		}),
		Handler: a.listTeams,
	}
}

func (a *api) listTeams(args mcp.Args) (*mcp.ToolResult, error) {
	comp, res := a.resolveCompetition(args.String("competition"))
	if res != nil {
		return res, nil
	}
	season, err := args.Int("season", 0)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	minMatches, err := args.Int("min_matches", 1)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	limit, res := limitArg(args, 50)
	if res != nil {
		return res, nil
	}
	query := soccer.Fold(args.String("query"))
	state := strings.ToUpper(args.String("state"))
	country := strings.ToUpper(args.String("country"))

	// A competition and a season have to be applied together - a club that
	// played the 2019 cup and the 2015 league is not part of the 2019 league.
	var eligible map[string]bool
	if comp != "" || season != 0 {
		eligible = map[string]bool{}
		for _, m := range a.store.FindMatches(soccer.MatchFilter{CompetitionID: comp, Season: season}).Matches {
			eligible[m.HomeTeamID] = true
			eligible[m.AwayTeamID] = true
		}
	}

	var picked []*soccer.Team
	for _, t := range a.store.Teams.Teams() {
		if t.Matches < minMatches {
			continue
		}
		if state != "" && !strings.EqualFold(t.State, state) {
			continue
		}
		if country != "" && !strings.EqualFold(t.Country, country) {
			continue
		}
		if query != "" && !matchesAnyAlias(t, query) {
			continue
		}
		if eligible != nil && !eligible[t.ID] {
			continue
		}
		picked = append(picked, t)
	}
	total := len(picked)
	sortTeamsByMatches(picked)
	if len(picked) > limit {
		picked = picked[:limit]
	}

	var b strings.Builder
	fmt.Fprintf(&b, "Clubs (%d of %d shown):\n", len(picked), total)
	items := make([]map[string]any, 0, len(picked))
	for _, t := range picked {
		where := t.State
		if where == "" {
			where = t.Country
		}
		fmt.Fprintf(&b, "- %-24s [%s] %s, %d matches, competitions: %s\n",
			t.Name, t.ID, orNA(where), t.Matches, strings.Join(compLabels(t.CompIDs), "/"))
		items = append(items, map[string]any{
			"id": t.ID, "name": t.Name, "state": t.State, "country": t.Country,
			"matches": t.Matches, "competitions": t.CompIDs, "seasons": t.Seasons,
			"aliases": t.Aliases, "squad_size": t.Squad,
		})
	}
	return mcp.TextWithData(b.String(), map[string]any{"total": total, "teams": items}), nil
}

func matchesAnyAlias(t *soccer.Team, foldedQuery string) bool {
	if strings.Contains(soccer.Fold(t.Name), foldedQuery) || strings.Contains(t.ID, foldedQuery) {
		return true
	}
	for _, alias := range t.Aliases {
		if strings.Contains(soccer.Fold(alias), foldedQuery) {
			return true
		}
	}
	return false
}

func sortTeamsByMatches(ts []*soccer.Team) {
	for i := 1; i < len(ts); i++ {
		for j := i; j > 0 && ts[j].Matches > ts[j-1].Matches; j-- {
			ts[j], ts[j-1] = ts[j-1], ts[j]
		}
	}
}

func orNA(s string) string {
	if s == "" {
		return "?"
	}
	return s
}

func (a *api) teamProfileTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "team_profile",
		Title:       "Club profile",
		Description: "Everything the graph knows about one club: identity and alternative spellings, overall and per-competition record, league titles inside the data window, biggest win, heaviest defeat, home grounds, derbies and the FIFA squad linked to it. Answers \"What competitions has Palmeiras played in?\".",
		InputSchema: mcp.Object(map[string]*mcp.Prop{
			"team": mcp.Str("Club name or id."),
		}, "team"),
		Handler: a.teamProfile,
	}
}

func (a *api) teamProfile(args mcp.Args) (*mcp.ToolResult, error) {
	team, res := a.resolveTeam(args.String("team"), "team")
	if res != nil {
		return res, nil
	}
	p := a.store.Profile(team.ID)
	if p == nil {
		return mcp.ErrorResult("no profile for %q", args.String("team")), nil
	}
	data := map[string]any{
		"team":         team,
		"record":       p.Record,
		"home_record":  p.Home,
		"away_record":  p.Away,
		"competitions": p.ByCompetition,
		"titles":       p.Titles,
		"squad":        playersJSON(p.Squad),
		"node":         string(soccer.TeamNode(team.ID)),
	}
	if p.BiggestWin != nil {
		data["biggest_win"] = matchesJSON([]*soccer.Match{p.BiggestWin})[0]
	}
	if p.HeaviestLoss != nil {
		data["heaviest_defeat"] = matchesJSON([]*soccer.Match{p.HeaviestLoss})[0]
	}
	return mcp.TextWithData(soccer.FormatTeamProfile(p), data), nil
}

func (a *api) teamStatsTool() *mcp.Tool {
	props := commonFilterProps()
	props["team"] = mcp.Str("Club name or id.")
	props["venue"] = mcp.Enum("Restrict to home or away fixtures (default any).", "home", "away", "any")
	props["split"] = mcp.Bool("Also break the record down by competition and by home/away (default true).")
	return &mcp.Tool{
		Name:        "team_stats",
		Title:       "Club statistics",
		Description: "Win/draw/loss record, goals for and against, points and win rate for one club, filtered by competition, season, date range and venue. Answers \"What is Corinthians' home record in 2022?\".",
		InputSchema: mcp.Object(props, "team"),
		Handler:     a.teamStats,
	}
}

func (a *api) teamStats(args mcp.Args) (*mcp.ToolResult, error) {
	team, res := a.resolveTeam(args.String("team"), "team")
	if res != nil {
		return res, nil
	}
	var f soccer.MatchFilter
	if res := a.applyCommonFilters(args, &f); res != nil {
		return res, nil
	}
	venue, err := soccer.ParseVenue(args.String("venue"))
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	f.Venue = venue
	split, err := args.Bool("split", true)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}

	rec := a.store.TeamRecord(team.ID, f)
	venueLabel := ""
	switch venue {
	case soccer.VenueHome:
		venueLabel = " home"
	case soccer.VenueAway:
		venueLabel = " away"
	}
	title := fmt.Sprintf("%s%s record (%s)", team.Name, venueLabel, scopeLabel(f))
	text := soccer.FormatRecord(title, rec)
	data := map[string]any{"team": team.ID, "record": rec, "scope": scopeLabel(f)}

	if rec.Matches == 0 {
		text += a.emptyMatchHint(f, team)
	} else if split {
		home := f
		home.Venue = soccer.VenueHome
		away := f
		away.Venue = soccer.VenueAway
		hr, ar := a.store.TeamRecord(team.ID, home), a.store.TeamRecord(team.ID, away)
		if venue == soccer.VenueAny {
			text += fmt.Sprintf("\nHome: %d matches, %dW %dD %dL, GF %d GA %d (win rate %.1f%%)\n",
				hr.Matches, hr.Wins, hr.Draws, hr.Losses, hr.GoalsFor, hr.GoalsAgainst, hr.WinRate())
			text += fmt.Sprintf("Away: %d matches, %dW %dD %dL, GF %d GA %d (win rate %.1f%%)\n",
				ar.Matches, ar.Wins, ar.Draws, ar.Losses, ar.GoalsFor, ar.GoalsAgainst, ar.WinRate())
			data["home_record"], data["away_record"] = hr, ar
		}
		if f.CompetitionID == "" {
			var byComp []map[string]any
			text += "\nBy competition:\n"
			for _, c := range a.store.CompetitionsWithData() {
				cf := f
				cf.CompetitionID = c.ID
				cr := a.store.TeamRecord(team.ID, cf)
				if cr.Matches == 0 {
					continue
				}
				text += fmt.Sprintf("- %-16s %3d matches: %dW %dD %dL, GF %d GA %d\n",
					c.Short, cr.Matches, cr.Wins, cr.Draws, cr.Losses, cr.GoalsFor, cr.GoalsAgainst)
				byComp = append(byComp, map[string]any{"competition": c.ID, "record": cr})
			}
			data["by_competition"] = byComp
		}
		if f.Season != 0 && f.CompetitionID != "" {
			if table := a.store.Standings(f.CompetitionID, f.Season, soccer.StandingsOptions{}); table != nil {
				for _, row := range table.Rows {
					if row.TeamID == team.ID {
						text += fmt.Sprintf("\nFinished %d of %d in the %d %s table with %d points.\n",
							row.Position, len(table.Rows), f.Season, soccer.CompetitionLabel(f.CompetitionID), row.Points)
						data["table_position"] = row.Position
						break
					}
				}
			}
		}
	}
	return mcp.TextWithData(text, data), nil
}

func (a *api) bestRecordsTool() *mcp.Tool {
	props := commonFilterProps()
	props["venue"] = mcp.Enum("Rank home records, away records or overall (default any).", "home", "away", "any")
	props["metric"] = mcp.Enum("Ranking metric (default points).", "points", "win_rate", "wins", "goals_for", "goals_against", "goal_diff", "points_per_match")
	props["min_matches"] = mcp.Int("Ignore clubs with fewer matches than this (default 10).")
	props["limit"] = mcp.IntRange("How many clubs to rank (default 10, max 200).", 1, maxLimit)
	return &mcp.Tool{
		Name:        "best_records",
		Title:       "Rank clubs",
		Description: "Rank clubs by points, win rate, wins, goals scored or conceded, over any competition/season/venue slice. Answers \"Which team has the best home record?\", \"Which team has the best away record?\" and \"Which team scored the most goals in Serie A 2023?\".",
		InputSchema: mcp.Object(props),
		Handler:     a.bestRecords,
	}
}

func (a *api) bestRecords(args mcp.Args) (*mcp.ToolResult, error) {
	var f soccer.MatchFilter
	if res := a.applyCommonFilters(args, &f); res != nil {
		return res, nil
	}
	venue, err := soccer.ParseVenue(args.String("venue"))
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	f.Venue = venue
	minMatches, err := args.Int("min_matches", 10)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	limit, res := limitArg(args, 10)
	if res != nil {
		return res, nil
	}
	metric := args.String("metric")
	if metric == "" {
		metric = "points"
	}
	records := a.store.TeamRecords(f, metric, minMatches, limit)
	venueLabel := "overall"
	switch venue {
	case soccer.VenueHome:
		venueLabel = "home"
	case soccer.VenueAway:
		venueLabel = "away"
	}
	title := fmt.Sprintf("Clubs ranked by %s (%s records, %s, minimum %d matches):",
		strings.ReplaceAll(metric, "_", " "), venueLabel, scopeLabel(f), minMatches)
	return mcp.TextWithData(soccer.FormatTeamRecords(title, records), map[string]any{
		"metric": metric, "venue": venueLabel, "scope": scopeLabel(f), "records": records,
	}), nil
}
