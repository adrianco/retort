// Match queries: lookup, team records, head-to-head, standings and aggregates.

package main

import (
	"sort"
	"strings"
	"time"
)

// MatchFilter selects fixtures. Zero values mean "no constraint".
type MatchFilter struct {
	Team        string // matches involving this team
	Opponent    string // combined with Team: matches between the two
	Venue       string // "home", "away" or "" (either); only meaningful with Team
	Competition string // substring match on competition name, case/accent-insensitive
	Season      int
	From        time.Time
	To          time.Time
}

// Side returns which side the team played in m: "home", "away" or "".
func sideOf(m Match, t TeamName) string {
	if t.Matches(m.Home) {
		return "home"
	}
	if t.Matches(m.Away) {
		return "away"
	}
	return ""
}

// FindMatches returns fixtures matching f, most recent first.
func (ds *Dataset) FindMatches(f MatchFilter) []Match {
	team := ParseTeam(f.Team, "")
	opp := ParseTeam(f.Opponent, "")
	comp := stripAccents(f.Competition)

	var out []Match
	for _, m := range ds.Matches {
		if f.Team != "" {
			side := sideOf(m, team)
			if side == "" {
				continue
			}
			if f.Venue != "" && side != f.Venue {
				continue
			}
			if f.Opponent != "" {
				other := m.Away
				if side == "away" {
					other = m.Home
				}
				if !opp.Matches(other) {
					continue
				}
			}
		} else if f.Opponent != "" {
			// Opponent without a team: match either side.
			if !opp.Matches(m.Home) && !opp.Matches(m.Away) {
				continue
			}
		}
		if comp != "" && !strings.Contains(stripAccents(m.Competition), comp) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !f.From.IsZero() && m.Date.Before(f.From) {
			continue
		}
		if !f.To.IsZero() && m.Date.After(f.To) {
			continue
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	return out
}

// Record is a win/draw/loss summary from one team's perspective.
type Record struct {
	Played, Wins, Draws, Losses int
	GoalsFor, GoalsAgainst      int
}

func (r Record) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Played) * 100
}

// addResult folds one match (from the team's side) into a record.
func (r *Record) add(gf, ga int) {
	r.Played++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	switch {
	case gf > ga:
		r.Wins++
	case gf < ga:
		r.Losses++
	default:
		r.Draws++
	}
}

// TeamRecord summarises matches for a team (optionally filtered by venue, season, competition).
func (ds *Dataset) TeamRecord(f MatchFilter) (Record, []Match) {
	team := ParseTeam(f.Team, "")
	var rec Record
	matches := ds.FindMatches(f)
	for _, m := range matches {
		switch sideOf(m, team) {
		case "home":
			rec.add(m.HomeGoals, m.AwayGoals)
		case "away":
			rec.add(m.AwayGoals, m.HomeGoals)
		}
	}
	return rec, matches
}

// HeadToHead returns a's record against b (from a's perspective) and the
// fixtures between them, most recent first.
func (ds *Dataset) HeadToHead(a, b string) (Record, []Match) {
	ta := ParseTeam(a, "")
	tb := ParseTeam(b, "")
	var rec Record
	var played []Match
	for _, m := range ds.FindMatches(MatchFilter{Team: a, Opponent: b}) {
		switch {
		case ta.Matches(m.Home) && tb.Matches(m.Away):
			rec.add(m.HomeGoals, m.AwayGoals)
		case ta.Matches(m.Away) && tb.Matches(m.Home):
			rec.add(m.AwayGoals, m.HomeGoals)
		default:
			continue
		}
		played = append(played, m)
	}
	return rec, played
}

// StandingRow is one line of a league table.
type StandingRow struct {
	Team string
	Record
	Points int
}

// GoalDiff returns goals for minus goals against.
func (s StandingRow) GoalDiff() int { return s.GoalsFor - s.GoalsAgainst }

// Standings builds a points table (3 for a win, 1 for a draw) for a competition and season.
// The table is sorted by points, goal difference, goals for, then name.
func (ds *Dataset) Standings(competition string, season int) []StandingRow {
	// Some rows carry a state code and others don't (e.g. BR-Football). Where a
	// base name is seen with exactly one state, stateless rows join that club.
	states := map[string]map[string]bool{}
	ms := ds.FindMatches(MatchFilter{Competition: competition, Season: season})
	for _, m := range ms {
		for _, t := range []TeamName{m.Home, m.Away} {
			if t.State != "" {
				if states[t.Base] == nil {
					states[t.Base] = map[string]bool{}
				}
				states[t.Base][t.State] = true
			}
		}
	}
	identity := func(t TeamName) string {
		if t.State == "" && len(states[t.Base]) == 1 {
			for st := range states[t.Base] {
				return t.Base + "|" + st
			}
		}
		return t.Key()
	}

	rows := map[string]*StandingRow{}
	add := func(t TeamName, gf, ga int) {
		k := identity(t)
		r, ok := rows[k]
		if !ok {
			r = &StandingRow{Team: displayName(t)}
			rows[k] = r
		}
		r.add(gf, ga)
		switch {
		case gf > ga:
			r.Points += 3
		case gf == ga:
			r.Points++
		}
	}

	for _, m := range ms {
		add(m.Home, m.HomeGoals, m.AwayGoals)
		add(m.Away, m.AwayGoals, m.HomeGoals)
	}

	out := make([]StandingRow, 0, len(rows))
	for _, r := range rows {
		out = append(out, *r)
	}
	sort.Slice(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.GoalDiff() != b.GoalDiff() {
			return a.GoalDiff() > b.GoalDiff()
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	return out
}

// displayName gives a readable club name: the raw dataset spelling without the state suffix.
func displayName(t TeamName) string {
	raw := strings.TrimSpace(t.Raw)
	if m := stateSuffixRe.FindStringSubmatch(raw); m != nil && brazilianStates[m[1]] {
		raw = stateSuffixRe.ReplaceAllString(raw, "")
	}
	return strings.TrimSpace(raw)
}

// LeagueStats summarises goals and results for a competition/season.
type LeagueStats struct {
	Matches       int
	Goals         int
	HomeWins      int
	Draws         int
	AwayWins      int
	GoalsPerMatch float64
	HomeWinPct    float64
	DrawPct       float64
	AwayWinPct    float64
}

// Aggregate computes LeagueStats for the matches selected by f.
func (ds *Dataset) Aggregate(f MatchFilter) LeagueStats {
	var s LeagueStats
	for _, m := range ds.FindMatches(f) {
		s.Matches++
		s.Goals += m.HomeGoals + m.AwayGoals
		switch m.Result() {
		case "H":
			s.HomeWins++
		case "A":
			s.AwayWins++
		default:
			s.Draws++
		}
	}
	if s.Matches > 0 {
		n := float64(s.Matches)
		s.GoalsPerMatch = float64(s.Goals) / n
		s.HomeWinPct = float64(s.HomeWins) / n * 100
		s.DrawPct = float64(s.Draws) / n * 100
		s.AwayWinPct = float64(s.AwayWins) / n * 100
	}
	return s
}

// BiggestWins returns the n matches with the largest winning margin, ties broken by date (newest first).
func (ds *Dataset) BiggestWins(f MatchFilter, n int) []Match {
	matches := ds.FindMatches(f)
	margin := func(m Match) int {
		d := m.HomeGoals - m.AwayGoals
		if d < 0 {
			return -d
		}
		return d
	}
	sort.SliceStable(matches, func(i, j int) bool { return margin(matches[i]) > margin(matches[j]) })
	if n > 0 && len(matches) > n {
		matches = matches[:n]
	}
	return matches
}
