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
	Round       string `json:"round,omitempty"`
	Source      string `json:"source,omitempty"`
	Derbies     bool   `json:"derbies,omitempty"`
	Name        string `json:"name,omitempty"`
	Nationality string `json:"nationality,omitempty"`
	Club        string `json:"club,omitempty"`
	Position    string `json:"position,omitempty"`
	Limit       int    `json:"limit,omitempty"`
	Offset      int    `json:"offset,omitempty"`
	Sort        string `json:"sort,omitempty"`
}

func (q Query) validate() error {
	if q.Venue != "" && q.Venue != "home" && q.Venue != "away" && q.Venue != "either" {
		return fmt.Errorf("venue must be home, away, or either")
	}
	if q.Opponent != "" && teamKey(q.Team) == teamKey(q.Opponent) {
		return fmt.Errorf("team and opponent must be different")
	}
	if q.Opponent != "" && q.Team == "" {
		return fmt.Errorf("opponent requires team")
	}
	if q.Limit < 0 || q.Limit > 500 || q.Offset < 0 || q.Season < 0 {
		return fmt.Errorf("limit must be 0..500; offset and season must be nonnegative")
	}
	for _, s := range []string{q.From, q.To} {
		if s != "" {
			t, e := parseDate(s)
			if e != nil || t.Format("2006-01-02") != s {
				return fmt.Errorf("date filters must use YYYY-MM-DD")
			}
		}
	}
	if q.From != "" && q.To != "" && q.From > q.To {
		return fmt.Errorf("from must be on or before to")
	}
	switch q.Sort {
	case "", "date", "biggest_win", "goals", "points", "win_rate", "overall":
	default:
		return fmt.Errorf("unsupported sort %q", q.Sort)
	}
	return nil
}

var rivalPairs = [][2]string{{"flamengo", "fluminense"}, {"flamengo", "vasco da gama"}, {"flamengo", "botafogo"}, {"fluminense", "botafogo"}, {"fluminense", "vasco da gama"}, {"botafogo", "vasco da gama"}, {"palmeiras", "corinthians"}, {"sao paulo", "corinthians"}, {"santos", "corinthians"}, {"palmeiras", "sao paulo"}, {"palmeiras", "santos"}, {"sao paulo", "santos"}, {"gremio", "internacional"}, {"atletico-mg", "cruzeiro"}, {"bahia", "vitoria"}, {"sport", "nautico"}, {"sport", "santa cruz"}, {"nautico", "santa cruz"}, {"ceara", "fortaleza"}, {"athletico-pr", "coritiba"}, {"avai", "figueirense"}, {"goias", "vila nova"}, {"remo", "paysandu"}}

func isDerby(m *Match) bool {
	for _, p := range rivalPairs {
		if m.Home == p[0] && m.Away == p[1] || m.Home == p[1] && m.Away == p[0] {
			return true
		}
	}
	return false
}
func completed(m *Match) bool { return m.HomeGoals != nil && m.AwayGoals != nil }

// Explicit mappings for the numbered rounds in the supplied cup file.
// Unknown seasons retain their raw round; an incomplete season is never treated as final.
func stage(m *Match) string {
	if m.Stage != "" {
		return fold(m.Stage)
	}
	if m.Competition == "Copa do Brasil" {
		n, e := number(m.Round)
		if e == nil {
			last, known := map[int]int{2012: 6, 2013: 8, 2014: 8, 2015: 8, 2016: 7, 2017: 8, 2018: 8, 2019: 8, 2020: 8, 2021: 7}[m.Season]
			if !known {
				return ""
			}
			switch last - n {
			case 0:
				return "final"
			case 1:
				return "semifinals"
			case 2:
				return "quarterfinals"
			case 3:
				return "round of 16"
			}
		}
	}
	return ""
}
func (g *Graph) FindMatches(q Query) []*Match {
	result := []*Match{}
	pool := g.Matches
	t, o := teamKey(q.Team), teamKey(q.Opponent)
	if t != "" {
		pool = g.Teams[t]
	}
	for _, m := range pool {
		if m.Date == "" && (q.From != "" || q.To != "") {
			continue
		}
		if q.Venue == "home" && t != "" && m.Home != t || q.Venue == "away" && t != "" && m.Away != t {
			continue
		}
		if o != "" && !(m.Home == t && m.Away == o || m.Home == o && m.Away == t) {
			continue
		}
		if q.Competition != "" && fold(m.Competition) != fold(competitionKey(q.Competition)) || q.Season != 0 && m.Season != q.Season || q.From != "" && m.Date < q.From || q.To != "" && m.Date > q.To {
			continue
		}
		if q.Round != "" && fold(m.Round) != fold(q.Round) || q.Stage != "" && stage(m) != fold(q.Stage) || q.Derbies && !isDerby(m) {
			continue
		}
		if q.Source != "" {
			if _, ok := m.Attributes[q.Source]; !ok {
				continue
			}
		}
		result = append(result, m)
	}
	if q.Sort == "biggest_win" {
		sort.SliceStable(result, func(i, j int) bool { return margin(result[i]) > margin(result[j]) })
	}
	return result
}
func margin(m *Match) int {
	if !completed(m) {
		return -1
	}
	d := *m.HomeGoals - *m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
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
func records(matches []*Match, venue string) []Record {
	by := map[string]*Record{}
	for _, m := range matches {
		if !completed(m) {
			continue
		}
		for _, home := range []bool{true, false} {
			if venue == "home" && !home || venue == "away" && home {
				continue
			}
			t, gf, ga := m.Home, *m.HomeGoals, *m.AwayGoals
			if !home {
				t, gf, ga = m.Away, ga, gf
			}
			if by[t] == nil {
				by[t] = &Record{Team: t}
			}
			by[t].add(gf, ga)
		}
	}
	out := []Record{}
	for _, r := range by {
		out = append(out, *r)
	}
	sortRecords(out, "points")
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
func recordFor(ms []*Match, t, venue string) Record {
	for _, r := range records(ms, venue) {
		if r.Team == teamKey(t) {
			return r
		}
	}
	return Record{Team: teamKey(t)}
}

type Summary struct {
	Matches      int     `json:"matches"`
	Played       int     `json:"played"`
	Goals        int     `json:"goals"`
	AverageGoals float64 `json:"average_goals"`
	HomeWins     int     `json:"home_wins"`
	AwayWins     int     `json:"away_wins"`
	Draws        int     `json:"draws"`
	HomeWinRate  float64 `json:"home_win_rate_percent"`
}

func summarize(ms []*Match) Summary {
	s := Summary{Matches: len(ms)}
	for _, m := range ms {
		if !completed(m) {
			continue
		}
		s.Played++
		s.Goals += *m.HomeGoals + *m.AwayGoals
		if *m.HomeGoals > *m.AwayGoals {
			s.HomeWins++
		} else if *m.HomeGoals < *m.AwayGoals {
			s.AwayWins++
		} else {
			s.Draws++
		}
	}
	if s.Played > 0 {
		s.AverageGoals = float64(s.Goals) / float64(s.Played)
		s.HomeWinRate = 100 * float64(s.HomeWins) / float64(s.Played)
	}
	return s
}
func page[T any](items []T, q Query) map[string]any {
	limit := q.Limit
	if limit == 0 {
		limit = 50
	}
	start := q.Offset
	if start > len(items) {
		start = len(items)
	}
	end := start + limit
	if end > len(items) {
		end = len(items)
	}
	r := map[string]any{"total": len(items), "offset": q.Offset, "items": items[start:end]}
	if end < len(items) {
		r["next_offset"] = end
	}
	return r
}
func (g *Graph) FindPlayers(q Query) []Player {
	out := []Player{}
	pool := g.Players
	if q.Club != "" {
		pool = g.Rosters[teamKey(q.Club)]
		if len(pool) == 0 {
			for club, players := range g.Rosters {
				if strings.Contains(club, teamKey(q.Club)) {
					pool = append(pool, players...)
				}
			}
		}
	}
	for _, p := range pool {
		if q.Name != "" && !strings.Contains(fold(p.Name), fold(q.Name)) || q.Nationality != "" && fold(p.Nationality) != fold(q.Nationality) {
			continue
		}
		pos := strings.ToUpper(q.Position)
		if pos != "" {
			if fold(pos) == "forward" || fold(pos) == "forwards" {
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
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		return out[i].ID < out[j].ID
	})
	return out
}

const caveat = "Results describe the supplied dataset, not live football. Overlapping matches are merged by competition, season, date and teams; cross-source adjacent-day fixtures also merge when scores agree (UTC/local date differences), with explicit seasons preferred over calendar-year guesses; source priority follows dataset_info. Standings use 3 points/win and 1/draw, ordered by points, wins, goal difference, goals for, then team name; official deductions and later tie-breakers are unavailable. Missing results are excluded from aggregates. FIFA clubs and ratings are a historical snapshot, not current rosters. Individual goalscorers and penalty shootouts are unavailable."

func (g *Graph) Call(name string, q Query) (any, error) {
	if e := q.validate(); e != nil {
		return nil, e
	}
	switch name {
	case "dataset_info":
		return map[string]any{"sources": g.Sources, "matches": len(g.Matches), "players": len(g.Players), "teams": len(g.Teams), "warnings": g.Warnings, "notes": caveat, "rivalries": rivalPairs}, nil
	case "search_players":
		return page(g.FindPlayers(q), q), nil
	case "search_matches":
		return page(g.FindMatches(q), q), nil
	case "head_to_head":
		if q.Team == "" || q.Opponent == "" {
			return nil, fmt.Errorf("team and opponent are required")
		}
		ms := g.FindMatches(q)
		return map[string]any{"team": recordFor(ms, q.Team, ""), "opponent": recordFor(ms, q.Opponent, ""), "matches": page(ms, q)}, nil
	case "team_profile":
		if q.Team == "" {
			return nil, fmt.Errorf("team is required")
		}
		ms := g.FindMatches(q)
		by := map[string][]*Match{}
		for _, m := range ms {
			by[m.Competition] = append(by[m.Competition], m)
		}
		comps := map[string]Record{}
		for c, m := range by {
			comps[c] = recordFor(m, q.Team, "")
		}
		return map[string]any{"team": teamKey(q.Team), "record": recordFor(ms, q.Team, ""), "home": recordFor(ms, q.Team, "home"), "away": recordFor(ms, q.Team, "away"), "competitions": comps, "players": page(g.FindPlayers(Query{Club: q.Team}), q), "matches": page(ms, q), "notes": caveat}, nil
	case "standings":
		if q.Competition == "" || q.Season == 0 {
			return nil, fmt.Errorf("competition and season are required")
		}
		comp := competitionKey(q.Competition)
		if comp == "Copa do Brasil" || comp == "Libertadores" {
			return nil, fmt.Errorf("knockout/group competitions do not have a single league table; use competition_results")
		}
		if q.Team != "" || q.Opponent != "" || q.Venue != "" || q.Stage != "" || q.Round != "" || q.From != "" || q.To != "" || q.Derbies {
			return nil, fmt.Errorf("standings require an unfiltered competition-season")
		}
		rs := records(g.FindMatches(q), "")
		return map[string]any{"standings": page(rs, q), "notes": caveat + " Champion/relegation positions are provisional; coverage and official rules must be verified."}, nil
	case "competition_results":
		ms := g.FindMatches(q)
		groups := map[string][]*Match{}
		for _, m := range ms {
			s := stage(m)
			if s == "" {
				s = "round " + m.Round
			}
			groups[s] = append(groups[s], m)
		}
		counts := map[string]int{}
		for s, items := range groups {
			counts[s] = len(items)
		}
		return map[string]any{"matches": page(ms, q), "stages": counts, "notes": "Filter by stage or round to inspect knockout legs. Cup stages use explicit season-specific mappings for the provided numbered rounds. Penalty shootouts, group assignments and advancement edges are unavailable; no bracket winner is inferred from tied scores."}, nil
	case "statistics":
		ms := g.FindMatches(q)
		rs := records(ms, q.Venue)
		sortRecords(rs, q.Sort)
		years := map[int][]*Match{}
		for _, m := range ms {
			years[m.Season] = append(years[m.Season], m)
		}
		trends := map[int]any{}
		for y, items := range years {
			if q.Team != "" {
				trends[y] = map[string]any{"summary": summarize(items), "record": recordFor(items, q.Team, q.Venue)}
			} else {
				trends[y] = summarize(items)
			}
		}
		return map[string]any{"summary": summarize(ms), "teams": page(rs, q), "seasons": trends, "notes": caveat}, nil
	default:
		return nil, fmt.Errorf("unknown tool %q", name)
	}
}
