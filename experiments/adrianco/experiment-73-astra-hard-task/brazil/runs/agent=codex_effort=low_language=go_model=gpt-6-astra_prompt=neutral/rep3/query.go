package main

import (
	"fmt"
	"sort"
	"strings"
)

// Filter is shared by match and aggregate queries; pagination never affects aggregates.
type Filter struct {
	Team        string `json:"team,omitempty"`
	Opponent    string `json:"opponent,omitempty"`
	Venue       string `json:"venue,omitempty"`
	Competition string `json:"competition,omitempty"`
	Season      int    `json:"season,omitempty"`
	From        string `json:"date_from,omitempty"`
	To          string `json:"date_to,omitempty"`
	Stage       string `json:"stage,omitempty"`
	Round       string `json:"round,omitempty"`
	Source      string `json:"source,omitempty"`
	Derbies     bool   `json:"derbies,omitempty"`
	Limit       int    `json:"limit,omitempty"`
	Offset      int    `json:"offset,omitempty"`
	Sort        string `json:"sort,omitempty"`
}

func (f Filter) Validate() error {
	if f.Venue != "" && f.Venue != "home" && f.Venue != "away" && f.Venue != "either" {
		return fmt.Errorf("venue must be home, away, or either")
	}
	if f.Opponent != "" && f.Team == "" {
		return fmt.Errorf("opponent requires team")
	}
	if f.Opponent != "" && NormalizeTeam(f.Team) == NormalizeTeam(f.Opponent) {
		return fmt.Errorf("team and opponent must differ")
	}
	if f.Venue != "" && f.Venue != "either" && f.Team == "" {
		return fmt.Errorf("venue requires team")
	}
	if f.Season < 0 || f.Limit < 0 || f.Limit > 500 || f.Offset < 0 {
		return fmt.Errorf("season and offset must be nonnegative; limit must be 0..500")
	}
	if f.Sort != "" && f.Sort != "date_desc" && f.Sort != "date_asc" && f.Sort != "biggest_wins" {
		return fmt.Errorf("invalid match sort")
	}
	if f.From != "" {
		if _, e := parseDate(f.From); e != nil {
			return e
		}
	}
	if f.To != "" {
		if _, e := parseDate(f.To); e != nil {
			return e
		}
	}
	if f.From != "" && f.To != "" {
		a, _ := parseDate(f.From)
		b, _ := parseDate(f.To)
		if a.After(b) {
			return fmt.Errorf("date_from must not follow date_to")
		}
	}
	if f.Source != "" {
		ok := false
		for _, x := range datasetFiles[:5] {
			if f.Source == x {
				ok = true
			}
		}
		if !ok {
			return fmt.Errorf("unknown match source %q", f.Source)
		}
	}
	return nil
}

var rivals = map[string]string{"flamengo|fluminense": "Fla-Flu", "corinthians|palmeiras": "Derby Paulista", "santos|sao paulo": "San-São", "gremio|internacional": "Gre-Nal", "atletico mg|cruzeiro": "Clássico Mineiro", "bahia|vitoria": "Ba-Vi", "athletico pr|coritiba": "Atletiba", "botafogo|flamengo": "Clássico da Rivalidade", "flamengo|vasco da gama": "Clássico dos Milhões", "corinthians|sao paulo": "Majestoso", "palmeiras|sao paulo": "Choque-Rei", "corinthians|santos": "Clássico Alvinegro", "palmeiras|santos": "Clássico da Saudade"}

func derby(a, b string) bool {
	if a > b {
		a, b = b, a
	}
	_, ok := rivals[a+"|"+b]
	return ok
}
func (s *Store) FindMatches(f Filter) ([]Match, error) {
	if e := f.Validate(); e != nil {
		return nil, e
	}
	out := []Match{}
	team, op := NormalizeTeam(f.Team), NormalizeTeam(f.Opponent)
	from, to := "", ""
	if f.From != "" {
		t, _ := parseDate(f.From)
		from = t.Format("2006-01-02")
	}
	if f.To != "" {
		t, _ := parseDate(f.To)
		to = t.Format("2006-01-02")
	}
	consider := func(m Match) {
		if team != "" && (m.Home != team && m.Away != team) {
			return
		}
		if op != "" && !((m.Home == team && m.Away == op) || (m.Away == team && m.Home == op)) {
			return
		}
		if f.Venue == "home" && m.Home != team || f.Venue == "away" && m.Away != team {
			return
		}
		if f.Competition != "" && fold(m.Competition) != fold(competition(f.Competition)) || f.Season > 0 && f.Season != m.Season {
			return
		}
		if (from != "" || to != "") && m.Date == "" {
			return
		}
		if from != "" && m.Date < from || to != "" && m.Date > to {
			return
		}
		if f.Stage != "" && fold(m.Stage) != fold(f.Stage) || f.Round != "" && m.Round != f.Round {
			return
		}
		if f.Derbies && !derby(m.Home, m.Away) {
			return
		}
		if f.Source != "" {
			found := false
			for _, src := range m.Sources {
				if src.File == f.Source {
					found = true
				}
			}
			if !found {
				return
			}
		}
		out = append(out, m)
	}
	if team != "" {
		for _, i := range s.teams[team] {
			consider(s.Matches[i])
		}
	} else {
		for _, m := range s.Matches {
			consider(m)
		}
	}
	sort.SliceStable(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if f.Sort == "biggest_wins" {
			da, db := margin(a), margin(b)
			if da != db {
				return da > db
			}
		}
		if a.Date == b.Date {
			return a.ID < b.ID
		}
		if f.Sort == "date_asc" {
			return a.Date < b.Date
		}
		return a.Date > b.Date
	})
	return out, nil
}
func margin(m Match) int {
	if m.HomeGoals == nil {
		return -1
	}
	d := *m.HomeGoals - *m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}
func bounds(n, offset, limit int) (int, int) {
	if limit == 0 {
		limit = 50
	}
	if offset > n {
		offset = n
	}
	end := offset + limit
	if end > n {
		end = n
	}
	return offset, end
}
func matchPage(ms []Match, f Filter) any {
	a, b := bounds(len(ms), f.Offset, f.Limit)
	return map[string]any{"total": len(ms), "offset": a, "matches": ms[a:b], "next_offset": nextOffset(b, len(ms)), "scope": "Provided datasets only; scores and raw source attributes are preserved."}
}
func nextOffset(end, total int) any {
	if end < total {
		return end
	}
	return nil
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

func (r *Record) add(gf, ga int) {
	r.Played++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	if gf > ga {
		r.Wins++
		r.Points += 3
	} else if gf == ga {
		r.Draws++
		r.Points++
	} else {
		r.Losses++
	}
	r.GoalDifference = r.GoalsFor - r.GoalsAgainst
	r.WinRate = 100 * float64(r.Wins) / float64(r.Played)
}
func records(ms []Match, venue string) []Record {
	r := map[string]*Record{}
	for _, m := range ms {
		if m.HomeGoals == nil {
			continue
		}
		for _, team := range []string{m.Home, m.Away} {
			if venue == "home" && team != m.Home || venue == "away" && team != m.Away {
				continue
			}
			if r[team] == nil {
				r[team] = &Record{Team: team}
			}
			if team == m.Home {
				r[team].add(*m.HomeGoals, *m.AwayGoals)
			} else {
				r[team].add(*m.AwayGoals, *m.HomeGoals)
			}
		}
	}
	out := []Record{}
	for _, v := range r {
		out = append(out, *v)
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
func teamRecord(ms []Match, team string) Record {
	for _, r := range records(ms, "") {
		if r.Team == team {
			return r
		}
	}
	return Record{Team: team}
}
func (s *Store) TeamStats(f Filter) (any, error) {
	if f.Team == "" {
		return nil, fmt.Errorf("team is required")
	}
	ms, e := s.FindMatches(f)
	if e != nil {
		return nil, e
	}
	byComp := map[string][]Match{}
	bySeason := map[int][]Match{}
	home, away := []Match{}, []Match{}
	team := NormalizeTeam(f.Team)
	for _, m := range ms {
		byComp[m.Competition] = append(byComp[m.Competition], m)
		bySeason[m.Season] = append(bySeason[m.Season], m)
		if m.Home == team {
			home = append(home, m)
		} else {
			away = append(away, m)
		}
	}
	comps := map[string]Record{}
	seasons := map[int]Record{}
	for k, v := range byComp {
		comps[k] = teamRecord(v, team)
	}
	for k, v := range bySeason {
		seasons[k] = teamRecord(v, team)
	}
	return map[string]any{"record": teamRecord(ms, team), "home": teamRecord(home, team), "away": teamRecord(away, team), "by_competition": comps, "by_season": seasons, "fixtures": len(ms)}, nil
}
func (s *Store) Standings(f Filter) (any, error) {
	if f.Competition == "" || f.Season == 0 {
		return nil, fmt.Errorf("competition and season are required")
	}
	if competition(f.Competition) != "Brasileirão" && competition(f.Competition) != "Serie B" {
		return nil, fmt.Errorf("a single league table is not valid for this cup/group competition; use competition_results")
	}
	if f.Team != "" || f.Opponent != "" || f.Venue != "" || f.From != "" || f.To != "" || f.Stage != "" || f.Round != "" || f.Derbies {
		return nil, fmt.Errorf("standings requires a whole season; use statistics for filtered records")
	}
	ms, e := s.FindMatches(f)
	if e != nil {
		return nil, e
	}
	rs := records(ms, "")
	return map[string]any{"competition": competition(f.Competition), "season": f.Season, "table": rs, "matches": len(ms), "note": "Calculated dataset standings: 3 points/win, 1/draw; ordered by points, wins, goal difference, goals for, then name. No disciplinary deductions or full official tiebreakers. Coverage may be incomplete; no official champion or relegation inferred."}, nil
}
func (s *Store) Statistics(f Filter) (any, error) {
	ms, e := s.FindMatches(f)
	if e != nil {
		return nil, e
	}
	played, goals, home, away, draws := 0, 0, 0, 0, 0
	for _, m := range ms {
		if m.HomeGoals == nil {
			continue
		}
		played++
		goals += *m.HomeGoals + *m.AwayGoals
		if *m.HomeGoals > *m.AwayGoals {
			home++
		} else if *m.HomeGoals < *m.AwayGoals {
			away++
		} else {
			draws++
		}
	}
	avg, rate := 0.0, 0.0
	if played > 0 {
		avg = float64(goals) / float64(played)
		rate = 100 * float64(home) / float64(played)
	}
	return map[string]any{"fixtures": len(ms), "played": played, "goals": goals, "goals_per_match": avg, "home_wins": home, "away_wins": away, "draws": draws, "home_win_rate_percent": rate, "teams": records(ms, ""), "home_records": records(ms, "home"), "away_records": records(ms, "away")}, nil
}

type PlayerFilter struct {
	Name        string `json:"name,omitempty"`
	Nationality string `json:"nationality,omitempty"`
	Club        string `json:"club,omitempty"`
	Position    string `json:"position,omitempty"`
	MinOverall  int    `json:"min_overall,omitempty"`
	Limit       int    `json:"limit,omitempty"`
	Offset      int    `json:"offset,omitempty"`
}

func (s *Store) FindPlayers(f PlayerFilter) (any, error) {
	if f.Limit < 0 || f.Limit > 500 || f.Offset < 0 || f.MinOverall < 0 || f.MinOverall > 100 {
		return nil, fmt.Errorf("invalid player filter: limit 0..500, offset >=0, min_overall 0..100")
	}
	out := []Player{}
	for _, p := range s.Players {
		if f.Name != "" && !strings.Contains(fold(p.Name), fold(f.Name)) {
			continue
		}
		if f.Nationality != "" && fold(p.Nationality) != fold(f.Nationality) {
			continue
		}
		if f.Club != "" && NormalizeTeam(p.Club) != NormalizeTeam(f.Club) {
			continue
		}
		if p.Overall < f.MinOverall {
			continue
		}
		pos := strings.ToUpper(f.Position)
		if pos != "" {
			if pos == "FORWARD" || pos == "FORWARDS" {
				if !strings.Contains("|ST|LS|RS|LW|RW|LF|RF|CF|", "|"+p.Position+"|") {
					continue
				}
			} else if pos != p.Position {
				continue
			}
		}
		out = append(out, p)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		if out[i].Name != out[j].Name {
			return out[i].Name < out[j].Name
		}
		return out[i].ID < out[j].ID
	})
	clubs := map[string]any{}
	totals, counts := map[string]int{}, map[string]int{}
	for _, p := range out {
		counts[p.Club]++
		totals[p.Club] += p.Overall
	}
	for c, n := range counts {
		clubs[c] = map[string]any{"players": n, "average_overall": float64(totals[c]) / float64(n)}
	}
	a, b := bounds(len(out), f.Offset, f.Limit)
	return map[string]any{"total": len(out), "players": out[a:b], "by_club": clubs, "next_offset": nextOffset(b, len(out)), "note": "FIFA snapshot attributes, not current rosters. Name search uses the names/abbreviations present in the CSV."}, nil
}

// Graph uses stable typed IDs and exposes traversable team -> match/competition/player edges.
func (s *Store) Graph(team string, limit, offset int) (any, error) {
	if strings.TrimSpace(team) == "" {
		return nil, fmt.Errorf("team is required")
	}
	if limit < 0 || limit > 500 || offset < 0 {
		return nil, fmt.Errorf("invalid pagination")
	}
	team = NormalizeTeam(team)
	edges := []map[string]string{}
	nodes := map[string]any{"team:" + team: map[string]string{"id": "team:" + team, "type": "team", "name": team}}
	comps := map[string]bool{}
	for _, i := range s.teams[team] {
		m := s.Matches[i]
		role := "away_team"
		if m.Home == team {
			role = "home_team"
		}
		edges = append(edges, map[string]string{"from": "team:" + team, "relation": role, "to": m.ID})
		comps[m.Competition] = true
	}
	for _, c := range sortedKeys(comps) {
		edges = append(edges, map[string]string{"from": "team:" + team, "relation": "participated_in", "to": "competition:" + c})
	}
	for _, i := range s.playersByClub[team] {
		p := s.Players[i]
		edges = append(edges, map[string]string{"from": "player:" + p.ID, "relation": "plays_for_snapshot", "to": "team:" + team})
	}
	a, b := bounds(len(edges), offset, limit)
	for _, edge := range edges[a:b] {
		for _, id := range []string{edge["from"], edge["to"]} {
			if _, ok := nodes[id]; ok {
				continue
			}
			if strings.HasPrefix(id, "match:") {
				for _, i := range s.teams[team] {
					if s.Matches[i].ID == id {
						nodes[id] = s.Matches[i]
						break
					}
				}
			} else if strings.HasPrefix(id, "player:") {
				for _, i := range s.playersByClub[team] {
					if "player:"+s.Players[i].ID == id {
						nodes[id] = s.Players[i]
						break
					}
				}
			} else {
				nodes[id] = map[string]string{"id": id, "type": "competition", "name": strings.TrimPrefix(id, "competition:")}
			}
		}
	}
	return map[string]any{"nodes": nodes, "edges": edges[a:b], "total_edges": len(edges), "next_offset": nextOffset(b, len(edges))}, nil
}
