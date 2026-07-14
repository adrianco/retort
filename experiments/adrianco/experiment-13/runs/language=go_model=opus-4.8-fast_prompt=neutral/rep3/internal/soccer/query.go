// query.go implements the query engine: match search, head-to-head, team
// records, league standings, player search and aggregate statistics.
package soccer

import (
	"sort"
	"strings"
	"time"
)

// teamKeyMatches reports whether a stored team key satisfies a user query key.
// It allows exact, full-name ("sport club corinthians paulista" contains
// "corinthians") and abbreviation matches in either direction.
func teamKeyMatches(stored, query string) bool {
	if query == "" {
		return false
	}
	if stored == query {
		return true
	}
	return strings.Contains(stored, query) || strings.Contains(query, stored)
}

// MatchFilter describes a match search.
type MatchFilter struct {
	Team        string // matches either side unless HomeOnly/AwayOnly set
	Opponent    string // optional second team
	HomeOnly    bool   // restrict Team to the home side
	AwayOnly    bool   // restrict Team to the away side
	Competition string
	Season      int // 0 = any
	Start, End  time.Time
	Limit       int // 0 = no limit
}

// FindMatches returns matches satisfying the filter, most recent first.
func (db *DB) FindMatches(f MatchFilter) []Match {
	teamKey := TeamKey(f.Team)
	oppKey := TeamKey(f.Opponent)

	var out []Match
	for _, m := range db.Matches {
		if f.Competition != "" && !competitionMatches(m.Competition, f.Competition) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !f.Start.IsZero() && (!m.HasDate || m.Date.Before(f.Start)) {
			continue
		}
		if !f.End.IsZero() && (!m.HasDate || m.Date.After(f.End)) {
			continue
		}
		if teamKey != "" && !matchInvolvesTeam(m, teamKey, f.HomeOnly, f.AwayOnly) {
			continue
		}
		if oppKey != "" && !(teamKeyMatches(m.HomeKey, oppKey) || teamKeyMatches(m.AwayKey, oppKey)) {
			continue
		}
		out = append(out, m)
	}

	sortMatchesByDateDesc(out)
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func matchInvolvesTeam(m Match, key string, homeOnly, awayOnly bool) bool {
	switch {
	case homeOnly:
		return teamKeyMatches(m.HomeKey, key)
	case awayOnly:
		return teamKeyMatches(m.AwayKey, key)
	default:
		return teamKeyMatches(m.HomeKey, key) || teamKeyMatches(m.AwayKey, key)
	}
}

func sortMatchesByDateDesc(ms []Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		if ms[i].HasDate != ms[j].HasDate {
			return ms[i].HasDate // dated matches first
		}
		if ms[i].Date.Equal(ms[j].Date) {
			return ms[i].Season > ms[j].Season
		}
		return ms[i].Date.After(ms[j].Date)
	})
}

// Record is a win/draw/loss summary from one team's perspective.
type Record struct {
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

// WinRate returns wins as a percentage of games played.
func (r Record) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return 100 * float64(r.Wins) / float64(r.Played)
}

// GoalDiff returns goals for minus goals against.
func (r Record) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }

// Points returns league points (3 per win, 1 per draw).
func (r Record) Points() int { return 3*r.Wins + r.Draws }

// TeamRecord computes a team's record under the given filter (season,
// competition, home/away restriction).
func (db *DB) TeamRecord(f MatchFilter) Record {
	teamKey := TeamKey(f.Team)
	rec := Record{Team: db.queryDisplay(f.Team, teamKey)}
	for _, m := range db.FindMatches(f) {
		if !m.HasScore {
			continue
		}
		home := teamKeyMatches(m.HomeKey, teamKey)
		away := teamKeyMatches(m.AwayKey, teamKey)
		if home == away { // neither or (defensively) both
			if !home {
				continue
			}
		}
		gf, ga := m.HomeGoals, m.AwayGoals
		if away && !home {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		rec.Played++
		rec.GoalsFor += gf
		rec.GoalsAgainst += ga
		switch {
		case gf > ga:
			rec.Wins++
		case gf < ga:
			rec.Losses++
		default:
			rec.Draws++
		}
	}
	return rec
}

// H2H is a head-to-head summary between two teams.
type H2H struct {
	TeamA, TeamB string
	AWins, BWins int
	Draws        int
	AGoals       int
	BGoals       int
	Matches      []Match
}

// HeadToHead returns every match between teamA and teamB plus the aggregate
// record from teamA's perspective.
func (db *DB) HeadToHead(teamA, teamB string) H2H {
	aKey, bKey := TeamKey(teamA), TeamKey(teamB)
	h := H2H{TeamA: db.queryDisplay(teamA, aKey), TeamB: db.queryDisplay(teamB, bKey)}
	for _, m := range db.Matches {
		aHome := teamKeyMatches(m.HomeKey, aKey)
		bHome := teamKeyMatches(m.HomeKey, bKey)
		aAway := teamKeyMatches(m.AwayKey, aKey)
		bAway := teamKeyMatches(m.AwayKey, bKey)
		if !((aHome && bAway) || (bHome && aAway)) {
			continue
		}
		h.Matches = append(h.Matches, m)
		if !m.HasScore {
			continue
		}
		// Goals/result from team A's perspective.
		var ag, bg int
		if aHome {
			ag, bg = m.HomeGoals, m.AwayGoals
		} else {
			ag, bg = m.AwayGoals, m.HomeGoals
		}
		h.AGoals += ag
		h.BGoals += bg
		switch {
		case ag > bg:
			h.AWins++
		case bg > ag:
			h.BWins++
		default:
			h.Draws++
		}
	}
	sortMatchesByDateDesc(h.Matches)
	return h
}

// Standings computes the league table for a competition and season.
func (db *DB) Standings(competition string, season int) []Record {
	agg := map[string]*Record{}
	get := func(key string) *Record {
		r, ok := agg[key]
		if !ok {
			r = &Record{Team: db.TeamDisplay(key)}
			agg[key] = r
		}
		return r
	}
	for _, m := range db.Matches {
		if !competitionMatches(m.Competition, competition) || m.Season != season || !m.HasScore {
			continue
		}
		home, away := get(m.HomeKey), get(m.AwayKey)
		home.Played++
		away.Played++
		home.GoalsFor += m.HomeGoals
		home.GoalsAgainst += m.AwayGoals
		away.GoalsFor += m.AwayGoals
		away.GoalsAgainst += m.HomeGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			home.Wins++
			away.Losses++
		case m.AwayGoals > m.HomeGoals:
			away.Wins++
			home.Losses++
		default:
			home.Draws++
			away.Draws++
		}
	}

	table := make([]Record, 0, len(agg))
	for _, r := range agg {
		table = append(table, *r)
	}
	sort.SliceStable(table, func(i, j int) bool {
		a, b := table[i], table[j]
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDiff() != b.GoalDiff() {
			return a.GoalDiff() > b.GoalDiff()
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	return table
}

// PlayerFilter describes a player search.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int // 0 = default applied by caller
}

// SearchPlayers returns players matching the filter, highest Overall first.
func (db *DB) SearchPlayers(f PlayerFilter) []Player {
	name := normText(f.Name)
	nat := normText(f.Nationality)
	club := normText(f.Club)
	pos := normText(f.Position)

	var out []Player
	for _, p := range db.Players {
		if name != "" && !strings.Contains(normText(p.Name), name) {
			continue
		}
		if nat != "" && !strings.Contains(normText(p.Nationality), nat) {
			continue
		}
		if club != "" && !strings.Contains(normText(p.Club), club) {
			continue
		}
		if pos != "" && !strings.EqualFold(p.Position, f.Position) && !strings.Contains(normText(p.Position), pos) {
			continue
		}
		if f.MinOverall != 0 && p.Overall < f.MinOverall {
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

// Stats aggregates competition-level statistics.
type Stats struct {
	Competition string
	Season      int // 0 = all seasons
	Matches     int
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
	BiggestWins []Match // largest goal margins, descending
}

// AvgGoals returns the mean number of goals per match.
func (s Stats) AvgGoals() float64 {
	if s.Matches == 0 {
		return 0
	}
	return float64(s.TotalGoals) / float64(s.Matches)
}

// HomeWinRate returns home wins as a percentage of decided + drawn matches.
func (s Stats) HomeWinRate() float64 {
	if s.Matches == 0 {
		return 0
	}
	return 100 * float64(s.HomeWins) / float64(s.Matches)
}

// CompetitionStats computes aggregate statistics for a competition (and
// optional season; pass 0 for all seasons). An empty competition aggregates
// across every competition.
func (db *DB) CompetitionStats(competition string, season int, topN int) Stats {
	s := Stats{Competition: competition, Season: season}
	var scored []Match
	for _, m := range db.Matches {
		if competition != "" && !competitionMatches(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if !m.HasScore {
			continue
		}
		s.Matches++
		s.TotalGoals += m.HomeGoals + m.AwayGoals
		switch m.Winner() {
		case "home":
			s.HomeWins++
		case "away":
			s.AwayWins++
		default:
			s.Draws++
		}
		scored = append(scored, m)
	}
	if topN <= 0 {
		topN = 10
	}
	sort.SliceStable(scored, func(i, j int) bool {
		mi := absInt(scored[i].HomeGoals - scored[i].AwayGoals)
		mj := absInt(scored[j].HomeGoals - scored[j].AwayGoals)
		if mi != mj {
			return mi > mj
		}
		gi := scored[i].HomeGoals + scored[i].AwayGoals
		gj := scored[j].HomeGoals + scored[j].AwayGoals
		return gi > gj
	})
	if len(scored) > topN {
		scored = scored[:topN]
	}
	s.BiggestWins = scored
	return s
}

func absInt(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
