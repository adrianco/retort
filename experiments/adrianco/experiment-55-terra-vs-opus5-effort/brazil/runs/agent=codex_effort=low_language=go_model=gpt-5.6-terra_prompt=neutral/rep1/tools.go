package main

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"time"
)

type toolCall struct {
	Name      string         `json:"name"`
	Arguments map[string]any `json:"arguments"`
}

func toolDefinitions() []map[string]any {
	return []map[string]any{
		{"name": "search_matches", "description": "Find Brazilian soccer matches by one or two teams, competition, season, and date range.", "inputSchema": schema(map[string]any{"team": "string", "opponent": "string", "competition": "string", "season": "integer", "from": "YYYY-MM-DD", "to": "YYYY-MM-DD", "limit": "integer"})},
		{"name": "team_statistics", "description": "Calculate a team's record, goals, and win rate.", "inputSchema": schema(map[string]any{"team": "string", "season": "integer", "competition": "string", "venue": "home, away, or all"})},
		{"name": "head_to_head", "description": "Compare two teams, including wins, draws, goals, and matches.", "inputSchema": schema(map[string]any{"team": "string", "opponent": "string", "season": "integer", "competition": "string"})},
		{"name": "search_players", "description": "Search FIFA players by name, nationality, club, position; returns highest rated first.", "inputSchema": schema(map[string]any{"name": "string", "nationality": "string", "club": "string", "position": "string", "limit": "integer"})},
		{"name": "standings", "description": "Calculate league standings from match results for a competition and season.", "inputSchema": schema(map[string]any{"season": "integer", "competition": "string"})},
		{"name": "competition_statistics", "description": "Aggregate goals, results, and biggest wins for a competition.", "inputSchema": schema(map[string]any{"competition": "string", "season": "integer"})},
	}
}
func schema(props map[string]any) map[string]any {
	return map[string]any{"type": "object", "properties": props}
}
func callTool(db *Database, raw json.RawMessage) (any, *rpcError) {
	var c toolCall
	if e := json.Unmarshal(raw, &c); e != nil {
		return nil, &rpcError{-32602, "invalid params"}
	}
	var v any
	var e error
	switch c.Name {
	case "search_matches":
		v = searchMatches(db, c.Arguments)
	case "team_statistics":
		v, e = teamStats(db, c.Arguments)
	case "head_to_head":
		v, e = head(db, c.Arguments)
	case "search_players":
		v = players(db, c.Arguments)
	case "standings":
		v, e = standings(db, c.Arguments)
	case "competition_statistics":
		v, e = competitionStats(db, c.Arguments)
	default:
		return nil, &rpcError{-32602, "unknown tool"}
	}
	if e != nil {
		return nil, &rpcError{-32602, e.Error()}
	}
	b, _ := json.Marshal(v)
	return map[string]any{"content": []map[string]string{{"type": "text", "text": string(b)}}, "structuredContent": v}, nil
}
func str(a map[string]any, k string) string { v, _ := a[k].(string); return v }
func integer(a map[string]any, k string) int {
	switch v := a[k].(type) {
	case float64:
		return int(v)
	case int:
		return v
	}
	return 0
}
func filtered(db *Database, a map[string]any) []Match {
	var o []Match
	season := integer(a, "season")
	comp := str(a, "competition")
	from := parseDate(str(a, "from"))
	to := parseDate(str(a, "to"))
	for _, m := range db.Matches {
		if season > 0 && m.Season != season {
			continue
		}
		if comp != "" && !strings.Contains(norm(m.Competition), norm(comp)) {
			continue
		}
		if !from.IsZero() && m.Date.Before(from) {
			continue
		}
		if !to.IsZero() && m.Date.After(to.Add(24*time.Hour)) {
			continue
		}
		o = append(o, m)
	}
	return o
}
func searchMatches(db *Database, a map[string]any) any {
	ms := filtered(db, a)
	t, o := str(a, "team"), str(a, "opponent")
	res := []Match{}
	for _, m := range ms {
		if t != "" && !teamMatch(m.Home, t) && !teamMatch(m.Away, t) {
			continue
		}
		if o != "" && !((teamMatch(m.Home, t) && teamMatch(m.Away, o)) || (teamMatch(m.Away, t) && teamMatch(m.Home, o))) {
			continue
		}
		res = append(res, m)
	}
	sort.Slice(res, func(i, j int) bool { return res[i].Date.After(res[j].Date) })
	l := integer(a, "limit")
	if l == 0 {
		l = 50
	}
	if len(res) > l {
		res = res[:l]
	}
	return map[string]any{"count": len(res), "matches": res}
}

type record struct {
	Matches      int     `json:"matches"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	WinRate      float64 `json:"win_rate"`
}

func teamStats(db *Database, a map[string]any) (any, error) {
	t := str(a, "team")
	if t == "" {
		return nil, fmt.Errorf("team is required")
	}
	r := record{}
	venue := str(a, "venue")
	for _, m := range filtered(db, a) {
		home, away := teamMatch(m.Home, t), teamMatch(m.Away, t)
		if (!home && !away) || (venue == "home" && !home) || (venue == "away" && !away) {
			continue
		}
		gf, ga := m.AwayGoals, m.HomeGoals
		if home {
			gf, ga = m.HomeGoals, m.AwayGoals
		}
		r.Matches++
		r.GoalsFor += gf
		r.GoalsAgainst += ga
		if gf > ga {
			r.Wins++
		} else if gf == ga {
			r.Draws++
		} else {
			r.Losses++
		}
	}
	if r.Matches > 0 {
		r.WinRate = float64(r.Wins) * 100 / float64(r.Matches)
	}
	return map[string]any{"team": t, "record": r}, nil
}
func head(db *Database, a map[string]any) (any, error) {
	t, o := str(a, "team"), str(a, "opponent")
	if t == "" || o == "" {
		return nil, fmt.Errorf("team and opponent are required")
	}
	r := record{}
	for _, m := range filtered(db, a) {
		if !((teamMatch(m.Home, t) && teamMatch(m.Away, o)) || (teamMatch(m.Away, t) && teamMatch(m.Home, o))) {
			continue
		}
		gf, ga := m.AwayGoals, m.HomeGoals
		if teamMatch(m.Home, t) {
			gf, ga = m.HomeGoals, m.AwayGoals
		}
		r.Matches++
		r.GoalsFor += gf
		r.GoalsAgainst += ga
		if gf > ga {
			r.Wins++
		} else if gf == ga {
			r.Draws++
		} else {
			r.Losses++
		}
	}
	return map[string]any{"team": t, "opponent": o, "team_record": r}, nil
}
func players(db *Database, a map[string]any) any {
	var r []Player
	for _, p := range db.Players {
		if (str(a, "name") != "" && !strings.Contains(norm(p.Name), norm(str(a, "name")))) || (str(a, "nationality") != "" && !strings.Contains(norm(p.Nationality), norm(str(a, "nationality")))) || (str(a, "club") != "" && !strings.Contains(norm(p.Club), norm(str(a, "club")))) || (str(a, "position") != "" && !strings.Contains(norm(p.Position), norm(str(a, "position")))) {
			continue
		}
		r = append(r, p)
	}
	sort.Slice(r, func(i, j int) bool { return r[i].Overall > r[j].Overall })
	l := integer(a, "limit")
	if l == 0 {
		l = 50
	}
	if len(r) > l {
		r = r[:l]
	}
	return map[string]any{"count": len(r), "players": r}
}

type tableRow struct {
	Team                                                                        string `json:"team"`
	Played, Points, Wins, Draws, Losses, GoalsFor, GoalsAgainst, GoalDifference int
}

func standings(db *Database, a map[string]any) (any, error) {
	if integer(a, "season") == 0 {
		return nil, fmt.Errorf("season is required")
	}
	tab := map[string]*tableRow{}
	for _, m := range filtered(db, a) {
		for _, x := range []struct {
			n      string
			gf, ga int
		}{{m.Home, m.HomeGoals, m.AwayGoals}, {m.Away, m.AwayGoals, m.HomeGoals}} {
			k := norm(x.n)
			if tab[k] == nil {
				tab[k] = &tableRow{Team: x.n}
			}
			r := tab[k]
			r.Played++
			r.GoalsFor += x.gf
			r.GoalsAgainst += x.ga
			r.GoalDifference = r.GoalsFor - r.GoalsAgainst
			if x.gf > x.ga {
				r.Wins++
				r.Points += 3
			} else if x.gf == x.ga {
				r.Draws++
				r.Points++
			} else {
				r.Losses++
			}
		}
	}
	out := make([]tableRow, 0, len(tab))
	for _, r := range tab {
		out = append(out, *r)
	}
	sort.Slice(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.GoalDifference != b.GoalDifference {
			return a.GoalDifference > b.GoalDifference
		}
		return a.GoalsFor > b.GoalsFor
	})
	return map[string]any{"season": integer(a, "season"), "standings": out}, nil
}
func competitionStats(db *Database, a map[string]any) (any, error) {
	ms := filtered(db, a)
	if len(ms) == 0 {
		return map[string]any{"matches": 0}, nil
	}
	goals, home, draw := 0, 0, 0
	best := ms[0]
	for _, m := range ms {
		goals += m.HomeGoals + m.AwayGoals
		if m.HomeGoals > m.AwayGoals {
			home++
		}
		if m.HomeGoals == m.AwayGoals {
			draw++
		}
		if abs(m.HomeGoals-m.AwayGoals) > abs(best.HomeGoals-best.AwayGoals) {
			best = m
		}
	}
	return map[string]any{"matches": len(ms), "average_goals": float64(goals) / float64(len(ms)), "home_win_rate": float64(home) * 100 / float64(len(ms)), "draw_rate": float64(draw) * 100 / float64(len(ms)), "biggest_win": best}, nil
}
func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
