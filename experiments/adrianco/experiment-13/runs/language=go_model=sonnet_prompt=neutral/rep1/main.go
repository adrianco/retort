package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	// Determine data directory: next to binary, or from env.
	dataDir := os.Getenv("DATA_DIR")
	if dataDir == "" {
		// Try relative to executable first, then working directory.
		exe, _ := os.Executable()
		candidate := filepath.Join(filepath.Dir(exe), "data", "kaggle")
		if _, err := os.Stat(candidate); err == nil {
			dataDir = candidate
		} else {
			dataDir = filepath.Join("data", "kaggle")
		}
	}

	db, err := LoadDatabase(dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to load database: %v\n", err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "Loaded %d matches and %d players\n", len(db.Matches), len(db.Players))

	server := NewServer(db)
	server.Run(os.Stdin, os.Stdout)
}

// --- MCP JSON-RPC types ---

type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      interface{}     `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

type Response struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      interface{} `json:"id"`
	Result  interface{} `json:"result,omitempty"`
	Error   *RPCError   `json:"error,omitempty"`
}

type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type Notification struct {
	JSONRPC string      `json:"jsonrpc"`
	Method  string      `json:"method"`
	Params  interface{} `json:"params,omitempty"`
}

// --- MCP types ---

type ServerInfo struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

type Capabilities struct {
	Tools *ToolsCapability `json:"tools,omitempty"`
}

type ToolsCapability struct {
	ListChanged bool `json:"listChanged"`
}

type InitializeResult struct {
	ProtocolVersion string       `json:"protocolVersion"`
	Capabilities    Capabilities `json:"capabilities"`
	ServerInfo      ServerInfo   `json:"serverInfo"`
}

type Tool struct {
	Name        string     `json:"name"`
	Description string     `json:"description"`
	InputSchema ToolSchema `json:"inputSchema"`
}

type ToolSchema struct {
	Type       string              `json:"type"`
	Properties map[string]Property `json:"properties,omitempty"`
	Required   []string            `json:"required,omitempty"`
}

type Property struct {
	Type        string `json:"type"`
	Description string `json:"description"`
}

type ToolsListResult struct {
	Tools []Tool `json:"tools"`
}

type CallToolParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

type TextContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type CallToolResult struct {
	Content []TextContent `json:"content"`
	IsError bool          `json:"isError,omitempty"`
}

// --- Server ---

type Server struct {
	db    *Database
	tools []Tool
}

func NewServer(db *Database) *Server {
	s := &Server{db: db}
	s.tools = s.buildTools()
	return s
}

func (s *Server) buildTools() []Tool {
	return []Tool{
		{
			Name:        "search_matches",
			Description: "Search for soccer matches by team, competition, season, or head-to-head between two teams. Returns match results with scores, dates, and competition info.",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"team":        {Type: "string", Description: "Team name to search for (partial match, e.g. 'Flamengo', 'Palmeiras')"},
					"team2":       {Type: "string", Description: "Second team name for head-to-head queries"},
					"competition": {Type: "string", Description: "Competition filter: 'brasileirao', 'copa do brasil', 'libertadores', or leave empty for all"},
					"season":      {Type: "integer", Description: "Season year (e.g. 2019, 2023), or 0 for all seasons"},
					"limit":       {Type: "integer", Description: "Maximum matches to return (default 20)"},
				},
			},
		},
		{
			Name:        "get_team_stats",
			Description: "Get win/loss/draw statistics for a team, including goals scored and conceded. Can filter by competition, season, and home/away.",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"team":        {Type: "string", Description: "Team name (e.g. 'Corinthians', 'Santos')"},
					"competition": {Type: "string", Description: "Competition filter (optional)"},
					"season":      {Type: "integer", Description: "Season year (optional, 0 for all)"},
					"home_only":   {Type: "boolean", Description: "If true, only count home matches"},
				},
				Required: []string{"team"},
			},
		},
		{
			Name:        "get_standings",
			Description: "Get league standings (points table) for a competition and season.",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"competition": {Type: "string", Description: "Competition name (e.g. 'brasileirao', 'copa do brasil')"},
					"season":      {Type: "integer", Description: "Season year (e.g. 2019)"},
					"limit":       {Type: "integer", Description: "Number of teams to show (default 20)"},
				},
				Required: []string{"season"},
			},
		},
		{
			Name:        "get_biggest_wins",
			Description: "Get the matches with the largest goal difference (biggest victories/defeats). Can filter by competition or season.",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"competition": {Type: "string", Description: "Competition filter (optional)"},
					"season":      {Type: "integer", Description: "Season year (optional)"},
					"limit":       {Type: "integer", Description: "Number of results (default 10)"},
				},
			},
		},
		{
			Name:        "search_players",
			Description: "Search FIFA player database by name, nationality, club, or position. Returns player ratings and attributes.",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"name":        {Type: "string", Description: "Player name (partial match, e.g. 'Neymar', 'Gabriel')"},
					"nationality": {Type: "string", Description: "Nationality filter (e.g. 'Brazil', 'Argentina')"},
					"club":        {Type: "string", Description: "Club filter (e.g. 'Flamengo', 'Palmeiras')"},
					"position":    {Type: "string", Description: "Position filter (e.g. 'GK', 'ST', 'CAM')"},
					"limit":       {Type: "integer", Description: "Maximum players to return (default 20)"},
				},
			},
		},
		{
			Name:        "get_competition_stats",
			Description: "Get overall statistics for a competition/season: average goals, home win rate, total matches, top scoring teams.",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"competition": {Type: "string", Description: "Competition name (optional)"},
					"season":      {Type: "integer", Description: "Season year (optional)"},
				},
			},
		},
		{
			Name:        "list_teams",
			Description: "List all teams in the database, optionally filtered by competition or season.",
			InputSchema: ToolSchema{
				Type: "object",
				Properties: map[string]Property{
					"competition": {Type: "string", Description: "Competition filter (optional)"},
					"season":      {Type: "integer", Description: "Season year (optional)"},
				},
			},
		},
	}
}

func (s *Server) Run(in io.Reader, out io.Writer) {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024)
	enc := json.NewEncoder(out)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(strings.TrimSpace(string(line))) == 0 {
			continue
		}

		var req Request
		if err := json.Unmarshal(line, &req); err != nil {
			// Send parse error
			resp := Response{
				JSONRPC: "2.0",
				ID:      nil,
				Error:   &RPCError{Code: -32700, Message: "Parse error"},
			}
			enc.Encode(resp)
			continue
		}

		resp := s.handleRequest(req)
		enc.Encode(resp)
	}
}

func (s *Server) handleRequest(req Request) Response {
	base := Response{JSONRPC: "2.0", ID: req.ID}

	switch req.Method {
	case "initialize":
		base.Result = InitializeResult{
			ProtocolVersion: "2024-11-05",
			Capabilities: Capabilities{
				Tools: &ToolsCapability{ListChanged: false},
			},
			ServerInfo: ServerInfo{Name: "brazilian-soccer-mcp", Version: "1.0.0"},
		}

	case "notifications/initialized":
		// No response needed for notifications, but we have an ID so respond.
		base.Result = map[string]interface{}{}

	case "ping":
		base.Result = map[string]interface{}{}

	case "tools/list":
		base.Result = ToolsListResult{Tools: s.tools}

	case "tools/call":
		var params CallToolParams
		if err := json.Unmarshal(req.Params, &params); err != nil {
			base.Error = &RPCError{Code: -32602, Message: "Invalid params"}
			return base
		}
		result, err := s.callTool(params.Name, params.Arguments)
		if err != nil {
			base.Result = CallToolResult{
				Content: []TextContent{{Type: "text", Text: err.Error()}},
				IsError: true,
			}
		} else {
			base.Result = CallToolResult{
				Content: []TextContent{{Type: "text", Text: result}},
			}
		}

	default:
		base.Error = &RPCError{Code: -32601, Message: "Method not found: " + req.Method}
	}

	return base
}

func (s *Server) callTool(name string, args json.RawMessage) (string, error) {
	var a map[string]interface{}
	if len(args) > 0 {
		json.Unmarshal(args, &a)
	}
	if a == nil {
		a = map[string]interface{}{}
	}

	getString := func(key string) string {
		if v, ok := a[key]; ok {
			return fmt.Sprintf("%v", v)
		}
		return ""
	}
	getInt := func(key string, def int) int {
		v := getString(key)
		if v == "" || v == "<nil>" || v == "0" {
			return def
		}
		// JSON numbers come as float64
		if f, ok := a[key].(float64); ok {
			return int(f)
		}
		return def
	}
	getBool := func(key string) bool {
		if v, ok := a[key].(bool); ok {
			return v
		}
		s := getString(key)
		return s == "true" || s == "1"
	}

	switch name {
	case "search_matches":
		return s.toolSearchMatches(getString("team"), getString("team2"), getString("competition"), getInt("season", 0), getInt("limit", 20))
	case "get_team_stats":
		return s.toolTeamStats(getString("team"), getString("competition"), getInt("season", 0), getBool("home_only"))
	case "get_standings":
		return s.toolStandings(getString("competition"), getInt("season", 0), getInt("limit", 20))
	case "get_biggest_wins":
		return s.toolBiggestWins(getString("competition"), getInt("season", 0), getInt("limit", 10))
	case "search_players":
		return s.toolSearchPlayers(getString("name"), getString("nationality"), getString("club"), getString("position"), getInt("limit", 20))
	case "get_competition_stats":
		return s.toolCompetitionStats(getString("competition"), getInt("season", 0))
	case "list_teams":
		return s.toolListTeams(getString("competition"), getInt("season", 0))
	default:
		return "", fmt.Errorf("unknown tool: %s", name)
	}
}
