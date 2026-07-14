package main

import (
	"sort"
	"strings"
)

// MatchFilter restricts a match search.
type MatchFilter struct {
	Team1       string // either team
	Team2       string // optional second team for head-to-head
	Season      int    // 0 = any
	Competition string // empty = any (substring match)
	Limit       int    // 0 = no limit
}

// FindMatches returns matches matching the filter, newest first.
func (d *DataStore) FindMatches(f MatchFilter) []Match {
	t1 := NormalizeTeam(f.Team1)
	t2 := NormalizeTeam(f.Team2)
	comp := strings.ToLower(f.Competition)

	var out []Match
	for _, m := range d.Matches {
		if t1 != "" {
			if t2 != "" {
				// head-to-head
				ok := (m.HomeKey == t1 && m.AwayKey == t2) ||
					(m.HomeKey == t2 && m.AwayKey == t1)
				if !ok {
					continue
				}
			} else {
				if m.HomeKey != t1 && m.AwayKey != t1 {
					continue
				}
			}
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if comp != "" && !strings.Contains(strings.ToLower(m.Competition), comp) {
			continue
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool {
		return out[i].Date.After(out[j].Date)
	})
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// TeamStats summarizes a team's match record over the matches.
type TeamStats struct {
	Team       string
	Matches    int
	Wins       int
	Draws      int
	Losses     int
	GoalsFor   int
	GoalsAgst  int
	HomeWins   int
	HomeDraws  int
	HomeLosses int
	AwayWins   int
	AwayDraws  int
	AwayLosses int
	Points     int // 3 win, 1 draw — useful for standings
}

func (s TeamStats) WinRate() float64 {
	if s.Matches == 0 {
		return 0
	}
	return float64(s.Wins) / float64(s.Matches)
}

// ComputeTeamStats aggregates over a set of matches relative to the given team key.
func ComputeTeamStats(team string, matches []Match) TeamStats {
	key := NormalizeTeam(team)
	s := TeamStats{Team: team}
	for _, m := range matches {
		var gf, ga int
		var home bool
		switch key {
		case m.HomeKey:
			gf, ga, home = m.HomeGoals, m.AwayGoals, true
		case m.AwayKey:
			gf, ga, home = m.AwayGoals, m.HomeGoals, false
		default:
			continue
		}
		s.Matches++
		s.GoalsFor += gf
		s.GoalsAgst += ga
		switch {
		case gf > ga:
			s.Wins++
			s.Points += 3
			if home {
				s.HomeWins++
			} else {
				s.AwayWins++
			}
		case gf == ga:
			s.Draws++
			s.Points++
			if home {
				s.HomeDraws++
			} else {
				s.AwayDraws++
			}
		default:
			s.Losses++
			if home {
				s.HomeLosses++
			} else {
				s.AwayLosses++
			}
		}
	}
	return s
}

// HeadToHead computes wins for each team across the matches between them.
type HeadToHead struct {
	Team1     string
	Team2     string
	Matches   int
	Team1Wins int
	Team2Wins int
	Draws     int
}

func ComputeHeadToHead(team1, team2 string, matches []Match) HeadToHead {
	k1 := NormalizeTeam(team1)
	k2 := NormalizeTeam(team2)
	h := HeadToHead{Team1: team1, Team2: team2}
	for _, m := range matches {
		var t1Goals, t2Goals int
		switch {
		case m.HomeKey == k1 && m.AwayKey == k2:
			t1Goals, t2Goals = m.HomeGoals, m.AwayGoals
		case m.HomeKey == k2 && m.AwayKey == k1:
			t1Goals, t2Goals = m.AwayGoals, m.HomeGoals
		default:
			continue
		}
		h.Matches++
		switch {
		case t1Goals > t2Goals:
			h.Team1Wins++
		case t1Goals < t2Goals:
			h.Team2Wins++
		default:
			h.Draws++
		}
	}
	return h
}

// Standings computes a ranked standings list for a competition+season.
type StandingsRow struct {
	Team       string
	Played     int
	Wins       int
	Draws      int
	Losses     int
	GoalsFor   int
	GoalsAgst  int
	GoalDiff   int
	Points     int
}

func (d *DataStore) Standings(competition string, season int) []StandingsRow {
	comp := strings.ToLower(competition)
	teamStats := map[string]*StandingsRow{}
	displayName := map[string]string{}

	for _, m := range d.Matches {
		if comp != "" && !strings.Contains(strings.ToLower(m.Competition), comp) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if m.HomeKey == "" || m.AwayKey == "" {
			continue
		}
		for _, side := range []struct {
			key, display string
			gf, ga       int
		}{
			{m.HomeKey, m.HomeTeam, m.HomeGoals, m.AwayGoals},
			{m.AwayKey, m.AwayTeam, m.AwayGoals, m.HomeGoals},
		} {
			row, ok := teamStats[side.key]
			if !ok {
				row = &StandingsRow{Team: side.display}
				teamStats[side.key] = row
				displayName[side.key] = side.display
			}
			row.Played++
			row.GoalsFor += side.gf
			row.GoalsAgst += side.ga
			switch {
			case side.gf > side.ga:
				row.Wins++
				row.Points += 3
			case side.gf == side.ga:
				row.Draws++
				row.Points++
			default:
				row.Losses++
			}
		}
	}

	out := make([]StandingsRow, 0, len(teamStats))
	for _, row := range teamStats {
		row.GoalDiff = row.GoalsFor - row.GoalsAgst
		out = append(out, *row)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Points != out[j].Points {
			return out[i].Points > out[j].Points
		}
		if out[i].GoalDiff != out[j].GoalDiff {
			return out[i].GoalDiff > out[j].GoalDiff
		}
		if out[i].GoalsFor != out[j].GoalsFor {
			return out[i].GoalsFor > out[j].GoalsFor
		}
		return out[i].Team < out[j].Team
	})
	return out
}

// --- Player queries -------------------------------------------------------

type PlayerFilter struct {
	Name        string // substring, case-insensitive
	Nationality string // exact (case-insensitive)
	Club        string // normalized key matching
	Position    string // substring, case-insensitive
	MinOverall  int
	Limit       int
}

func (d *DataStore) FindPlayers(f PlayerFilter) []Player {
	nameQ := strings.ToLower(strings.TrimSpace(f.Name))
	natQ := strings.ToLower(strings.TrimSpace(f.Nationality))
	clubKey := NormalizeTeam(f.Club)
	posQ := strings.ToLower(strings.TrimSpace(f.Position))

	var out []Player
	for _, p := range d.Players {
		if nameQ != "" && !strings.Contains(strings.ToLower(p.Name), nameQ) {
			continue
		}
		if natQ != "" && strings.ToLower(p.Nationality) != natQ {
			continue
		}
		if clubKey != "" && p.ClubKey != clubKey {
			continue
		}
		if posQ != "" && !strings.Contains(strings.ToLower(p.Position), posQ) {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		return out[i].Name < out[j].Name
	})
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// --- Aggregate / statistical analysis -------------------------------------

type AggregateStats struct {
	Matches         int
	TotalGoals      int
	HomeWins        int
	AwayWins        int
	Draws           int
	AvgGoalsPerGame float64
	HomeWinRate     float64
}

func ComputeAggregate(matches []Match) AggregateStats {
	a := AggregateStats{Matches: len(matches)}
	for _, m := range matches {
		a.TotalGoals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			a.HomeWins++
		case m.HomeGoals < m.AwayGoals:
			a.AwayWins++
		default:
			a.Draws++
		}
	}
	if a.Matches > 0 {
		a.AvgGoalsPerGame = float64(a.TotalGoals) / float64(a.Matches)
		a.HomeWinRate = float64(a.HomeWins) / float64(a.Matches)
	}
	return a
}

// BiggestWins returns the matches with the largest goal-difference.
func BiggestWins(matches []Match, limit int) []Match {
	cp := append([]Match(nil), matches...)
	sort.SliceStable(cp, func(i, j int) bool {
		di := abs(cp[i].HomeGoals - cp[i].AwayGoals)
		dj := abs(cp[j].HomeGoals - cp[j].AwayGoals)
		if di != dj {
			return di > dj
		}
		return (cp[i].HomeGoals + cp[i].AwayGoals) > (cp[j].HomeGoals + cp[j].AwayGoals)
	})
	if limit > 0 && len(cp) > limit {
		cp = cp[:limit]
	}
	return cp
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
