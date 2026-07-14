package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"strings"
)

// Minimal Model Context Protocol server implementation over stdio.
// Implements: initialize, tools/list, tools/call.

const (
	protocolVersion = "2024-11-05"
	serverName      = "brazilian-soccer-mcp"
	serverVersion   = "1.0.0"
)

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  interface{}     `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type toolInput struct {
	Type       string                 `json:"type"`
	Properties map[string]interface{} `json:"properties"`
	Required   []string               `json:"required,omitempty"`
}

type toolDef struct {
	Name        string    `json:"name"`
	Description string    `json:"description"`
	InputSchema toolInput `json:"inputSchema"`
}

type textContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type toolResult struct {
	Content []textContent `json:"content"`
	IsError bool          `json:"isError,omitempty"`
}

// MCPServer holds the data store and serves JSON-RPC requests.
type MCPServer struct {
	store *DataStore
}

func NewMCPServer(store *DataStore) *MCPServer {
	return &MCPServer{store: store}
}

// Serve reads JSON-RPC requests from in (one per line), writes responses to out.
func (s *MCPServer) Serve(in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024)
	for scanner.Scan() {
		line := scanner.Bytes()
		line = []byte(strings.TrimSpace(string(line)))
		if len(line) == 0 {
			continue
		}
		var req rpcRequest
		if err := json.Unmarshal(line, &req); err != nil {
			s.writeError(out, nil, -32700, "parse error: "+err.Error())
			continue
		}
		s.handle(out, req)
	}
	return scanner.Err()
}

func (s *MCPServer) writeError(out io.Writer, id json.RawMessage, code int, msg string) {
	resp := rpcResponse{
		JSONRPC: "2.0",
		ID:      id,
		Error:   &rpcError{Code: code, Message: msg},
	}
	_ = writeResp(out, resp)
}

func writeResp(out io.Writer, resp rpcResponse) error {
	b, err := json.Marshal(resp)
	if err != nil {
		return err
	}
	b = append(b, '\n')
	_, err = out.Write(b)
	return err
}

func (s *MCPServer) handle(out io.Writer, req rpcRequest) {
	// Notifications (no ID) get no response per JSON-RPC.
	isNotification := len(req.ID) == 0 || string(req.ID) == "null"

	switch req.Method {
	case "initialize":
		s.respond(out, req.ID, map[string]interface{}{
			"protocolVersion": protocolVersion,
			"capabilities": map[string]interface{}{
				"tools": map[string]interface{}{},
			},
			"serverInfo": map[string]interface{}{
				"name":    serverName,
				"version": serverVersion,
			},
		})
	case "notifications/initialized", "initialized":
		// nothing to send
	case "tools/list":
		s.respond(out, req.ID, map[string]interface{}{"tools": s.tools()})
	case "tools/call":
		s.handleToolCall(out, req)
	case "ping":
		s.respond(out, req.ID, map[string]interface{}{})
	default:
		if isNotification {
			return
		}
		s.writeError(out, req.ID, -32601, "method not found: "+req.Method)
	}
}

func (s *MCPServer) respond(out io.Writer, id json.RawMessage, result interface{}) {
	if len(id) == 0 {
		return
	}
	_ = writeResp(out, rpcResponse{JSONRPC: "2.0", ID: id, Result: result})
}

// --- Tool definitions ----------------------------------------------------

func (s *MCPServer) tools() []toolDef {
	strProp := func(desc string) map[string]interface{} {
		return map[string]interface{}{"type": "string", "description": desc}
	}
	intProp := func(desc string) map[string]interface{} {
		return map[string]interface{}{"type": "integer", "description": desc}
	}
	return []toolDef{
		{
			Name:        "find_matches",
			Description: "Find soccer matches. Filter by team(s), season, and competition. Returns newest first.",
			InputSchema: toolInput{
				Type: "object",
				Properties: map[string]interface{}{
					"team1":       strProp("Team name (matches home or away). Optional."),
					"team2":       strProp("Second team for head-to-head. Optional."),
					"season":      intProp("Year (e.g. 2023). Optional."),
					"competition": strProp("Competition substring (Brasileirão, Copa do Brasil, Libertadores). Optional."),
					"limit":       intProp("Max results. Default 20."),
				},
			},
		},
		{
			Name:        "team_stats",
			Description: "Aggregate a team's record (matches, wins, draws, losses, goals) optionally filtered by season and competition.",
			InputSchema: toolInput{
				Type: "object",
				Properties: map[string]interface{}{
					"team":        strProp("Team name."),
					"season":      intProp("Year. Optional."),
					"competition": strProp("Competition substring. Optional."),
				},
				Required: []string{"team"},
			},
		},
		{
			Name:        "head_to_head",
			Description: "Compare two teams head-to-head across all loaded match data.",
			InputSchema: toolInput{
				Type: "object",
				Properties: map[string]interface{}{
					"team1":       strProp("First team."),
					"team2":       strProp("Second team."),
					"season":      intProp("Year. Optional."),
					"competition": strProp("Competition substring. Optional."),
				},
				Required: []string{"team1", "team2"},
			},
		},
		{
			Name:        "standings",
			Description: "Calculate league standings for a competition and season from match results.",
			InputSchema: toolInput{
				Type: "object",
				Properties: map[string]interface{}{
					"competition": strProp("Competition substring (e.g. Brasileirão)."),
					"season":      intProp("Year (e.g. 2019)."),
					"limit":       intProp("Top N teams. Default 20."),
				},
				Required: []string{"competition", "season"},
			},
		},
		{
			Name:        "find_players",
			Description: "Search FIFA player data. Filter by name (substring), nationality, club, position, min overall rating.",
			InputSchema: toolInput{
				Type: "object",
				Properties: map[string]interface{}{
					"name":        strProp("Player name substring. Optional."),
					"nationality": strProp("Exact nationality, e.g. 'Brazil'. Optional."),
					"club":        strProp("Club name. Optional."),
					"position":    strProp("Position substring (e.g. 'ST', 'LW', 'GK'). Optional."),
					"min_overall": intProp("Minimum FIFA overall rating. Optional."),
					"limit":       intProp("Max results. Default 20."),
				},
			},
		},
		{
			Name:        "aggregate_stats",
			Description: "Aggregate statistics (total goals, avg goals/match, home win rate) over filtered match set.",
			InputSchema: toolInput{
				Type: "object",
				Properties: map[string]interface{}{
					"team":        strProp("Filter by team. Optional."),
					"season":      intProp("Filter by season. Optional."),
					"competition": strProp("Filter by competition. Optional."),
				},
			},
		},
		{
			Name:        "biggest_wins",
			Description: "List matches with the largest margin of victory.",
			InputSchema: toolInput{
				Type: "object",
				Properties: map[string]interface{}{
					"team":        strProp("Filter by team. Optional."),
					"competition": strProp("Filter by competition. Optional."),
					"season":      intProp("Filter by season. Optional."),
					"limit":       intProp("Default 10."),
				},
			},
		},
	}
}

// --- Tool dispatch -------------------------------------------------------

func (s *MCPServer) handleToolCall(out io.Writer, req rpcRequest) {
	var p struct {
		Name      string                 `json:"name"`
		Arguments map[string]interface{} `json:"arguments"`
	}
	if err := json.Unmarshal(req.Params, &p); err != nil {
		s.writeError(out, req.ID, -32602, "invalid params: "+err.Error())
		return
	}
	text, isErr := s.dispatch(p.Name, p.Arguments)
	s.respond(out, req.ID, toolResult{
		Content: []textContent{{Type: "text", Text: text}},
		IsError: isErr,
	})
}

func (s *MCPServer) dispatch(name string, args map[string]interface{}) (string, bool) {
	switch name {
	case "find_matches":
		return s.toolFindMatches(args), false
	case "team_stats":
		return s.toolTeamStats(args)
	case "head_to_head":
		return s.toolHeadToHead(args)
	case "standings":
		return s.toolStandings(args)
	case "find_players":
		return s.toolFindPlayers(args), false
	case "aggregate_stats":
		return s.toolAggregateStats(args), false
	case "biggest_wins":
		return s.toolBiggestWins(args), false
	default:
		return "unknown tool: " + name, true
	}
}

// --- Tool implementations -----------------------------------------------

func argString(args map[string]interface{}, key string) string {
	v, ok := args[key]
	if !ok || v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

func argInt(args map[string]interface{}, key string) int {
	v, ok := args[key]
	if !ok || v == nil {
		return 0
	}
	switch x := v.(type) {
	case float64:
		return int(x)
	case int:
		return x
	case string:
		return parseInt(x)
	}
	return 0
}

func (s *MCPServer) toolFindMatches(args map[string]interface{}) string {
	f := MatchFilter{
		Team1:       argString(args, "team1"),
		Team2:       argString(args, "team2"),
		Season:      argInt(args, "season"),
		Competition: argString(args, "competition"),
		Limit:       argInt(args, "limit"),
	}
	if f.Limit == 0 {
		f.Limit = 20
	}
	matches := s.store.FindMatches(f)
	return formatMatchList(matches, &f)
}

func (s *MCPServer) toolTeamStats(args map[string]interface{}) (string, bool) {
	team := argString(args, "team")
	if team == "" {
		return "team is required", true
	}
	f := MatchFilter{
		Team1:       team,
		Season:      argInt(args, "season"),
		Competition: argString(args, "competition"),
	}
	matches := s.store.FindMatches(f)
	stats := ComputeTeamStats(team, matches)
	return formatTeamStats(stats, f), false
}

func (s *MCPServer) toolHeadToHead(args map[string]interface{}) (string, bool) {
	t1 := argString(args, "team1")
	t2 := argString(args, "team2")
	if t1 == "" || t2 == "" {
		return "team1 and team2 are required", true
	}
	f := MatchFilter{
		Team1:       t1,
		Team2:       t2,
		Season:      argInt(args, "season"),
		Competition: argString(args, "competition"),
	}
	matches := s.store.FindMatches(f)
	h2h := ComputeHeadToHead(t1, t2, matches)
	return formatHeadToHead(h2h, matches), false
}

func (s *MCPServer) toolStandings(args map[string]interface{}) (string, bool) {
	comp := argString(args, "competition")
	season := argInt(args, "season")
	limit := argInt(args, "limit")
	if comp == "" || season == 0 {
		return "competition and season are required", true
	}
	if limit == 0 {
		limit = 20
	}
	rows := s.store.Standings(comp, season)
	if len(rows) > limit {
		rows = rows[:limit]
	}
	return formatStandings(rows, comp, season), false
}

func (s *MCPServer) toolFindPlayers(args map[string]interface{}) string {
	f := PlayerFilter{
		Name:        argString(args, "name"),
		Nationality: argString(args, "nationality"),
		Club:        argString(args, "club"),
		Position:    argString(args, "position"),
		MinOverall:  argInt(args, "min_overall"),
		Limit:       argInt(args, "limit"),
	}
	if f.Limit == 0 {
		f.Limit = 20
	}
	players := s.store.FindPlayers(f)
	return formatPlayers(players)
}

func (s *MCPServer) toolAggregateStats(args map[string]interface{}) string {
	f := MatchFilter{
		Team1:       argString(args, "team"),
		Season:      argInt(args, "season"),
		Competition: argString(args, "competition"),
	}
	matches := s.store.FindMatches(f)
	agg := ComputeAggregate(matches)
	return formatAggregate(agg)
}

func (s *MCPServer) toolBiggestWins(args map[string]interface{}) string {
	f := MatchFilter{
		Team1:       argString(args, "team"),
		Season:      argInt(args, "season"),
		Competition: argString(args, "competition"),
	}
	limit := argInt(args, "limit")
	if limit == 0 {
		limit = 10
	}
	matches := s.store.FindMatches(f)
	big := BiggestWins(matches, limit)
	return formatMatchList(big, nil)
}

// --- Formatting helpers -------------------------------------------------

func formatMatchList(matches []Match, f *MatchFilter) string {
	if len(matches) == 0 {
		return "No matches found."
	}
	var b strings.Builder
	if f != nil && f.Team1 != "" && f.Team2 != "" {
		fmt.Fprintf(&b, "%s vs %s — %d matches:\n", f.Team1, f.Team2, len(matches))
	} else {
		fmt.Fprintf(&b, "%d matches:\n", len(matches))
	}
	for _, m := range matches {
		date := "????-??-??"
		if !m.Date.IsZero() {
			date = m.Date.Format("2006-01-02")
		}
		round := m.Round
		if round != "" {
			round = " (Round " + round + ")"
		}
		fmt.Fprintf(&b, "- %s: %s %d-%d %s [%s%s]\n",
			date, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam,
			m.Competition, round)
	}
	return b.String()
}

func formatTeamStats(s TeamStats, f MatchFilter) string {
	if s.Matches == 0 {
		return "No matches found for " + s.Team + "."
	}
	var b strings.Builder
	header := s.Team
	if f.Season != 0 {
		header += fmt.Sprintf(" (%d)", f.Season)
	}
	if f.Competition != "" {
		header += " — " + f.Competition
	}
	fmt.Fprintf(&b, "%s record:\n", header)
	fmt.Fprintf(&b, "- Matches: %d\n", s.Matches)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", s.Wins, s.Draws, s.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (diff %+d)\n",
		s.GoalsFor, s.GoalsAgst, s.GoalsFor-s.GoalsAgst)
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", s.WinRate()*100)
	fmt.Fprintf(&b, "- Home: %dW %dD %dL | Away: %dW %dD %dL\n",
		s.HomeWins, s.HomeDraws, s.HomeLosses, s.AwayWins, s.AwayDraws, s.AwayLosses)
	fmt.Fprintf(&b, "- Points (3W/1D): %d\n", s.Points)
	return b.String()
}

func formatHeadToHead(h HeadToHead, matches []Match) string {
	if h.Matches == 0 {
		return fmt.Sprintf("No matches between %s and %s.", h.Team1, h.Team2)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s head-to-head:\n", h.Team1, h.Team2)
	fmt.Fprintf(&b, "- %d matches: %s %d wins, %s %d wins, %d draws\n",
		h.Matches, h.Team1, h.Team1Wins, h.Team2, h.Team2Wins, h.Draws)
	if len(matches) > 0 {
		b.WriteString("Recent matches:\n")
		shown := matches
		if len(shown) > 10 {
			shown = shown[:10]
		}
		for _, m := range shown {
			date := "????-??-??"
			if !m.Date.IsZero() {
				date = m.Date.Format("2006-01-02")
			}
			fmt.Fprintf(&b, "- %s: %s %d-%d %s [%s]\n",
				date, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Competition)
		}
	}
	return b.String()
}

func formatStandings(rows []StandingsRow, comp string, season int) string {
	if len(rows) == 0 {
		return "No standings data."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s standings (from match data):\n", season, comp)
	for i, r := range rows {
		fmt.Fprintf(&b, "%2d. %-30s P:%2d  %2dW %2dD %2dL  GF:%2d GA:%2d (%+d)  Pts:%d\n",
			i+1, r.Team, r.Played, r.Wins, r.Draws, r.Losses,
			r.GoalsFor, r.GoalsAgst, r.GoalDiff, r.Points)
	}
	return b.String()
}

func formatPlayers(players []Player) string {
	if len(players) == 0 {
		return "No players found."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d players:\n", len(players))
	for i, p := range players {
		fmt.Fprintf(&b, "%2d. %s — Overall:%d Pos:%s Club:%s Nat:%s Age:%d\n",
			i+1, p.Name, p.Overall, p.Position, p.Club, p.Nationality, p.Age)
	}
	return b.String()
}

func formatAggregate(a AggregateStats) string {
	if a.Matches == 0 {
		return "No matches matched the filter."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Aggregate over %d matches:\n", a.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", a.TotalGoals)
	fmt.Fprintf(&b, "- Average goals/match: %.2f\n", a.AvgGoalsPerGame)
	fmt.Fprintf(&b, "- Home wins: %d, Away wins: %d, Draws: %d\n", a.HomeWins, a.AwayWins, a.Draws)
	fmt.Fprintf(&b, "- Home win rate: %.1f%%\n", a.HomeWinRate*100)
	return b.String()
}
