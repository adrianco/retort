package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
)

// JSON-RPC 2.0 types

type jsonRPCRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      interface{}     `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type jsonRPCResponse struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      interface{} `json:"id,omitempty"`
	Result  interface{} `json:"result,omitempty"`
	Error   *rpcError   `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// MCP types

type serverInfo struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

type initResult struct {
	ProtocolVersion string       `json:"protocolVersion"`
	Capabilities    capabilities `json:"capabilities"`
	ServerInfo      serverInfo   `json:"serverInfo"`
}

type capabilities struct {
	Tools map[string]interface{} `json:"tools"`
}

type toolDef struct {
	Name        string      `json:"name"`
	Description string      `json:"description"`
	InputSchema interface{} `json:"inputSchema"`
}

type toolsListResult struct {
	Tools []toolDef `json:"tools"`
}

type contentItem struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type toolCallResult struct {
	Content []contentItem `json:"content"`
	IsError bool          `json:"isError,omitempty"`
}

// MCPServer is the MCP server.
type MCPServer struct {
	db     *Database
	writer *bufio.Writer
}

func newMCPServer(db *Database) *MCPServer {
	return &MCPServer{
		db:     db,
		writer: bufio.NewWriter(os.Stdout),
	}
}

// Run reads JSON-RPC messages from stdin and writes responses to stdout.
func (s *MCPServer) Run() {
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Buffer(make([]byte, 10*1024*1024), 10*1024*1024)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		s.handleMessage(line)
	}
}

func (s *MCPServer) handleMessage(data []byte) {
	var req jsonRPCRequest
	if err := json.Unmarshal(data, &req); err != nil {
		s.writeError(nil, -32700, "parse error")
		return
	}

	switch req.Method {
	case "initialize":
		s.handleInitialize(req)
	case "notifications/initialized":
		// No response needed
	case "tools/list":
		s.handleToolsList(req)
	case "tools/call":
		s.handleToolsCall(req)
	default:
		if req.ID != nil {
			s.writeError(req.ID, -32601, "method not found: "+req.Method)
		}
	}
}

func (s *MCPServer) handleInitialize(req jsonRPCRequest) {
	result := initResult{
		ProtocolVersion: "2024-11-05",
		Capabilities:    capabilities{Tools: map[string]interface{}{}},
		ServerInfo:      serverInfo{Name: "brazilian-soccer-mcp", Version: "1.0.0"},
	}
	s.writeResult(req.ID, result)
}

func (s *MCPServer) handleToolsList(req jsonRPCRequest) {
	s.writeResult(req.ID, toolsListResult{Tools: allTools()})
}

func (s *MCPServer) handleToolsCall(req jsonRPCRequest) {
	var params struct {
		Name      string          `json:"name"`
		Arguments json.RawMessage `json:"arguments"`
	}
	if err := json.Unmarshal(req.Params, &params); err != nil {
		s.writeError(req.ID, -32600, "invalid params")
		return
	}

	text, err := s.dispatchTool(params.Name, params.Arguments)
	if err != nil {
		s.writeResult(req.ID, toolCallResult{
			Content: []contentItem{{Type: "text", Text: "Error: " + err.Error()}},
			IsError: true,
		})
		return
	}
	s.writeResult(req.ID, toolCallResult{
		Content: []contentItem{{Type: "text", Text: text}},
	})
}

func (s *MCPServer) writeResult(id interface{}, result interface{}) {
	resp := jsonRPCResponse{JSONRPC: "2.0", ID: id, Result: result}
	s.write(resp)
}

func (s *MCPServer) writeError(id interface{}, code int, msg string) {
	resp := jsonRPCResponse{
		JSONRPC: "2.0",
		ID:      id,
		Error:   &rpcError{Code: code, Message: msg},
	}
	s.write(resp)
}

func (s *MCPServer) write(v interface{}) {
	data, err := json.Marshal(v)
	if err != nil {
		fmt.Fprintf(os.Stderr, "marshal error: %v\n", err)
		return
	}
	s.writer.Write(data)
	s.writer.WriteByte('\n')
	s.writer.Flush()
}

// dispatchTool routes a tool call to the appropriate handler.
func (s *MCPServer) dispatchTool(name string, args json.RawMessage) (string, error) {
	switch name {
	case "search_matches":
		return s.toolSearchMatches(args)
	case "get_head_to_head":
		return s.toolGetHeadToHead(args)
	case "get_team_stats":
		return s.toolGetTeamStats(args)
	case "get_standings":
		return s.toolGetStandings(args)
	case "search_players":
		return s.toolSearchPlayers(args)
	case "get_statistics":
		return s.toolGetStatistics(args)
	default:
		return "", fmt.Errorf("unknown tool: %s", name)
	}
}

// --- Tool: search_matches ---

func (s *MCPServer) toolSearchMatches(args json.RawMessage) (string, error) {
	var p struct {
		Team        string `json:"team"`
		HomeTeam    string `json:"home_team"`
		AwayTeam    string `json:"away_team"`
		StartDate   string `json:"start_date"`
		EndDate     string `json:"end_date"`
		Competition string `json:"competition"`
		Season      int    `json:"season"`
		Limit       int    `json:"limit"`
	}
	json.Unmarshal(args, &p)
	if p.Limit == 0 {
		p.Limit = 50
	}

	matches := SearchMatches(s.db, SearchMatchesParams{
		Team:        p.Team,
		HomeTeam:    p.HomeTeam,
		AwayTeam:    p.AwayTeam,
		StartDate:   p.StartDate,
		EndDate:     p.EndDate,
		Competition: p.Competition,
		Season:      p.Season,
		Limit:       p.Limit,
	})

	if len(matches) == 0 {
		return "No matches found for the given criteria.", nil
	}

	out := fmt.Sprintf("Found %d match(es):\n\n", len(matches))
	for _, m := range matches {
		out += fmt.Sprintf("- %s: %s %d-%d %s (%s", m.Date, m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam, m.Competition)
		if m.Season > 0 {
			out += fmt.Sprintf(" %d", m.Season)
		}
		if m.Round != "" {
			out += fmt.Sprintf(" Round %s", m.Round)
		}
		if m.Stage != "" {
			out += fmt.Sprintf(" - %s", m.Stage)
		}
		out += ")\n"
	}
	return out, nil
}

// --- Tool: get_head_to_head ---

func (s *MCPServer) toolGetHeadToHead(args json.RawMessage) (string, error) {
	var p struct {
		Team1       string `json:"team1"`
		Team2       string `json:"team2"`
		Competition string `json:"competition"`
		Season      int    `json:"season"`
		Limit       int    `json:"limit"`
	}
	json.Unmarshal(args, &p)
	if p.Team1 == "" || p.Team2 == "" {
		return "", fmt.Errorf("team1 and team2 are required")
	}
	if p.Limit == 0 {
		p.Limit = 20
	}

	h2h := GetHeadToHead(s.db, p.Team1, p.Team2, GetHeadToHeadParams{
		Competition: p.Competition,
		Season:      p.Season,
	})

	if h2h.TotalMatches == 0 {
		return fmt.Sprintf("No matches found between %s and %s.", p.Team1, p.Team2), nil
	}

	out := fmt.Sprintf("Head-to-head: %s vs %s\n", p.Team1, p.Team2)
	out += fmt.Sprintf("Total matches: %d\n", h2h.TotalMatches)
	out += fmt.Sprintf("%s wins: %d | %s wins: %d | Draws: %d\n",
		p.Team1, h2h.Team1Wins, p.Team2, h2h.Team2Wins, h2h.Draws)
	out += fmt.Sprintf("Goals: %s %d - %d %s\n\n", p.Team1, h2h.Team1Goals, h2h.Team2Goals, p.Team2)

	limit := p.Limit
	if limit > len(h2h.Matches) {
		limit = len(h2h.Matches)
	}
	out += "Recent matches:\n"
	for _, m := range h2h.Matches[:limit] {
		out += fmt.Sprintf("- %s: %s %d-%d %s (%s %d)\n",
			m.Date, m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam, m.Competition, m.Season)
	}
	return out, nil
}

// --- Tool: get_team_stats ---

func (s *MCPServer) toolGetTeamStats(args json.RawMessage) (string, error) {
	var p struct {
		Team        string `json:"team"`
		Competition string `json:"competition"`
		Season      int    `json:"season"`
		HomeOnly    bool   `json:"home_only"`
		AwayOnly    bool   `json:"away_only"`
	}
	json.Unmarshal(args, &p)
	if p.Team == "" {
		return "", fmt.Errorf("team is required")
	}

	stats := GetTeamStats(s.db, p.Team, GetTeamStatsParams{
		Competition: p.Competition,
		Season:      p.Season,
		HomeOnly:    p.HomeOnly,
		AwayOnly:    p.AwayOnly,
	})

	if stats.Played == 0 {
		return fmt.Sprintf("No matches found for %s.", p.Team), nil
	}

	context := ""
	if p.Competition != "" {
		context += " " + p.Competition
	}
	if p.Season != 0 {
		context += fmt.Sprintf(" %d", p.Season)
	}
	if p.HomeOnly {
		context += " (home)"
	} else if p.AwayOnly {
		context += " (away)"
	}

	winRate := 0.0
	if stats.Played > 0 {
		winRate = float64(stats.Wins) / float64(stats.Played) * 100
	}

	out := fmt.Sprintf("%s record%s:\n", p.Team, context)
	out += fmt.Sprintf("Matches: %d\n", stats.Played)
	out += fmt.Sprintf("Wins: %d | Draws: %d | Losses: %d\n", stats.Wins, stats.Draws, stats.Losses)
	out += fmt.Sprintf("Goals For: %d | Goals Against: %d | Goal Difference: %d\n", stats.GF, stats.GA, stats.GD)
	out += fmt.Sprintf("Points: %d | Win rate: %.1f%%\n", stats.Points, winRate)
	return out, nil
}

// --- Tool: get_standings ---

func (s *MCPServer) toolGetStandings(args json.RawMessage) (string, error) {
	var p struct {
		Competition string `json:"competition"`
		Season      int    `json:"season"`
		Limit       int    `json:"limit"`
	}
	json.Unmarshal(args, &p)
	if p.Limit == 0 {
		p.Limit = 20
	}

	standings := GetStandings(s.db, p.Competition, p.Season)
	if len(standings) == 0 {
		return "No standings data found.", nil
	}

	title := "Standings"
	if p.Competition != "" {
		title = p.Competition + " Standings"
	}
	if p.Season != 0 {
		title = fmt.Sprintf("%d %s", p.Season, title)
	}

	out := title + ":\n\n"
	out += fmt.Sprintf("%-4s %-25s %5s %5s %5s %5s %5s %5s %5s %5s\n",
		"Pos", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts")
	out += fmt.Sprintf("%s\n", "--------------------------------------------------------------------")

	limit := p.Limit
	if limit > len(standings) {
		limit = len(standings)
	}
	for i, s := range standings[:limit] {
		out += fmt.Sprintf("%-4d %-25s %5d %5d %5d %5d %5d %5d %5d %5d\n",
			i+1, truncate(s.Team, 25), s.Played, s.Wins, s.Draws, s.Losses, s.GF, s.GA, s.GD, s.Points)
	}
	return out, nil
}

// --- Tool: search_players ---

func (s *MCPServer) toolSearchPlayers(args json.RawMessage) (string, error) {
	var p struct {
		Name        string `json:"name"`
		Nationality string `json:"nationality"`
		Club        string `json:"club"`
		Position    string `json:"position"`
		MinOverall  int    `json:"min_overall"`
		Limit       int    `json:"limit"`
	}
	json.Unmarshal(args, &p)
	if p.Limit == 0 {
		p.Limit = 20
	}

	players := SearchPlayers(s.db, SearchPlayersParams{
		Name:        p.Name,
		Nationality: p.Nationality,
		Club:        p.Club,
		Position:    p.Position,
		MinOverall:  p.MinOverall,
		Limit:       p.Limit,
	})

	if len(players) == 0 {
		return "No players found for the given criteria.", nil
	}

	out := fmt.Sprintf("Found %d player(s):\n\n", len(players))
	for i, pl := range players {
		out += fmt.Sprintf("%d. %s - Overall: %d | Potential: %d | Pos: %s | Club: %s | Nationality: %s | Age: %d\n",
			i+1, pl.Name, pl.Overall, pl.Potential, pl.Position, pl.Club, pl.Nationality, pl.Age)
	}
	return out, nil
}

// --- Tool: get_statistics ---

func (s *MCPServer) toolGetStatistics(args json.RawMessage) (string, error) {
	var p struct {
		StatType    string `json:"stat_type"`
		Competition string `json:"competition"`
		Season      int    `json:"season"`
		Limit       int    `json:"limit"`
	}
	json.Unmarshal(args, &p)
	if p.Limit == 0 {
		p.Limit = 10
	}
	if p.StatType == "" {
		p.StatType = "all"
	}

	stats := GetStatistics(s.db, p.StatType, GetStatisticsParams{
		Competition: p.Competition,
		Season:      p.Season,
		Limit:       p.Limit,
	})

	context := ""
	if p.Competition != "" {
		context += " " + p.Competition
	}
	if p.Season != 0 {
		context += fmt.Sprintf(" %d", p.Season)
	}

	out := fmt.Sprintf("Statistics%s:\n\n", context)
	out += fmt.Sprintf("Total matches analyzed: %d\n", stats.TotalMatches)
	out += fmt.Sprintf("Average goals per match: %.2f\n", stats.GoalsPerMatch)
	out += fmt.Sprintf("Home win rate: %.1f%%\n", stats.HomeWinRate*100)
	out += fmt.Sprintf("Away win rate: %.1f%%\n", stats.AwayWinRate*100)
	out += fmt.Sprintf("Draw rate: %.1f%%\n\n", stats.DrawRate*100)

	out += fmt.Sprintf("Biggest wins (top %d):\n", len(stats.BiggestWins))
	for i, m := range stats.BiggestWins {
		margin := m.HomeGoal - m.AwayGoal
		winner := m.HomeTeam
		loser := m.AwayTeam
		winGoals := m.HomeGoal
		loseGoals := m.AwayGoal
		if margin < 0 {
			margin = -margin
			winner = m.AwayTeam
			loser = m.HomeTeam
			winGoals = m.AwayGoal
			loseGoals = m.HomeGoal
		}
		out += fmt.Sprintf("%d. %s: %s %d-%d %s (%s %d, margin: %d)\n",
			i+1, m.Date, winner, winGoals, loseGoals, loser, m.Competition, m.Season, margin)
	}
	return out, nil
}

// allTools returns the list of tool definitions for tools/list.
func allTools() []toolDef {
	strProp := func(desc string) map[string]interface{} {
		return map[string]interface{}{"type": "string", "description": desc}
	}
	intProp := func(desc string) map[string]interface{} {
		return map[string]interface{}{"type": "integer", "description": desc}
	}
	boolProp := func(desc string) map[string]interface{} {
		return map[string]interface{}{"type": "boolean", "description": desc}
	}

	return []toolDef{
		{
			Name:        "search_matches",
			Description: "Search for Brazilian soccer matches by team, date, competition, or season. Returns matches sorted by date (newest first).",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"team":        strProp("Team name (home or away). Supports partial match and accent-insensitive search. E.g. 'Flamengo', 'São Paulo', 'Palmeiras'"),
					"home_team":   strProp("Home team name (for specific home/away matchups)"),
					"away_team":   strProp("Away team name"),
					"start_date":  strProp("Start date filter in YYYY-MM-DD format"),
					"end_date":    strProp("End date filter in YYYY-MM-DD format"),
					"competition": strProp("Competition: 'brasileirao', 'copa_do_brasil', 'libertadores', or 'all'"),
					"season":      intProp("Season year (e.g. 2023)"),
					"limit":       intProp("Maximum number of results to return (default: 50)"),
				},
			},
		},
		{
			Name:        "get_head_to_head",
			Description: "Get head-to-head record and recent matches between two teams.",
			InputSchema: map[string]interface{}{
				"type":     "object",
				"required": []string{"team1", "team2"},
				"properties": map[string]interface{}{
					"team1":       strProp("First team name"),
					"team2":       strProp("Second team name"),
					"competition": strProp("Filter by competition (optional)"),
					"season":      intProp("Filter by season year (optional)"),
					"limit":       intProp("Maximum recent matches to show (default: 20)"),
				},
			},
		},
		{
			Name:        "get_team_stats",
			Description: "Get win/loss/draw statistics and goals for a team, optionally filtered by competition and season.",
			InputSchema: map[string]interface{}{
				"type":     "object",
				"required": []string{"team"},
				"properties": map[string]interface{}{
					"team":        strProp("Team name"),
					"competition": strProp("Filter by competition (optional)"),
					"season":      intProp("Filter by season year (optional)"),
					"home_only":   boolProp("Only count home matches"),
					"away_only":   boolProp("Only count away matches"),
				},
			},
		},
		{
			Name:        "get_standings",
			Description: "Calculate league standings (table) for a competition and season based on match results.",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"competition": strProp("Competition name: 'brasileirao', 'copa_do_brasil', 'libertadores'"),
					"season":      intProp("Season year (e.g. 2019)"),
					"limit":       intProp("Maximum teams to show (default: 20)"),
				},
			},
		},
		{
			Name:        "search_players",
			Description: "Search for players in the FIFA database by name, nationality, club, or position. Results sorted by Overall rating.",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"name":        strProp("Player name (partial match supported). E.g. 'Neymar', 'Gabriel Barbosa'"),
					"nationality": strProp("Player nationality. E.g. 'Brazil', 'Argentina'"),
					"club":        strProp("Club name (partial match). E.g. 'Flamengo', 'Palmeiras'"),
					"position":    strProp("Playing position: GK, CB, LB, RB, CDM, CM, CAM, LW, RW, ST, etc."),
					"min_overall": intProp("Minimum FIFA Overall rating"),
					"limit":       intProp("Maximum results (default: 20)"),
				},
			},
		},
		{
			Name:        "get_statistics",
			Description: "Calculate aggregate statistics: goals per match, home/away win rates, biggest wins.",
			InputSchema: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"stat_type":   strProp("Type of stats: 'goals_per_match', 'biggest_wins', 'home_record', or 'all'"),
					"competition": strProp("Filter by competition (optional)"),
					"season":      intProp("Filter by season year (optional)"),
					"limit":       intProp("Number of biggest wins to return (default: 10)"),
				},
			},
		},
	}
}

func truncate(s string, n int) string {
	runes := []rune(s)
	if len(runes) <= n {
		return s
	}
	return string(runes[:n-1]) + "…"
}

// RunMCPServer is exported for testing.
func RunMCPServer(db *Database, in io.Reader, out io.Writer) {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 10*1024*1024), 10*1024*1024)
	writer := bufio.NewWriter(out)

	send := func(v interface{}) {
		data, _ := json.Marshal(v)
		writer.Write(data)
		writer.WriteByte('\n')
		writer.Flush()
	}

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var req jsonRPCRequest
		if err := json.Unmarshal(line, &req); err != nil {
			send(jsonRPCResponse{JSONRPC: "2.0", Error: &rpcError{Code: -32700, Message: "parse error"}})
			continue
		}

		srv := &MCPServer{db: db, writer: bufio.NewWriter(out)}

		switch req.Method {
		case "initialize":
			srv.handleInitialize(req)
		case "notifications/initialized":
			// no response
		case "tools/list":
			srv.handleToolsList(req)
		case "tools/call":
			srv.handleToolsCall(req)
		default:
			if req.ID != nil {
				send(jsonRPCResponse{
					JSONRPC: "2.0", ID: req.ID,
					Error: &rpcError{Code: -32601, Message: "method not found"},
				})
			}
		}
	}
}
