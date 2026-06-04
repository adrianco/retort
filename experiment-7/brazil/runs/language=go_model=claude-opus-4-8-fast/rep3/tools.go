// tools.go - registration of the MCP tools and their argument handling.
//
// Context
// -------
// This file is the bridge between the generic MCP transport (internal/mcp) and
// the soccer knowledge graph (internal/soccer). It defines the seven tools the
// server advertises, their JSON Schemas, and decodes/validates arguments before
// delegating to query functions and rendering the results as text.
//
// Tools:
//
//	search_matches        - find fixtures by team/opponent/competition/season/dates
//	head_to_head          - aggregate record between two teams
//	team_stats            - W/D/L, goals and win rate for one team
//	search_players        - FIFA players by name/nationality/club/position/rating
//	competition_standings - computed league table for a competition+season
//	league_statistics     - avg goals, home/away win rates, biggest wins, best records
//	list_competitions     - dataset coverage (competitions and season ranges)
package main

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/soccer"
)

// registerTools wires every tool into the server, closing over the loaded DB.
func registerTools(s *mcp.Server, db *soccer.DB) {
	s.Register("search_matches",
		"Search Brazilian soccer matches by team, opponent, competition, season and/or date range. "+
			"Use 'team' alone to list a club's matches, or 'team'+'opponent' for a specific fixture. "+
			"Competition accepts names like 'Brasileirão', 'Copa do Brasil', 'Libertadores', 'Serie B'.",
		schema(map[string]any{
			"team":        strProp("Team name (matches home or away), e.g. 'Flamengo'."),
			"opponent":    strProp("Opponent team name; combine with 'team' for a specific fixture."),
			"home":        strProp("Restrict to this team playing at home."),
			"away":        strProp("Restrict to this team playing away."),
			"competition": strProp("Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'."),
			"season":      intProp("Season/year filter, e.g. 2019."),
			"start_date":  strProp("Inclusive start date (YYYY-MM-DD)."),
			"end_date":    strProp("Inclusive end date (YYYY-MM-DD)."),
			"limit":       intProp("Maximum matches to list (default 20)."),
		}, nil),
		handleSearchMatches(db))

	s.Register("head_to_head",
		"Compute the head-to-head record between two teams: wins, draws, goals and the list of matches.",
		schema(map[string]any{
			"team_a":      strProp("First team."),
			"team_b":      strProp("Second team."),
			"competition": strProp("Optional competition filter."),
			"limit":       intProp("Maximum matches to list (default 20)."),
		}, []string{"team_a", "team_b"}),
		handleHeadToHead(db))

	s.Register("team_stats",
		"Aggregate a team's record (matches, wins, draws, losses, goals for/against, points, win rate), "+
			"optionally scoped to a season, competition and venue (home/away/all).",
		schema(map[string]any{
			"team":        strProp("Team name."),
			"season":      intProp("Season/year filter."),
			"competition": strProp("Competition filter."),
			"venue":       strProp("'home', 'away' or 'all' (default 'all')."),
		}, []string{"team"}),
		handleTeamStats(db))

	s.Register("search_players",
		"Search the FIFA player database by name, nationality (e.g. 'Brazil'), club, position and rating. "+
			"Results are sorted by overall rating, highest first.",
		schema(map[string]any{
			"name":        strProp("Player name substring, e.g. 'Gabriel'."),
			"nationality": strProp("Nationality, e.g. 'Brazil'."),
			"club":        strProp("Club name substring, e.g. 'Flamengo'."),
			"position":    strProp("Position code, e.g. 'ST', 'GK', 'LW'."),
			"min_overall": intProp("Minimum overall rating."),
			"max_overall": intProp("Maximum overall rating."),
			"limit":       intProp("Maximum players to list (default 20)."),
		}, nil),
		handleSearchPlayers(db))

	s.Register("competition_standings",
		"Compute a league table (standings) for a competition and season from match results. "+
			"Best for round-robin leagues such as the Brasileirão.",
		schema(map[string]any{
			"competition": strProp("Competition, e.g. 'Brasileirão', 'Serie B'."),
			"season":      intProp("Season/year, e.g. 2019."),
			"limit":       intProp("Maximum teams to list (default: full table)."),
		}, []string{"competition", "season"}),
		handleStandings(db))

	s.Register("league_statistics",
		"Aggregate statistics for a competition/season. metric is one of: "+
			"'summary' (avg goals, home/away win rates), 'biggest_wins', 'best_home', 'best_away', "+
			"'best_overall', 'top_scoring'.",
		schema(map[string]any{
			"metric":      strProp("One of: summary, biggest_wins, best_home, best_away, best_overall, top_scoring."),
			"competition": strProp("Optional competition filter."),
			"season":      intProp("Optional season filter."),
			"limit":       intProp("Maximum rows for ranked metrics (default 10)."),
			"min_played":  intProp("Minimum matches for best-record metrics (default 10)."),
		}, []string{"metric"}),
		handleLeagueStatistics(db))

	s.Register("list_competitions",
		"List the competitions present in the dataset with match counts and the seasons covered. "+
			"Use this to discover what can be queried.",
		schema(map[string]any{}, nil),
		handleListCompetitions(db))
}

// --- argument decoding helpers ---

// args is the decoded, loosely-typed argument bag for a tool call. Numbers may
// arrive as JSON numbers or numeric strings, so accessors are tolerant.
type args map[string]any

func decode(raw json.RawMessage) (args, error) {
	if len(raw) == 0 || string(raw) == "null" {
		return args{}, nil
	}
	var a args
	if err := json.Unmarshal(raw, &a); err != nil {
		return nil, fmt.Errorf("invalid arguments: %w", err)
	}
	return a, nil
}

func (a args) str(key string) string {
	v, ok := a[key]
	if !ok || v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return strings.TrimSpace(t)
	case float64:
		return strings.TrimSpace(fmt.Sprintf("%v", t))
	default:
		return strings.TrimSpace(fmt.Sprintf("%v", t))
	}
}

func (a args) intOr(key string, def int) int {
	v, ok := a[key]
	if !ok || v == nil {
		return def
	}
	switch t := v.(type) {
	case float64:
		return int(t)
	case string:
		var n int
		if _, err := fmt.Sscanf(strings.TrimSpace(t), "%d", &n); err == nil {
			return n
		}
	}
	return def
}

func (a args) competition(key string) string {
	if k, ok := soccer.ParseCompetition(a.str(key)); ok {
		return k
	}
	return ""
}

func (a args) date(key string) (time.Time, bool) {
	s := a.str(key)
	if s == "" {
		return time.Time{}, false
	}
	for _, layout := range []string{"2006-01-02", "02/01/2006", "2006-01-02 15:04:05"} {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// --- tool handlers ---

func handleSearchMatches(db *soccer.DB) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := decode(raw)
		if err != nil {
			return "", err
		}
		f := soccer.MatchFilter{
			Team:        a.str("team"),
			Opponent:    a.str("opponent"),
			Home:        a.str("home"),
			Away:        a.str("away"),
			Competition: a.competition("competition"),
			Season:      a.intOr("season", 0),
		}
		if t, ok := a.date("start_date"); ok {
			f.Start = t
		}
		if t, ok := a.date("end_date"); ok {
			f.End = t
		}
		if f.Team == "" && f.Opponent == "" && f.Home == "" && f.Away == "" &&
			f.Competition == "" && f.Season == 0 && f.Start.IsZero() && f.End.IsZero() {
			return "", fmt.Errorf("provide at least one filter (team, competition, season or date range)")
		}
		matches := db.FindMatches(f)
		limit := a.intOr("limit", 20)
		header := fmt.Sprintf("Found %d match(es).\n", len(matches))
		return header + soccer.FormatMatchList(matches, limit), nil
	}
}

func handleHeadToHead(db *soccer.DB) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := decode(raw)
		if err != nil {
			return "", err
		}
		teamA, teamB := a.str("team_a"), a.str("team_b")
		if teamA == "" || teamB == "" {
			return "", fmt.Errorf("both team_a and team_b are required")
		}
		res := db.HeadToHead(teamA, teamB, a.competition("competition"))
		return soccer.FormatHeadToHead(res, a.intOr("limit", 20)), nil
	}
}

func handleTeamStats(db *soccer.DB) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := decode(raw)
		if err != nil {
			return "", err
		}
		team := a.str("team")
		if team == "" {
			return "", fmt.Errorf("team is required")
		}
		stats := db.ComputeTeamStats(team, a.intOr("season", 0), a.competition("competition"), a.str("venue"))
		if stats.Played == 0 {
			return fmt.Sprintf("No matches found for %q with the given filters.", team), nil
		}
		return soccer.FormatTeamStats(stats), nil
	}
}

func handleSearchPlayers(db *soccer.DB) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := decode(raw)
		if err != nil {
			return "", err
		}
		f := soccer.PlayerFilter{
			Name:        a.str("name"),
			Nationality: a.str("nationality"),
			Club:        a.str("club"),
			Position:    a.str("position"),
			MinOverall:  a.intOr("min_overall", 0),
			MaxOverall:  a.intOr("max_overall", 0),
		}
		if f.Name == "" && f.Nationality == "" && f.Club == "" && f.Position == "" &&
			f.MinOverall == 0 && f.MaxOverall == 0 {
			return "", fmt.Errorf("provide at least one filter (name, nationality, club, position or rating)")
		}
		players := db.FindPlayers(f)
		header := fmt.Sprintf("Found %d player(s).\n", len(players))
		return header + soccer.FormatPlayerList(players, a.intOr("limit", 20)), nil
	}
}

func handleStandings(db *soccer.DB) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := decode(raw)
		if err != nil {
			return "", err
		}
		comp := a.competition("competition")
		season := a.intOr("season", 0)
		if comp == "" || season == 0 {
			return "", fmt.Errorf("both competition and season are required")
		}
		rows := db.Standings(comp, season)
		return soccer.FormatStandings(rows, comp, season, a.intOr("limit", 0)), nil
	}
}

func handleLeagueStatistics(db *soccer.DB) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := decode(raw)
		if err != nil {
			return "", err
		}
		metric := strings.ToLower(strings.TrimSpace(a.str("metric")))
		comp := a.competition("competition")
		season := a.intOr("season", 0)
		limit := a.intOr("limit", 10)
		minPlayed := a.intOr("min_played", 10)
		f := soccer.MatchFilter{Competition: comp, Season: season}

		switch metric {
		case "", "summary":
			return soccer.FormatGoalStats(db.GoalStatistics(f), comp, season), nil
		case "biggest_wins", "biggest", "biggest_victories":
			matches := db.BiggestWins(f, limit)
			return "Biggest victories" + scopeNote(comp, season) + ":\n" + soccer.FormatMatchList(matches, limit), nil
		case "best_home":
			recs := db.BestRecords(comp, season, "home", minPlayed, limit)
			return soccer.FormatTeamRecordsTable("Best home records"+scopeNote(comp, season)+":", recs, limit), nil
		case "best_away":
			recs := db.BestRecords(comp, season, "away", minPlayed, limit)
			return soccer.FormatTeamRecordsTable("Best away records"+scopeNote(comp, season)+":", recs, limit), nil
		case "best_overall", "best_record":
			recs := db.BestRecords(comp, season, "all", minPlayed, limit)
			return soccer.FormatTeamRecordsTable("Best overall records"+scopeNote(comp, season)+":", recs, limit), nil
		case "top_scoring", "top_scorers", "most_goals":
			recs := db.TopScoringTeams(comp, season, limit)
			return soccer.FormatTeamRecordsTable("Top scoring teams"+scopeNote(comp, season)+":", recs, limit), nil
		default:
			return "", fmt.Errorf("unknown metric %q; valid: summary, biggest_wins, best_home, best_away, best_overall, top_scoring", metric)
		}
	}
}

func handleListCompetitions(db *soccer.DB) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		comps := db.Competitions()
		var b strings.Builder
		fmt.Fprintf(&b, "Dataset coverage (%d matches, %d players):\n", len(db.Matches), len(db.Players))
		for _, c := range comps {
			if c.MinSeason == 0 {
				fmt.Fprintf(&b, "- %s: %d matches\n", c.Name, c.Matches)
				continue
			}
			fmt.Fprintf(&b, "- %s: %d matches (seasons %d–%d)\n", c.Name, c.Matches, c.MinSeason, c.MaxSeason)
		}
		return strings.TrimRight(b.String(), "\n"), nil
	}
}

// scopeNote renders a short " (2019 Brasileirão Série A)" suffix for titles.
func scopeNote(competition string, season int) string {
	var parts []string
	if season != 0 {
		parts = append(parts, fmt.Sprintf("%d", season))
	}
	if competition != "" {
		parts = append(parts, soccer.CompetitionName(competition))
	}
	if len(parts) == 0 {
		return ""
	}
	return " (" + strings.Join(parts, " ") + ")"
}

// --- JSON Schema helpers ---

func schema(props map[string]any, required []string) map[string]any {
	s := map[string]any{
		"type":       "object",
		"properties": props,
	}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

func strProp(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}
func intProp(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}
