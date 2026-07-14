package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"strings"

	"soccer-mcp/soccer"
)

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
}

type server struct {
	db *soccer.DB
}

type tool struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema json.RawMessage `json:"inputSchema"`
}

func (s *server) tools() []tool {
	raw := func(j string) json.RawMessage { return json.RawMessage(j) }
	return []tool{
		{
			Name:        "matches_between",
			Description: "Find matches between two teams (any competition).",
			InputSchema: raw(`{"type":"object","properties":{"team_a":{"type":"string"},"team_b":{"type":"string"}},"required":["team_a","team_b"]}`),
		},
		{
			Name:        "matches_by_team",
			Description: "List matches for a team (home or away).",
			InputSchema: raw(`{"type":"object","properties":{"team":{"type":"string"},"season":{"type":"integer"},"competition":{"type":"string"}},"required":["team"]}`),
		},
		{
			Name:        "team_stats",
			Description: "Aggregated stats for a team (wins, draws, losses, goals).",
			InputSchema: raw(`{"type":"object","properties":{"team":{"type":"string"},"season":{"type":"integer"},"competition":{"type":"string"},"home_only":{"type":"boolean"},"away_only":{"type":"boolean"}},"required":["team"]}`),
		},
		{
			Name:        "head_to_head",
			Description: "Head to head summary between two teams.",
			InputSchema: raw(`{"type":"object","properties":{"team_a":{"type":"string"},"team_b":{"type":"string"}},"required":["team_a","team_b"]}`),
		},
		{
			Name:        "standings",
			Description: "Calculate standings for a season/competition.",
			InputSchema: raw(`{"type":"object","properties":{"season":{"type":"integer"},"competition":{"type":"string"}},"required":["season"]}`),
		},
		{
			Name:        "biggest_wins",
			Description: "Return the matches with the largest goal differences.",
			InputSchema: raw(`{"type":"object","properties":{"limit":{"type":"integer"}}}`),
		},
		{
			Name:        "average_goals",
			Description: "Average total goals per match in a competition/season.",
			InputSchema: raw(`{"type":"object","properties":{"season":{"type":"integer"},"competition":{"type":"string"}}}`),
		},
		{
			Name:        "find_player",
			Description: "Search players by name substring.",
			InputSchema: raw(`{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}`),
		},
		{
			Name:        "top_players",
			Description: "Top players by overall rating, optionally filtered.",
			InputSchema: raw(`{"type":"object","properties":{"limit":{"type":"integer"},"nationality":{"type":"string"},"club":{"type":"string"},"position":{"type":"string"}}}`),
		},
		{
			Name:        "players_by_club",
			Description: "List players whose club matches a substring.",
			InputSchema: raw(`{"type":"object","properties":{"club":{"type":"string"}},"required":["club"]}`),
		},
	}
}

func textContent(s string) any {
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": s}},
	}
}

func (s *server) callTool(name string, args map[string]any) (any, error) {
	getStr := func(k string) string {
		if v, ok := args[k].(string); ok {
			return v
		}
		return ""
	}
	getInt := func(k string) int {
		switch v := args[k].(type) {
		case float64:
			return int(v)
		case int:
			return v
		}
		return 0
	}
	getBool := func(k string) bool {
		b, _ := args[k].(bool)
		return b
	}

	switch name {
	case "matches_between":
		ms := s.db.MatchesBetween(getStr("team_a"), getStr("team_b"))
		h := s.db.H2H(getStr("team_a"), getStr("team_b"))
		out := fmt.Sprintf("Found %d matches.\n%s\nH2H: %s %d wins, %s %d wins, %d draws\n",
			len(ms), soccer.FormatMatches(ms), getStr("team_a"), h.AWins, getStr("team_b"), h.BWins, h.Draws)
		return textContent(out), nil
	case "matches_by_team":
		ms := s.db.MatchesByTeam(getStr("team"))
		season := getInt("season")
		comp := getStr("competition")
		var filtered []soccer.Match
		for _, m := range ms {
			if season > 0 && m.Season != season {
				continue
			}
			if comp != "" && !strings.Contains(strings.ToLower(m.Competition), strings.ToLower(comp)) {
				continue
			}
			filtered = append(filtered, m)
		}
		return textContent(fmt.Sprintf("%d matches\n%s", len(filtered), soccer.FormatMatches(filtered))), nil
	case "team_stats":
		f := soccer.StatsFilter{Season: getInt("season"), Competition: getStr("competition"), HomeOnly: getBool("home_only"), AwayOnly: getBool("away_only")}
		ts := s.db.TeamStats(getStr("team"), f)
		return textContent(fmt.Sprintf("%s: %d matches, %dW-%dD-%dL, GF %d, GA %d, Pts %d, Win rate %.1f%%",
			ts.Team, ts.Matches, ts.Wins, ts.Draws, ts.Losses, ts.GoalsFor, ts.GoalsAgainst, ts.Points, ts.WinRate())), nil
	case "head_to_head":
		h := s.db.H2H(getStr("team_a"), getStr("team_b"))
		return textContent(fmt.Sprintf("%s %d wins, %s %d wins, %d draws across %d matches",
			h.TeamA, h.AWins, h.TeamB, h.BWins, h.Draws, len(h.Matches))), nil
	case "standings":
		table := s.db.Standings(getInt("season"), getStr("competition"))
		var b strings.Builder
		for i, t := range table {
			fmt.Fprintf(&b, "%2d. %-25s %3d pts (%dW %dD %dL, %d:%d)\n", i+1, t.Team, t.Points, t.Wins, t.Draws, t.Losses, t.GoalsFor, t.GoalsAgainst)
			if i >= 19 {
				break
			}
		}
		return textContent(b.String()), nil
	case "biggest_wins":
		n := getInt("limit")
		if n <= 0 {
			n = 10
		}
		return textContent(soccer.FormatMatches(s.db.BiggestWins(n))), nil
	case "average_goals":
		avg := s.db.AverageGoalsPerMatch(getInt("season"), getStr("competition"))
		return textContent(fmt.Sprintf("Average goals per match: %.2f", avg)), nil
	case "find_player":
		ps := s.db.PlayersByName(getStr("name"))
		var b strings.Builder
		for _, p := range ps {
			fmt.Fprintf(&b, "%s — Overall %d, %s, %s, Age %d\n", p.Name, p.Overall, p.Position, p.Club, p.Age)
		}
		if b.Len() == 0 {
			b.WriteString("No players found.")
		}
		return textContent(b.String()), nil
	case "top_players":
		n := getInt("limit")
		if n <= 0 {
			n = 10
		}
		top := s.db.TopPlayers(n, getStr("nationality"), getStr("club"), getStr("position"))
		var b strings.Builder
		for i, p := range top {
			fmt.Fprintf(&b, "%d. %s — Overall %d, %s, %s\n", i+1, p.Name, p.Overall, p.Position, p.Club)
		}
		return textContent(b.String()), nil
	case "players_by_club":
		ps := s.db.PlayersByClub(getStr("club"))
		var b strings.Builder
		for _, p := range ps {
			fmt.Fprintf(&b, "%s — Overall %d, %s, %s\n", p.Name, p.Overall, p.Position, p.Club)
		}
		return textContent(b.String()), nil
	}
	return nil, fmt.Errorf("unknown tool: %s", name)
}

func (s *server) handle(req rpcRequest) rpcResponse {
	resp := rpcResponse{JSONRPC: "2.0", ID: req.ID}
	switch req.Method {
	case "initialize":
		resp.Result = map[string]any{
			"protocolVersion": "2024-11-05",
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": "brazilian-soccer-mcp", "version": "0.1.0"},
		}
	case "tools/list":
		resp.Result = map[string]any{"tools": s.tools()}
	case "tools/call":
		var p struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			resp.Error = &rpcError{Code: -32602, Message: err.Error()}
			return resp
		}
		out, err := s.callTool(p.Name, p.Arguments)
		if err != nil {
			resp.Error = &rpcError{Code: -32000, Message: err.Error()}
			return resp
		}
		resp.Result = out
	case "ping":
		resp.Result = map[string]any{}
	default:
		resp.Error = &rpcError{Code: -32601, Message: "method not found: " + req.Method}
	}
	return resp
}

func (s *server) serve(r io.Reader, w io.Writer) error {
	dec := json.NewDecoder(bufio.NewReader(r))
	enc := json.NewEncoder(w)
	for {
		var req rpcRequest
		if err := dec.Decode(&req); err != nil {
			if err == io.EOF {
				return nil
			}
			return err
		}
		// notifications (no id) -> don't respond
		if len(req.ID) == 0 {
			continue
		}
		resp := s.handle(req)
		if err := enc.Encode(resp); err != nil {
			return err
		}
	}
}

func main() {
	dir := os.Getenv("SOCCER_DATA_DIR")
	if dir == "" {
		dir = "data/kaggle"
	}
	db, err := soccer.LoadAll(dir)
	if err != nil {
		log.Fatalf("load data: %v", err)
	}
	log.Printf("loaded %d matches, %d players", len(db.Matches), len(db.Players))
	s := &server{db: db}
	if err := s.serve(os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}
