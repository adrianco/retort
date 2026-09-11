package main

import (
	"fmt"
	"sort"
	"strings"
)

type Filter struct {
	Team        string `json:"team,omitempty"`
	Opponent    string `json:"opponent,omitempty"`
	Venue       string `json:"venue,omitempty"`
	Competition string `json:"competition,omitempty"`
	Season      int    `json:"season,omitempty"`
	From        string `json:"from,omitempty"`
	To          string `json:"to,omitempty"`
	Round       string `json:"round,omitempty"`
	Stage       string `json:"stage,omitempty"`
	Source      string `json:"source,omitempty"`
	Derbies     bool   `json:"derbies,omitempty"`
	Limit       int    `json:"limit,omitempty"`
	Offset      int    `json:"offset,omitempty"`
	Sort        string `json:"sort,omitempty"`
	Name        string `json:"name,omitempty"`
	Nationality string `json:"nationality,omitempty"`
	Club        string `json:"club,omitempty"`
	Position    string `json:"position,omitempty"`
}

func (f Filter) validate() error {
	if f.Season < 0 {
		return fmt.Errorf("season must be nonnegative")
	}
	if f.Sort != "" && f.Sort != "biggest_win" && f.Sort != "goals" {
		return fmt.Errorf("sort must be biggest_win or goals")
	}
	if f.Opponent != "" && f.Team != "" && team(f.Team) == team(f.Opponent) {
		return fmt.Errorf("team and opponent must differ")
	}
	if f.Venue != "" && f.Venue != "home" && f.Venue != "away" && f.Venue != "either" {
		return fmt.Errorf("venue must be home, away, or either")
	}
	if f.Limit < 0 || f.Limit > 1000 || f.Offset < 0 {
		return fmt.Errorf("limit must be 0..1000 and offset nonnegative")
	}
	for _, d := range []string{f.From, f.To} {
		if d != "" {
			p, e := parseDate(d)
			if e != nil || p != d {
				return fmt.Errorf("dates must be YYYY-MM-DD")
			}
		}
	}
	if f.From != "" && f.To != "" && f.From > f.To {
		return fmt.Errorf("from must not exceed to")
	}
	return nil
}
func derby(a, b string) bool {
	for _, p := range [][2]string{{"flamengo", "fluminense"}, {"flamengo", "vasco"}, {"botafogo", "flamengo"}, {"botafogo", "fluminense"}, {"botafogo", "vasco"}, {"fluminense", "vasco"}, {"palmeiras", "corinthians"}, {"palmeiras", "santos"}, {"palmeiras", "sao paulo"}, {"corinthians", "sao paulo"}, {"corinthians", "santos"}, {"sao paulo", "santos"}, {"gremio", "internacional"}, {"atletico-mg", "cruzeiro"}, {"bahia", "vitoria"}, {"athletico-pr", "coritiba"}, {"ceara", "fortaleza"}} {
		if a == p[0] && b == p[1] || a == p[1] && b == p[0] {
			return true
		}
	}
	return false
}
func (g *Graph) matches(f Filter) []Match {
	out := []Match{}
	a, b := team(f.Team), team(f.Opponent)
	for _, m := range g.Matches {
		if (f.From != "" || f.To != "") && m.Date == "" {
			continue
		}
		if a != "" {
			if f.Venue == "home" && m.Home != a || f.Venue == "away" && m.Away != a || m.Home != a && m.Away != a {
				continue
			}
		}
		if b != "" {
			if a != "" {
				if !(m.Home == a && m.Away == b || m.Home == b && m.Away == a) {
					continue
				}
			} else if m.Home != b && m.Away != b {
				continue
			}
		}
		if f.Competition != "" && fold(m.Competition) != fold(competition(f.Competition)) || f.Season != 0 && m.Season != f.Season || f.From != "" && m.Date < f.From || f.To != "" && m.Date > f.To || f.Round != "" && fold(m.Round) != fold(f.Round) || f.Stage != "" && fold(m.Stage) != fold(f.Stage) || f.Derbies && !derby(m.Home, m.Away) {
			continue
		}
		if f.Source != "" {
			found := false
			for _, s := range m.Sources {
				if s == f.Source {
					found = true
				}
			}
			if !found {
				continue
			}
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if f.Sort == "biggest_win" {
			di, dj := margin(out[i]), margin(out[j])
			if di != dj {
				return di > dj
			}
		}
		if out[i].Date == out[j].Date {
			return out[i].ID < out[j].ID
		}
		return out[i].Date > out[j].Date
	})
	return out
}
func margin(m Match) int {
	if m.HomeGoals == nil || m.AwayGoals == nil {
		return -1
	}
	d := *m.HomeGoals - *m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}
func page[T any](items []T, f Filter) []T {
	start := f.Offset
	if start > len(items) {
		start = len(items)
	}
	n := f.Limit
	if n == 0 {
		n = 50
	}
	end := start + n
	if end > len(items) {
		end = len(items)
	}
	return items[start:end]
}

type Record struct {
	Team           string  `json:"team"`
	Played         int     `json:"played"`
	Wins           int     `json:"wins"`
	Draws          int     `json:"draws"`
	Losses         int     `json:"losses"`
	GoalsFor       int     `json:"goals_for"`
	GoalsAgainst   int     `json:"goals_against"`
	GoalDifference int     `json:"goal_difference"`
	Points         int     `json:"points"`
	WinRate        float64 `json:"win_rate"`
}

func (r *Record) add(gf, ga int) {
	r.Played++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	r.GoalDifference = r.GoalsFor - r.GoalsAgainst
	if gf > ga {
		r.Wins++
		r.Points += 3
	} else if gf == ga {
		r.Draws++
		r.Points++
	} else {
		r.Losses++
	}
	r.WinRate = 100 * float64(r.Wins) / float64(r.Played)
}
func records(ms []Match, venue string) []Record {
	rs := map[string]*Record{}
	for _, m := range ms {
		if m.HomeGoals == nil || m.AwayGoals == nil {
			continue
		}
		for i, t := range []string{m.Home, m.Away} {
			if venue == "home" && i == 1 || venue == "away" && i == 0 {
				continue
			}
			if rs[t] == nil {
				rs[t] = &Record{Team: t}
			}
			if i == 0 {
				rs[t].add(*m.HomeGoals, *m.AwayGoals)
			} else {
				rs[t].add(*m.AwayGoals, *m.HomeGoals)
			}
		}
	}
	out := []Record{}
	for _, r := range rs {
		out = append(out, *r)
	}
	sort.Slice(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDifference != b.GoalDifference {
			return a.GoalDifference > b.GoalDifference
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	return out
}
func (g *Graph) players(f Filter) []Player {
	out := []Player{}
	for _, p := range g.Players {
		if f.Name != "" && !strings.Contains(fold(p.Name), fold(f.Name)) || f.Club != "" && !strings.Contains(p.Club, team(f.Club)) || f.Nationality != "" && fold(p.Nationality) != fold(f.Nationality) {
			continue
		}
		if f.Position != "" {
			pos := strings.ToUpper(f.Position)
			if fold(f.Position) == "forward" || fold(f.Position) == "forwards" {
				if !strings.Contains("|ST|CF|LF|RF|LW|RW|LS|RS|", "|"+p.Position+"|") {
					continue
				}
			} else if p.Position != pos {
				continue
			}
		}
		out = append(out, p)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Overall == out[j].Overall {
			return out[i].ID < out[j].ID
		}
		return out[i].Overall > out[j].Overall
	})
	return out
}

const caveat = "Historical dataset results only. Standings use 3/1/0 points and wins, goal difference, goals for; disciplinary deductions and official tie-breaks are unavailable. Cup tables are not league standings; stages/results do not establish a complete bracket or penalty winners. Individual goal scorers are not recorded. FIFA clubs/ratings are a historical snapshot, not current rosters."

func (g *Graph) Query(name string, f Filter) (any, error) {
	if e := f.validate(); e != nil {
		return nil, e
	}
	ms := g.matches(f)
	switch name {
	case "search_matches":
		return map[string]any{"total": len(ms), "matches": page(ms, f)}, nil
	case "search_players":
		ps := g.players(f)
		return map[string]any{"total": len(ps), "players": page(ps, f), "note": "Historical FIFA snapshot; attributes retain original values."}, nil
	case "team_info", "head_to_head":
		if f.Team == "" {
			return nil, fmt.Errorf("team is required")
		}
		if name == "head_to_head" && f.Opponent == "" {
			return nil, fmt.Errorf("opponent is required")
		}
		r := Record{Team: team(f.Team)}
		home, away := r, r
		comps := map[string]bool{}
		byComp := map[string]*Record{}
		bySeason := map[int]*Record{}
		for _, m := range ms {
			comps[m.Competition] = true
			if m.HomeGoals == nil || m.AwayGoals == nil {
				continue
			}
			gf, ga := *m.HomeGoals, *m.AwayGoals
			if m.Away == r.Team {
				gf, ga = ga, gf
				away.add(gf, ga)
			} else {
				home.add(gf, ga)
			}
			r.add(gf, ga)
			if byComp[m.Competition] == nil {
				byComp[m.Competition] = &Record{Team: r.Team}
			}
			byComp[m.Competition].add(gf, ga)
			if bySeason[m.Season] == nil {
				bySeason[m.Season] = &Record{Team: r.Team}
			}
			bySeason[m.Season].add(gf, ga)
		}
		cs := []string{}
		for c := range comps {
			cs = append(cs, c)
		}
		sort.Strings(cs)
		ps := g.players(Filter{Club: f.Team})
		return map[string]any{"record": r, "home": home, "away": away, "by_competition": byComp, "by_season": bySeason, "competitions": cs, "matches": page(ms, f), "total_matches": len(ms), "players": page(ps, f), "total_players": len(ps), "note": caveat}, nil
	case "standings":
		if f.Competition == "" || f.Season == 0 {
			return nil, fmt.Errorf("competition and season are required")
		}
		if competition(f.Competition) != "Brasileirão" {
			return nil, fmt.Errorf("league standings supported for Brasileirão; use search_matches with stage/round for cup results")
		}
		return map[string]any{"standings": records(ms, ""), "note": caveat, "matches": len(ms)}, nil
	case "statistics":
		played, goals, hw, draws := 0, 0, 0, 0
		seasons := map[int]map[string]float64{}
		for _, m := range ms {
			if m.HomeGoals == nil || m.AwayGoals == nil {
				continue
			}
			played++
			n := *m.HomeGoals + *m.AwayGoals
			goals += n
			if *m.HomeGoals > *m.AwayGoals {
				hw++
			}
			if *m.HomeGoals == *m.AwayGoals {
				draws++
			}
			if seasons[m.Season] == nil {
				seasons[m.Season] = map[string]float64{}
			}
			seasons[m.Season]["played"]++
			seasons[m.Season]["goals"] += float64(n)
		}
		for _, s := range seasons {
			s["average_goals"] = s["goals"] / s["played"]
		}
		avg, rate := 0.0, 0.0
		if played > 0 {
			avg = float64(goals) / float64(played)
			rate = 100 * float64(hw) / float64(played)
		}
		rs := records(ms, f.Venue)
		sort.SliceStable(rs, func(i, j int) bool {
			if f.Sort == "goals" {
				return rs[i].GoalsFor > rs[j].GoalsFor
			}
			return rs[i].WinRate > rs[j].WinRate
		})
		return map[string]any{"played": played, "goals": goals, "average_goals": avg, "home_win_rate": rate, "draws": draws, "by_season": seasons, "teams": page(rs, f), "note": caveat}, nil
	case "data_info":
		return map[string]any{"sources": g.Sources, "unique_matches": len(g.Matches), "players": len(g.Players), "warnings": g.Warnings, "note": caveat}, nil
	}
	return nil, fmt.Errorf("unknown tool %q", name)
}
