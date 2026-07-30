package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"strings"
)

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}
type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}
type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}
type toolDef struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

func schema(properties map[string]any) map[string]any {
	return map[string]any{"type": "object", "properties": properties}
}
func stringProp(description string) map[string]any {
	return map[string]any{"type": "string", "description": description}
}
func intProp(description string) map[string]any {
	return map[string]any{"type": "integer", "description": description}
}
func toolsList() []toolDef {
	return []toolDef{
		{"search_matches", "Find matches from all supplied match datasets. Team matching is accent-insensitive and understands common club-name variants. Exact cross-source duplicates are suppressed unless source is specified.", schema(map[string]any{"team": stringProp("Team that played"), "opponent": stringProp("Opposing team"), "competition": stringProp("Brasileirão, Copa do Brasil, Copa Libertadores, Serie A, etc."), "season": intProp("Season year"), "source": stringProp("Optional CSV filename, e.g. BR-Football-Dataset.csv"), "date_from": stringProp("Inclusive ISO date"), "date_to": stringProp("Inclusive ISO date"), "limit": intProp("Maximum results, default 100")})},
		{"team_statistics", "Calculate a team's results, goals, and win rate.", schema(map[string]any{"team": stringProp("Team name"), "competition": stringProp("Optional competition"), "season": intProp("Optional season"), "home_only": map[string]any{"type": "boolean", "description": "Only home matches"}})},
		{"head_to_head", "Compare two teams and list their direct meetings.", schema(map[string]any{"team_a": stringProp("First team"), "team_b": stringProp("Second team"), "competition": stringProp("Optional competition"), "season": intProp("Optional season"), "limit": intProp("Meetings to display")})},
		{"search_players", "Search FIFA players by name, nationality, club, position, and rating.", schema(map[string]any{"name": stringProp("Player name"), "nationality": stringProp("Nationality"), "club": stringProp("Club"), "position": stringProp("Position"), "min_overall": intProp("Minimum overall rating"), "limit": intProp("Maximum results")})},
		{"competition_standings", "Calculate standings from results. Use a single competition and season for meaningful tables.", schema(map[string]any{"competition": stringProp("Competition, e.g. Brasileirão"), "season": intProp("Season year"), "limit": intProp("Teams to display")})},
		{"competition_statistics", "Calculate match, goal, home-win, and draw aggregates.", schema(map[string]any{"competition": stringProp("Optional competition"), "season": intProp("Optional season")})},
		{"team_rankings", "Rank teams by win rate for overall, home, or away results. Use this to answer best-home or best-away-record questions.", schema(map[string]any{"competition": stringProp("Optional competition"), "season": intProp("Optional season"), "venue": stringProp("overall (default), home, or away"), "limit": intProp("Teams to display")})},
		{"biggest_wins", "List the largest score margins in the loaded match results.", schema(map[string]any{"competition": stringProp("Optional competition"), "season": intProp("Optional season"), "limit": intProp("Matches to display, default 10")})},
	}
}

func object(raw json.RawMessage) map[string]any {
	var v map[string]any
	_ = json.Unmarshal(raw, &v)
	if v == nil {
		v = map[string]any{}
	}
	return v
}
func str(a map[string]any, k string) string {
	if v, ok := a[k].(string); ok {
		return v
	}
	return ""
}
func number(a map[string]any, k string) int {
	switch v := a[k].(type) {
	case float64:
		return int(v)
	case json.Number:
		n, _ := v.Int64()
		return int(n)
	}
	return 0
}
func boolArg(a map[string]any, k string) bool { v, _ := a[k].(bool); return v }
func toolText(s string) map[string]any {
	return map[string]any{"content": []map[string]string{{"type": "text", "text": s}}}
}
func toolError(s string) map[string]any {
	return map[string]any{"content": []map[string]string{{"type": "text", "text": s}}, "isError": true}
}

func (r *Repository) callTool(name string, a map[string]any) map[string]any {
	switch name {
	case "search_matches":
		ms := r.SearchMatches(MatchFilter{Team: str(a, "team"), Opponent: str(a, "opponent"), Competition: str(a, "competition"), Source: str(a, "source"), Season: number(a, "season"), DateFrom: str(a, "date_from"), DateTo: str(a, "date_to"), Limit: number(a, "limit")})
		lines := []string{fmt.Sprintf("%d match(es) found:", len(ms))}
		for _, m := range ms {
			lines = append(lines, formatMatch(m))
		}
		return toolText(strings.Join(lines, "\n"))
	case "team_statistics":
		team := str(a, "team")
		if team == "" {
			return toolError("team is required")
		}
		s := r.TeamStatistics(team, str(a, "competition"), number(a, "season"), boolArg(a, "home_only"))
		rate := 0.0
		if s.Matches > 0 {
			rate = 100 * float64(s.Wins) / float64(s.Matches)
		}
		scope := strings.TrimSpace(fmt.Sprintf("%s %d", str(a, "competition"), number(a, "season")))
		return toolText(fmt.Sprintf("%s record (%s):\nMatches: %d\nWins: %d, Draws: %d, Losses: %d\nGoals for: %d, Goals against: %d\nWin rate: %.1f%%", team, scope, s.Matches, s.Wins, s.Draws, s.Losses, s.GoalsFor, s.GoalsAgainst, rate))
	case "head_to_head":
		x, y := str(a, "team_a"), str(a, "team_b")
		if x == "" || y == "" {
			return toolError("team_a and team_b are required")
		}
		as, bs, ms := r.HeadToHead(x, y, str(a, "competition"), number(a, "season"))
		limit := number(a, "limit")
		if limit <= 0 {
			limit = 20
		}
		if len(ms) > limit {
			ms = ms[:limit]
		}
		lines := []string{fmt.Sprintf("%s vs %s: %d meetings", x, y, as.Matches), fmt.Sprintf("%s: %d wins; %s: %d wins; Draws: %d", x, as.Wins, y, bs.Wins, as.Draws)}
		for _, m := range ms {
			lines = append(lines, formatMatch(m))
		}
		return toolText(strings.Join(lines, "\n"))
	case "search_players":
		ps := r.SearchPlayers(PlayerFilter{Name: str(a, "name"), Nationality: str(a, "nationality"), Club: str(a, "club"), Position: str(a, "position"), MinOverall: number(a, "min_overall"), Limit: number(a, "limit")})
		lines := []string{fmt.Sprintf("%d player(s) found:", len(ps))}
		for _, p := range ps {
			lines = append(lines, fmt.Sprintf("- %s — Overall %d, %s, %s, %s", p.Name, p.Overall, p.Position, p.Club, p.Nationality))
		}
		return toolText(strings.Join(lines, "\n"))
	case "competition_standings":
		comp := str(a, "competition")
		season := number(a, "season")
		if comp == "" || season == 0 {
			return toolError("competition and season are required")
		}
		ss := r.Standings(comp, season)
		limit := number(a, "limit")
		if limit <= 0 {
			limit = 30
		}
		if len(ss) > limit {
			ss = ss[:limit]
		}
		lines := []string{fmt.Sprintf("%s %d standings (calculated from loaded results):", comp, season)}
		for i, s := range ss {
			lines = append(lines, fmt.Sprintf("%d. %s — %d pts (%dW %dD %dL, GF %d GA %d)", i+1, s.Team, s.Points, s.Wins, s.Draws, s.Losses, s.GoalsFor, s.GoalsAgainst))
		}
		return toolText(strings.Join(lines, "\n"))
	case "competition_statistics":
		n, g, hw, d := r.Summary(str(a, "competition"), number(a, "season"))
		if n == 0 {
			return toolText("No matches found.")
		}
		return toolText(fmt.Sprintf("%s %d: %d matches, %.2f goals/match, home wins %.1f%%, draws %.1f%%", str(a, "competition"), number(a, "season"), n, float64(g)/float64(n), 100*float64(hw)/float64(n), 100*float64(d)/float64(n)))
	case "team_rankings":
		venue := strings.ToLower(str(a, "venue"))
		if venue != "home" && venue != "away" {
			venue = "overall"
		}
		ranked := r.RankTeams(str(a, "competition"), number(a, "season"), venue)
		limit := number(a, "limit")
		if limit <= 0 {
			limit = 10
		}
		if len(ranked) > limit {
			ranked = ranked[:limit]
		}
		lines := []string{fmt.Sprintf("Best %s records (%s %d):", venue, str(a, "competition"), number(a, "season"))}
		for i, s := range ranked {
			lines = append(lines, fmt.Sprintf("%d. %s — %.1f%% win rate (%dW %dD %dL, %d matches)", i+1, s.Team, s.WinRate, s.Wins, s.Draws, s.Losses, s.Matches))
		}
		return toolText(strings.Join(lines, "\n"))
	case "biggest_wins":
		ms := r.BiggestWins(str(a, "competition"), number(a, "season"), number(a, "limit"))
		lines := []string{fmt.Sprintf("Biggest wins (%s %d):", str(a, "competition"), number(a, "season"))}
		for _, m := range ms {
			lines = append(lines, formatMatch(m))
		}
		return toolText(strings.Join(lines, "\n"))
	default:
		return toolError("unknown tool: " + name)
	}
}

func Serve(r *Repository, in io.Reader, out io.Writer) error {
	sc := bufio.NewScanner(in)
	sc.Buffer(make([]byte, 4096), 4*1024*1024)
	enc := json.NewEncoder(out)
	for sc.Scan() {
		var req rpcRequest
		if err := json.Unmarshal(sc.Bytes(), &req); err != nil {
			_ = enc.Encode(rpcResponse{JSONRPC: "2.0", Error: &rpcError{-32700, "parse error"}})
			continue
		}
		if len(req.ID) == 0 {
			continue
		}
		res := rpcResponse{JSONRPC: "2.0", ID: req.ID}
		switch req.Method {
		case "initialize":
			res.Result = map[string]any{"protocolVersion": "2024-11-05", "capabilities": map[string]any{"tools": map[string]any{}}, "serverInfo": map[string]string{"name": "brazilian-soccer", "version": "1.0.0"}}
		case "tools/list":
			res.Result = map[string]any{"tools": toolsList()}
		case "tools/call":
			var p struct {
				Name      string          `json:"name"`
				Arguments json.RawMessage `json:"arguments"`
			}
			if err := json.Unmarshal(req.Params, &p); err != nil {
				res.Error = &rpcError{-32602, "invalid tool arguments"}
			} else {
				res.Result = r.callTool(p.Name, object(p.Arguments))
			}
		default:
			res.Error = &rpcError{-32601, "method not found"}
		}
		if err := enc.Encode(res); err != nil {
			return err
		}
	}
	return sc.Err()
}
