package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"strconv"
	"strings"
	"time"
)

const protocolVersion = "2026-07-28"

var supportedProtocolVersions = []string{"2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"}

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

type tool struct {
	Name        string         `json:"name"`
	Title       string         `json:"title,omitempty"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	Annotations map[string]any `json:"annotations,omitempty"`
}

type Server struct{ store *Store }

func NewServer(store *Store) *Server { return &Server{store: store} }

func (s *Server) Serve(ctx context.Context, in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 64*1024), 4*1024*1024)
	enc := json.NewEncoder(out)
	for scanner.Scan() {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var req rpcRequest
		if err := json.Unmarshal([]byte(line), &req); err != nil {
			if err := enc.Encode(rpcResponse{JSONRPC: "2.0", Error: &rpcError{Code: -32700, Message: "parse error", Data: err.Error()}}); err != nil {
				return err
			}
			continue
		}
		// Notifications have no id and must never receive a response.
		if len(req.ID) == 0 {
			continue
		}
		result, rpcErr := s.handle(req)
		if err := enc.Encode(rpcResponse{JSONRPC: "2.0", ID: req.ID, Result: result, Error: rpcErr}); err != nil {
			return err
		}
	}
	return scanner.Err()
}

func (s *Server) handle(req rpcRequest) (any, *rpcError) {
	switch req.Method {
	case "server/discover":
		return map[string]any{"resultType": "complete", "supportedVersions": supportedProtocolVersions, "capabilities": map[string]any{"tools": map[string]any{}}, "_meta": map[string]any{"io.modelcontextprotocol/serverInfo": map[string]any{"name": "brazilian-soccer", "version": "1.0.0"}}, "instructions": serverInstructions(), "ttlMs": 3600000, "cacheScope": "public"}, nil
	case "initialize":
		var p struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		_ = json.Unmarshal(req.Params, &p)
		negotiated := protocolVersion
		for _, version := range supportedProtocolVersions {
			if p.ProtocolVersion == version {
				negotiated = version
				break
			}
		}
		return map[string]any{"protocolVersion": negotiated, "capabilities": map[string]any{"tools": map[string]any{"listChanged": false}}, "serverInfo": map[string]any{"name": "brazilian-soccer", "version": "1.0.0"}, "instructions": serverInstructions()}, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		return map[string]any{"tools": toolDefinitions(), "ttlMs": 3600000, "cacheScope": "public"}, nil
	case "tools/call":
		var p struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return nil, invalidParams(err.Error())
		}
		if !toolExists(p.Name) {
			return nil, invalidParams("unknown tool: " + p.Name)
		}
		result, err := s.callTool(p.Name, p.Arguments)
		if err != nil {
			return toolError(err), nil
		}
		return toolResult(result), nil
	default:
		return nil, &rpcError{Code: -32601, Message: "method not found", Data: req.Method}
	}
}

func serverInstructions() string {
	return "Use the tools to query the bundled Brazilian soccer match and FIFA player datasets. Team names are accent-, suffix-, and alias-normalized."
}

func toolExists(name string) bool {
	for _, t := range toolDefinitions() {
		if t.Name == name {
			return true
		}
	}
	return false
}

func toolDefinitions() []tool {
	str := func(desc string) map[string]any { return map[string]any{"type": "string", "description": desc} }
	integer := func(desc string) map[string]any { return map[string]any{"type": "integer", "description": desc} }
	tools := []tool{
		{Name: "search_matches", Description: "Find match results across all five match datasets. Filters can be combined; results are newest first and overlapping feeds are deduplicated.", InputSchema: objectSchema(map[string]any{"team": str("Team playing either side"), "opponent": str("Second team, useful for head-to-head searches"), "home_team": str("Home team only"), "away_team": str("Away team only"), "competition": str("Brasileirão, Copa do Brasil, Libertadores, Serie B, or Serie C"), "season": integer("Season year"), "date_from": str("Inclusive YYYY-MM-DD"), "date_to": str("Inclusive YYYY-MM-DD"), "stage": str("Round or stage, such as final or group stage"), "source": str("Exact CSV filename for raw source-specific results"), "limit": integer("1-200, default 20")}, nil)},
		{Name: "team_statistics", Description: "Calculate a team's wins, draws, losses, goals, points, and win rate, optionally by season, competition, and venue.", InputSchema: objectSchema(map[string]any{"team": str("Team name"), "competition": str("Optional competition"), "season": integer("Optional season year"), "venue": map[string]any{"type": "string", "enum": []string{"all", "home", "away"}}}, []string{"team"})},
		{Name: "head_to_head", Description: "Compare two teams and return their aggregate record plus individual results.", InputSchema: objectSchema(map[string]any{"team_1": str("First team"), "team_2": str("Second team"), "competition": str("Optional competition"), "season": integer("Optional season year")}, []string{"team_1", "team_2"})},
		{Name: "search_players", Description: "Search FIFA players by name, nationality, club, position, or minimum overall rating. Results are highest-rated first.", InputSchema: objectSchema(map[string]any{"name": str("Partial player name"), "nationality": str("Nationality, e.g. Brazil"), "club": str("Club name"), "position": str("Position code, e.g. ST, LW, GK"), "min_overall": integer("Minimum FIFA overall rating"), "limit": integer("1-200, default 20")}, nil)},
		{Name: "standings", Description: "Calculate final table-style standings from match results using 3 points for a win. Best for league competitions; cup results are also accepted.", InputSchema: objectSchema(map[string]any{"competition": str("Competition, defaults to Brasileirão Serie A"), "season": integer("Required season year"), "limit": integer("Optional number of teams")}, []string{"season"})},
		{Name: "competition_statistics", Description: "Calculate matches, teams, goals per match, home/away wins, draws, and home win rate.", InputSchema: objectSchema(map[string]any{"competition": str("Required competition"), "season": integer("Optional season year")}, []string{"competition"})},
		{Name: "biggest_wins", Description: "Rank matches by winning margin, optionally filtered by team, competition, and season.", InputSchema: objectSchema(map[string]any{"team": str("Optional team"), "competition": str("Optional competition"), "season": integer("Optional season year"), "limit": integer("1-100, default 10")}, nil)},
		{Name: "team_profile", Description: "Cross-file team view combining match record, competitions played, and players at that club in the FIFA dataset.", InputSchema: objectSchema(map[string]any{"team": str("Team name"), "season": integer("Optional season year for match data")}, []string{"team"})},
		{Name: "derbies", Description: "Find matches between curated traditional Brazilian rivals and label each derby by name.", InputSchema: objectSchema(map[string]any{"season": integer("Optional season year"), "competition": str("Optional competition"), "limit": integer("1-200, default 20")}, nil)},
	}
	for i := range tools {
		tools[i].Title = strings.ReplaceAll(strings.Title(strings.ReplaceAll(tools[i].Name, "_", " ")), "And", "and")
		tools[i].Annotations = map[string]any{"readOnlyHint": true, "destructiveHint": false, "idempotentHint": true, "openWorldHint": false}
	}
	return tools
}

func objectSchema(properties map[string]any, required []string) map[string]any {
	s := map[string]any{"type": "object", "properties": properties, "additionalProperties": false}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

func (s *Server) callTool(name string, a map[string]any) (any, error) {
	switch name {
	case "search_matches":
		from, err := dateArg(a, "date_from", false)
		if err != nil {
			return nil, err
		}
		to, err := dateArg(a, "date_to", true)
		if err != nil {
			return nil, err
		}
		return s.store.Matches(MatchFilter{Team: strArg(a, "team"), Opponent: strArg(a, "opponent"), HomeTeam: strArg(a, "home_team"), AwayTeam: strArg(a, "away_team"), Competition: strArg(a, "competition"), Season: intArg(a, "season"), DateFrom: from, DateTo: to, Stage: strArg(a, "stage"), Source: strArg(a, "source"), Limit: intArg(a, "limit")}), nil
	case "team_statistics":
		team, err := requiredString(a, "team")
		if err != nil {
			return nil, err
		}
		venue := strArg(a, "venue")
		if venue == "all" {
			venue = ""
		}
		if venue != "" && venue != "home" && venue != "away" {
			return nil, fmt.Errorf("venue must be all, home, or away")
		}
		return s.store.TeamStatistics(team, strArg(a, "competition"), venue, intArg(a, "season")), nil
	case "head_to_head":
		t1, err := requiredString(a, "team_1")
		if err != nil {
			return nil, err
		}
		t2, err := requiredString(a, "team_2")
		if err != nil {
			return nil, err
		}
		return s.store.HeadToHead(t1, t2, strArg(a, "competition"), intArg(a, "season")), nil
	case "search_players":
		return s.store.Players(PlayerFilter{Name: strArg(a, "name"), Nationality: strArg(a, "nationality"), Club: strArg(a, "club"), Position: strArg(a, "position"), MinOverall: intArg(a, "min_overall"), Limit: intArg(a, "limit")}), nil
	case "standings":
		season := intArg(a, "season")
		if season == 0 {
			return nil, fmt.Errorf("season is required and must be a year")
		}
		competition := strArg(a, "competition")
		if competition == "" {
			competition = "Brasileirão Serie A"
		}
		return s.store.Standings(competition, season, intArg(a, "limit")), nil
	case "competition_statistics":
		competition, err := requiredString(a, "competition")
		if err != nil {
			return nil, err
		}
		return s.store.CompetitionStatistics(competition, intArg(a, "season")), nil
	case "biggest_wins":
		return s.store.BiggestWins(strArg(a, "team"), strArg(a, "competition"), intArg(a, "season"), intArg(a, "limit")), nil
	case "team_profile":
		team, err := requiredString(a, "team")
		if err != nil {
			return nil, err
		}
		return s.store.TeamProfile(team, intArg(a, "season")), nil
	case "derbies":
		return s.store.Derbies(intArg(a, "season"), strArg(a, "competition"), intArg(a, "limit")), nil
	default:
		return nil, fmt.Errorf("unknown tool %q", name)
	}
}

func toolResult(v any) map[string]any {
	b, _ := json.MarshalIndent(v, "", "  ")
	return map[string]any{"content": []map[string]any{{"type": "text", "text": string(b)}}, "structuredContent": map[string]any{"result": v}, "isError": false}
}
func toolError(err error) map[string]any {
	return map[string]any{"content": []map[string]any{{"type": "text", "text": err.Error()}}, "isError": true}
}
func invalidParams(msg string) *rpcError {
	return &rpcError{Code: -32602, Message: "invalid params", Data: msg}
}

func strArg(a map[string]any, key string) string {
	if v, ok := a[key].(string); ok {
		return strings.TrimSpace(v)
	}
	return ""
}
func intArg(a map[string]any, key string) int {
	switch v := a[key].(type) {
	case float64:
		return int(v)
	case int:
		return v
	case json.Number:
		n, _ := strconv.Atoi(v.String())
		return n
	}
	return 0
}
func requiredString(a map[string]any, key string) (string, error) {
	v := strArg(a, key)
	if v == "" {
		return "", fmt.Errorf("%s is required", key)
	}
	return v, nil
}
func dateArg(a map[string]any, key string, endOfDay bool) (time.Time, error) {
	v := strArg(a, key)
	if v == "" {
		return time.Time{}, nil
	}
	d, err := parseDate(v)
	if err != nil {
		return time.Time{}, fmt.Errorf("%s must be YYYY-MM-DD", key)
	}
	if endOfDay {
		d = d.Add(24*time.Hour - time.Nanosecond)
	}
	return d, nil
}
