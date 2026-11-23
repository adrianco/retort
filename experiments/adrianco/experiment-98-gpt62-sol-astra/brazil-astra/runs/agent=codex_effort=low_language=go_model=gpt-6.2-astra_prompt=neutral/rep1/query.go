package main

import (
	"fmt"
	"sort"
	"strings"
)

type Args struct {
	Team, Opponent, Venue, Competition, Season, Start, End, Stage, Source, Sort, Name, Nationality, Club, Position string
	Derbies                                                                                                        bool
	Limit, Offset                                                                                                  int
}

var rivals = map[string]bool{"flamengo/fluminense": true, "flamengo/vasco da gama": true, "fluminense/vasco da gama": true, "botafogo rj/flamengo": true, "botafogo rj/fluminense": true, "botafogo rj/vasco da gama": true, "corinthians/palmeiras": true, "corinthians/sao paulo": true, "palmeiras/sao paulo": true, "palmeiras/santos": true, "santos/sao paulo": true, "corinthians/santos": true, "gremio/internacional": true, "atletico mg/cruzeiro": true, "bahia/vitoria": true, "atletico pr/coritiba": true, "ceara/fortaleza": true}

func (a Args) matches(m *Match) bool {
	if a.Competition != "" && a.Competition != m.Competition || a.Season != "" && a.Season != m.Season || a.Source != "" && m.Sources[a.Source] == nil || a.Start != "" && m.Date < a.Start || a.End != "" && (m.Date == "" || m.Date > a.End) || a.Stage != "" && a.Stage != m.Stage && a.Stage != m.Round {
		return false
	}
	if a.Derbies && !rivals[min(m.Home, m.Away)+"/"+max(m.Home, m.Away)] {
		return false
	}
	return (a.Venue != "away" && (a.Team == "" || a.Team == m.Home) && (a.Opponent == "" || a.Opponent == m.Away)) || (a.Venue != "home" && (a.Team == "" || a.Team == m.Away) && (a.Opponent == "" || a.Opponent == m.Home))
}

type Record struct {
	Team                                                                        string
	Played, Wins, Draws, Losses, GoalsFor, GoalsAgainst, GoalDifference, Points int
	WinRatePercent                                                              float64
}

func (r *Record) add(f, a int) {
	r.Played++
	r.GoalsFor += f
	r.GoalsAgainst += a
	r.GoalDifference += f - a
	switch {
	case f > a:
		r.Wins++
		r.Points += 3
	case f == a:
		r.Draws++
		r.Points++
	default:
		r.Losses++
	}
	r.WinRatePercent = 100 * float64(r.Wins) / float64(r.Played)
}

type Page struct {
	Total int
	Items any
}

func page[T any](s []T, a Args) Page {
	lo := min(len(s), a.Offset)
	return Page{len(s), s[lo : lo+min(len(s)-lo, a.Limit)]}
}
func (g *Graph) query(name string, a Args) (any, error) {
	if a.Offset < 0 || a.Limit < 0 || a.Limit > 100 {
		return nil, fmt.Errorf("offset must be nonnegative and limit in 1..100")
	}
	if a.Limit == 0 {
		a.Limit = 20
	}
	if a.Venue != "" && a.Venue != "home" && a.Venue != "away" && a.Venue != "either" {
		return nil, fmt.Errorf("invalid venue")
	}
	for _, v := range []string{a.Start, a.End} {
		if v != "" && day(v) != v {
			return nil, fmt.Errorf("expected ISO date")
		}
	}
	if a.Start != "" && a.End != "" && a.Start > a.End {
		return nil, fmt.Errorf("start exceeds end")
	}
	a.Team = team(a.Team)
	a.Opponent = team(a.Opponent)
	a.Competition = competition(a.Competition)
	a.Stage = fold(a.Stage)
	if name == "players" {
		rows := []Row{}
		club, nation, n, p := team(a.Club), fold(a.Nationality), fold(a.Name), fold(a.Position)
		if nation == "brazilian" {
			nation = "brazil"
		}
		for _, v := range g.Players {
			pos := fold(v.row["Position"])
			if strings.Contains(v.name, n) && strings.Contains(v.club, club) && (nation == "" || nation == v.nation) && (p == "" || p == pos || p == "forward" && strings.Contains(" st cf lw rw ls rs lf rf ", " "+pos+" ") && pos != "") {
				rows = append(rows, v.row)
			}
		}
		return page(rows, a), nil
	}
	ms := []*Match{}
	for _, m := range g.Matches {
		if a.matches(m) {
			ms = append(ms, m)
		}
	}
	if name == "matches" {
		if a.Sort == "margin" {
			scored := ms[:0]
			for _, m := range ms {
				if m.HomeGoals != nil && m.AwayGoals != nil {
					scored = append(scored, m)
				}
			}
			ms = scored
			margin := func(m *Match) int { return max(*m.HomeGoals-*m.AwayGoals, *m.AwayGoals-*m.HomeGoals) }
			sort.SliceStable(ms, func(i, j int) bool { return margin(ms[i]) > margin(ms[j]) })
		}
		return page(ms, a), nil
	}
	table := map[string]*Record{}
	count, total, homeWins := 0, 0, 0
	comps := map[string]int{}
	for _, m := range ms {
		comps[m.Competition]++
		if m.HomeGoals == nil || m.AwayGoals == nil {
			continue
		}
		h, b := *m.HomeGoals, *m.AwayGoals
		count++
		total += h + b
		if h > b {
			homeWins++
		}
		add := func(t string, v string, f, c int) {
			if a.Team != "" && t != a.Team || a.Venue != "" && a.Venue != "either" && a.Venue != v {
				return
			}
			if table[t] == nil {
				table[t] = &Record{Team: t}
			}
			table[t].add(f, c)
		}
		add(m.Home, "home", h, b)
		add(m.Away, "away", b, h)
	}
	if name == "summary" {
		out := map[string]any{"fixtures": len(ms), "played": count, "goals": total, "competitions": comps, "goalsPerMatch": nil, "homeWinPercent": nil}
		if count > 0 {
			out["goalsPerMatch"] = float64(total) / float64(count)
			out["homeWinPercent"] = 100 * float64(homeWins) / float64(count)
		}
		return out, nil
	}
	if name != "records" {
		return nil, fmt.Errorf("unknown tool %q", name)
	}
	rs := []*Record{}
	for _, r := range table {
		rs = append(rs, r)
	}
	sort.Slice(rs, func(i, j int) bool {
		x, y := rs[i], rs[j]
		if a.Sort == "goals" && x.GoalsFor != y.GoalsFor {
			return x.GoalsFor > y.GoalsFor
		}
		if a.Sort == "win_rate" && x.WinRatePercent != y.WinRatePercent {
			return x.WinRatePercent > y.WinRatePercent
		}
		if x.Points != y.Points {
			return x.Points > y.Points
		}
		if x.Wins != y.Wins {
			return x.Wins > y.Wins
		}
		if x.GoalDifference != y.GoalDifference {
			return x.GoalDifference > y.GoalDifference
		}
		if x.GoalsFor != y.GoalsFor {
			return x.GoalsFor > y.GoalsFor
		}
		return x.Team < y.Team
	})
	return page(rs, a), nil
}
