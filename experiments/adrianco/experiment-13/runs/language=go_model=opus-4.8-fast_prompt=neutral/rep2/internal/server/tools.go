// Context: defines the MCP tool catalog. Build() constructs an mcp.Server with
// one Tool per supported query category from TASK.md (matches, teams, players,
// competitions, statistics). Each tool parses its arguments, calls into the
// soccer.DB query layer, and formats the answer. Input schemas are JSON Schema
// objects so an LLM client can discover argument shapes via tools/list.
package server

import (
	"fmt"
	"io"
	"strings"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/soccer"
)

const defaultLimit = 25

// Build constructs a fully wired MCP server over the given streams.
func Build(db *soccer.DB, in io.Reader, out io.Writer) *mcp.Server {
	s := mcp.NewServer("brazilian-soccer", "1.0.0", in, out)
	for _, t := range Tools(db) {
		s.Register(t)
	}
	return s
}

// schema is a small helper for building JSON Schema objects.
func schema(props map[string]interface{}, required ...string) map[string]interface{} {
	m := map[string]interface{}{
		"type":       "object",
		"properties": props,
	}
	if len(required) > 0 {
		m["required"] = required
	}
	return m
}

func strProp(desc string) map[string]interface{} {
	return map[string]interface{}{"type": "string", "description": desc}
}
func intProp(desc string) map[string]interface{} {
	return map[string]interface{}{"type": "integer", "description": desc}
}
func boolProp(desc string) map[string]interface{} {
	return map[string]interface{}{"type": "boolean", "description": desc}
}

// Tools returns the catalog bound to db. Exposed for testing.
func Tools(db *soccer.DB) []mcp.Tool {
	return []mcp.Tool{
		{
			Name:        "search_matches",
			Description: "Find soccer matches by team, opponent, competition, season, or season range. Returns matches most-recent first.",
			InputSchema: schema(map[string]interface{}{
				"team":        strProp("Team name; matches where it played home OR away."),
				"home_team":   strProp("Restrict to matches where this team was at home."),
				"away_team":   strProp("Restrict to matches where this team was away."),
				"opponent":    strProp("Together with 'team', finds matches between the two."),
				"competition": strProp("One of: Brasileirão, Copa do Brasil, Libertadores."),
				"season":      intProp("Exact season/year, e.g. 2019."),
				"season_from": intProp("Start of a season range (inclusive)."),
				"season_to":   intProp("End of a season range (inclusive)."),
				"limit":       intProp("Maximum matches to return (default 25)."),
			}),
			Handler: handleSearchMatches(db),
		},
		{
			Name:        "head_to_head",
			Description: "Head-to-head rivalry record between two teams: wins, draws, goals, and recent meetings.",
			InputSchema: schema(map[string]interface{}{
				"team_a":      strProp("First team."),
				"team_b":      strProp("Second team."),
				"competition": strProp("Optional competition filter."),
				"limit":       intProp("Max recent matches to list (default 10)."),
			}, "team_a", "team_b"),
			Handler: handleHeadToHead(db),
		},
		{
			Name:        "team_record",
			Description: "Aggregate win/draw/loss record and goals for a team, optionally filtered by competition, season, and home/away.",
			InputSchema: schema(map[string]interface{}{
				"team":        strProp("Team name."),
				"competition": strProp("Optional competition filter."),
				"season":      intProp("Optional season/year filter."),
				"home_only":   boolProp("Count only home matches."),
				"away_only":   boolProp("Count only away matches."),
			}, "team"),
			Handler: handleTeamRecord(db),
		},
		{
			Name:        "search_players",
			Description: "Search the FIFA player database by name, nationality, club, position, and minimum overall rating. Sorted by rating.",
			InputSchema: schema(map[string]interface{}{
				"name":        strProp("Substring of the player name."),
				"nationality": strProp("Nationality, e.g. Brazil."),
				"club":        strProp("Club name."),
				"position":    strProp("Position code, e.g. GK, LW, CDM, ST."),
				"min_overall": intProp("Minimum FIFA overall rating."),
				"limit":       intProp("Maximum players to return (default 25)."),
			}),
			Handler: handleSearchPlayers(db),
		},
		{
			Name:        "players_by_club",
			Description: "Group players by club (optionally for one nationality) with player counts and average ratings.",
			InputSchema: schema(map[string]interface{}{
				"nationality": strProp("Optional nationality filter, e.g. Brazil."),
				"limit":       intProp("Maximum clubs to return (default 25)."),
			}),
			Handler: handlePlayersByClub(db),
		},
		{
			Name:        "competition_standings",
			Description: "Compute the league table for a competition and season from match results (3 pts win, 1 draw).",
			InputSchema: schema(map[string]interface{}{
				"competition": strProp("Competition, e.g. Brasileirão."),
				"season":      intProp("Season/year, e.g. 2019."),
				"limit":       intProp("Max rows to return (default all)."),
			}, "competition", "season"),
			Handler: handleStandings(db),
		},
		{
			Name:        "match_statistics",
			Description: "Aggregate statistics over matches: average goals, home/away/draw split, and biggest-margin results.",
			InputSchema: schema(map[string]interface{}{
				"competition": strProp("Optional competition filter."),
				"season":      intProp("Optional season filter."),
				"team":        strProp("Optional team filter."),
				"top_wins":    intProp("How many biggest wins to list (default 10)."),
			}),
			Handler: handleStatistics(db),
		},
		{
			Name:        "list_competitions",
			Description: "List the competitions available in the dataset and overall data coverage counts.",
			InputSchema: schema(map[string]interface{}{}),
			Handler:     handleListCompetitions(db),
		},
	}
}

func handleSearchMatches(db *soccer.DB) func(map[string]interface{}) (string, error) {
	return func(a map[string]interface{}) (string, error) {
		limit := argInt(a, "limit")
		if limit == 0 {
			limit = defaultLimit
		}
		q := soccer.MatchQuery{
			Team:        argString(a, "team"),
			HomeTeam:    argString(a, "home_team"),
			AwayTeam:    argString(a, "away_team"),
			Opponent:    argString(a, "opponent"),
			Competition: argString(a, "competition"),
			Season:      argInt(a, "season"),
			SeasonFrom:  argInt(a, "season_from"),
			SeasonTo:    argInt(a, "season_to"),
		}
		matches := db.SearchMatches(q)
		header := fmt.Sprintf("Found %d match(es).", len(matches))
		return header + "\n" + formatMatchList(matches, limit), nil
	}
}

func handleHeadToHead(db *soccer.DB) func(map[string]interface{}) (string, error) {
	return func(a map[string]interface{}) (string, error) {
		ta := argString(a, "team_a")
		tb := argString(a, "team_b")
		if ta == "" || tb == "" {
			return "", fmt.Errorf("both team_a and team_b are required")
		}
		limit := argInt(a, "limit")
		if limit == 0 {
			limit = 10
		}
		h := db.HeadToHead(ta, tb, argString(a, "competition"))
		if len(h.Matches) == 0 {
			return fmt.Sprintf("No matches found between %s and %s.", ta, tb), nil
		}
		var b strings.Builder
		fmt.Fprintf(&b, "%s vs %s — head-to-head (%d matches in dataset):\n", h.TeamA, h.TeamB, len(h.Matches))
		fmt.Fprintf(&b, "%s %d wins, %s %d wins, %d draws\n", h.TeamA, h.AWins, h.TeamB, h.BWins, h.Draws)
		fmt.Fprintf(&b, "Goals: %s %d - %d %s\n\n", h.TeamA, h.AGoals, h.BGoals, h.TeamB)
		b.WriteString("Recent meetings:\n")
		b.WriteString(formatMatchList(h.Matches, limit))
		return b.String(), nil
	}
}

func handleTeamRecord(db *soccer.DB) func(map[string]interface{}) (string, error) {
	return func(a map[string]interface{}) (string, error) {
		team := argString(a, "team")
		if team == "" {
			return "", fmt.Errorf("team is required")
		}
		opt := soccer.TeamRecordOptions{
			Competition: argString(a, "competition"),
			Season:      argInt(a, "season"),
			HomeOnly:    argBool(a, "home_only"),
			AwayOnly:    argBool(a, "away_only"),
		}
		rec := db.TeamRecord(team, opt)
		label := team
		var quals []string
		if opt.Season != 0 {
			quals = append(quals, fmt.Sprintf("%d", opt.Season))
		}
		if opt.Competition != "" {
			quals = append(quals, opt.Competition)
		}
		if opt.HomeOnly {
			quals = append(quals, "home only")
		}
		if opt.AwayOnly {
			quals = append(quals, "away only")
		}
		if len(quals) > 0 {
			label += " (" + strings.Join(quals, ", ") + ")"
		}
		if rec.Matches == 0 {
			return fmt.Sprintf("No matches found for %s with those filters.", label), nil
		}
		return formatRecord(label+" record", rec), nil
	}
}

func handleSearchPlayers(db *soccer.DB) func(map[string]interface{}) (string, error) {
	return func(a map[string]interface{}) (string, error) {
		limit := argInt(a, "limit")
		if limit == 0 {
			limit = defaultLimit
		}
		q := soccer.PlayerQuery{
			Name:          argString(a, "name"),
			Nationality:   argString(a, "nationality"),
			Club:          argString(a, "club"),
			Position:      argString(a, "position"),
			MinOverall:    argInt(a, "min_overall"),
			SortByOverall: true,
		}
		players := db.SearchPlayers(q)
		total := len(players)
		if limit > 0 && len(players) > limit {
			players = players[:limit]
		}
		if total == 0 {
			return "No players found.", nil
		}
		var b strings.Builder
		fmt.Fprintf(&b, "Found %d player(s)", total)
		if total > len(players) {
			fmt.Fprintf(&b, " (showing top %d)", len(players))
		}
		b.WriteString(":\n")
		for i, p := range players {
			b.WriteString(formatPlayer(i+1, p))
			b.WriteString("\n")
		}
		return strings.TrimRight(b.String(), "\n"), nil
	}
}

func handlePlayersByClub(db *soccer.DB) func(map[string]interface{}) (string, error) {
	return func(a map[string]interface{}) (string, error) {
		limit := argInt(a, "limit")
		if limit == 0 {
			limit = defaultLimit
		}
		nat := argString(a, "nationality")
		summaries := db.PlayersByClub(nat, limit)
		if len(summaries) == 0 {
			return "No clubs found.", nil
		}
		var b strings.Builder
		if nat != "" {
			fmt.Fprintf(&b, "Clubs by %s player count:\n", nat)
		} else {
			b.WriteString("Clubs by player count:\n")
		}
		for _, c := range summaries {
			fmt.Fprintf(&b, "- %s: %d players (avg rating: %.1f)\n", c.Club, c.Count, c.AvgRating)
		}
		return strings.TrimRight(b.String(), "\n"), nil
	}
}

func handleStandings(db *soccer.DB) func(map[string]interface{}) (string, error) {
	return func(a map[string]interface{}) (string, error) {
		comp := argString(a, "competition")
		season := argInt(a, "season")
		if comp == "" || season == 0 {
			return "", fmt.Errorf("competition and season are required")
		}
		rows := db.Standings(comp, season)
		if len(rows) == 0 {
			return fmt.Sprintf("No standings could be computed for %s %d.", comp, season), nil
		}
		limit := argInt(a, "limit")
		if limit > 0 && len(rows) > limit {
			rows = rows[:limit]
		}
		var b strings.Builder
		fmt.Fprintf(&b, "%s %d standings (computed from matches):\n", comp, season)
		for i, r := range rows {
			fmt.Fprintf(&b, "%2d. %s - %d pts (%dW %dD %dL, GD %+d)\n",
				i+1, r.Team, r.Points, r.Wins, r.Draws, r.Losses, r.GoalDiff)
		}
		return strings.TrimRight(b.String(), "\n"), nil
	}
}

func handleStatistics(db *soccer.DB) func(map[string]interface{}) (string, error) {
	return func(a map[string]interface{}) (string, error) {
		f := soccer.StatsFilter{
			Competition: argString(a, "competition"),
			Season:      argInt(a, "season"),
			Team:        argString(a, "team"),
		}
		top := argInt(a, "top_wins")
		st := db.Statistics(f, top)
		if st.Matches == 0 {
			return "No matches found for those filters.", nil
		}
		var b strings.Builder
		scope := strings.Join(nonEmpty(f.Competition, yearStr(f.Season), f.Team), ", ")
		if scope == "" {
			scope = "all matches"
		}
		fmt.Fprintf(&b, "Statistics (%s):\n", scope)
		fmt.Fprintf(&b, "- Matches: %d\n", st.Matches)
		fmt.Fprintf(&b, "- Total goals: %d (avg %.2f per match)\n", st.TotalGoals, st.AvgGoals())
		fmt.Fprintf(&b, "- Home wins: %d (%.1f%%), Away wins: %d, Draws: %d\n",
			st.HomeWins, st.HomeWinRate(), st.AwayWins, st.Draws)
		b.WriteString("\nBiggest-margin results:\n")
		b.WriteString(formatMatchList(st.BiggestWins, 0))
		return b.String(), nil
	}
}

func handleListCompetitions(db *soccer.DB) func(map[string]interface{}) (string, error) {
	return func(a map[string]interface{}) (string, error) {
		comps := db.Competitions()
		var b strings.Builder
		b.WriteString("Available competitions:\n")
		for _, c := range comps {
			b.WriteString("- " + c + "\n")
		}
		fmt.Fprintf(&b, "\nData coverage: %d matches, %d players.", len(db.Matches), len(db.Players))
		return b.String(), nil
	}
}

func yearStr(y int) string {
	if y == 0 {
		return ""
	}
	return fmt.Sprintf("%d", y)
}

func nonEmpty(ss ...string) []string {
	var out []string
	for _, s := range ss {
		if s != "" {
			out = append(out, s)
		}
	}
	return out
}
