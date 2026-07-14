// Context:
//   - Project: Brazilian Soccer MCP Server (see TASK.md).
//   - Role of this file: define the soccer query tools exposed over MCP, their
//     JSON input schemas, and the handlers that bridge tools/call into the
//     query.Engine. It also wires the lifecycle methods (initialize,
//     notifications/initialized, ping, tools/list, tools/call).
//   - The set of tools covers every capability category in the spec: match
//     queries, team queries, player queries, competition queries, and
//     statistical analysis.
package mcp

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/query"
)

// Tool is the public description of an MCP tool.
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

// toolEntry binds a Tool's metadata to its execution function.
type toolEntry struct {
	tool Tool
	run  func(args map[string]any) (string, error)
}

// SoccerServer wires a query.Engine to an MCP Server.
type SoccerServer struct {
	engine *query.Engine
	srv    *Server
	tools  []toolEntry
	byName map[string]toolEntry
}

// NewSoccerServer constructs the MCP server with all soccer tools registered.
func NewSoccerServer(engine *query.Engine, srv *Server) *SoccerServer {
	s := &SoccerServer{
		engine: engine,
		srv:    srv,
		byName: map[string]toolEntry{},
	}
	s.registerTools()
	s.registerMethods()
	return s
}

func obj(props map[string]any, required ...string) map[string]any {
	schema := map[string]any{
		"type":       "object",
		"properties": props,
	}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}

func strProp(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}
func intProp(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}

func (s *SoccerServer) add(t Tool, run func(map[string]any) (string, error)) {
	e := toolEntry{tool: t, run: run}
	s.tools = append(s.tools, e)
	s.byName[t.Name] = e
}

func (s *SoccerServer) registerTools() {
	s.add(Tool{
		Name: "search_matches",
		Description: "Search soccer matches by team, opponent, competition, season, venue, " +
			"and/or date range across all datasets (Brasileirão, Copa do Brasil, Libertadores). " +
			"Returns matches most recent first.",
		InputSchema: obj(map[string]any{
			"team":        strProp("Team name (matches home or away). Name variants are normalized, e.g. 'Flamengo' matches 'Flamengo-RJ'."),
			"opponent":    strProp("Restrict to matches against this opponent (used with team)."),
			"competition": strProp("Competition filter: 'Brasileirão'/'Serie A', 'Copa do Brasil', or 'Libertadores'."),
			"season":      intProp("Season year, e.g. 2023."),
			"venue":       strProp("'home', 'away', or 'all' (default)."),
			"start_date":  strProp("Earliest match date (YYYY-MM-DD)."),
			"end_date":    strProp("Latest match date (YYYY-MM-DD)."),
			"limit":       intProp("Maximum matches to return (default 20)."),
		}),
	}, s.runSearchMatches)

	s.add(Tool{
		Name:        "head_to_head",
		Description: "Compute the all-time head-to-head record between two teams across all competitions.",
		InputSchema: obj(map[string]any{
			"team_a": strProp("First team."),
			"team_b": strProp("Second team."),
			"limit":  intProp("Maximum recent matches to list (default 20)."),
		}, "team_a", "team_b"),
	}, s.runHeadToHead)

	s.add(Tool{
		Name: "team_stats",
		Description: "Aggregate a team's record (played, wins, draws, losses, goals for/against, " +
			"points, win rate), optionally filtered by season, competition and venue.",
		InputSchema: obj(map[string]any{
			"team":        strProp("Team name."),
			"season":      intProp("Season year filter."),
			"competition": strProp("Competition filter."),
			"venue":       strProp("'home', 'away', or 'all' (default)."),
		}, "team"),
	}, s.runTeamStats)

	s.add(Tool{
		Name:        "standings",
		Description: "Compute the league table for a competition and season from match results (points, W/D/L, goal difference).",
		InputSchema: obj(map[string]any{
			"competition": strProp("Competition, e.g. 'Brasileirão' or 'Libertadores'. Defaults to Brasileirão Série A."),
			"season":      intProp("Season year, e.g. 2019."),
			"limit":       intProp("Maximum teams to list (default all)."),
		}, "season"),
	}, s.runStandings)

	s.add(Tool{
		Name: "competition_stats",
		Description: "Aggregate statistics for a competition/season: match count, average goals per game, " +
			"home/away/draw rates, and the biggest-margin victories.",
		InputSchema: obj(map[string]any{
			"competition": strProp("Competition filter (optional; omit for all data)."),
			"season":      intProp("Season year filter (optional)."),
			"top_wins":    intProp("How many biggest victories to include (default 5)."),
		}),
	}, s.runCompetitionStats)

	s.add(Tool{
		Name: "search_players",
		Description: "Search the FIFA player database by name, nationality (e.g. 'Brazil'), club, " +
			"and/or position, with an optional minimum overall rating. Sorted by overall rating.",
		InputSchema: obj(map[string]any{
			"name":        strProp("Substring of the player's name."),
			"nationality": strProp("Nationality filter, e.g. 'Brazil'."),
			"club":        strProp("Club name substring, e.g. 'Flamengo'."),
			"position":    strProp("Position code, e.g. 'ST', 'GK', 'CB'."),
			"min_overall": intProp("Minimum FIFA overall rating."),
			"limit":       intProp("Maximum players to return (default 20)."),
		}),
	}, s.runSearchPlayers)

	s.add(Tool{
		Name:        "list_competitions",
		Description: "List the distinct competitions available in the loaded datasets.",
		InputSchema: obj(map[string]any{}),
	}, s.runListCompetitions)
}

func (s *SoccerServer) registerMethods() {
	s.srv.Handle("initialize", s.handleInitialize)
	s.srv.Handle("notifications/initialized", func(json.RawMessage) (interface{}, *RPCError) { return nil, nil })
	s.srv.Handle("ping", func(json.RawMessage) (interface{}, *RPCError) { return map[string]any{}, nil })
	s.srv.Handle("tools/list", s.handleToolsList)
	s.srv.Handle("tools/call", s.handleToolsCall)
}

func (s *SoccerServer) handleInitialize(json.RawMessage) (interface{}, *RPCError) {
	return map[string]any{
		"protocolVersion": protocolVersion,
		"capabilities": map[string]any{
			"tools": map[string]any{},
		},
		"serverInfo": map[string]any{
			"name":    "brazilian-soccer-mcp",
			"version": "1.0.0",
		},
	}, nil
}

func (s *SoccerServer) handleToolsList(json.RawMessage) (interface{}, *RPCError) {
	tools := make([]Tool, 0, len(s.tools))
	for _, e := range s.tools {
		tools = append(tools, e.tool)
	}
	return map[string]any{"tools": tools}, nil
}

// callParams is the shape of tools/call params.
type callParams struct {
	Name      string         `json:"name"`
	Arguments map[string]any `json:"arguments"`
}

func (s *SoccerServer) handleToolsCall(params json.RawMessage) (interface{}, *RPCError) {
	var p callParams
	if err := json.Unmarshal(params, &p); err != nil {
		return nil, &RPCError{Code: codeInvalidParams, Message: "invalid params: " + err.Error()}
	}
	entry, ok := s.byName[p.Name]
	if !ok {
		return nil, &RPCError{Code: codeMethodNotFound, Message: "unknown tool: " + p.Name}
	}
	if p.Arguments == nil {
		p.Arguments = map[string]any{}
	}
	text, err := entry.run(p.Arguments)
	if err != nil {
		// Tool execution errors are reported as tool results with isError=true,
		// per MCP conventions, rather than protocol errors.
		return toolResult(fmt.Sprintf("Error: %v", err), true), nil
	}
	return toolResult(text, false), nil
}

// toolResult builds an MCP tools/call result with a single text content block.
func toolResult(text string, isErr bool) map[string]any {
	return map[string]any{
		"content": []map[string]any{
			{"type": "text", "text": text},
		},
		"isError": isErr,
	}
}

// --- argument helpers -------------------------------------------------------

func argStr(args map[string]any, key string) string {
	if v, ok := args[key]; ok {
		if s, ok := v.(string); ok {
			return strings.TrimSpace(s)
		}
		return strings.TrimSpace(fmt.Sprintf("%v", v))
	}
	return ""
}

func argInt(args map[string]any, key string) int {
	v, ok := args[key]
	if !ok {
		return 0
	}
	switch n := v.(type) {
	case float64:
		return int(n)
	case int:
		return n
	case json.Number:
		i, _ := n.Int64()
		return int(i)
	case string:
		var i int
		fmt.Sscanf(strings.TrimSpace(n), "%d", &i)
		return i
	}
	return 0
}

func parseDateArg(s string) (time.Time, bool) {
	if s == "" {
		return time.Time{}, false
	}
	for _, f := range []string{"2006-01-02", "2006-01-02 15:04:05", "02/01/2006"} {
		if t, err := time.Parse(f, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

func limitOrDefault(n, def int) int {
	if n <= 0 {
		return def
	}
	return n
}

// --- tool handlers ----------------------------------------------------------

func (s *SoccerServer) runSearchMatches(args map[string]any) (string, error) {
	f := query.MatchFilter{
		Team:        argStr(args, "team"),
		Opponent:    argStr(args, "opponent"),
		Competition: argStr(args, "competition"),
		Season:      argInt(args, "season"),
		Venue:       argStr(args, "venue"),
		Limit:       limitOrDefault(argInt(args, "limit"), 20),
	}
	if t, ok := parseDateArg(argStr(args, "start_date")); ok {
		f.StartDate = t
	}
	if t, ok := parseDateArg(argStr(args, "end_date")); ok {
		f.EndDate = t
	}
	matches := s.engine.SearchMatches(f)
	title := "Matches"
	if f.Team != "" && f.Opponent != "" {
		title = fmt.Sprintf("%s vs %s matches:", f.Team, f.Opponent)
	} else if f.Team != "" {
		title = fmt.Sprintf("%s matches:", f.Team)
	}
	return query.FormatMatches(title, matches, f.Limit), nil
}

func (s *SoccerServer) runHeadToHead(args map[string]any) (string, error) {
	a, b := argStr(args, "team_a"), argStr(args, "team_b")
	if a == "" || b == "" {
		return "", fmt.Errorf("both team_a and team_b are required")
	}
	limit := limitOrDefault(argInt(args, "limit"), 20)
	h := s.engine.HeadToHead(a, b)
	return h.Format(limit), nil
}

func (s *SoccerServer) runTeamStats(args map[string]any) (string, error) {
	team := argStr(args, "team")
	if team == "" {
		return "", fmt.Errorf("team is required")
	}
	st := s.engine.TeamStats(team, argInt(args, "season"), argStr(args, "competition"), argStr(args, "venue"))
	return st.Format(), nil
}

func (s *SoccerServer) runStandings(args map[string]any) (string, error) {
	season := argInt(args, "season")
	if season == 0 {
		return "", fmt.Errorf("season is required")
	}
	comp := argStr(args, "competition")
	if comp == "" {
		comp = "Brasileirão"
	}
	table := s.engine.Standings(comp, season)
	// Use the canonical competition label from the first row when available.
	label := comp
	if len(table) > 0 && table[0].Competition != "" {
		label = table[0].Competition
	}
	return query.FormatStandings(label, season, table, argInt(args, "limit")), nil
}

func (s *SoccerServer) runCompetitionStats(args map[string]any) (string, error) {
	cs := s.engine.CompetitionStats(argStr(args, "competition"), argInt(args, "season"), argInt(args, "top_wins"))
	return cs.Format(), nil
}

func (s *SoccerServer) runSearchPlayers(args map[string]any) (string, error) {
	f := query.PlayerFilter{
		Name:        argStr(args, "name"),
		Nationality: argStr(args, "nationality"),
		Club:        argStr(args, "club"),
		Position:    argStr(args, "position"),
		MinOverall:  argInt(args, "min_overall"),
		Limit:       limitOrDefault(argInt(args, "limit"), 20),
	}
	players := s.engine.SearchPlayers(f)
	var title string
	switch {
	case f.Name != "":
		title = fmt.Sprintf("Players matching %q:", f.Name)
	case f.Club != "":
		title = fmt.Sprintf("Players at %s:", f.Club)
	case f.Nationality != "":
		title = fmt.Sprintf("%s players:", f.Nationality)
	default:
		title = "Players:"
	}
	return query.FormatPlayers(title, players, f.Limit), nil
}

func (s *SoccerServer) runListCompetitions(args map[string]any) (string, error) {
	comps := s.engine.Competitions()
	var b strings.Builder
	b.WriteString("Available competitions:\n")
	for _, c := range comps {
		fmt.Fprintf(&b, "- %s\n", c)
	}
	return b.String(), nil
}
