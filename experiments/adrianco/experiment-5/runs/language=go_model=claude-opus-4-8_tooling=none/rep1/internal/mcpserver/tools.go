// Context:
//   - This file declares every MCP tool the server exposes and connects it to
//     the soccer query layer. Each tool has a JSON Schema describing its
//     arguments (used by the LLM to call it) and a handler that parses those
//     arguments, runs the query and returns formatted text.
//   - The tools cover the five capability areas in the specification: match
//     search, team statistics & head-to-head, player search, competition
//     standings, and statistical aggregates.
//   - Argument parsing is defensive: it accepts numbers supplied either as JSON
//     numbers or numeric strings, since LLM clients are inconsistent about this.
package mcpserver

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// toolDef is a single registered tool.
type toolDef struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(*soccer.Store, map[string]any) (string, error)
}

// schema helpers -----------------------------------------------------------

func obj(props map[string]any, required ...string) map[string]any {
	m := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		m["required"] = required
	}
	return m
}

func strProp(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}
func intProp(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}

// argument extraction ------------------------------------------------------

func argStr(args map[string]any, key string) string {
	if v, ok := args[key]; ok && v != nil {
		return strings.TrimSpace(fmt.Sprintf("%v", v))
	}
	return ""
}

func argInt(args map[string]any, key string) int {
	v, ok := args[key]
	if !ok || v == nil {
		return 0
	}
	switch n := v.(type) {
	case float64:
		return int(n)
	case int:
		return n
	case string:
		i, _ := strconv.Atoi(strings.TrimSpace(n))
		return i
	default:
		return 0
	}
}

func argDate(args map[string]any, key string) time.Time {
	s := argStr(args, key)
	if s == "" {
		return time.Time{}
	}
	for _, layout := range []string{"2006-01-02", "02/01/2006", "2006-01-02 15:04:05"} {
		if t, err := time.Parse(layout, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

// limitOr returns the requested limit or a default when unset.
func limitOr(args map[string]any, def int) int {
	if n := argInt(args, "limit"); n > 0 {
		return n
	}
	return def
}

// buildTools registers the full tool set.
func (s *Server) buildTools() []toolDef {
	return []toolDef{
		{
			Name:        "search_matches",
			Description: "Search soccer matches by team, opponent, competition, season, venue and/or date range. Returns a dated list of results with scores and competition.",
			InputSchema: obj(map[string]any{
				"team":        strProp("Team name (matches home or away side). Suffix/accents optional, e.g. 'Flamengo'."),
				"opponent":    strProp("Optional opponent team; restricts to games between team and opponent."),
				"competition": strProp("Competition filter: 'Brasileirão'/'Serie A', 'Serie B', 'Serie C', 'Copa do Brasil', 'Libertadores'."),
				"season":      intProp("Season/year, e.g. 2019."),
				"venue":       strProp("Restrict to 'home' or 'away' relative to team."),
				"date_from":   strProp("Earliest match date (YYYY-MM-DD)."),
				"date_to":     strProp("Latest match date (YYYY-MM-DD)."),
				"limit":       intProp("Maximum matches to return (default 25)."),
			}),
			Handler: handleSearchMatches,
		},
		{
			Name:        "head_to_head",
			Description: "Compute the all-time head-to-head record (wins/draws/losses and goals) between two teams, with the list of matches.",
			InputSchema: obj(map[string]any{
				"team1": strProp("First team."),
				"team2": strProp("Second team."),
				"limit": intProp("Max matches to list (default 20)."),
			}, "team1", "team2"),
			Handler: handleHeadToHead,
		},
		{
			Name:        "team_stats",
			Description: "Compute a team's record (matches, wins, draws, losses, goals for/against, points, win rate), optionally filtered by season, competition and venue.",
			InputSchema: obj(map[string]any{
				"team":        strProp("Team name."),
				"season":      intProp("Season/year filter."),
				"competition": strProp("Competition filter."),
				"venue":       strProp("'home' or 'away' to restrict the record."),
			}, "team"),
			Handler: handleTeamStats,
		},
		{
			Name:        "search_players",
			Description: "Search the FIFA player database by name, nationality (e.g. 'Brazil'), club, position and/or minimum overall rating. Sorted by rating.",
			InputSchema: obj(map[string]any{
				"name":        strProp("Player name substring."),
				"nationality": strProp("Nationality, e.g. 'Brazil'."),
				"club":        strProp("Club name substring, e.g. 'Flamengo'."),
				"position":    strProp("Position code, e.g. 'ST', 'GK', 'CB'."),
				"min_overall": intProp("Minimum FIFA overall rating."),
				"limit":       intProp("Maximum players to return (default 25)."),
			}),
			Handler: handleSearchPlayers,
		},
		{
			Name:        "competition_standings",
			Description: "Compute the final league table for a competition and season from match results (points, W/D/L, goal difference).",
			InputSchema: obj(map[string]any{
				"competition": strProp("Competition, e.g. 'Brasileirão Série A'."),
				"season":      intProp("Season/year, e.g. 2019."),
				"limit":       intProp("Max table rows to show (default: all)."),
			}, "season"),
			Handler: handleStandings,
		},
		{
			Name:        "competition_stats",
			Description: "Aggregate statistics for a competition (optionally a season): match count, average goals per match, home win rate and the biggest wins.",
			InputSchema: obj(map[string]any{
				"competition": strProp("Competition filter (optional; omit for all)."),
				"season":      intProp("Season/year filter (optional)."),
				"limit":       intProp("How many biggest wins to list (default 10)."),
			}),
			Handler: handleCompetitionStats,
		},
		{
			Name:        "list_competitions",
			Description: "List the competitions available in the loaded dataset and the total number of matches and players.",
			InputSchema: obj(map[string]any{}),
			Handler:     handleListCompetitions,
		},
	}
}

// handlers -----------------------------------------------------------------

func handleSearchMatches(store *soccer.Store, args map[string]any) (string, error) {
	q := soccer.MatchQuery{
		Team:        argStr(args, "team"),
		Opponent:    argStr(args, "opponent"),
		Competition: argStr(args, "competition"),
		Season:      argInt(args, "season"),
		Venue:       argStr(args, "venue"),
		From:        argDate(args, "date_from"),
		To:          argDate(args, "date_to"),
		Limit:       limitOr(args, 25),
	}
	matches := store.SearchMatches(q)
	title := "Matches"
	if q.Team != "" && q.Opponent != "" {
		title = fmt.Sprintf("%s vs %s matches", q.Team, q.Opponent)
	} else if q.Team != "" {
		title = q.Team + " matches"
	}
	return soccer.FormatMatches(title+":", matches, q.Limit), nil
}

func handleHeadToHead(store *soccer.Store, args map[string]any) (string, error) {
	t1 := argStr(args, "team1")
	t2 := argStr(args, "team2")
	if t1 == "" || t2 == "" {
		return "", fmt.Errorf("both team1 and team2 are required")
	}
	h := store.HeadToHead(t1, t2)
	return h.Format(limitOr(args, 20)), nil
}

func handleTeamStats(store *soccer.Store, args map[string]any) (string, error) {
	team := argStr(args, "team")
	if team == "" {
		return "", fmt.Errorf("team is required")
	}
	rec := store.TeamStats(team, argInt(args, "season"), argStr(args, "competition"), argStr(args, "venue"))
	if rec.Played == 0 {
		return fmt.Sprintf("No matches found for %q with the given filters.", team), nil
	}
	return rec.Format(), nil
}

func handleSearchPlayers(store *soccer.Store, args map[string]any) (string, error) {
	q := soccer.PlayerQuery{
		Name:        argStr(args, "name"),
		Nationality: argStr(args, "nationality"),
		Club:        argStr(args, "club"),
		Position:    argStr(args, "position"),
		MinOverall:  argInt(args, "min_overall"),
		Limit:       limitOr(args, 25),
	}
	players := store.SearchPlayers(q)
	return soccer.FormatPlayers("Players:", players, q.Limit), nil
}

func handleStandings(store *soccer.Store, args map[string]any) (string, error) {
	season := argInt(args, "season")
	if season == 0 {
		return "", fmt.Errorf("season is required")
	}
	comp := argStr(args, "competition")
	if comp == "" {
		comp = soccer.CompSerieA
	}
	table := store.Standings(comp, season)
	return soccer.FormatStandings(comp, season, table, argInt(args, "limit")), nil
}

func handleCompetitionStats(store *soccer.Store, args map[string]any) (string, error) {
	stats := store.LeagueAggregate(argStr(args, "competition"), argInt(args, "season"), limitOr(args, 10))
	if stats.Matches == 0 {
		return "No matches found for the given competition/season.", nil
	}
	return stats.Format(), nil
}

func handleListCompetitions(store *soccer.Store, args map[string]any) (string, error) {
	var b strings.Builder
	b.WriteString("Available competitions:\n")
	for _, c := range store.Competitions() {
		b.WriteString("- " + c + "\n")
	}
	fmt.Fprintf(&b, "\nLoaded: %d matches, %d players.", len(store.Matches), len(store.Players))
	return b.String(), nil
}
