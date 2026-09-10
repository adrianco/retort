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
	Stage       string `json:"stage,omitempty"`
	Source      string `json:"source,omitempty"`
	Name        string `json:"name,omitempty"`
	Nationality string `json:"nationality,omitempty"`
	Club        string `json:"club,omitempty"`
	Position    string `json:"position,omitempty"`
	Sort        string `json:"sort,omitempty"`
	Derby       bool   `json:"derby,omitempty"`
	Limit       int    `json:"limit,omitempty"`
	Offset      int    `json:"offset,omitempty"`
}

func (f *Filter) validate() error {
	if f.Limit < 0 || f.Limit > 500 || f.Offset < 0 {
		return fmt.Errorf("limit must be 0..500 and offset nonnegative")
	}
	if f.Limit == 0 {
		f.Limit = 50
	}
	if f.Venue != "" && f.Venue != "home" && f.Venue != "away" && f.Venue != "either" {
		return fmt.Errorf("venue must be home, away or either")
	}
	if f.Sort != "" && f.Sort != "date" && f.Sort != "biggest_win" && f.Sort != "goals" && f.Sort != "win_rate" {
		return fmt.Errorf("unknown sort")
	}
	for _, p := range []*string{&f.From, &f.To} {
		if *p != "" {
			d, e := parseDate(*p)
			if e != nil {
				return e
			}
			*p = d
		}
	}
	if f.From != "" && f.To != "" && f.From > f.To {
		return fmt.Errorf("from must not be after to")
	}
	if f.Opponent != "" && f.Team == "" {
		return fmt.Errorf("opponent requires team")
	}
	return nil
}

var rivalries = [][2]string{{"flamengo", "fluminense"}, {"flamengo", "vasco"}, {"flamengo", "botafogo"}, {"fluminense", "botafogo"}, {"fluminense", "vasco"}, {"botafogo", "vasco"}, {"corinthians", "palmeiras"}, {"corinthians", "sao paulo"}, {"corinthians", "santos"}, {"palmeiras", "sao paulo"}, {"palmeiras", "santos"}, {"sao paulo", "santos"}, {"gremio", "internacional"}, {"cruzeiro", "atletico mg"}, {"bahia", "vitoria"}, {"athletico pr", "coritiba"}, {"ceara", "fortaleza"}, {"sport", "nautico"}, {"sport", "santa cruz"}, {"nautico", "santa cruz"}, {"avai", "figueirense"}, {"goias", "vila nova"}}

func derby(m Match) bool {
	for _, p := range rivalries {
		if m.Home == p[0] && m.Away == p[1] || m.Home == p[1] && m.Away == p[0] {
			return true
		}
	}
	return false
}
func (db *Store) matches(f Filter) []Match {
	out := []Match{}
	t, o := team(f.Team), team(f.Opponent)
	for _, m := range db.Matches {
		if t != "" {
			if f.Venue == "home" && m.Home != t || f.Venue == "away" && m.Away != t || m.Home != t && m.Away != t {
				continue
			}
		}
		if o != "" && !(m.Home == t && m.Away == o || m.Away == t && m.Home == o) {
			continue
		}
		if m.Date == "" && (f.From != "" || f.To != "") {
			continue
		}
		if f.Competition != "" && fold(m.Competition) != fold(competition(f.Competition)) || f.Season != 0 && m.Season != f.Season || f.From != "" && m.Date < f.From || f.To != "" && m.Date > f.To {
			continue
		}
		if f.Stage != "" {
			s := fold(f.Stage)
			if s == "final" || s == "finals" {
				if m.Stage != "final" && !strings.HasPrefix(m.Stage, "final (") {
					continue
				}
			} else if fold(m.Stage) != s && fold(m.Round) != s {
				continue
			}
		}
		if f.Source != "" {
			ok := false
			for _, s := range m.Sources {
				if s == f.Source {
					ok = true
				}
			}
			if !ok {
				continue
			}
		}
		if f.Derby && !derby(m) {
			continue
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if f.Sort == "biggest_win" {
			a, b := margin(out[i]), margin(out[j])
			if a != b {
				return a > b
			}
		}
		if out[i].Date != out[j].Date {
			return out[i].Date > out[j].Date
		}
		return out[i].ID < out[j].ID
	})
	return out
}
func margin(m Match) int {
	if m.HomeGoals == nil || m.AwayGoals == nil {
		return -1
	}
	n := *m.HomeGoals - *m.AwayGoals
	if n < 0 {
		return -n
	}
	return n
}
func page[T any](v []T, f Filter) map[string]any {
	start := f.Offset
	if start > len(v) {
		start = len(v)
	}
	end := start + f.Limit
	if end > len(v) {
		end = len(v)
	}
	var next any
	if end < len(v) {
		next = end
	}
	return map[string]any{"total": len(v), "offset": start, "next_offset": next, "items": v[start:end]}
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

func record(name string, ms []Match, venue string) Record {
	r := Record{Team: name}
	for _, m := range ms {
		if m.HomeGoals == nil || m.AwayGoals == nil {
			continue
		}
		home := m.Home == name
		if !home && m.Away != name || venue == "home" && !home || venue == "away" && home {
			continue
		}
		gf, ga := *m.HomeGoals, *m.AwayGoals
		if !home {
			gf, ga = ga, gf
		}
		r.Played++
		r.GoalsFor += gf
		r.GoalsAgainst += ga
		if gf > ga {
			r.Wins++
		} else if gf < ga {
			r.Losses++
		} else {
			r.Draws++
		}
	}
	r.GoalDifference = r.GoalsFor - r.GoalsAgainst
	r.Points = 3*r.Wins + r.Draws
	if r.Played > 0 {
		r.WinRate = 100 * float64(r.Wins) / float64(r.Played)
	}
	return r
}
func table(ms []Match, f Filter) []Record {
	names := map[string]bool{}
	for _, m := range ms {
		names[m.Home] = true
		names[m.Away] = true
	}
	out := []Record{}
	for _, n := range sortedKeys(names) {
		out = append(out, record(n, ms, f.Venue))
	}
	sort.SliceStable(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if f.Sort == "goals" && a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		if f.Sort == "win_rate" && a.WinRate != b.WinRate {
			return a.WinRate > b.WinRate
		}
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
func summary(ms []Match) map[string]any {
	played, goals, home, away, draw := 0, 0, 0, 0, 0
	for _, m := range ms {
		if m.HomeGoals == nil || m.AwayGoals == nil {
			continue
		}
		played++
		goals += *m.HomeGoals + *m.AwayGoals
		if *m.HomeGoals > *m.AwayGoals {
			home++
		} else if *m.HomeGoals < *m.AwayGoals {
			away++
		} else {
			draw++
		}
	}
	avg, rate := 0.0, 0.0
	if played > 0 {
		avg = float64(goals) / float64(played)
		rate = 100 * float64(home) / float64(played)
	}
	return map[string]any{"matches": len(ms), "played": played, "goals": goals, "average_goals": avg, "home_wins": home, "away_wins": away, "draws": draw, "home_win_rate": rate}
}

const caveat = "Dataset-only historical results, not live data. FIFA clubs and ratings are a historical snapshot. Standings use 3 points/win and 1/draw, sorted by points, wins, goal difference, goals for, then name; official sanctions and remaining tie-breakers are unavailable. Coverage may be incomplete. Cup final labels from numeric rounds are inferred; knockout winners, full bracket progression, individual goalscorers, and official relegation cannot be established reliably from these data."

func (db *Store) Query(name string, f Filter) (any, error) {
	if e := f.validate(); e != nil {
		return nil, e
	}
	switch name {
	case "search_matches":
		return page(db.matches(f), f), nil
	case "search_players":
		out := []Player{}
		for _, p := range db.Players {
			if f.Name != "" && !strings.Contains(fold(p.Name), fold(f.Name)) || f.Nationality != "" && !strings.EqualFold(p.Nationality, f.Nationality) && !(fold(f.Nationality) == "brazilian" && p.Nationality == "Brazil") || f.Club != "" && !strings.Contains(p.Club, team(f.Club)) {
				continue
			}
			if f.Position != "" {
				pos := strings.ToUpper(f.Position)
				if pos == "FORWARD" || pos == "FORWARDS" {
					if !strings.Contains(" ST CF LF RF LW RW LS RS ", " "+p.Position+" ") {
						continue
					}
				} else if p.Position != pos {
					continue
				}
			}
			out = append(out, p)
		}
		sort.SliceStable(out, func(i, j int) bool {
			if out[i].Overall != out[j].Overall {
				return out[i].Overall > out[j].Overall
			}
			return out[i].Name < out[j].Name
		})
		return page(out, f), nil
	case "team_stats", "head_to_head", "team_profile":
		if f.Team == "" {
			return nil, fmt.Errorf("team is required")
		}
		if name == "head_to_head" && f.Opponent == "" {
			return nil, fmt.Errorf("opponent is required")
		}
		ms := db.matches(f)
		t := team(f.Team)
		by := map[string]Record{}
		comps := map[string][]Match{}
		seasons := map[int][]Match{}
		for _, m := range ms {
			comps[m.Competition] = append(comps[m.Competition], m)
			seasons[m.Season] = append(seasons[m.Season], m)
		}
		for c, v := range comps {
			by[c] = record(t, v, "")
		}
		trends := map[int]Record{}
		for s, v := range seasons {
			trends[s] = record(t, v, "")
		}
		out := map[string]any{"record": record(t, ms, ""), "home": record(t, ms, "home"), "away": record(t, ms, "away"), "by_competition": by, "by_season": trends, "matches": page(ms, f), "note": caveat}
		if f.Opponent != "" {
			out["opponent"] = record(team(f.Opponent), ms, "")
		}
		if name == "team_profile" {
			p, _ := db.Query("search_players", Filter{Club: f.Team, Limit: f.Limit, Offset: f.Offset})
			out["players"] = p
		}
		return out, nil
	case "standings":
		if f.Competition == "" || f.Season == 0 {
			return nil, fmt.Errorf("competition and season are required")
		}
		if competition(f.Competition) != competition("serie a") && competition(f.Competition) != competition("serie b") {
			return nil, fmt.Errorf("league standings supported for Serie A/B; use competition_info for cup results")
		}
		return map[string]any{"standings": table(db.matches(f), f), "note": caveat}, nil
	case "statistics":
		ms := db.matches(f)
		groups := map[int][]Match{}
		for _, m := range ms {
			groups[m.Season] = append(groups[m.Season], m)
		}
		by := map[int]any{}
		for s, v := range groups {
			by[s] = summary(v)
		}
		big := append([]Match{}, ms...)
		sort.SliceStable(big, func(i, j int) bool { return margin(big[i]) > margin(big[j]) })
		return map[string]any{"summary": summary(ms), "by_season": by, "teams": page(table(ms, f), f), "biggest_wins": page(big, f), "note": caveat}, nil
	case "competition_info":
		ms := db.matches(f)
		groups := map[string][]Match{}
		for _, m := range ms {
			key := fmt.Sprintf("%s/%d/%s/%s", m.Competition, m.Season, m.Stage, m.Round)
			groups[key] = append(groups[key], m)
		}
		overview := map[string]any{}
		for k, v := range groups {
			overview[k] = summary(v)
		}
		return map[string]any{"groups": overview, "matches": page(ms, f), "note": caveat}, nil
	case "graph":
		if f.Team == "" {
			return nil, fmt.Errorf("team is required")
		}
		ms := db.matches(f)
		nodes := []map[string]string{{"id": "team:" + team(f.Team), "type": "team"}}
		edges := []map[string]string{}
		added := map[string]bool{}
		add := func(id, kind string) {
			if !added[id] {
				added[id] = true
				nodes = append(nodes, map[string]string{"id": id, "type": kind})
			}
		}
		added["team:"+team(f.Team)] = true
		start, end := f.Offset, f.Offset+f.Limit
		if start > len(ms) {
			start = len(ms)
		}
		if end > len(ms) {
			end = len(ms)
		}
		for _, m := range ms[start:end] {
			add(m.ID, "match")
			for _, n := range []string{m.Home, m.Away} {
				add("team:"+n, "team")
			}
			c := fmt.Sprintf("competition:%s:%d", m.Competition, m.Season)
			add(c, "competition_season")
			edges = append(edges, map[string]string{"from": m.ID, "relation": "home_team", "to": "team:" + m.Home}, map[string]string{"from": m.ID, "relation": "away_team", "to": "team:" + m.Away}, map[string]string{"from": m.ID, "relation": "part_of", "to": c})
		}
		ps := []Player{}
		for _, p := range db.Players {
			if p.Club == team(f.Team) {
				ps = append(ps, p)
			}
		}
		pstart, pend := f.Offset, f.Offset+f.Limit
		if pstart > len(ps) {
			pstart = len(ps)
		}
		if pend > len(ps) {
			pend = len(ps)
		}
		for _, p := range ps[pstart:pend] {
			id := "player:" + p.ID
			add(id, "player")
			edges = append(edges, map[string]string{"from": id, "relation": "plays_for_snapshot", "to": "team:" + p.Club})
		}
		return map[string]any{"nodes": nodes, "edges": edges, "match_total": len(ms), "player_total": len(ps), "offset": f.Offset, "note": caveat}, nil
	case "data_info":
		return map[string]any{"sources": db.Sources, "unique_matches": len(db.Matches), "players": len(db.Players), "teams": sortedKeys(db.Teams), "warnings": db.Warnings, "note": caveat}, nil
	}
	return nil, fmt.Errorf("unknown tool %q", name)
}
