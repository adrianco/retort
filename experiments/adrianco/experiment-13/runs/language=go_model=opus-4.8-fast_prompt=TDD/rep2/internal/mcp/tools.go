package mcp

import (
	"fmt"
	"strings"

	"brazilian-soccer-mcp/internal/soccer"
)

// toolArgs is the union of all arguments accepted by the tools. Each tool
// reads only the fields relevant to it; unset fields are ignored.
type toolArgs struct {
	// Match / team filters.
	Team        string `json:"team"`
	Opponent    string `json:"opponent"`
	HomeTeam    string `json:"home_team"`
	AwayTeam    string `json:"away_team"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	SeasonFrom  int    `json:"season_from"`
	SeasonTo    int    `json:"season_to"`
	DateFrom    string `json:"date_from"`
	DateTo      string `json:"date_to"`
	HomeOnly    bool   `json:"home_only"`
	AwayOnly    bool   `json:"away_only"`
	Limit       int    `json:"limit"`

	// Player filters.
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	MinOverall  int    `json:"min_overall"`

	// Head-to-head.
	Team1 string `json:"team1"`
	Team2 string `json:"team2"`
}

// schema is a tiny helper for building JSON-schema property maps.
type schema = map[string]any

func strProp(desc string) schema { return schema{"type": "string", "description": desc} }
func intProp(desc string) schema { return schema{"type": "integer", "description": desc} }

func objectSchema(props schema, required ...string) schema {
	s := schema{"type": "object", "properties": props}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

// toolDefinitions returns the MCP tool descriptors advertised by tools/list.
func toolDefinitions() []schema {
	return []schema{
		{
			"name":        "search_matches",
			"description": "Search Brazilian soccer matches by team, opponent, home/away side, competition (Brasileirão, Copa do Brasil, Libertadores), season, or date range. Returns matches most-recent first.",
			"inputSchema": objectSchema(schema{
				"team":        strProp("Team involved on either side (e.g. 'Flamengo')"),
				"opponent":    strProp("Restrict to fixtures against this opponent"),
				"home_team":   strProp("Match only when this team played at home"),
				"away_team":   strProp("Match only when this team played away"),
				"competition": strProp("Competition name: Brasileirão, Copa do Brasil, or Libertadores"),
				"season":      intProp("Season year, e.g. 2019"),
				"season_from": intProp("Earliest season (inclusive)"),
				"season_to":   intProp("Latest season (inclusive)"),
				"date_from":   strProp("Earliest date YYYY-MM-DD (inclusive)"),
				"date_to":     strProp("Latest date YYYY-MM-DD (inclusive)"),
				"limit":       intProp("Maximum matches to return (default 25)"),
			}),
		},
		{
			"name":        "head_to_head",
			"description": "Head-to-head record and match list between two teams across all competitions.",
			"inputSchema": objectSchema(schema{
				"team1": strProp("First team"),
				"team2": strProp("Second team"),
				"limit": intProp("Maximum matches to list (default 25)"),
			}, "team1", "team2"),
		},
		{
			"name":        "team_record",
			"description": "Win/draw/loss record, goals for/against and points for a team, optionally filtered by competition, season, and home/away.",
			"inputSchema": objectSchema(schema{
				"team":        strProp("Team name"),
				"competition": strProp("Optional competition filter"),
				"season":      intProp("Optional season filter"),
				"home_only":   schema{"type": "boolean", "description": "Only count home matches"},
				"away_only":   schema{"type": "boolean", "description": "Only count away matches"},
			}, "team"),
		},
		{
			"name":        "search_players",
			"description": "Search FIFA player data by name, nationality (e.g. Brazil), club, position, and minimum overall rating. Sorted by overall rating descending.",
			"inputSchema": objectSchema(schema{
				"name":        strProp("Substring of the player name"),
				"nationality": strProp("Nationality, e.g. 'Brazil'"),
				"club":        strProp("Club name"),
				"position":    strProp("Position code, e.g. ST, GK, CDM"),
				"min_overall": intProp("Minimum FIFA overall rating"),
				"limit":       intProp("Maximum players to return (default 25)"),
			}),
		},
		{
			"name":        "standings",
			"description": "League table for a competition and season, calculated from match results (points, W/D/L, goals).",
			"inputSchema": objectSchema(schema{
				"competition": strProp("Competition name, e.g. Brasileirão"),
				"season":      intProp("Season year, e.g. 2019"),
			}, "competition", "season"),
		},
		{
			"name":        "competition_stats",
			"description": "Aggregate statistics (average goals per match, home/away/draw rates, biggest victories) for a competition, optionally a single season.",
			"inputSchema": objectSchema(schema{
				"competition": strProp("Competition name"),
				"season":      intProp("Optional season year"),
				"limit":       intProp("Number of biggest victories to list (default 5)"),
			}),
		},
	}
}

// limitOr returns the requested limit or def when limit is non-positive.
func limitOr(limit, def int) int {
	if limit <= 0 {
		return def
	}
	return limit
}

func (s *Server) toolSearchMatches(a toolArgs) (string, error) {
	f := soccer.MatchFilter{
		Team:        a.Team,
		Opponent:    a.Opponent,
		HomeTeam:    a.HomeTeam,
		AwayTeam:    a.AwayTeam,
		Competition: a.Competition,
		Season:      a.Season,
		SeasonFrom:  a.SeasonFrom,
		SeasonTo:    a.SeasonTo,
		Limit:       limitOr(a.Limit, 25),
	}
	if a.DateFrom != "" {
		if t, ok := soccer.ParseDate(a.DateFrom); ok {
			f.DateFrom = t
		} else {
			return "", fmt.Errorf("invalid date_from: %q", a.DateFrom)
		}
	}
	if a.DateTo != "" {
		if t, ok := soccer.ParseDate(a.DateTo); ok {
			f.DateTo = t
		} else {
			return "", fmt.Errorf("invalid date_to: %q", a.DateTo)
		}
	}
	matches := s.kb.SearchMatches(f)
	if len(matches) == 0 {
		return "No matches found for the given criteria.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d match(es):\n", len(matches))
	writeMatchList(&b, matches)
	return b.String(), nil
}

func (s *Server) toolHeadToHead(a toolArgs) (string, error) {
	if a.Team1 == "" || a.Team2 == "" {
		return "", fmt.Errorf("team1 and team2 are required")
	}
	h := s.kb.HeadToHead(a.Team1, a.Team2)
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s — head-to-head\n", a.Team1, a.Team2)
	fmt.Fprintf(&b, "Matches in dataset: %d\n", len(h.Matches))
	fmt.Fprintf(&b, "%s wins: %d, %s wins: %d, Draws: %d\n",
		a.Team1, h.Team1Wins, a.Team2, h.Team2Wins, h.Draws)
	if len(h.Matches) > 0 {
		b.WriteString("\nRecent meetings:\n")
		writeMatchList(&b, capMatches(h.Matches, limitOr(a.Limit, 25)))
	}
	return b.String(), nil
}

func (s *Server) toolTeamRecord(a toolArgs) (string, error) {
	if a.Team == "" {
		return "", fmt.Errorf("team is required")
	}
	f := soccer.MatchFilter{Competition: a.Competition, Season: a.Season}
	switch {
	case a.HomeOnly:
		f.HomeTeam = a.Team
	case a.AwayOnly:
		f.AwayTeam = a.Team
	default:
		f.Team = a.Team
	}
	rec := s.kb.TeamRecord(f)

	scope := a.Team
	if a.HomeOnly {
		scope += " (home)"
	} else if a.AwayOnly {
		scope += " (away)"
	}
	var qualifiers []string
	if a.Competition != "" {
		qualifiers = append(qualifiers, a.Competition)
	}
	if a.Season != 0 {
		qualifiers = append(qualifiers, fmt.Sprintf("%d", a.Season))
	}
	header := scope + " record"
	if len(qualifiers) > 0 {
		header += " (" + strings.Join(qualifiers, " ") + ")"
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n", header)
	fmt.Fprintf(&b, "- Matches: %d\n", rec.Matches)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", rec.Wins, rec.Draws, rec.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (diff %+d)\n", rec.GoalsFor, rec.GoalsAgainst, rec.GoalDiff())
	fmt.Fprintf(&b, "- Points: %d\n", rec.Points())
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", rec.WinRate())
	return b.String(), nil
}

func (s *Server) toolSearchPlayers(a toolArgs) (string, error) {
	f := soccer.PlayerFilter{
		Name:        a.Name,
		Nationality: a.Nationality,
		Club:        a.Club,
		Position:    a.Position,
		MinOverall:  a.MinOverall,
		Limit:       limitOr(a.Limit, 25),
	}
	players := s.kb.SearchPlayers(f)
	if len(players) == 0 {
		return "No players found for the given criteria.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d player(s):\n", len(players))
	for i, p := range players {
		fmt.Fprintf(&b, "%d. %s — Overall: %d, Position: %s, Club: %s, Nationality: %s",
			i+1, p.Name, p.Overall, dash(p.Position), dash(p.Club), dash(p.Nationality))
		if p.Age > 0 {
			fmt.Fprintf(&b, ", Age: %d", p.Age)
		}
		b.WriteString("\n")
	}
	return b.String(), nil
}

func (s *Server) toolStandings(a toolArgs) (string, error) {
	if a.Competition == "" || a.Season == 0 {
		return "", fmt.Errorf("competition and season are required")
	}
	table := s.kb.Standings(a.Competition, a.Season)
	if len(table) == 0 {
		return fmt.Sprintf("No standings available for %s %d.", a.Competition, a.Season), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d — Final Standings (calculated from matches):\n", a.Competition, a.Season)
	fmt.Fprintf(&b, "%-4s %-28s %4s %4s %3s %3s %3s %5s %5s\n", "Pos", "Team", "Pts", "P", "W", "D", "L", "GF", "GA")
	for i, r := range table {
		label := ""
		if i == 0 {
			label = "  ← Champion"
		}
		fmt.Fprintf(&b, "%-4d %-28s %4d %4d %3d %3d %3d %5d %5d%s\n",
			i+1, trunc(r.Team, 28), r.Points(), r.Matches, r.Wins, r.Draws, r.Losses,
			r.GoalsFor, r.GoalsAgainst, label)
	}
	return b.String(), nil
}

func (s *Server) toolCompetitionStats(a toolArgs) (string, error) {
	f := soccer.MatchFilter{Competition: a.Competition, Season: a.Season}
	cs := s.kb.CompetitionStats(f)
	if cs.Matches == 0 {
		return "No matches found for the given criteria.", nil
	}
	scope := "all competitions"
	if a.Competition != "" {
		scope = a.Competition
	}
	if a.Season != 0 {
		scope = fmt.Sprintf("%s %d", scope, a.Season)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Statistics for %s:\n", scope)
	fmt.Fprintf(&b, "- Matches: %d\n", cs.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", cs.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", cs.AvgGoals())
	fmt.Fprintf(&b, "- Home wins: %d (%.1f%%), Away wins: %d (%.1f%%), Draws: %d (%.1f%%)\n",
		cs.HomeWins, cs.HomeWinRate(),
		cs.AwayWins, pct(cs.AwayWins, cs.Matches),
		cs.Draws, pct(cs.Draws, cs.Matches))

	top := s.kb.BiggestWins(f, limitOr(a.Limit, 5))
	if len(top) > 0 {
		b.WriteString("\nBiggest victories:\n")
		for i, m := range top {
			fmt.Fprintf(&b, "%d. %s\n", i+1, formatMatch(m))
		}
	}
	return b.String(), nil
}

// pct returns 100*n/total, guarding against division by zero.
func pct(n, total int) float64 {
	if total == 0 {
		return 0
	}
	return 100 * float64(n) / float64(total)
}
