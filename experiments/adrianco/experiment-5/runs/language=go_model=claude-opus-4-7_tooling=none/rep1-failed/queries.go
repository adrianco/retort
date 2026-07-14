package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// MatchFilter narrows the set of matches returned by FindMatches.
type MatchFilter struct {
	Team        string // either home or away
	Home        string // home team only
	Away        string // away team only
	OtherTeam   string // pair filter: must include both Team and OtherTeam
	Competition string // substring match on competition name
	Season      int    // 0 = any
	From        time.Time
	To          time.Time
	Limit       int // 0 = unlimited
}

// FindMatches returns matches matching the filter, sorted by date desc.
func (db *DB) FindMatches(f MatchFilter) []Match {
	var out []Match
	for _, m := range db.Matches {
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.Competition != "" && !strings.Contains(
			strings.ToLower(stripAccents(m.Competition)),
			strings.ToLower(stripAccents(f.Competition)),
		) {
			continue
		}
		if !f.From.IsZero() && m.Date.Before(f.From) {
			continue
		}
		if !f.To.IsZero() && m.Date.After(f.To) {
			continue
		}
		if f.Home != "" && !teamsMatch(m.HomeTeam, f.Home) {
			continue
		}
		if f.Away != "" && !teamsMatch(m.AwayTeam, f.Away) {
			continue
		}
		if f.Team != "" && f.OtherTeam == "" {
			if !teamsMatch(m.HomeTeam, f.Team) && !teamsMatch(m.AwayTeam, f.Team) {
				continue
			}
		}
		if f.Team != "" && f.OtherTeam != "" {
			a := teamsMatch(m.HomeTeam, f.Team) || teamsMatch(m.AwayTeam, f.Team)
			b := teamsMatch(m.HomeTeam, f.OtherTeam) || teamsMatch(m.AwayTeam, f.OtherTeam)
			if !(a && b) {
				continue
			}
		}
		out = append(out, m)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// TeamStats summarizes a team's record over a set of matches.
type TeamStats struct {
	Team         string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	HomeMatches  int
	HomeWins     int
	HomeDraws    int
	HomeLosses   int
	AwayMatches  int
	AwayWins     int
	AwayDraws    int
	AwayLosses   int
	Points       int // standard 3/1/0
}

// WinRate returns wins / matches as a 0..1 fraction.
func (t TeamStats) WinRate() float64 {
	if t.Matches == 0 {
		return 0
	}
	return float64(t.Wins) / float64(t.Matches)
}

// ComputeTeamStats aggregates stats for the given team across the matches.
func ComputeTeamStats(team string, matches []Match) TeamStats {
	ts := TeamStats{Team: canonicalTeamName(team)}
	for _, m := range matches {
		isHome := teamsMatch(m.HomeTeam, team)
		isAway := teamsMatch(m.AwayTeam, team)
		if !isHome && !isAway {
			continue
		}
		ts.Matches++
		var gf, ga int
		if isHome {
			ts.HomeMatches++
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			ts.AwayMatches++
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		ts.GoalsFor += gf
		ts.GoalsAgainst += ga
		switch {
		case gf > ga:
			ts.Wins++
			ts.Points += 3
			if isHome {
				ts.HomeWins++
			} else {
				ts.AwayWins++
			}
		case gf == ga:
			ts.Draws++
			ts.Points++
			if isHome {
				ts.HomeDraws++
			} else {
				ts.AwayDraws++
			}
		default:
			ts.Losses++
			if isHome {
				ts.HomeLosses++
			} else {
				ts.AwayLosses++
			}
		}
	}
	return ts
}

// HeadToHead summarizes wins/draws/losses between two specific teams.
type HeadToHead struct {
	TeamA   string
	TeamB   string
	Matches int
	WinsA   int
	WinsB   int
	Draws   int
	GoalsA  int
	GoalsB  int
}

// ComputeHeadToHead returns head-to-head stats between teamA and teamB.
func (db *DB) ComputeHeadToHead(teamA, teamB string) HeadToHead {
	h := HeadToHead{TeamA: canonicalTeamName(teamA), TeamB: canonicalTeamName(teamB)}
	for _, m := range db.Matches {
		aHome := teamsMatch(m.HomeTeam, teamA)
		bHome := teamsMatch(m.HomeTeam, teamB)
		aAway := teamsMatch(m.AwayTeam, teamA)
		bAway := teamsMatch(m.AwayTeam, teamB)
		if !((aHome && bAway) || (bHome && aAway)) {
			continue
		}
		h.Matches++
		var goalsA, goalsB int
		if aHome {
			goalsA, goalsB = m.HomeGoals, m.AwayGoals
		} else {
			goalsA, goalsB = m.AwayGoals, m.HomeGoals
		}
		h.GoalsA += goalsA
		h.GoalsB += goalsB
		switch {
		case goalsA > goalsB:
			h.WinsA++
		case goalsB > goalsA:
			h.WinsB++
		default:
			h.Draws++
		}
	}
	return h
}

// Standing represents one row of a league table.
type Standing struct {
	Team         string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	GoalDiff     int
	Points       int
}

// ComputeStandings produces a sorted table for a given competition/season.
func (db *DB) ComputeStandings(competition string, season int) []Standing {
	agg := map[string]*Standing{}
	for _, m := range db.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if competition != "" && !strings.Contains(
			strings.ToLower(stripAccents(m.Competition)),
			strings.ToLower(stripAccents(competition)),
		) {
			continue
		}
		for _, side := range []struct {
			name     string
			gf, ga   int
			opponent string
		}{
			{m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam},
			{m.AwayTeam, m.AwayGoals, m.HomeGoals, m.HomeTeam},
		} {
			key := normalizeTeam(side.name)
			if key == "" {
				continue
			}
			s, ok := agg[key]
			if !ok {
				s = &Standing{Team: canonicalTeamName(side.name)}
				agg[key] = s
			}
			s.Matches++
			s.GoalsFor += side.gf
			s.GoalsAgainst += side.ga
			switch {
			case side.gf > side.ga:
				s.Wins++
				s.Points += 3
			case side.gf == side.ga:
				s.Draws++
				s.Points++
			default:
				s.Losses++
			}
		}
	}
	out := make([]Standing, 0, len(agg))
	for _, s := range agg {
		s.GoalDiff = s.GoalsFor - s.GoalsAgainst
		out = append(out, *s)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Points != out[j].Points {
			return out[i].Points > out[j].Points
		}
		if out[i].Wins != out[j].Wins {
			return out[i].Wins > out[j].Wins
		}
		if out[i].GoalDiff != out[j].GoalDiff {
			return out[i].GoalDiff > out[j].GoalDiff
		}
		return out[i].GoalsFor > out[j].GoalsFor
	})
	return out
}

// CompetitionStats summarizes aggregate stats across a set of matches.
type CompetitionStats struct {
	Matches           int
	TotalGoals        int
	HomeGoals         int
	AwayGoals         int
	HomeWins          int
	Draws             int
	AwayWins          int
	AverageGoals      float64
	HomeWinRate       float64
	AverageHomeGoals  float64
	AverageAwayGoals  float64
}

// ComputeCompetitionStats summarizes aggregate stats across matches matching
// the competition+season filter (either may be empty/0).
func (db *DB) ComputeCompetitionStats(competition string, season int) CompetitionStats {
	cs := CompetitionStats{}
	for _, m := range db.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if competition != "" && !strings.Contains(
			strings.ToLower(stripAccents(m.Competition)),
			strings.ToLower(stripAccents(competition)),
		) {
			continue
		}
		cs.Matches++
		cs.HomeGoals += m.HomeGoals
		cs.AwayGoals += m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			cs.HomeWins++
		case m.HomeGoals == m.AwayGoals:
			cs.Draws++
		default:
			cs.AwayWins++
		}
	}
	cs.TotalGoals = cs.HomeGoals + cs.AwayGoals
	if cs.Matches > 0 {
		cs.AverageGoals = float64(cs.TotalGoals) / float64(cs.Matches)
		cs.AverageHomeGoals = float64(cs.HomeGoals) / float64(cs.Matches)
		cs.AverageAwayGoals = float64(cs.AwayGoals) / float64(cs.Matches)
		cs.HomeWinRate = float64(cs.HomeWins) / float64(cs.Matches)
	}
	return cs
}

// BiggestWins returns the matches with the largest goal differential.
func (db *DB) BiggestWins(competition string, season, limit int) []Match {
	var pool []Match
	for _, m := range db.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if competition != "" && !strings.Contains(
			strings.ToLower(stripAccents(m.Competition)),
			strings.ToLower(stripAccents(competition)),
		) {
			continue
		}
		pool = append(pool, m)
	}
	sort.Slice(pool, func(i, j int) bool {
		di := abs(pool[i].HomeGoals - pool[i].AwayGoals)
		dj := abs(pool[j].HomeGoals - pool[j].AwayGoals)
		if di != dj {
			return di > dj
		}
		// Tie-break: more total goals first, then more recent.
		ti := pool[i].HomeGoals + pool[i].AwayGoals
		tj := pool[j].HomeGoals + pool[j].AwayGoals
		if ti != tj {
			return ti > tj
		}
		return pool[i].Date.After(pool[j].Date)
	})
	if limit > 0 && len(pool) > limit {
		pool = pool[:limit]
	}
	return pool
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

// PlayerFilter constrains FindPlayers.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

// FindPlayers returns players matching the filter, sorted by Overall desc.
func (db *DB) FindPlayers(f PlayerFilter) []Player {
	var out []Player
	name := normalizeText(f.Name)
	nat := normalizeText(f.Nationality)
	club := normalizeText(f.Club)
	pos := strings.ToUpper(strings.TrimSpace(f.Position))
	for _, p := range db.Players {
		if name != "" && !strings.Contains(normalizeText(p.Name), name) {
			continue
		}
		if nat != "" && !strings.EqualFold(stripAccents(p.Nationality), stripAccents(f.Nationality)) {
			// Allow substring match too.
			if !strings.Contains(normalizeText(p.Nationality), nat) {
				continue
			}
		}
		if club != "" && !strings.Contains(normalizeText(p.Club), club) {
			continue
		}
		if pos != "" && !strings.EqualFold(p.Position, pos) {
			// Allow grouped positions (e.g. "forward" matches ST/CF/LW/RW).
			if !matchPositionGroup(p.Position, pos) {
				continue
			}
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.Slice(out, func(i, j int) bool {
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

// positionGroups maps a high-level role to the FIFA position codes.
var positionGroups = map[string][]string{
	"GOALKEEPER": {"GK"},
	"GK":         {"GK"},
	"DEFENDER":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"DEFENCE":    {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"MIDFIELDER": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
	"MIDFIELD":   {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
	"FORWARD":    {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
	"FORWARDS":   {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
	"ATTACKER":   {"ST", "CF", "LW", "RW", "LF", "RF"},
	"STRIKER":    {"ST", "CF"},
	"WINGER":     {"LW", "RW", "LM", "RM"},
}

func matchPositionGroup(playerPos, query string) bool {
	q := strings.ToUpper(query)
	codes, ok := positionGroups[q]
	if !ok {
		return false
	}
	pp := strings.ToUpper(playerPos)
	for _, c := range codes {
		if pp == c {
			return true
		}
	}
	return false
}

// FormatMatch returns a human-readable single-line description of a match.
func FormatMatch(m Match) string {
	date := "????-??-??"
	if !m.Date.IsZero() {
		date = m.Date.Format("2006-01-02")
	}
	tail := m.Competition
	if m.Round != "" {
		tail += " Round " + m.Round
	}
	if m.Stage != "" {
		tail += " - " + m.Stage
	}
	return fmt.Sprintf("%s: %s %d-%d %s (%s)",
		date,
		canonicalTeamName(m.HomeTeam), m.HomeGoals,
		m.AwayGoals, canonicalTeamName(m.AwayTeam),
		strings.TrimSpace(tail),
	)
}
