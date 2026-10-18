package main

import (
	"fmt"
	"sort"
	"strings"
)

type Query struct {
	Team        string `json:"team,omitempty"`
	Opponent    string `json:"opponent,omitempty"`
	Venue       string `json:"venue,omitempty"`
	Competition string `json:"competition,omitempty"`
	Season      int    `json:"season,omitempty"`
	From        string `json:"from,omitempty"`
	To          string `json:"to,omitempty"`
	Stage       string `json:"stage,omitempty"`
	Source      string `json:"source,omitempty"`
	Derbies     bool   `json:"derbies,omitempty"`
	Name        string `json:"name,omitempty"`
	Nationality string `json:"nationality,omitempty"`
	Club        string `json:"club,omitempty"`
	Position    string `json:"position,omitempty"`
	MinRating   int    `json:"min_rating,omitempty"`
	Sort        string `json:"sort,omitempty"`
	GroupBy     string `json:"group_by,omitempty"`
	Limit       int    `json:"limit,omitempty"`
	Offset      int    `json:"offset,omitempty"`
}

func (q Query) validate() error {
	if q.Limit < 0 || q.Limit > 500 || q.Offset < 0 {
		return fmt.Errorf("limit must be 0..500 and offset nonnegative")
	}
	if q.Season < 0 || q.MinRating < 0 || q.MinRating > 100 {
		return fmt.Errorf("invalid season or rating")
	}
	if q.Venue != "" && q.Venue != "home" && q.Venue != "away" && q.Venue != "either" {
		return fmt.Errorf("venue must be home, away, or either")
	}
	for _, d := range []string{q.From, q.To} {
		if d != "" {
			v, e := date(d)
			if e != nil || v != d {
				return fmt.Errorf("date filters must be YYYY-MM-DD")
			}
		}
	}
	if q.From != "" && q.To != "" && q.From > q.To {
		return fmt.Errorf("from must be before to")
	}
	if q.Sort != "" && q.Sort != "latest" && q.Sort != "biggest_win" && q.Sort != "goals" && q.Sort != "points" && q.Sort != "win_rate" {
		return fmt.Errorf("unsupported sort")
	}
	if q.GroupBy != "" && q.GroupBy != "season" && q.GroupBy != "competition" {
		return fmt.Errorf("group_by must be season or competition")
	}
	if q.Source != "" {
		ok := false
		for _, f := range files {
			if f == q.Source {
				ok = true
			}
		}
		if !ok {
			return fmt.Errorf("unknown source")
		}
	}
	return nil
}
func window(n int, q Query) (int, int) {
	start := q.Offset
	if start > n {
		start = n
	}
	limit := q.Limit
	if limit == 0 {
		limit = 50
	}
	end := start + limit
	if end > n {
		end = n
	}
	return start, end
}

var rivals = [][2]string{{"flamengo", "fluminense"}, {"flamengo", "vasco"}, {"flamengo", "botafogo"}, {"fluminense", "vasco"}, {"fluminense", "botafogo"}, {"vasco", "botafogo"}, {"palmeiras", "corinthians"}, {"palmeiras", "santos"}, {"palmeiras", "sao paulo"}, {"corinthians", "santos"}, {"corinthians", "sao paulo"}, {"santos", "sao paulo"}, {"gremio", "internacional"}, {"cruzeiro", "atletico mg"}, {"bahia", "vitoria"}, {"sport", "nautico"}, {"sport", "santa cruz"}, {"nautico", "santa cruz"}, {"ceara", "fortaleza"}, {"atletico pr", "coritiba"}, {"avai", "figueirense"}, {"goias", "vila nova"}, {"remo", "paysandu"}}

func derby(m Match) bool {
	for _, r := range rivals {
		if m.Home == r[0] && m.Away == r[1] || m.Home == r[1] && m.Away == r[0] {
			return true
		}
	}
	return false
}
func contains(a []string, v string) bool {
	for _, s := range a {
		if s == v {
			return true
		}
	}
	return false
}
func (s *Store) matches(q Query) []Match {
	out := []Match{}
	t, o, c := team(q.Team), team(q.Opponent), competition(q.Competition)
	for _, m := range s.Matches {
		if m.Date == "" && (q.From != "" || q.To != "") {
			continue
		}
		if t != "" {
			if q.Venue == "home" && m.Home != t || q.Venue == "away" && m.Away != t || m.Home != t && m.Away != t {
				continue
			}
		}
		if o != "" {
			if t != "" {
				if !(m.Home == t && m.Away == o || m.Home == o && m.Away == t) {
					continue
				}
			} else if m.Home != o && m.Away != o {
				continue
			}
		}
		if c != "" && c != m.Competition || q.Season != 0 && q.Season != m.Season || q.From != "" && m.Date < q.From || q.To != "" && m.Date > q.To {
			continue
		}
		if q.Source != "" && !contains(m.Sources, q.Source) {
			continue
		}
		if q.Stage != "" && fold(q.Stage) != fold(m.Stage) && fold(q.Stage) != fold(m.Round) {
			continue
		}
		if q.Derbies && !derby(m) {
			continue
		}
		out = append(out, m)
	}
	if q.Sort == "biggest_win" {
		sort.SliceStable(out, func(i, j int) bool { return margin(out[i]) > margin(out[j]) })
	}
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
	WinRate        float64 `json:"win_rate_percent"`
}

func records(ms []Match, venue string) []Record {
	by := map[string]*Record{}
	for _, m := range ms {
		if m.HomeGoals == nil || m.AwayGoals == nil {
			continue
		}
		for i, t := range []string{m.Home, m.Away} {
			if venue == "home" && i == 1 || venue == "away" && i == 0 {
				continue
			}
			r := by[t]
			if r == nil {
				r = &Record{Team: t}
				by[t] = r
			}
			gf, ga := *m.HomeGoals, *m.AwayGoals
			if i == 1 {
				gf, ga = ga, gf
			}
			r.Played++
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
	}
	out := []Record{}
	for _, r := range by {
		r.Points = r.Wins*3 + r.Draws
		r.GoalDifference = r.GoalsFor - r.GoalsAgainst
		r.WinRate = 100 * float64(r.Wins) / float64(r.Played)
		out = append(out, *r)
	}
	sortRecords(out, "")
	return out
}
func sortRecords(rs []Record, order string) {
	sort.Slice(rs, func(i, j int) bool {
		a, b := rs[i], rs[j]
		if order == "goals" && a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		if order == "win_rate" && a.WinRate != b.WinRate {
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
}
func (s *Store) players(q Query) []Player {
	out := []Player{}
	for _, p := range s.Players {
		if q.Name != "" && !strings.Contains(fold(p.Name), fold(q.Name)) || q.Nationality != "" && fold(p.Nationality) != fold(q.Nationality) || q.Club != "" && !strings.Contains(p.Club, team(q.Club)) || p.Overall < q.MinRating {
			continue
		}
		if q.Position != "" {
			pos := strings.ToUpper(q.Position)
			if pos == "FORWARD" || pos == "FORWARDS" {
				if !contains([]string{"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"}, p.Position) {
					continue
				}
			} else if pos != p.Position {
				continue
			}
		}
		out = append(out, p)
	}
	return out
}

const caveat = "Historical dataset results only; coverage may be incomplete. Duplicate directed pairings are merged by competition and season for Série A/B, or by competition and date for other tournaments; conflicting scores prefer files in documented load order. No player goalscorer events, official sanctions, tiebreak adjudication or penalty-shootout data are available."

func summary(ms []Match) map[string]any {
	played, goals, home, draw, away := 0, 0, 0, 0, 0
	for _, m := range ms {
		if m.HomeGoals == nil || m.AwayGoals == nil {
			continue
		}
		played++
		goals += *m.HomeGoals + *m.AwayGoals
		if *m.HomeGoals > *m.AwayGoals {
			home++
		} else if *m.HomeGoals == *m.AwayGoals {
			draw++
		} else {
			away++
		}
	}
	avg, rate := 0.0, 0.0
	if played > 0 {
		avg = float64(goals) / float64(played)
		rate = 100 * float64(home) / float64(played)
	}
	return map[string]any{"matches": len(ms), "played": played, "goals": goals, "average_goals": avg, "home_wins": home, "draws": draw, "away_wins": away, "home_win_rate_percent": rate}
}
func (s *Store) Call(name string, q Query) (any, error) {
	if e := q.validate(); e != nil {
		return nil, e
	}
	switch name {
	case "search_matches":
		ms := s.matches(q)
		a, b := window(len(ms), q)
		return map[string]any{"total": len(ms), "matches": ms[a:b], "note": caveat}, nil
	case "search_players":
		ps := s.players(q)
		a, b := window(len(ps), q)
		return map[string]any{"total": len(ps), "players": ps[a:b], "note": "FIFA snapshot, not current rosters. Attributes are original CSV fields."}, nil
	case "team_profile":
		if q.Team == "" {
			return nil, fmt.Errorf("team is required")
		}
		ms := s.matches(q)
		ps := s.players(Query{Club: q.Team})
		comps := map[string]int{}
		for _, m := range ms {
			comps[m.Competition]++
		}
		rs := records(ms, q.Venue)
		r := Record{Team: team(q.Team)}
		for _, v := range rs {
			if v.Team == r.Team {
				r = v
			}
		}
		a, b := window(len(ms), q)
		pa, pb := window(len(ps), Query{Limit: q.Limit})
		return map[string]any{"team_id": "team:" + r.Team, "record": r, "competitions": comps, "match_total": len(ms), "matches": ms[a:b], "player_total": len(ps), "players": ps[pa:pb], "relationships": "Match home/away and player club fields reference normalized team entities. Player affiliations are historical FIFA snapshot data.", "note": caveat}, nil
	case "head_to_head":
		if q.Team == "" || q.Opponent == "" || team(q.Team) == team(q.Opponent) {
			return nil, fmt.Errorf("two distinct teams are required")
		}
		ms := s.matches(q)
		a, b := window(len(ms), q)
		return map[string]any{"records": records(ms, ""), "summary": summary(ms), "matches": ms[a:b], "note": caveat}, nil
	case "standings":
		if q.Competition == "" || q.Season == 0 {
			return nil, fmt.Errorf("competition and season are required")
		}
		c := competition(q.Competition)
		if c != "Brasileirão" && c != "Série B" && c != "Série C" {
			return nil, fmt.Errorf("knockout competitions have no single league table; use competition_results")
		}
		ms := s.matches(q)
		rs := records(ms, q.Venue)
		sortRecords(rs, q.Sort)
		a, b := window(len(rs), q)
		return map[string]any{"total": len(rs), "standings": rs[a:b], "note": "Calculated table: 3 points per win, then wins, goal difference, goals scored, team name. Partial filters produce partial tables. Champion/relegation cannot be certified from incomplete data; Série C may contain multiple groups. " + caveat}, nil
	case "statistics":
		ms := s.matches(q)
		rs := records(ms, q.Venue)
		sortRecords(rs, q.Sort)
		a, b := window(len(rs), q)
		groups := map[string]any{}
		groupMatches := map[string][]Match{}
		if q.GroupBy != "" {
			for _, m := range ms {
				k := m.Competition
				if q.GroupBy == "season" {
					k = fmt.Sprint(m.Season)
				}
				groupMatches[k] = append(groupMatches[k], m)
			}
			for k, v := range groupMatches {
				groups[k] = summary(v)
			}
		}
		return map[string]any{"summary": summary(ms), "team_total": len(rs), "teams": rs[a:b], "groups": groups, "note": caveat}, nil
	case "competition_results":
		if q.Competition == "" {
			return nil, fmt.Errorf("competition is required")
		}
		ms := s.matches(q)
		a, b := window(len(ms), q)
		stages := map[string]int{}
		for _, m := range ms {
			k := m.Stage
			if k == "" {
				k = m.Round
			}
			if k == "" {
				k = "unknown"
			}
			stages[k]++
		}
		return map[string]any{"total": len(ms), "matches": ms[a:b], "stages": stages, "note": "Stage-grouped fixtures represent available bracket results; advancement and shootout winners are not inferred. Copa do Brasil final is inferred as the maximum numbered round within each season of its dedicated source. " + caveat}, nil
	case "data_info":
		comps := map[string]map[string]any{}
		for _, m := range s.Matches {
			v := comps[m.Competition]
			if v == nil {
				v = map[string]any{"from": m.Date, "to": m.Date, "matches": 0}
				comps[m.Competition] = v
			}
			if m.Date != "" && (v["from"].(string) == "" || m.Date < v["from"].(string)) {
				v["from"] = m.Date
			}
			if m.Date > v["to"].(string) {
				v["to"] = m.Date
			}
			v["matches"] = v["matches"].(int) + 1
		}
		return map[string]any{"source_rows": s.Counts, "unique_matches": len(s.Matches), "players": len(s.Players), "competitions": comps, "warnings": s.Warnings, "note": caveat, "load_order": files}, nil
	default:
		return nil, fmt.Errorf("unknown tool %q", name)
	}
}
