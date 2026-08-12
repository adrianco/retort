package main

import (
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"
)

type Server struct{ Store *Store }
type MatchFilter struct {
	Team, Home, Away, Competition string
	Season                        int
	From, To                      string
	Limit                         int
}
type TeamStats struct {
	Team         string  `json:"team"`
	Matches      int     `json:"matches"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	WinRate      float64 `json:"win_rate"`
	Points       int     `json:"points,omitempty"`
}

func (s *Server) Matches(f MatchFilter) []Match {
	out := []Match{}
	from, to := parseDate(f.From), parseDate(f.To)
	for _, m := range s.Store.Matches {
		if f.Season != 0 && m.Season != f.Season || f.Competition != "" && !strings.Contains(clean(m.Competition), clean(f.Competition)) || f.Team != "" && !teamMatch(m.Home, f.Team) && !teamMatch(m.Away, f.Team) || f.Home != "" && !teamMatch(m.Home, f.Home) || f.Away != "" && !teamMatch(m.Away, f.Away) {
			continue
		}
		if !from.IsZero() && m.Date.Before(from) || !to.IsZero() && m.Date.After(to.Add(24*time.Hour)) {
			continue
		}
		out = append(out, m)
		if f.Limit > 0 && len(out) >= f.Limit {
			break
		}
	}
	return out
}
func (s *Server) Stats(team string, f MatchFilter) TeamStats {
	r := TeamStats{Team: team}
	f.Team = ""
	for _, m := range s.Matches(f) {
		home := teamMatch(m.Home, team)
		away := teamMatch(m.Away, team)
		if !home && !away {
			continue
		}
		r.Matches++
		if home {
			r.GoalsFor += m.HomeGoals
			r.GoalsAgainst += m.AwayGoals
			if m.HomeGoals > m.AwayGoals {
				r.Wins++
			} else if m.HomeGoals == m.AwayGoals {
				r.Draws++
			} else {
				r.Losses++
			}
		} else {
			r.GoalsFor += m.AwayGoals
			r.GoalsAgainst += m.HomeGoals
			if m.AwayGoals > m.HomeGoals {
				r.Wins++
			} else if m.HomeGoals == m.AwayGoals {
				r.Draws++
			} else {
				r.Losses++
			}
		}
	}
	if r.Matches > 0 {
		r.WinRate = float64(r.Wins) * 100 / float64(r.Matches)
	}
	return r
}
func (s *Server) Players(name, nationality, club, position string, minOverall, limit int) []Player {
	out := []Player{}
	for _, p := range s.Store.Players {
		if name != "" && !strings.Contains(clean(p.Name), clean(name)) || nationality != "" && !strings.Contains(clean(p.Nationality), clean(nationality)) || club != "" && !strings.Contains(clean(p.Club), clean(club)) || position != "" && !strings.EqualFold(p.Position, position) || p.Overall < minOverall {
			continue
		}
		out = append(out, p)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Overall > out[j].Overall })
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}
func (s *Server) Standings(season int, competition string) []TeamStats {
	m := map[string]*TeamStats{}
	for _, x := range s.Matches(MatchFilter{Season: season, Competition: competition}) {
		homeKey, awayKey := teamKey(x.Home), teamKey(x.Away)
		for _, pair := range [][2]string{{homeKey, x.Home}, {awayKey, x.Away}} {
			if _, ok := m[pair[0]]; !ok {
				m[pair[0]] = &TeamStats{Team: displayTeam(pair[1])}
			}
		}
		a, b := m[homeKey], m[awayKey]
		a.Matches++
		b.Matches++
		a.GoalsFor += x.HomeGoals
		a.GoalsAgainst += x.AwayGoals
		b.GoalsFor += x.AwayGoals
		b.GoalsAgainst += x.HomeGoals
		if x.HomeGoals > x.AwayGoals {
			a.Wins++
			b.Losses++
		} else if x.HomeGoals < x.AwayGoals {
			b.Wins++
			a.Losses++
		} else {
			a.Draws++
			b.Draws++
		}
	}
	out := []TeamStats{}
	for _, x := range m {
		x.WinRate = float64(x.Wins) * 100 / float64(max(1, x.Matches))
		x.Points = points(*x)
		out = append(out, *x)
	}
	sort.Slice(out, func(i, j int) bool {
		return points(out[i]) > points(out[j]) || points(out[i]) == points(out[j]) && out[i].GoalsFor-out[i].GoalsAgainst > out[j].GoalsFor-out[j].GoalsAgainst
	})
	return out
}
func points(t TeamStats) int { return t.Wins*3 + t.Draws }
func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
func (s *Server) CallTool(name string, args map[string]any) (any, error) {
	str := func(k string) string { v, _ := args[k].(string); return v }
	num := func(k string) int {
		switch v := args[k].(type) {
		case float64:
			return int(v)
		case json.Number:
			i, _ := strconv.Atoi(string(v))
			return i
		}
		return 0
	}
	switch name {
	case "search_matches":
		return s.Matches(MatchFilter{Team: str("team"), Home: str("home"), Away: str("away"), Competition: str("competition"), Season: num("season"), From: str("from"), To: str("to"), Limit: num("limit")}), nil
	case "team_stats":
		return s.Stats(str("team"), MatchFilter{Competition: str("competition"), Season: num("season"), From: str("from"), To: str("to")}), nil
	case "search_players":
		return s.Players(str("name"), str("nationality"), str("club"), str("position"), num("min_overall"), num("limit")), nil
	case "standings":
		return s.Standings(num("season"), str("competition")), nil
	case "statistics":
		ms := s.Matches(MatchFilter{Competition: str("competition"), Season: num("season")})
		goals := 0
		big := []Match{}
		for _, m := range ms {
			goals += m.HomeGoals + m.AwayGoals
			if abs(m.HomeGoals-m.AwayGoals) >= 3 {
				big = append(big, m)
			}
		}
		avg := 0.0
		if len(ms) > 0 {
			avg = float64(goals) / float64(len(ms))
		}
		return map[string]any{"matches": len(ms), "goals": goals, "average_goals_per_match": avg, "biggest_wins": big}, nil
	}
	return nil, fmt.Errorf("unknown tool %q", name)
}
func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
