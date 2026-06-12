// Context: Brazilian Soccer MCP Server.
// File: tools.go
// Purpose: Defines the MCP tools exposed to the LLM and the Handler that
// dispatches a tool call (name + arguments) to the query engine, returning a
// formatted, human-readable answer. Argument coercion tolerates the JSON
// number/string forms an MCP client may send.
package mcpserver

import (
	"fmt"

	"brazilian-soccer-mcp/internal/soccer"
)

// Tool is the metadata advertised for an MCP tool via tools/list.
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

// Handler dispatches tool calls against a loaded soccer database.
type Handler struct {
	DB *soccer.DB
}

// NewHandler creates a Handler over the given database.
func NewHandler(db *soccer.DB) *Handler { return &Handler{DB: db} }

func obj(props map[string]any, required ...string) map[string]any {
	schema := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}

func str(desc string) map[string]any { return map[string]any{"type": "string", "description": desc} }
func num(desc string) map[string]any { return map[string]any{"type": "integer", "description": desc} }

// Tools returns the list of MCP tools advertised by this server.
func Tools() []Tool {
	return []Tool{
		{
			Name:        "search_matches",
			Description: "Search Brazilian soccer matches by team, opponent, competition (Brasileirão, Copa do Brasil, Copa Libertadores), season, or date range. Returns matches with dates and scores.",
			InputSchema: obj(map[string]any{
				"team":        str("Team name (matches home or away). Partial names and accents are tolerated."),
				"opponent":    str("Restrict to matches against this opponent."),
				"competition": str("Competition name filter."),
				"season":      num("Season year, e.g. 2023."),
				"from":        str("Inclusive start date (YYYY-MM-DD)."),
				"to":          str("Inclusive end date (YYYY-MM-DD)."),
				"limit":       num("Maximum matches to return (default 30)."),
			}),
		},
		{
			Name:        "head_to_head",
			Description: "Compute the all-time head-to-head record between two teams (wins, draws, goals) across all competitions in the dataset.",
			InputSchema: obj(map[string]any{
				"team_a": str("First team."),
				"team_b": str("Second team."),
			}, "team_a", "team_b"),
		},
		{
			Name:        "team_record",
			Description: "Compute a team's win/draw/loss record, goals for/against and win rate, optionally filtered by season, competition and venue (home/away/any).",
			InputSchema: obj(map[string]any{
				"team":        str("Team name."),
				"season":      num("Season year filter."),
				"competition": str("Competition filter."),
				"venue":       map[string]any{"type": "string", "enum": []string{"any", "home", "away"}, "description": "Restrict to home or away matches."},
			}, "team"),
		},
		{
			Name:        "standings",
			Description: "Compute the league table for a season and competition from match results, sorted by points, goal difference and goals scored.",
			InputSchema: obj(map[string]any{
				"season":      num("Season year, e.g. 2019."),
				"competition": str("Competition (default Brasileirão)."),
			}, "season"),
		},
		{
			Name:        "search_players",
			Description: "Search the FIFA player database by name, nationality (e.g. Brazil), club, or position, with an optional minimum overall rating. Results are sorted by overall rating descending.",
			InputSchema: obj(map[string]any{
				"name":        str("Player name (partial match)."),
				"nationality": str("Nationality filter, e.g. Brazil."),
				"club":        str("Club filter."),
				"position":    str("Position code, e.g. ST, GK, LW."),
				"min_overall": num("Minimum FIFA overall rating."),
				"limit":       num("Maximum players to return (default 20)."),
			}),
		},
		{
			Name:        "match_statistics",
			Description: "Aggregate statistics for a set of matches: average goals per match, home win rate, and the biggest victories. Filterable by team, competition and season.",
			InputSchema: obj(map[string]any{
				"team":        str("Optional team filter."),
				"competition": str("Optional competition filter."),
				"season":      num("Optional season filter."),
			}),
		},
	}
}

// Call dispatches a tool invocation and returns the formatted answer text.
func (h *Handler) Call(name string, args map[string]any) (string, error) {
	switch name {
	case "search_matches":
		return h.searchMatches(args)
	case "head_to_head":
		return h.headToHead(args)
	case "team_record":
		return h.teamRecord(args)
	case "standings":
		return h.standings(args)
	case "search_players":
		return h.searchPlayers(args)
	case "match_statistics":
		return h.matchStatistics(args)
	default:
		return "", fmt.Errorf("unknown tool %q", name)
	}
}

// --- argument coercion helpers ---

func argString(args map[string]any, key string) string {
	if args == nil {
		return ""
	}
	switch v := args[key].(type) {
	case string:
		return v
	case fmt.Stringer:
		return v.String()
	default:
		return ""
	}
}

func argInt(args map[string]any, key string) int {
	if args == nil {
		return 0
	}
	switch v := args[key].(type) {
	case float64:
		return int(v)
	case int:
		return v
	case string:
		return soccer.Atoi(v)
	default:
		return 0
	}
}

func requireString(args map[string]any, key string) (string, error) {
	s := argString(args, key)
	if s == "" {
		return "", fmt.Errorf("missing required argument %q", key)
	}
	return s, nil
}
