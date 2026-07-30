package main

import (
	"context"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"time"
)

type rpcRequest struct {
	JSONRPC, Method string
	ID              json.RawMessage `json:"id"`
	Params          json.RawMessage `json:"params"`
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
type Server struct{ db *Database }

func NewServer(db *Database) *Server { return &Server{db} }
func (s *Server) Handle(_ context.Context, r rpcRequest) rpcResponse {
	out := rpcResponse{JSONRPC: "2.0", ID: r.ID}
	switch r.Method {
	case "initialize":
		out.Result = map[string]any{"protocolVersion": "2024-11-05", "capabilities": map[string]any{"tools": map[string]any{}}, "serverInfo": map[string]string{"name": "brazilian-soccer-mcp", "version": "1.0.0"}}
	case "notifications/initialized":
		out.ID = nil
	case "tools/list":
		out.Result = map[string]any{"tools": toolDefinitions()}
	case "tools/call":
		var p struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if err := json.Unmarshal(r.Params, &p); err != nil {
			out.Error = &rpcError{-32602, "invalid tool arguments"}
			break
		}
		text, err := s.call(p.Name, p.Arguments)
		if err != nil {
			out.Result = map[string]any{"content": []any{map[string]string{"type": "text", "text": err.Error()}}, "isError": true}
		} else {
			out.Result = map[string]any{"content": []any{map[string]string{"type": "text", "text": text}}}
		}
	default:
		out.Error = &rpcError{-32601, "method not found"}
	}
	return out
}
func schema(props map[string]any, required ...string) map[string]any {
	return map[string]any{"type": "object", "properties": props, "required": required, "additionalProperties": false}
}
func toolDefinitions() []map[string]any {
	str := func(d string) map[string]any { return map[string]any{"type": "string", "description": d} }
	integer := func(d string) map[string]any { return map[string]any{"type": "integer", "description": d} }
	return []map[string]any{
		{"name": "search_matches", "description": "Find Brazilian soccer matches across every supplied match dataset.", "inputSchema": schema(map[string]any{"team": str("team playing in the match"), "opponent": str("other team; makes a head-to-head search"), "competition": str("Brasileirao, Copa do Brasil, Libertadores, or a tournament name"), "season": integer("season year"), "from": str("inclusive YYYY-MM-DD date"), "to": str("inclusive YYYY-MM-DD date"), "stage": str("cup stage or round text"), "limit": integer("maximum results, default 25")})},
		{"name": "team_statistics", "description": "Calculate a team's record, goals, and win rate from loaded match results.", "inputSchema": schema(map[string]any{"team": str("team name"), "season": integer("optional season"), "competition": str("optional competition"), "venue": str("home, away, or all")}, "team")},
		{"name": "head_to_head", "description": "Compare two teams, including wins and draws.", "inputSchema": schema(map[string]any{"team1": str("first team"), "team2": str("second team"), "season": integer("optional season"), "competition": str("optional competition")}, "team1", "team2")},
		{"name": "search_players", "description": "Search FIFA players by name, nationality, club, or position, sorted by rating.", "inputSchema": schema(map[string]any{"name": str("partial player name"), "nationality": str("nationality such as Brazil"), "club": str("partial club name"), "position": str("position such as ST"), "limit": integer("maximum results, default 25")})},
		{"name": "standings", "description": "Calculate a competition table from match results for one season.", "inputSchema": schema(map[string]any{"season": integer("season year"), "competition": str("defaults to Brasileirao")}, "season")},
		{"name": "competition_statistics", "description": "Calculate match count, goals per match, and home/draw/away win rates.", "inputSchema": schema(map[string]any{"competition": str("optional competition"), "season": integer("optional season")})},
		{"name": "biggest_wins", "description": "Return matches with the largest winning margin.", "inputSchema": schema(map[string]any{"competition": str("optional competition"), "season": integer("optional season"), "limit": integer("maximum results, default 10")})},
	}
}
func argStr(a map[string]any, k string) string { v, _ := a[k].(string); return strings.TrimSpace(v) }
func argInt(a map[string]any, k string) int {
	switch v := a[k].(type) {
	case float64:
		return int(v)
	case int:
		return v
	case json.Number:
		n, _ := v.Int64()
		return int(n)
	}
	return 0
}
func matchesFor(db *Database, a map[string]any) []Match {
	team, opp, comp, stage := argStr(a, "team"), argStr(a, "opponent"), normalize(argStr(a, "competition")), normalize(argStr(a, "stage"))
	year := argInt(a, "season")
	from, _ := dateArg(argStr(a, "from"))
	to, _ := dateArg(argStr(a, "to"))
	var out []Match
	for _, m := range db.Matches {
		if team != "" && !teamMatches(team, m.Home) && !teamMatches(team, m.Away) {
			continue
		}
		if opp != "" && !teamMatches(opp, m.Home) && !teamMatches(opp, m.Away) {
			continue
		}
		if comp != "" && !strings.Contains(normalize(m.Competition), comp) {
			continue
		}
		if stage != "" && !strings.Contains(normalize(m.Stage+" "+m.Round), stage) {
			continue
		}
		if year != 0 && m.Season != year {
			continue
		}
		if !from.IsZero() && m.Date.Before(from) {
			continue
		}
		if !to.IsZero() && m.Date.After(to.Add(24*time.Hour)) {
			continue
		}
		out = append(out, m)
	}
	return out
}
func dateArg(s string) (time.Time, error) {
	if s == "" {
		return time.Time{}, nil
	}
	return parseDate(s)
}
func fmtMatch(m Match) string {
	detail := m.Competition
	if m.Stage != "" {
		detail += " " + m.Stage
	} else if m.Round != "" {
		detail += " Round " + m.Round
	}
	return fmt.Sprintf("%s: %s %d-%d %s (%s)", m.Date.Format("2006-01-02"), m.Home, m.HomeGoals, m.AwayGoals, m.Away, detail)
}
func (s *Server) call(name string, a map[string]any) (string, error) {
	switch name {
	case "search_matches":
		ms := matchesFor(s.db, a)
		return formatMatches(ms, argInt(a, "limit")), nil
	case "team_statistics":
		return s.teamStats(a)
	case "head_to_head":
		return s.h2h(a)
	case "search_players":
		return s.players(a), nil
	case "standings":
		return s.standings(a)
	case "competition_statistics":
		return s.competitionStats(a), nil
	case "biggest_wins":
		return s.biggest(a), nil
	}
	return "", fmt.Errorf("unknown tool %q", name)
}
func formatMatches(ms []Match, limit int) string {
	if limit <= 0 {
		limit = 25
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d match(es) found\n", len(ms))
	for i, m := range ms {
		if i >= limit {
			fmt.Fprintf(&b, "... %d more match(es)", len(ms)-limit)
			break
		}
		fmt.Fprintf(&b, "- %s\n", fmtMatch(m))
	}
	return strings.TrimSpace(b.String())
}

type record struct{ Played, W, D, L, GF, GA, Points int }

func addRecord(r *record, gf, ga int) {
	r.Played++
	r.GF += gf
	r.GA += ga
	if gf > ga {
		r.W++
		r.Points += 3
	} else if gf == ga {
		r.D++
		r.Points++
	} else {
		r.L++
	}
}
func (s *Server) teamStats(a map[string]any) (string, error) {
	team := argStr(a, "team")
	ms := matchesFor(s.db, a)
	venue := strings.ToLower(argStr(a, "venue"))
	r := record{}
	for _, m := range ms {
		if teamMatches(team, m.Home) && (venue == "" || venue == "all" || venue == "home") {
			addRecord(&r, m.HomeGoals, m.AwayGoals)
		}
		if teamMatches(team, m.Away) && (venue == "" || venue == "all" || venue == "away") {
			addRecord(&r, m.AwayGoals, m.HomeGoals)
		}
	}
	if r.Played == 0 {
		return "No matching matches found.", nil
	}
	return fmt.Sprintf("%s record: %d matches | %dW %dD %dL | goals %d for, %d against | points %d | win rate %.1f%%", team, r.Played, r.W, r.D, r.L, r.GF, r.GA, r.Points, 100*float64(r.W)/float64(r.Played)), nil
}
func (s *Server) h2h(a map[string]any) (string, error) {
	t1, t2 := argStr(a, "team1"), argStr(a, "team2")
	ms := matchesFor(s.db, map[string]any{"team": t1, "opponent": t2, "season": a["season"], "competition": a["competition"]})
	w1, w2, d := 0, 0, 0
	for _, m := range ms {
		var x, y int
		if teamMatches(t1, m.Home) {
			x, y = m.HomeGoals, m.AwayGoals
		} else {
			x, y = m.AwayGoals, m.HomeGoals
		}
		if x > y {
			w1++
		} else if y > x {
			w2++
		} else {
			d++
		}
	}
	return fmt.Sprintf("%s vs %s: %d matches | %s %d wins, %s %d wins, %d draws\n%s", t1, t2, len(ms), t1, w1, t2, w2, d, formatMatches(ms, 10)), nil
}
func (s *Server) players(a map[string]any) string {
	n, nat, club, pos := normalize(argStr(a, "name")), normalize(argStr(a, "nationality")), normalize(argStr(a, "club")), normalize(argStr(a, "position"))
	limit := argInt(a, "limit")
	if limit <= 0 {
		limit = 25
	}
	var b strings.Builder
	count := 0
	for _, p := range s.db.Players {
		if n != "" && !strings.Contains(normalize(p.Name), n) {
			continue
		}
		if nat != "" && !strings.Contains(normalize(p.Nationality), nat) {
			continue
		}
		if club != "" && !strings.Contains(normalize(p.Club), club) {
			continue
		}
		if pos != "" && !strings.EqualFold(p.Position, pos) {
			continue
		}
		count++
		if count <= limit {
			fmt.Fprintf(&b, "- %s — Overall %d, Potential %d, %s, %s, age %d\n", p.Name, p.Overall, p.Potential, p.Position, p.Club, p.Age)
		}
	}
	if count == 0 {
		return "No players found."
	}
	if count > limit {
		fmt.Fprintf(&b, "... %d more player(s)", count-limit)
	}
	return fmt.Sprintf("%d player(s) found\n%s", count, strings.TrimSpace(b.String()))
}
func (s *Server) standings(a map[string]any) (string, error) {
	if argStr(a, "competition") == "" {
		a = clone(a)
		a["competition"] = "Brasileirao"
	}
	ms := matchesFor(s.db, a)
	// The historical file overlaps the modern Brasileirão file.  Prefer the
	// dedicated modern source when it covers the requested season so points are
	// not counted twice; the historical source remains fully searchable.
	if normalize(argStr(a, "competition")) == "brasileirao" {
		modern := make([]Match, 0, len(ms))
		for _, m := range ms {
			if m.Source == "Brasileirao_Matches.csv" {
				modern = append(modern, m)
			}
		}
		if len(modern) > 0 {
			ms = modern
		}
	}
	table := map[string]*record{}
	names := map[string]string{}
	for _, m := range ms {
		h, aw := normalize(m.Home), normalize(m.Away)
		if table[h] == nil {
			table[h] = &record{}
			names[h] = m.Home
		}
		if table[aw] == nil {
			table[aw] = &record{}
			names[aw] = m.Away
		}
		addRecord(table[h], m.HomeGoals, m.AwayGoals)
		addRecord(table[aw], m.AwayGoals, m.HomeGoals)
	}
	type row struct {
		k string
		r *record
	}
	rows := []row{}
	for k, r := range table {
		rows = append(rows, row{k, r})
	}
	sort.Slice(rows, func(i, j int) bool {
		a, b := rows[i].r, rows[j].r
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.GF-a.GA != b.GF-b.GA {
			return a.GF-a.GA > b.GF-b.GA
		}
		return a.GF > b.GF
	})
	var b strings.Builder
	fmt.Fprintf(&b, "Standings (%s %d; %d matches)\n", argStr(a, "competition"), argInt(a, "season"), len(ms))
	for i, x := range rows {
		fmt.Fprintf(&b, "%d. %s — %d pts (%dW %dD %dL, GF %d GA %d)\n", i+1, names[x.k], x.r.Points, x.r.W, x.r.D, x.r.L, x.r.GF, x.r.GA)
	}
	return strings.TrimSpace(b.String()), nil
}
func clone(a map[string]any) map[string]any {
	b := map[string]any{}
	for k, v := range a {
		b[k] = v
	}
	return b
}
func (s *Server) competitionStats(a map[string]any) string {
	ms := matchesFor(s.db, a)
	if len(ms) == 0 {
		return "No matching matches found."
	}
	goals, hw, d, aw := 0, 0, 0, 0
	for _, m := range ms {
		goals += m.HomeGoals + m.AwayGoals
		if m.HomeGoals > m.AwayGoals {
			hw++
		} else if m.HomeGoals < m.AwayGoals {
			aw++
		} else {
			d++
		}
	}
	n := float64(len(ms))
	return fmt.Sprintf("%d matches | %.2f goals/match | home wins %.1f%% | draws %.1f%% | away wins %.1f%%", len(ms), float64(goals)/n, 100*float64(hw)/n, 100*float64(d)/n, 100*float64(aw)/n)
}
func (s *Server) biggest(a map[string]any) string {
	ms := matchesFor(s.db, a)
	sort.SliceStable(ms, func(i, j int) bool {
		return abs(ms[i].HomeGoals-ms[i].AwayGoals) > abs(ms[j].HomeGoals-ms[j].AwayGoals)
	})
	return formatMatches(ms, argInt(a, "limit"))
}
func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}
