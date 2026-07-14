// stats.go: aggregate analysis over match slices — team records, head-to-head,
// league standings, competition-wide statistics, biggest wins and top-scoring
// teams. These functions are pure (slice in, struct out) so they are easy to
// test; the human-readable formatting lives in format.go.
package soccer

import "sort"

// Record is a win/draw/loss + goals summary for one team over a set of matches.
type Record struct {
	Team         string
	Key          string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

// Points returns league points (3 per win, 1 per draw).
func (r Record) Points() int { return r.Wins*3 + r.Draws }

// GoalDiff returns goals for minus goals against.
func (r Record) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }

// WinRate returns wins as a fraction of matches played (0 if none).
func (r Record) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Matches)
}

// Venue selects which of a team's matches to count.
type Venue int

const (
	VenueAll Venue = iota
	VenueHome
	VenueAway
)

// TeamRecord computes a team's record over the given matches, restricted to the
// chosen venue. teamKey must be a normalized team key.
func TeamRecord(matches []Match, teamKey, display string, venue Venue) Record {
	r := Record{Team: display, Key: teamKey}
	for _, m := range matches {
		home := m.HomeKey == teamKey
		away := m.AwayKey == teamKey
		if !home && !away {
			continue
		}
		if venue == VenueHome && !home {
			continue
		}
		if venue == VenueAway && !away {
			continue
		}
		var gf, ga int
		if home {
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		r.Matches++
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
	return r
}

// H2H is a head-to-head summary between two teams.
type H2H struct {
	TeamA, TeamB        string
	KeyA, KeyB          string
	Matches             int
	WinsA, WinsB, Draws int
	GoalsA, GoalsB      int
}

// HeadToHead computes the head-to-head record between two team keys over the
// given matches (only matches featuring both teams are counted).
func HeadToHead(matches []Match, keyA, keyB, dispA, dispB string) H2H {
	h := H2H{TeamA: dispA, TeamB: dispB, KeyA: keyA, KeyB: keyB}
	for _, m := range matches {
		var ga, gb int
		switch {
		case m.HomeKey == keyA && m.AwayKey == keyB:
			ga, gb = m.HomeGoals, m.AwayGoals
		case m.HomeKey == keyB && m.AwayKey == keyA:
			ga, gb = m.AwayGoals, m.HomeGoals
		default:
			continue
		}
		h.Matches++
		h.GoalsA += ga
		h.GoalsB += gb
		switch {
		case ga > gb:
			h.WinsA++
		case gb > ga:
			h.WinsB++
		default:
			h.Draws++
		}
	}
	return h
}

// Standings builds a league table from the given matches (typically one
// competition + season), sorted by points, goal difference, goals for, wins.
func Standings(matches []Match, display func(key string) string) []Record {
	idx := map[string]*Record{}
	order := []string{}
	touch := func(key string) *Record {
		r, ok := idx[key]
		if !ok {
			r = &Record{Key: key, Team: display(key)}
			idx[key] = r
			order = append(order, key)
		}
		return r
	}
	for _, m := range matches {
		h := touch(m.HomeKey)
		a := touch(m.AwayKey)
		h.Matches++
		a.Matches++
		h.GoalsFor += m.HomeGoals
		h.GoalsAgainst += m.AwayGoals
		a.GoalsFor += m.AwayGoals
		a.GoalsAgainst += m.HomeGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			h.Wins++
			a.Losses++
		case m.AwayGoals > m.HomeGoals:
			a.Wins++
			h.Losses++
		default:
			h.Draws++
			a.Draws++
		}
	}
	table := make([]Record, 0, len(order))
	for _, k := range order {
		table = append(table, *idx[k])
	}
	sort.SliceStable(table, func(i, j int) bool {
		ri, rj := table[i], table[j]
		if ri.Points() != rj.Points() {
			return ri.Points() > rj.Points()
		}
		if ri.Wins != rj.Wins {
			return ri.Wins > rj.Wins
		}
		if ri.GoalDiff() != rj.GoalDiff() {
			return ri.GoalDiff() > rj.GoalDiff()
		}
		if ri.GoalsFor != rj.GoalsFor {
			return ri.GoalsFor > rj.GoalsFor
		}
		return ri.Team < rj.Team
	})
	return table
}

// CompetitionStats summarizes a set of matches as a whole.
type CompetitionStats struct {
	Matches    int
	TotalGoals int
	HomeWins   int
	AwayWins   int
	Draws      int
}

// GoalsPerMatch returns the average goals per match (0 if no matches).
func (c CompetitionStats) GoalsPerMatch() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.TotalGoals) / float64(c.Matches)
}

// HomeWinRate returns the fraction of matches won by the home side.
func (c CompetitionStats) HomeWinRate() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.HomeWins) / float64(c.Matches)
}

// Summarize computes aggregate statistics for the given matches.
func Summarize(matches []Match) CompetitionStats {
	var c CompetitionStats
	for _, m := range matches {
		c.Matches++
		c.TotalGoals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			c.HomeWins++
		case m.AwayGoals > m.HomeGoals:
			c.AwayWins++
		default:
			c.Draws++
		}
	}
	return c
}

// BiggestWins returns up to limit matches with the largest goal margin,
// ordered by margin descending then date.
func BiggestWins(matches []Match, limit int) []Match {
	out := make([]Match, len(matches))
	copy(out, matches)
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Margin() != out[j].Margin() {
			return out[i].Margin() > out[j].Margin()
		}
		return out[i].Date.After(out[j].Date)
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// TopScoringTeams ranks teams by total goals scored over the given matches.
func TopScoringTeams(matches []Match, display func(key string) string, limit int) []Record {
	table := Standings(matches, display)
	sort.SliceStable(table, func(i, j int) bool {
		if table[i].GoalsFor != table[j].GoalsFor {
			return table[i].GoalsFor > table[j].GoalsFor
		}
		return table[i].Team < table[j].Team
	})
	if limit > 0 && len(table) > limit {
		table = table[:limit]
	}
	return table
}
