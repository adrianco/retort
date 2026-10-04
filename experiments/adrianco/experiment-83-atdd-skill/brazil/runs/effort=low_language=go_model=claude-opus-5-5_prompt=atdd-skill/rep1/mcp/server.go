// Package mcp exposes the soccer knowledge base as a Model Context Protocol
// server speaking newline-delimited JSON-RPC 2.0 over stdio.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"

	"brsoccer/soccer"
)

type tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	handler     func(soccer.Args) (string, error)
}

func schema(props map[string]string, required ...string) map[string]any {
	p := map[string]any{}
	for k, desc := range props {
		typ := "string"
		switch k {
		case "season", "limit", "min_overall":
			typ = "integer"
		case "finals_only", "all_clubs":
			typ = "boolean"
		}
		p[k] = map[string]any{"type": typ, "description": desc}
	}
	s := map[string]any{"type": "object", "properties": p}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

const (
	dTeam   = "Team name; any spelling works (e.g. 'São Paulo', 'Sao Paulo-SP', 'Palmeiras')"
	dComp   = "Competition: 'Brasileirão Série A', 'Brasileirão Série B', 'Série C', 'Copa do Brasil', 'Libertadores'"
	dSeason = "Season year, e.g. 2019"
)

type Server struct {
	tools []tool
}

func New(db *soccer.DB) *Server {
	return &Server{tools: []tool{
		{"search_matches", "Find matches by team, opponent, competition, season, date range, stage or finals.", schema(map[string]string{
			"team": dTeam, "opponent": "Opponent team", "competition": dComp, "season": dSeason, "venue": "home or away (relative to team)",
			"date_from": "Start date (YYYY-MM-DD or DD/MM/YYYY)", "date_to": "End date", "stage": "Libertadores stage, e.g. final",
			"finals_only": "Only cup finals", "limit": "Max matches listed (default 50)"}), db.SearchMatches},
		{"last_meeting", "Most recent match between two teams, with the score.", schema(map[string]string{"team_a": dTeam, "team_b": dTeam, "competition": dComp}, "team_a", "team_b"), db.LastMeeting},
		{"head_to_head", "Head-to-head record between two teams.", schema(map[string]string{"team_a": dTeam, "team_b": dTeam, "competition": dComp, "season": dSeason}, "team_a", "team_b"), db.HeadToHead},
		{"team_record", "Win/draw/loss and goals record for a team, optionally by season, competition and home/away.", schema(map[string]string{
			"team": dTeam, "season": dSeason, "competition": dComp, "venue": "home, away or all", "date_from": "Start date", "date_to": "End date"}, "team"), db.TeamRecord},
		{"team_competitions", "Competitions a team has played in.", schema(map[string]string{"team": dTeam}, "team"), db.TeamCompetitions},
		{"team_ranking", "Rank teams by points, goals_for, goals_against, win_rate, home_win_rate or away_win_rate.", schema(map[string]string{
			"by": "points|goals_for|goals_against|win_rate|home_win_rate|away_win_rate", "season": dSeason, "competition": dComp, "limit": "Number of teams (default 10)"}), db.TeamRanking},
		{"standings", "League table for a season calculated from match results, with champion and relegated teams.", schema(map[string]string{"season": dSeason, "competition": dComp + " (default Série A)"}, "season"), db.Standings},
		{"libertadores_bracket", "Copa Libertadores knockout matches for a season.", schema(map[string]string{"season": dSeason}, "season"), db.LibertadoresBracket},
		{"stats_summary", "Aggregate statistics: average goals per match, home/away/draw rates.", schema(map[string]string{"competition": dComp, "season": dSeason, "team": dTeam}), db.StatsSummary},
		{"biggest_wins", "Matches with the largest winning margins.", schema(map[string]string{"competition": dComp, "season": dSeason, "team": dTeam, "limit": "Number of matches (default 10)"}), db.BiggestWins},
		{"derbies", "Traditional Brazilian derby matches (Fla-Flu, Grenal, Derby Paulista...).", schema(map[string]string{"season": dSeason, "competition": dComp}), db.Derbies},
		{"search_players", "Search FIFA player data by name, nationality, club, position; sorted by overall rating.", schema(map[string]string{
			"name": "Player name (partial)", "nationality": "e.g. Brazil", "club": "Club name (partial, accents optional)",
			"position": "e.g. GK, ST, or forward/midfielder/defender/goalkeeper", "min_overall": "Minimum overall rating", "limit": "Max players (default 20)"}), db.SearchPlayers},
		{"club_summary", "Player counts and average rating per Brazilian club, optionally filtered by nationality.", schema(map[string]string{
			"nationality": "e.g. Brazil", "position": "Position filter", "all_clubs": "Include non-Brazilian clubs"}), db.ClubSummary},
	}}
}

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

// Serve handles requests until in is closed.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	sc := bufio.NewScanner(in)
	sc.Buffer(make([]byte, 1<<20), 16<<20)
	enc := json.NewEncoder(out)
	for sc.Scan() {
		var req request
		if err := json.Unmarshal(sc.Bytes(), &req); err != nil {
			enc.Encode(map[string]any{"jsonrpc": "2.0", "id": nil, "error": map[string]any{"code": -32700, "message": "parse error"}})
			continue
		}
		if len(req.ID) == 0 {
			continue // notification
		}
		result, rpcErr := s.handle(req)
		resp := map[string]any{"jsonrpc": "2.0", "id": req.ID}
		if rpcErr != nil {
			resp["error"] = rpcErr
		} else {
			resp["result"] = result
		}
		if err := enc.Encode(resp); err != nil {
			return err
		}
	}
	return sc.Err()
}

func (s *Server) handle(req request) (any, map[string]any) {
	switch req.Method {
	case "initialize":
		return map[string]any{
			"protocolVersion": "2024-11-05",
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": "brazilian-soccer", "version": "1.0.0"},
		}, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		return map[string]any{"tools": s.tools}, nil
	case "tools/call":
		var p struct {
			Name      string      `json:"name"`
			Arguments soccer.Args `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return nil, map[string]any{"code": -32602, "message": "invalid params"}
		}
		for _, t := range s.tools {
			if t.Name == p.Name {
				text, err := t.handler(p.Arguments)
				if err != nil {
					return map[string]any{"content": []any{map[string]any{"type": "text", "text": "Error: " + err.Error()}}, "isError": true}, nil
				}
				return map[string]any{"content": []any{map[string]any{"type": "text", "text": text}}}, nil
			}
		}
		return nil, map[string]any{"code": -32602, "message": fmt.Sprintf("unknown tool %q", p.Name)}
	}
	return nil, map[string]any{"code": -32601, "message": "method not found: " + req.Method}
}
